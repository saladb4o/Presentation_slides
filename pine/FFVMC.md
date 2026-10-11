# FFVMC: Monte Carlo library

Publish this as a new version of your private library FFVMC (version 2: it now also holds the statistics helpers and the scenario draws moved out of FFV Pro), then republish FFV Pro, which imports FFVMC/2. Copy everything inside the code block over the library in the Pine Editor.

```pine
//@version=6
// @description Companion library for Fundamental Fair Value Pro: the Monte Carlo engine (quasi-random
// lattice, the history pools, block length, bootstrap paths and draws) and the forecast statistics
// (rate-width variance, MIDAS, LASSO). It was split out of FFVLib to keep each library under the
// compile-size limit. Publish it as a PRIVATE library named FFVMC; after any change, publish a new
// version and bump the number in the indicator's import line.
library('FFVMC')
// ==========================================
// MONTE CARLO: the lattice and its random shifts, the history pool, the block length, the paths
// ==========================================
// @type Wichmann-Hill (2006) generator: four multiplicative congruential generators, period about 2^121; it draws the lattice's random shift (f_lat). Plain arithmetic, so a copy in any language gives the same numbers from the same seeds.
// @field a First state.
// @field b Second state.
// @field c Third state.
// @field d Fourth state.
export type WH
    float a = 123456789.0
    float b = 987654321.0
    float c = 192837465.0
    float d = 564738291.0
// x mod m for whole numbers below 2^53 (the products here stay under 1.1e14, so this is exact).
f_imod(float x, float m) =>
    x - m * math.floor(x / m)
// @function The next uniform number in [0, 1).
export method nxt(WH g) =>
    g.a := f_imod(11600.0 * g.a, 2147483579.0)
    g.b := f_imod(47003.0 * g.b, 2147483543.0)
    g.c := f_imod(23000.0 * g.c, 2147483423.0)
    g.d := f_imod(33000.0 * g.d, 2147483123.0)
    float w = g.a / 2147483579.0 + g.b / 2147483543.0 + g.c / 2147483423.0 + g.d / 2147483123.0
    w - math.floor(w)
// @type A randomly shifted rank-1 lattice (quasi-Monte Carlo): point i's coordinate j is frac(i z_j / 1024 + shift_j), z the 1,024-point generating vector of Cools, Kuo and Nuyens (2006, order-2 weights; Kuo's lattice-22001-1024), one random shift for all points (Cranley and Patterson 1976). Each path reads 2h - 1 fixed coordinates of its point (start, then a jump and a pick per step), so the 1,024 paths are spread evenly instead of at random.
// @field z Generating vector (28 coordinates: four paths of 7).
// @field sh The shift, one per coordinate.
// @field i The point (the draw).
// @field j The next coordinate.
export type LP
    array<float> z
    array<float> sh
    int i = 0
    int j = 0
// @function The lattice for the draws: the shift from the Wichmann-Hill generator at its fixed seeds, so a reload gives the same points.
export f_lat() =>
    g = WH.new()
    sh = array.new_float()
    for j = 1 to 28
        sh.push(g.nxt())
    LP.new(array.from(1.0, 275, 451, 245, 215, 367, 247, 363, 491, 143, 269, 359, 397, 187, 497, 221, 225, 393, 91, 185, 395, 87, 335, 179, 299, 125, 193, 457), sh)
// @function The current point's next coordinate, in [0, 1).
export method nxt(LP p) =>
    float x = p.i * p.z.get(p.j) / 1024.0 + p.sh.get(p.j)
    p.j += 1
    x - math.floor(x)
// @function The quarters the Monte Carlo draws from: the n quarters before the open one (oldest first) whose rate, stage-1 growth and terminal growth (columns c0 to c0 + 2) are known at that quarter and the one before, and whose rate source (c0 + 3) and growth parts (c0 + 4) did not change between them. A change across a switch is a data artefact, not a revision: it is skipped and counted.
// @returns [lags, rate changes, growth changes, terminal changes, skipped].
export f_pool(matrix<float> hm, int hq, int n, int c0) =>
    lg = array.new_int()
    dr = array.new_float()
    dg = array.new_float()
    dt = array.new_float()
    int sk = 0
    int top = math.min(n, math.min(hq, 127) - 1)
    if top >= 1
        for lag = top to 1
            a = hm.row((hq - lag) % 128)
            b = hm.row((hq - lag - 1) % 128)
            ok = true
            for c = c0 to c0 + 2
                ok := ok and not na(a.get(c)) and not na(b.get(c))
            if ok and a.get(c0 + 3) == b.get(c0 + 3) and a.get(c0 + 4) == b.get(c0 + 4)
                lg.push(lag)
                dr.push(a.get(c0) - b.get(c0))
                dg.push(a.get(c0 + 1) - b.get(c0 + 1))
                dt.push(a.get(c0 + 2) - b.get(c0 + 2))
            else if ok
                sk += 1
    [lg, dr, dg, dt, sk]
// Sum of x[i0 + t] * x[j0 + t] for t = 0 .. len - 1.
f_dot(array<float> x, int i0, int j0, int len) =>
    float s = 0.0
    if len > 0
        for t = 0 to len - 1
            s += x.get(i0 + t) * x.get(j0 + t)
    s
// @function Optimal stationary-bootstrap block length of one series (Politis and White 2004, with the Patton, Politis and White 2009 correction), computed as the Python arch package does. na when it cannot be computed (a series that never moves).
export f_pwb(array<float> x) =>
    int n = x.size()
    float mu = x.avg()
    e = array.new_float()
    for v in x
        e.push(v - mu)
    int kn = math.max(5, int(math.floor(math.log10(n))))
    int mmax = int(math.ceil(math.sqrt(n))) + kn
    float cv = 2 * math.sqrt(math.log10(n) / n)
    acv = array.new_float(mmax + 1, 0.0)
    ac = array.new_float(mmax + 1, na)
    int om = -1
    for i = 0 to mmax
        float v1 = f_dot(e, i + 1, i + 1, n - i - 1)
        float v2 = f_dot(e, 0, 0, n - i - 1)
        float cp = f_dot(e, i, 0, n - i)
        acv.set(i, cp / n)
        ac.set(i, v1 * v2 > 0 ? math.abs(cp) / math.sqrt(v1 * v2) : na)
        if i >= kn and om < 0
            all_in = true
            for j = i - kn to i - 1
                all_in := all_in and ac.get(j) < cv
            om := all_in ? i - kn : -1
    int m = math.min(om >= 0 ? 2 * math.max(om, 1) : mmax, mmax)
    float g = 0.0
    float lr = acv.get(0)
    for k = 1 to m
        float lam = k / m <= 0.5 ? 1.0 : 2 * (1 - k / m)
        g += 2 * lam * k * acv.get(k)
        lr += 2 * lam * acv.get(k)
    float b = lr != 0 ? math.pow(2 * g * g / (2 * lr * lr), 1.0 / 3) * math.pow(n, 1.0 / 3) : na
    b > 0 ? b : na
// @function The block length for the joint draws: the largest of the three series' optimal lengths, n^(1/3) when none can be computed, held inside [1, ceil(min(3 sqrt(n), n / 3))] (the upper bound the method uses).
export f_blen(array<float> a, array<float> b, array<float> c) =>
    int n = a.size()
    float x = math.max(nz(f_pwb(a), 0), nz(f_pwb(b), 0), nz(f_pwb(c), 0))
    float bmax = math.ceil(math.min(3 * math.sqrt(n), n / 3.0))
    math.max(1.0, math.min(x > 0 ? x : math.pow(n, 1.0 / 3), bmax))
// @function Each pool position's successor: the next position when it holds the very next quarter (its lag one less), else -1. A pool that skips quarters (a missing value, a source switch) has gaps, and its last quarter has no successor: a path does not step across either (it jumped from the newest quarter back to the oldest, or over the skipped ones), it restarts at a random quarter.
// @param lg The pool's lags, oldest first.
// @returns An array of positions (or -1), one per pool entry.
export f_next(array<int> lg) =>
    nx = array.new_int()
    int n = lg.size()
    for i = 0 to n - 1
        nx.push(i + 1 < n and lg.get(i + 1) == lg.get(i) - 1 ? i + 1 : -1)
    nx
// @function One stationary-bootstrap path (Politis and Romano 1994) of h positions in a pool (successors nx, f_next) from lattice point g.i, coordinates g.j on: a random start, then each step either moves to the next quarter or, with probability 1 / blen or where there is no next quarter (f_next), jumps to a new random quarter. Each step reads its jump and pick coordinates whether it jumps or not, so every path uses the same 2h - 1 coordinates.
export f_path(LP g, array<int> nx, float blen, int h) =>
    out = array.new_int()
    int n = nx.size()
    int i = int(math.floor(g.nxt() * n))
    out.push(i)
    if h > 1
        for s = 2 to h
            float uj = g.nxt()
            float up = g.nxt()
            i := uj < 1.0 / blen or nx.get(i) < 0 ? int(math.floor(up * n)) : nx.get(i)
            out.push(i)
    out
// @function One driver's own pool, for when the joint pool is too short: the quarterly changes of column c over the n quarters before the open one (oldest first), where c is known at that quarter and the one before and the switch column cs (rate source or growth parts) did not change between them.
// @returns [changes, their lags].
export f_pool1(matrix<float> hm, int hq, int n, int c, int cs) =>
    ch = array.new_float()
    lg = array.new_int()
    int top = math.min(n, math.min(hq, 127) - 1)
    if top >= 1
        for lag = top to 1
            int ra = (hq - lag) % 128
            int rb = (hq - lag - 1) % 128
            float a = hm.get(ra, c)
            float b = hm.get(rb, c)
            if not na(a) and not na(b) and hm.get(ra, cs) == hm.get(rb, cs)
                ch.push(a - b)
                lg.push(lag)
    [ch, lg]
// @function The quarterly changes of a year-on-year growth rate built from column c (a TTM total, such as revenue): growth at a quarter is its total against the one 4 quarters before, and each change needs the total at that quarter, the one before, and 4 quarters before each (non-zero).
// @returns [changes, their lags], oldest first.
export f_pool_yoy(matrix<float> hm, int hq, int n, int c) =>
    ch = array.new_float()
    lg = array.new_int()
    int top = math.min(n, math.min(hq, 127) - 5)
    if top >= 1
        for lag = top to 1
            float a0 = hm.get((hq - lag) % 128, c)
            float a4 = hm.get((hq - lag - 4) % 128, c)
            float b0 = hm.get((hq - lag - 1) % 128, c)
            float b4 = hm.get((hq - lag - 5) % 128, c)
            if not na(a0) and not na(a4) and not na(b0) and not na(b4) and a4 != 0 and b4 != 0
                ch.push((a0 - a4) / math.abs(a4) - (b0 - b4) / math.abs(b4))
                lg.push(lag)
    [ch, lg]
// @function A series less its own average (centred bootstrap, Hall and Wilson 1991): the draws then keep how much a driver has moved, not the direction it drifted in over the sample, so a one-way trend does not take away a side.
// @returns A new array.
export f_demean(array<float> x) =>
    out = array.new_float()
    float mu = x.size() > 0 ? x.avg() : na
    for v in x
        out.push(v - mu)
    out
// The first index whose cumulative weight passes u (a share of the total).
f_pick(array<float> cw, float u) =>
    float x = u * cw.last()
    int i = 0
    while i < cw.size() - 1 and cw.get(i) <= x
        i += 1
    i
// @function Cumulative weights.
export f_cum(array<float> w) =>
    cw = array.new_float()
    float s = 0.0
    for y in w
        s += y
        cw.push(s)
    cw
// @function A stationary-bootstrap path whose start and each jump (including where there is no next quarter, f_next) fall on a quarter with probability its weight (cumulative weights cw); otherwise as f_path (the same fixed coordinates).
export f_wpath(LP g, array<float> cw, array<int> nx, float blen, int h) =>
    out = array.new_int()
    int i = f_pick(cw, g.nxt())
    out.push(i)
    if h > 1
        for s = 2 to h
            float uj = g.nxt()
            float up = g.nxt()
            i := uj < 1.0 / blen or nx.get(i) < 0 ? f_pick(cw, up) : nx.get(i)
            out.push(i)
    out
// @function A series less its mean under the weighted paths: the average over the h steps of where a path is (step 1 the weights, each next step a jump to the weights with probability 1 / blen, or where there is no next quarter (nx, f_next), else a move to the next quarter), so the draws are centred on the paths they are summed along.
// @returns A new array.
export f_wdemean(array<float> x, array<float> w, array<int> nx, float blen, int h) =>
    int n = x.size()
    float sw = w.sum()
    p = array.new_float()
    for y in w
        p.push(y / sw)
    float mu = 0.0
    for s = 1 to h
        if s > 1
            // Mass that jumps: 1 / blen of all of it, and the rest of it at a quarter with no successor.
            float jm = 0.0
            np = array.new_float(n, 0.0)
            for i = 0 to n - 1
                int k = nx.get(i)
                jm += p.get(i) * (k < 0 ? 1.0 : 1 / blen)
                if k >= 0
                    np.set(k, np.get(k) + (1 - 1 / blen) * p.get(i))
            for i = 0 to n - 1
                np.set(i, np.get(i) + jm * w.get(i) / sw)
            p := np
        for i = 0 to n - 1
            mu += p.get(i) * x.get(i) / h
    out = array.new_float()
    for v in x
        out.push(v - mu)
    out
// @function nd draws of one driver on its own: the changes centred on their mean under the paths (f_wdemean, equal weights), each draw the sum along an h-step stationary-bootstrap path (f_path; draw i on lattice point i from coordinate j0), the block length that series' own optimal one.
// @param lg The changes' lags (oldest first), for the pool's gaps (f_next).
// @returns The nd sums, in draw order.
export f_draws1(LP g, int j0, array<float> ch, array<int> lg, int nd, int h) =>
    out = array.new_float()
    float bl = f_blen(ch, ch, ch)
    nx = f_next(lg)
    x = f_wdemean(ch, array.new_float(ch.size(), 1.0), nx, bl, h)
    for i = 0 to nd - 1
        g.i := i, g.j := j0
        float s = 0.0
        for j in f_path(g, nx, bl, h)
            s += x.get(j)
        out.push(s)
    out
// @function Variance of a weekly series' one-year (q-week) change, from overlapping windows with the Lo and MacKinlay (1988) small-sample correction: the changes are centred on their mean (as the bootstrap's are) and the sum of squares divided by m (1 - q / T), m windows from T weekly steps. A window whose two ends carry a different source code, or a stand-in code (2, 4), is left out, as the quarterly pool skips a source switch.
// @returns [variance of the one-year change (na under q windows), windows used].
export f_yvar(array<float> x, array<float> s, int q) =>
    d = array.new_float()
    int n = x.size()
    if n > q
        for t = q to n - 1
            float a = x.get(t)
            float b = x.get(t - q)
            float sa = s.get(t)
            if not na(a) and not na(b) and sa == s.get(t - q) and sa != 2 and sa != 4
                d.push(a - b)
    int m = d.size()
    float v = na
    if m >= q
        float mu = d.avg()
        float ss = 0.0
        for y in d
            ss += (y - mu) * (y - mu)
        v := ss / (m * (1.0 - float(q) / (n - 1)))
    [v, m]
// @function MIDAS summary of the last 13 weekly changes of a series (Ball and Ghysels 2018; Babii, Ball, Ghysels and Striaukas 2023): the changes projected on the first three shifted Legendre polynomials over the lag position (0 = the latest week, 1 = 13 weeks back), so a quarter of weekly data enters as three numbers: the level, the tilt and the bend of the recent path.
// @param a The weekly values, oldest first (14 or more).
// @param lg true: log changes (prices); false: plain changes (a rate).
// @returns [p0, p1, p2], na when a value is missing.
export f_midas(array<float> a, bool lg) =>
    float p0 = na
    float p1 = na
    float p2 = na
    int n = a.size()
    if n >= 14
        float s0 = 0.0
        float s1 = 0.0
        float s2 = 0.0
        bool ok = true
        for j = 0 to 12
            float x1 = a.get(n - 1 - j)
            float x0 = a.get(n - 2 - j)
            if na(x1) or na(x0) or (lg and (x1 <= 0 or x0 <= 0))
                ok := false
            else
                float d = lg ? math.log(x1 / x0) : x1 - x0
                float t = j / 12.0
                s0 += d
                s1 += d * (2 * t - 1)
                s2 += d * (6 * t * t - 6 * t + 1)
        if ok
            p0 := s0 / 13
            p1 := s1 / 13
            p2 := s2 / 13
    [p0, p1, p2]
// @function LASSO (Tibshirani 1996) of the year-ahead log growth of a stored series on p stored features, fitted by coordinate descent on standardised features with warm starts down a 20-step penalty path (lambda_max to 1% of it when rows are fewer than features, else 0.01%), the penalty picked by BIC (n log(RSS / n) + df log n; the path starts at no feature, the plain mean). Point in time: a row's target is the series 4 quarters later over the series in that row, so only rows 4 or more quarters back train. A feature missing now leaves; while fewer than nmin rows have every feature, the feature missing in most rows leaves.
// @param v The store's matrix (a ring of 128 rows).
// @param q The store's open row count.
// @param c0 First feature column.
// @param p Number of feature columns.
// @param cy The series column (TTM revenue).
// @param nmin Fewest training rows.
// @param nmax Most training rows (the latest).
// @returns [mean target, p coefficients (standardised), p means, p standard deviations]; empty when under nmin rows.
export f_lasso(matrix<float> v, int q, int c0, int p, int cy, int nmin, int nmax) =>
    out = array.new_float()
    if q >= 4 + nmin - 1
        cur = v.row(q % 128)
        keep = array.new_bool(p, false)
        for j = 0 to p - 1
            keep.set(j, not na(cur.get(c0 + j)))
        lags = array.new_int()
        ys = array.new_float()
        for lag = 4 to math.min(math.min(q, 127), nmax + 3)
            float a = v.get((q - lag + 4) % 128, cy)
            float b = v.get((q - lag) % 128, cy)
            if a > 0 and b > 0
                lags.push(lag)
                ys.push(math.log(a / b))
        int nt = lags.size()
        // Drop features until enough rows have all of them.
        rows = array.new_int()
        bool go = nt >= nmin
        while go
            rows.clear()
            miss = array.new_int(p, 0)
            for i = 0 to nt - 1
                bool full = true
                for j = 0 to p - 1
                    if keep.get(j) and na(v.get((q - lags.get(i)) % 128, c0 + j))
                        full := false
                        miss.set(j, miss.get(j) + 1)
                if full
                    rows.push(i)
            int jw = -1
            for j = 0 to p - 1
                if keep.get(j) and miss.get(j) > 0 and (jw < 0 or miss.get(j) >= miss.get(jw))
                    jw := j
            if rows.size() >= nmin or jw < 0
                go := false
            else
                keep.set(jw, false)
        int n = rows.size()
        if nt >= nmin and n >= nmin
            x = matrix.new<float>(n, p, 0.0)
            y = array.new_float()
            for i = 0 to n - 1
                int r = (q - lags.get(rows.get(i))) % 128
                y.push(ys.get(rows.get(i)))
                for j = 0 to p - 1
                    if keep.get(j)
                        x.set(i, j, v.get(r, c0 + j))
            float ym = y.avg()
            mu = array.new_float(p, 0.0)
            sd = array.new_float(p, 1.0)
            for j = 0 to p - 1
                if keep.get(j)
                    float m = 0.0
                    for i = 0 to n - 1
                        m += x.get(i, j) / n
                    float ss = 0.0
                    for i = 0 to n - 1
                        ss += (x.get(i, j) - m) * (x.get(i, j) - m) / n
                    mu.set(j, m)
                    if ss > 0
                        sd.set(j, math.sqrt(ss))
                        for i = 0 to n - 1
                            x.set(i, j, (x.get(i, j) - m) / math.sqrt(ss))
                    else
                        keep.set(j, false)
            res = array.new_float()
            float rss = 0.0
            float lmax = 0.0
            for i = 0 to n - 1
                res.push(y.get(i) - ym)
                rss += (y.get(i) - ym) * (y.get(i) - ym)
            for j = 0 to p - 1
                if keep.get(j)
                    float c = 0.0
                    for i = 0 to n - 1
                        c += x.get(i, j) * res.get(i)
                    lmax := math.max(lmax, math.abs(c) / n)
            b = array.new_float(p, 0.0)
            best = array.new_float(p, 0.0)
            float bic = n * math.log(math.max(rss / n, 1e-12))
            if lmax > 0
                float ratio = n < p ? 0.01 : 0.0001
                for k = 1 to 19
                    float lam = lmax * math.pow(ratio, k / 19.0)
                    int sweep = 0
                    float dmax = 1.0
                    while dmax > 1e-6 and sweep < 100
                        dmax := 0.0
                        sweep += 1
                        for j = 0 to p - 1
                            if keep.get(j)
                                float bj = b.get(j)
                                float z = bj
                                for i = 0 to n - 1
                                    z += x.get(i, j) * res.get(i) / n
                                float nb = math.sign(z) * math.max(math.abs(z) - lam, 0.0)
                                if nb != bj
                                    for i = 0 to n - 1
                                        res.set(i, res.get(i) - x.get(i, j) * (nb - bj))
                                    b.set(j, nb)
                                    dmax := math.max(dmax, math.abs(nb - bj))
                    float r2 = 0.0
                    for e in res
                        r2 += e * e
                    int df = 0
                    for bj in b
                        df += bj != 0 ? 1 : 0
                    float bk = n * math.log(math.max(r2 / n, 1e-12)) + df * math.log(n)
                    if bk < bic
                        bic := bk
                        best := b.copy()
            out.push(ym)
            out.concat(best)
            out.concat(mu)
            out.concat(sd)
    out
// @function The LASSO's fitted log growth for one store row (f_lasso).
// @param m The fit from f_lasso.
// @param x The row (every column).
// @param c0 First feature column.
// @param p Number of feature columns.
// @returns The fitted log growth, na without a fit or with a used feature missing.
export f_lasso_at(array<float> m, array<float> x, int c0, int p) =>
    float y = na
    if m.size() == 1 + 3 * p
        y := m.get(0)
        for j = 0 to p - 1
            float bj = m.get(1 + j)
            if bj != 0
                y += bj * (x.get(c0 + j) - m.get(1 + p + j)) / m.get(1 + 2 * p + j)
    y
// ==========================================
// STATISTICS HELPERS for the indicator (moved here to keep its compile time down)
// ==========================================
// @function Median of an array (na when empty); the input is not reordered.
export f_median(array<float> a) =>
    int n = a.size()
    float r = na
    if n > 0
        array<float> s = a.copy()
        s.sort()
        r := n % 2 == 1 ? s.get(int(n / 2)) : (s.get(int(n / 2) - 1) + s.get(int(n / 2))) / 2.0
    r
// @function Hampel identifier (Hampel 1974; Pearson 2002): is x beyond the median +- 3 x 1.4826 x
// MAD of the stored annual rates (1.4826 x MAD estimates the standard deviation under normality)?
// The rates are one a year (quarters 0, 4 ... 36 back: up to 10, none overlapping), so a short
// record cannot pass for a steady one.
// @param v Quarter store (ring of 128 rows).
// @param q Open quarter's index.
// @param c Column of the annual rates.
// @param x Value tested.
// @returns true when x is an outlier; false when it is not, x is na or under 5 rates are stored.
export f_hampel(matrix<float> v, int q, int c, float x) =>
    array<float> h = array.new_float()
    for k = 0 to 9
        int lag = 4 * k
        if lag <= math.min(q, 127)
            float r = v.get((q - lag) % 128, c)
            if not na(r)
                h.push(r)
    bool out = false
    if h.size() >= 5 and not na(x)
        float m = f_median(h)
        array<float> d = array.new_float()
        for r in h
            d.push(math.abs(r - m))
        out := math.abs(x - m) > 3 * 1.4826 * f_median(d)
    out
// Harmonic mean of the positive entries (na with none).
f_harmonic_mean(array<float> a) =>
    sr = 0.0
    k = 0
    for v in a
        if v > 0
            sr += 1.0 / v
            k += 1
    sr > 0 ? k / sr : na
// @function Percentile p (linear interpolation) of an ALREADY-SORTED array.
export f_pct_sorted(array<float> s, float p) =>
    float idx = (s.size() - 1) * p
    int lo = int(math.floor(idx))
    int hi = int(math.ceil(idx))
    lo == hi ? s.get(lo) : s.get(lo) * (1 - (idx - lo)) + s.get(hi) * (idx - lo)
// @function Central tendency (harmonic mean or median) and both percentile legs from one sort.
// @returns [centre, centre from under 4 values, lo percentile, hi percentile (both na under min_n values)].
export f_ratio_stats(array<float> arr, bool use_mean, float lo_p, float hi_p, int min_n) =>
    int n = arr.size()
    float ct = na
    float c_lo = na
    float c_hi = na
    if n > 0
        array<float> s = arr.copy()
        s.sort()
        ct := use_mean ? f_harmonic_mean(arr) : f_pct_sorted(s, 0.5)
        if n >= min_n
            c_lo := f_pct_sorted(s, lo_p)
            c_hi := f_pct_sorted(s, hi_p)
    [ct, not na(ct) and n < 4, c_lo, c_hi]
// @function Predictive weight of a fair-value record: how well the value stored at quarter i predicted the price h quarters later (algo 0 IVW, 1 SMAPE, 2 MALE, 3 WMAPE, 4 RMSLE). No record (under 4 scored quarters) -> 0.
// @returns [weight, error].
export f_model_weight(array<float> fv, array<float> px, int algo, int h) =>
    w = 0.0
    float e = na
    int np = math.min(fv.size(), px.size()) - h
    if np >= 4
        se = 0.0
        sp = 0.0
        k = 0
        for i = 0 to np - 1
            float f = fv.get(i)
            float p = px.get(i + h)
            if f > 0 and p > 0
                float l = math.log(p / f)
                se += algo == 1 ? 2 * math.abs(f - p) / (f + p) : algo == 2 ? math.abs(l) : algo == 3 ? math.abs(f - p) : l * l
                sp += p
                k += 1
        if k >= 4
            // IVW floor = a 5% RMS miss; nothing resolves price tighter.
            float err = algo == 3 ? se / sp : algo == 4 ? math.sqrt(se / k) : se / k
            w := math.min(k / 12.0, 1.0) / math.max(err, algo == 0 ? 0.0025 : 0.02)
            e := err
    [w, e]
// @function Normalises the weights w in place and caps each family (fam: the family of each weight, 0-6) at max(40%, 1 / families), the excess spread over the families below the cap.
// @returns w.
export f_fam_cap(array<float> w, array<int> fam) =>
    float tot = w.sum()
    if tot > 0
        fs = array.new_float(7, 0.0)
        for i = 0 to w.size() - 1
            float x = w.get(i) / tot
            w.set(i, x)
            int f = fam.get(i)
            fs.set(f, fs.get(f) + x)
        nf = 0
        for y in fs
            nf += y > 0 ? 1 : 0
        float cap = math.max(0.4, 1.0 / nf)
        for it = 0 to 5
            over = 0.0
            room = 0.0
            // A family at (or within 1e-12 of) the cap is frozen there; the rest absorb the excess.
            for y in fs
                over += math.max(y - cap, 0.0)
                room += y < cap - 1e-12 ? y : 0.0
            if nf >= 3 and over > 1e-9 and room > 0
                for i = 0 to w.size() - 1
                    float fx = fs.get(fam.get(i))
                    w.set(i, w.get(i) * (fx >= cap - 1e-12 ? cap / fx : 1 + over / room))
                for f = 0 to 6
                    float fx = fs.get(f)
                    fs.set(f, fx >= cap - 1e-12 ? (fx > 0 ? cap : 0.0) : fx * (1 + over / room))
    w
// @function Band half-width: the members' share-weighted spread around the blend mu; na under two members with weight (no spread to measure).
export f_wsd(array<float> v, array<float> w, float mu) =>
    ss = 0.0
    int nw = 0
    for [i, x] in v
        float wi = w.get(i)
        ss += wi * (x - mu) * (x - mu)
        nw += wi > 0 ? 1 : 0
    nw >= 2 ? math.sqrt(ss) : na
// @function Whether the last 14 source codes are one and the same real source (not a stand-in, 2 or 4).
export f_one_src(array<float> s) =>
    bool ok = s.size() >= 14
    if ok
        for j = s.size() - 14 to s.size() - 1
            ok := ok and s.get(j) == s.last() and s.get(j) != 2 and s.get(j) != 4
    ok
// @function Share of a (4+ value) array below x (na otherwise).
export f_pct_rank(array<float> a, float x) =>
    int n = a.size()
    float r = na
    if n >= 4 and not na(x)
        below = 0
        for v in a
            below += v < x ? 1 : 0
        r := below / float(n)
    r
// ==========================================
// THE SCENARIO DRAWS: Bear / Bull of each axis and the Monte Carlo's draws
// ==========================================
// One driver's draws on its own into column c, on the lattice's coordinates from j0.
f_draws(matrix<float> ds, int c, array<float> ch, array<int> lg, LP g, int j0, int nmin, int nd, int h) =>
    if ch.size() >= nmin
        for [i, v] in f_draws1(g, j0, ch, lg, nd, h)
            ds.set(i, c, v)
// [25th percentile, at most 0 | 75th, at least 0] of a draw column (na without draws).
f_side(matrix<float> ds, int c) =>
    s = ds.col(c)
    float lo = na
    float hi = na
    if not na(s.first())
        s.sort()
        lo := math.min(f_pct_sorted(s, 0.25), 0.0)
        hi := math.max(f_pct_sorted(s, 0.75), 0.0)
    [lo, hi]
// @function The scenario draws: nd (1,024, the lattice's points; h = 4) h-quarter stationary-bootstrap sums on the lattice's points, every quarter equally likely to start a block, of the rate, stage-1 growth and terminal growth changes (joint pool from column qmc; each driver on its own pool when the joint one is under nmin quarters), the rate draws rescaled to the weekly one-year rate moves (wkr, sources wks) and the growth draws widened to the implied-growth moves (wkg), plus the revenue-growth draws (column qrev).
// @param v Quarter store matrix.
// @param q Quarters stored.
// @param nq Quarters in the own-multiple window.
// @returns [draws (nd x 5: rate, growth, terminal sums, end quarter, revenue-growth sum), quarters behind each axis (4), Bear / Bull per axis (8: rate, growth, terminal, revenue growth), joint quarters, skipped quarters, rate windows, block length, growth windows].
export f_scen_draws(matrix<float> v, int q, int nq, int qmc, int qrev, int nmin, array<float> wkr, array<float> wks, array<float> wkg, int nd, int h) =>
    ds = matrix.new<float>(nd, 5, na)
    axq = array.new_int(4, 0)
    float mc_b = na
    [lg, cr0, cg0, ct0, sk] = f_pool(v, q, nq, qmc)
    cr = f_demean(cr0), cg = f_demean(cg0), ct = f_demean(ct0)
    int mc_q = lg.size()
    // One lattice for every path set: the joint path (or the rate, growth and
    // terminal ones each on its own) and the revenue-growth one read their own 2h - 1 coordinates of
    // each point.
    g = f_lat()
    int dh = 2 * h - 1
    if mc_q >= nmin
        mc_b := f_blen(cr, cg, ct)
        // Every quarter equally likely to start a block; the changes centred on the paths' mean.
        w = array.new_float(mc_q, 1.0)
        cw = f_cum(w)
        nx = f_next(lg)
        cr := f_wdemean(cr0, w, nx, mc_b, h), cg := f_wdemean(cg0, w, nx, mc_b, h), ct := f_wdemean(ct0, w, nx, mc_b, h)
        for i = 0 to nd - 1
            g.i := i, g.j := 0
            path = f_wpath(g, cw, nx, mc_b, h)
            float sr = 0.0, float sg = 0.0, float st = 0.0
            for j in path
                sr += cr.get(j)
                sg += cg.get(j)
                st += ct.get(j)
            ds.set(i, 0, sr)
            ds.set(i, 1, sg)
            ds.set(i, 2, st)
            ds.set(i, 3, lg.get(path.last()))
        for c = 0 to 2
            axq.set(c, mc_q)
    else
        for c = 0 to 2
            [ch, cl] = f_pool1(v, q, nq, qmc + c, qmc + (c == 1 ? 4 : 3))
            axq.set(c, ch.size())
            f_draws(ds, c, ch, cl, g, c * dh, nmin, nd, h)
    // The rate draws keep their paths but are rescaled to the spread of the rate's weekly one-year
    // moves; under 52 windows they stay as drawn.
    [yv, yn] = f_yvar(wkr, wks, 52)
    if not na(yv) and not na(ds.get(0, 0))
        float s0 = ds.col(0).stdev()
        if s0 > 0
            float rk = math.sqrt(yv) / s0
            for i = 0 to nd - 1
                ds.set(i, 0, ds.get(i, 0) * rk)
    // The growth draws widen (never narrow) to the spread of the market-implied growth's weekly
    // one-year moves; under 52 windows they stay as drawn.
    [gv, gn] = f_yvar(wkg, wks, 52)
    if not na(gv) and not na(ds.get(0, 1))
        float s1 = ds.col(1).stdev()
        if s1 > 0
            float gk = math.max(1.0, math.sqrt(gv) / s1)
            for i = 0 to nd - 1
                ds.set(i, 1, ds.get(i, 1) * gk)
    [rv, rvl] = f_pool_yoy(v, q, nq, qrev)
    axq.set(3, rv.size())
    f_draws(ds, 4, rv, rvl, g, 3 * dh, nmin, nd, h)
    sd = array.new_float(8, na)
    for [i, c] in array.from(0, 1, 2, 4)
        [lo, hi] = f_side(ds, c)
        sd.set(2 * i, lo)
        sd.set(2 * i + 1, hi)
    [ds, axq, sd, mc_q, sk, yn, mc_b, gn]
// ==========================================
// FIRM REBUILD: the identity solver's fill stages and the report-quarter scores
// (moved here to keep the indicator under the compile-size limit)
// ==========================================
// Fill slot i of the solver arrays (values v, tiers t) only while it is still open.
f_putv(array<float> v, array<int> t, int i, float x, int tier) =>
    if na(v.get(i)) and not na(x)
        v.set(i, x)
        t.set(i, tier)
// @function The solver's fill stages, one pass each: 0 identities only, 1 the firm's own last ratios (revenue carried first), 2 last latched value, 3 generic constants behind the firebreak (tier 0), 4 final solve. Every stage then re-solves the identities and runs the rules: near-exact EBIT ~ pretax + interest, capex ~ 1y change in net PPE + D&A; from stage 1 also rough D&A ~ OCF - NI and OCF ~ NI + D&A. All rule output is tier <= 1. Item order: assets, liabilities, equity, current and non-current assets, revenue, COGS, gross profit, EBIT, D&A, EBITDA, OCF, FCF, capex, gross PPE, accumulated depreciation, net PPE, NI, cash, receivables, debt, then the balance items without an identity.
// @param v Solver values (filled in place).
// @param t Solver tiers (filled in place).
// @param mem Last latched value per item.
// @param ratio Carry ratio per item.
// @param fill_base Ratio base per item (-1: none).
// @param cf_ok The feed is on.
// @param cf_v Feed values.
// @param cf_t Feed tiers.
// @param life The lifeline stage may run (shares known and some real fundamental).
// @param pretax Pretax income TTM.
// @param tax Income tax TTM.
// @param interest Interest expense TTM.
// @param pn_1y Net PPE a year earlier.
// @returns Nothing: v and t are filled.
export f_fill(array<float> v, array<int> t, array<float> mem, array<float> ratio, array<int> fill_base, bool cf_ok, array<float> cf_v, array<int> cf_t, bool life, float pretax, float tax, float interest, float pn_1y) =>
    // Exact identities as triples: x[a] = x[b] + x[c]
    // Assets = Liab + Equity | Assets = Current + Non-current | Revenue = COGS + GP
    // EBITDA = EBIT + D&A | FCF = OCF + Capex (capex < 0) | Gross PPE = Accum. dep. + Net PPE
    id3 = array.from(0, 1, 2, 0, 3, 4, 5, 6, 7, 10, 8, 9, 12, 11, 13, 14, 15, 16)
    // Lifeline triples: item = base x k (assets, revenue, cash, gross PPE, net PPE, receivables,
    // current assets, NI, D&A, capex)
    lf_i = array.from(0, 5, 18, 14, 16, 19, 3, 17, 9, 13)
    lf_b = array.from(5, 0, 0, 0, 14, 5, 0, 5, 5, 9)
    lf_k = array.from(1.5, 0.5, 0.05, 0.3, 0.8, 0.1, 0.4, 0.05, 0.05, -1.0)
    int ne = v.size()
    for st = 0 to 4
        if st == 1 or st == 2
            f_putv(v, t, 5, mem.get(5), 1)
            for i = 0 to ne - 1
                int b = fill_base.get(i)
                f_putv(v, t, i, st == 2 ? mem.get(i) : b >= 0 ? v.get(b) * ratio.get(i) : na, st == 2 or b < 0 ? 1 : math.min(t.get(b), 1))
        if st == 3 and life
            for k = 0 to 9
                int i = lf_i.get(k)
                // Capex = D&A is the standard maintenance-capex assumption on the firm's own D&A: tier 1, not a guess.
                f_putv(v, t, i, v.get(lf_b.get(k)) * lf_k.get(k), i == 13 ? math.min(t.get(9), 1) : 0)
                if i == 0
                    f_putv(v, t, 2, v.get(0) - nz(v.get(1), nz(v.get(20))), 0)
        for p = 0 to 3
            // The feed fills only what the exact identities left open, then they run again.
            if st == 0 and p == 2 and cf_ok
                for [k, i] in array.from(2, 7, 10, 13, 9, -1, -1, -1, -1, 18, 20, 21, 22, 25, -1, 23)
                    if i >= 0
                        f_putv(v, t, i, cf_v.get(k), cf_t.get(k))
            for k = 0 to 5
                int a = id3.get(3 * k), int b = id3.get(3 * k + 1), int c = id3.get(3 * k + 2)
                float va = v.get(a), float vb = v.get(b), float vc = v.get(c)
                if (na(va) ? 1 : 0) + (na(vb) ? 1 : 0) + (na(vc) ? 1 : 0) == 1
                    int j = na(va) ? a : na(vb) ? b : c
                    v.set(j, na(va) ? vb + vc : na(vb) ? va - vc : va - vb)
                    t.set(j, math.min(j == a ? t.get(b) : t.get(a), j == c ? t.get(b) : t.get(c)))
        if st < 4
            f_putv(v, t, 8, nz(pretax, v.get(17) + nz(tax)) + nz(interest), not na(pretax) ? 1 : math.min(t.get(17), 1))
            f_putv(v, t, 13, -math.max(v.get(16) - pn_1y + v.get(9), 0), math.min(math.min(t.get(16), t.get(9)), 1))
            if st > 0
                f_putv(v, t, 9, math.max(v.get(11) - v.get(17), 0), math.min(math.min(t.get(11), t.get(17)), 1))
                f_putv(v, t, 11, v.get(17) + v.get(9), math.min(math.min(t.get(17), t.get(9)), 1))
// @function Piotroski F-score inputs and tests on the solved quarter: 9 signals; a missing input leaves its signal untested (banks have no gross margin), and a test counts only on reported (or exact) inputs (tier >= 2).
// @param v Solver values (item order as in f_fill).
// @param t Solver tiers after the staleness cap.
// @param sh Shares.
// @param t_sh Shares tier.
// @param roa_p ROA a year earlier.
// @param cr_p Current ratio a year earlier.
// @param lev_p Leverage a year earlier.
// @param gm_p Gross margin a year earlier.
// @param at_p Asset turnover a year earlier.
// @param sh_p Shares a year earlier.
// @returns [passes, signals tested, ROA, current ratio, leverage, gross margin, asset turnover].
export f_pio(array<float> v, array<int> t, float sh, int t_sh, float roa_p, float cr_p, float lev_p, float gm_p, float at_p, float sh_p) =>
    float asv = v.get(0), float ni = v.get(17), float ocf = v.get(11), float rv = v.get(5), float cl = v.get(21)
    float roa = asv > 0 ? ni / asv : na
    float cr = cl > 0 ? v.get(3) / cl : na
    float lev = asv > 0 ? nz(v.get(20)) / asv : na
    float gm = rv > 0 ? v.get(7) / rv : na
    float atv = asv > 0 ? rv / asv : na
    array<float> pio = array.from(roa > 0 ? 1.0 : 0.0, ocf > 0 ? 1.0 : 0.0, roa > roa_p ? 1.0 : 0.0, ocf > ni ? 1.0 : 0.0, lev < lev_p ? 1.0 : 0.0, cr > cr_p ? 1.0 : 0.0, sh <= sh_p * 1.001 ? 1.0 : 0.0, gm > gm_p ? 1.0 : 0.0, atv > at_p ? 1.0 : 0.0)
    bool pa = t.get(0) >= 2, bool pn = t.get(17) >= 2, bool po = t.get(11) >= 2, bool pr = t.get(5) >= 2
    array<float> pin = array.from(pa and pn ? roa : na, po ? ocf : na, pa and pn ? roa + roa_p : na, po and pn ? ocf + ni : na, pa and t.get(20) >= 2 ? lev + lev_p : na, math.min(t.get(3), t.get(21)) >= 2 ? cr + cr_p : na, t_sh >= 2 ? sh + sh_p : na, pr and t.get(7) >= 2 ? gm + gm_p : na, pa and pr ? atv + at_p : na)
    int f = 0, int n = 0
    for k = 0 to 8
        if not na(pin.get(k))
            n += 1
            f += int(pio.get(k))
    [f, n, roa, cr, lev, gm, atv]
// @function Margin and return adjustments: normalised EBIT (up to three years), the effective tax rate (a loss year or a missing tax line takes Vietnam's 20% statutory rate), NOPAT on TTM and normalised EBIT with R&D capitalised, unlevered FCF (after-tax interest added back to OCF-based FCF), invested capital (equity method; operating assets at net PPE + operating working capital for negative equity; floored at the operating assets deployed) and ROIC (held to +-150%).
// @returns [normalised EBIT, effective tax, NOPAT, normalised NOPAT, FCFF, invested capital, ROIC].
export f_nopat(float ebit, float ebit_1y, float ebit_2y, float rnd, float rnd_am, float rnd_asset, float pretax, float tax, float fcf, float interest, float wc, float equity, float debt, float cash, float ppe_net, float ppe_gross, float assets) =>
    float ebit_n = ebit
    if not na(ebit_1y) and not na(ebit_2y)
        ebit_n := (ebit + ebit_1y + ebit_2y) / 3.0
    else if not na(ebit_1y)
        ebit_n := (ebit + ebit_1y) / 2.0
    float etax = pretax > 0 ? math.min(math.max(nz(tax / pretax, 0.20), 0.0), 0.35) : 0.20
    float nopat = (ebit + rnd - rnd_am) * (1 - etax)
    float nopat_n = (ebit_n + rnd - rnd_am) * (1 - etax)
    float fcff = fcf + nz(interest) * (1 - etax)
    float ic_eq = equity + debt - nz(cash)
    float ppe_ic = nz(ppe_net, nz(ppe_gross))
    float ic = equity < 0 ? ppe_ic + math.max(wc, 0) : ic_eq
    float ic_floor = math.max(ppe_ic + math.max(nz(wc), 0), nz(assets) * 0.05, 1.0)
    ic := math.max(nz(ic, ic_floor), nz(debt), ic_floor) + rnd_asset
    float roic = nopat / ic
    roic := na(roic) ? na : math.max(math.min(roic, 1.50), -1.50)
    [ebit_n, etax, nopat, nopat_n, fcff, ic, roic]
// @function Year-on-year revenue growth and capital allocation over 3 years (a year each: one year of EBITDA is too noisy). Empire building needs the asset base to actually grow faster than EBITDA (or grow with EBITDA <= 0).
// @returns [revenue growth, asset growth, EBITDA growth, empire building, deteriorating].
export f_capalloc(float rev, float rev_p, float assets, float assets_p, float ebitda, float ebitda_p) =>
    float rev_growth = na
    if not na(rev) and not na(rev_p) and rev_p != 0
        rev_growth := (rev - rev_p) / math.abs(rev_p)
    float asset_growth = na
    if not na(assets) and assets_p > 0
        asset_growth := math.pow(math.max(assets, 0) / assets_p, 1.0 / 3) - 1
    float ebitda_growth = na
    if not na(ebitda) and ebitda_p > 0
        ebitda_growth := ebitda > 0 ? math.pow(ebitda / ebitda_p, 1.0 / 3) - 1 : (ebitda / ebitda_p - 1) / 3
    bool dummy = false
    if not na(asset_growth)
        if not na(ebitda_growth)
            dummy := asset_growth > 0 and asset_growth > ebitda_growth
        else if ebitda <= 0 and asset_growth > 0
            dummy := true
    [rev_growth, asset_growth, ebitda_growth, dummy, asset_growth < 0 and ebitda_growth < asset_growth]
// @function Damodaran synthetic credit spread from interest cover (EBIT / interest). Unknown EBIT or unknown interest: no spread (na), not a guessed mid (BBB) bucket.
export f_synthetic_spread(float ebit, float interest) =>
    var array<float> cut = array.from(8.5, 6.5, 5.5, 4.25, 3.0, 2.5, 2.25, 2.0, 1.75, 1.5, 1.25, 0.8)
    var array<float> spr = array.from(0.0063, 0.0078, 0.0098, 0.0108, 0.0122, 0.0156, 0.0200, 0.0240, 0.0351, 0.0417, 0.0600, 0.0800, 0.1200)
    float icr = na(interest) ? na : interest > 0 ? ebit / interest : 100.0
    k = 0
    while not na(icr) and k < 12 and not (icr > cut.get(k))
        k += 1
    na(icr) ? na : spr.get(k)
// ==========================================
// GROWTH, COST OF CAPITAL AND OUR CONFIDENCE (moved here to keep the indicator under the
// compile-size limit)
// ==========================================
// 0 below a, 1 above b, linear between: a premium phases in instead of stepping.
f_band(float x, float a, float b) =>
    math.min(math.max((x - a) / (b - a), 0.0), 1.0)
// The LASSO's share against the other leg on their records (equal before either is scored); one leg missing -> the other alone.
f_las_share(float w_inc, float w_las, float x_inc, float x_las) =>
    na(x_las) ? 0.0 : na(x_inc) ? 1.0 : w_inc + w_las > 0 ? w_las / (w_inc + w_las) : 0.5
// @function Stage-1 growth by triangulation: sustainable growth (ROE x retention) 15%, ROIC x reinvestment 40% (a bank: ROE x retention), the forward leg (the FY revenue consensus growth combined with the LASSO's on their records, Bates and Granger 1969) 15%, the 3-year sales CAGR 30%; a leg with no data leaves and the others are re-weighted. Also next year's EBITDA on the TTM margin.
// @param lw The LASSO members' records (LASSO, consensus, CAGR).
// @returns [sustainable growth, ROIC x reinvestment, forward leg, LASSO share of it, stage-1 growth, forward EBITDA, stage-1 growth before its limits].
export f_growth(float roe_med, float op_med, float tax, float dps, float eps, float nopat, float fcff, float roic, bool bank, float fwd_g, float g_las, array<float> lw, float cagr, float gcap, float rev, float rev_est, float ebitda) =>
    float ret = 1.0
    if not na(dps) and eps > 0
        ret := 1.0 - math.min(dps / eps, 1.0)
    float prof = roe_med > 0 ? roe_med : op_med > 0 ? op_med * (1 - tax) : na
    float sgr = prof * ret
    float rr = nopat > 0 ? (nopat - fcff) / nopat : na
    float roic_sgr = bank ? sgr : na(rr) ? na : math.max(roic * rr, 0.0)
    float w_las = f_las_share(lw.get(1), lw.get(0), fwd_g, g_las)
    float leg = na(g_las) or w_las == 0 ? fwd_g : w_las == 1 ? g_las : (1 - w_las) * fwd_g + w_las * g_las
    array<float> g_leg = array.from(sgr, roic_sgr, leg, cagr)
    array<float> g_wt = array.from(0.15, 0.40, 0.15, 0.30)
    g_num = 0.0
    g_den = 0.0
    for [i, x] in g_leg
        if not na(x)
            g_num += x * g_wt.get(i)
            g_den += g_wt.get(i)
    float g1u = g_num / g_den
    float g1 = math.max(math.min(math.min(math.max(g1u, -0.10), 0.35), gcap), -0.05)
    // Next-year sales: the FY revenue consensus, else the sales CAGR, each combined with the LASSO.
    float s_inc = nz(rev_est, rev * (1 + cagr))
    float w_las_s = f_las_share(lw.get(not na(rev_est) ? 1 : 2), lw.get(0), s_inc, g_las)
    float sales_f1 = na(g_las) or w_las_s == 0 ? s_inc : w_las_s == 1 ? rev * (1 + g_las) : (1 - w_las_s) * s_inc + w_las_s * rev * (1 + g_las)
    float margin = rev > 0 ? ebitda / rev : na
    [sgr, roic_sgr, leg, w_las, g1, not na(margin) ? sales_f1 * margin : na, g1u]
// @function Equity risk premium: Bayes-Stein shrinkage of the market's mean excess return toward a prior, one asset (Jorion 1986, N = 1): w = (N + 2) / (N + 2 + T d^2 / s^2), d the per-period sample mean less the prior, s^2 the sum of squared deviations over T - N - 2. A noisy mean shrinks hard toward the prior, a precise one keeps its own value. Floored at 0 (a risk-averse market holds no negative premium, Merton 1980). Under a year of returns: N/A.
// @param n Periods. @param s Sum of the per-period excess returns. @param ss Sum of their squares. @param yrs Years covered. @param mu0 Prior, a year.
// @returns The premium, a year.
export f_erp(float n, float s, float ss, float yrs, float mu0) =>
    float m = s / n
    float v = (ss - s * m) / (n - 3)
    float d = m - mu0 * yrs / n
    float w = 3.0 / (3.0 + n * d * d / v)
    yrs >= 1 and n > 3 and v > 0 ? math.max(w * mu0 + (1 - w) * s / yrs, 0.0) : na
// @function Cost of capital. Equity: CAPM on the local base + size and profitability premia (each phasing in over a band, f_band) + the liquidity premium, floored at the base + 3%. Debt: the base + the synthetic spread. WACC on market weights; the unlevered cost strips only the leverage part of beta (Hamada on market leverage), floored at the cost of debt and the base. Terminal growth: long-run inflation + 0.5pt, held to 1.5-3.5%.
// @returns [cost of equity, cost of debt, WACC, unlevered cost, terminal growth].
export f_coc(bool factors, float mc, float fx, float smb, float ebit, float eq, float rf, float beta, float erp, float micro, float ebit_n, float interest, float debt, float tax, float infl) =>
    size_p = 0.0
    rmw_p = 0.0
    if factors
        float mc_usd_b = mc / fx / 1e9
        size_p := na(smb) or na(mc_usd_b) ? 0.0 : mc_usd_b < 1.0 ? smb : mc_usd_b < 4.0 ? smb * (1.0 - ((mc_usd_b - 1.0) / 3.0)) : 0.0
        float op = not na(ebit) and eq > 0 ? ebit / eq : 0.0
        rmw_p := 0.015 * (f_band(op, 0.175, 0.225) - f_band(-op, -0.075, -0.025))
    float coe = math.max(rf + (beta * erp) + size_p + rmw_p + micro, rf + 0.03)
    float cod = rf + f_synthetic_spread(ebit_n, interest)
    float ew = mc + debt > 0 ? mc / (mc + debt) : 1.0
    float wacc = ew == 1.0 ? coe : ew * coe + (1.0 - ew) * cod * (1 - tax)
    float de = nz(debt) / (mc > 0 ? mc : math.max(nz(eq), 1.0))
    float ub = beta / (1 + (1 - tax) * de)
    float gT = math.min(math.max(infl + 0.005, 0.015), 0.035)
    [coe, cod, wacc, math.max(coe - (beta - ub) * erp, na(cod) ? rf : math.min(cod, coe), rf), gT]
f_clamp01(float x) =>
    na(x) ? na : math.max(math.min(x, 1.0), 0.0)
// @function Our confidence and the range overlap with the street (ours Bear-Bull vs street Bear-Bull, 0..1). Parts: agreement (1 - model spread / 0.290; na under two weighted members) 35%, depth (models, x0.5 without a track record) 20%, record (exp(-RMS log error / 0.290)) 25%, quality (input tiers less the flags) 20%; a part with no data leaves and the rest are re-weighted.
// @returns [overlap, agreement, depth, record, quality, confidence 0-100].
export f_our_conf(bool has, float fv, float lo, float hi, float st_lo, float st_hi, float sd, int n, bool track, float err, float tier, float flags) =>
    float our_lo = nz(lo, fv)
    float our_hi = nz(hi, fv)
    float rng = has and not na(fv) ? math.max(our_hi, st_hi) - math.min(our_lo, st_lo) : na
    float overlap = na(rng) ? na : rng <= 0 ? 1.0 : math.max(math.min(our_hi, st_hi) - math.max(our_lo, st_lo), 0.0) / rng
    // Dispersion sd / fv (Diether-Malloy-Scherbina 2002) on the scale of the forward P/E's pricing-error SD, 0.290 (Liu-Nissim-Thomas 2002, Table 2)
    float ag = fv > 0 ? f_clamp01(1 - (sd / fv) / 0.290) : na
    float dp = f_clamp01(n / 8.0) * (track ? 1.0 : 0.5)
    // RMS log error on the same scale, the forward P/E's pricing-error SD 0.290 (Liu-Nissim-Thomas 2002)
    float rl = math.exp(-err / 0.290)
    float ql = f_clamp01(tier - flags)
    array<float> x = array.from(ag, dp, rl, ql)
    array<float> w = array.from(0.35, 0.20, 0.25, 0.20)
    float num = 0.0
    float den = 0.0
    for [i, v] in x
        if not na(v)
            num += v * w.get(i)
            den += w.get(i)
    [overlap, ag, dp, rl, ql, fv > 0 ? 100 * (den > 0 ? num / den : na) : na]
// @function Debt cover metrics; almost no debt (under 2% of assets) reads 99. Debt service cover: (EBITDA - tax) / (interest + the current portion of long-term debt). Stressed cover: the worst 12-month EBITDA of 5 years (12 quarters at least) / (interest x 1.3). Interest cover on EBITDA (dz_ru) or EBIT. Net debt / EBITDA: 99 for net debt on EBITDA <= 0, -1 for net cash on it.
// @returns [debt service cover, stressed cover, interest cover, net debt / EBITDA].
export f_credit(float debt, float assets, float ebit, float interest, float tax, float cpd, float ebitda, float nd, float lo, int nlo, bool dz_ru) =>
    bool nodebt = debt / assets < 0.02
    float tax_x = math.max(nz(ebit) - nz(interest), 0) * math.min(math.max(tax, 0.0), 0.5)
    float dsc = nodebt ? 99.0 : na(cpd) or not (interest + cpd > 0) ? float(na) : (ebitda - tax_x) / (interest + cpd)
    float stc = nodebt ? 99.0 : nlo >= 12 and interest > 0 ? lo / (interest * 1.3) : float(na)
    float icv = nodebt ? 99.0 : interest > 0 ? (dz_ru ? ebitda : ebit) / interest : float(na)
    float nde = na(ebitda) ? float(na) : ebitda > 0 ? nd / ebitda : nd > 0 ? 99.0 : nd <= 0 ? -1.0 : float(na)
    [dsc, stc, icv, nde]

```
