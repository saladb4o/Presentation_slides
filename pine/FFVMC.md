# FFVMC: Monte Carlo library

Publish this as a private library named FFVMC (it becomes version 1), before republishing FFVLib and FFV Pro. Copy everything inside the code block into a new Pine Editor tab.

```pine
//@version=6
// @description Companion library for Fundamental Fair Value Pro: the Monte Carlo engine (random
// numbers, the history pools, block length, bootstrap paths and draws) and the forecast statistics
// (rate-width variance, MIDAS, LASSO). It was split out of FFVLib to keep each library under the
// compile-size limit. Publish it as a PRIVATE library named FFVMC; after any change, publish a new
// version and bump the number in the indicator's import line.
library('FFVMC')
// ==========================================
// MONTE CARLO: random numbers, the history pool, the block length, the paths
// ==========================================
// @type Wichmann-Hill (2006) generator: four multiplicative congruential generators, period about 2^121. Plain arithmetic, so a copy in any language gives the same numbers from the same seeds.
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
// @function One stationary-bootstrap path (Politis and Romano 1994) of h positions in a pool (successors nx, f_next): a random start, then each step either moves to the next quarter or, with probability 1 / blen or where there is no next quarter (f_next), jumps to a new random quarter.
export f_path(WH g, array<int> nx, float blen, int h) =>
    out = array.new_int()
    int n = nx.size()
    int i = int(math.floor(g.nxt() * n))
    out.push(i)
    if h > 1
        for s = 2 to h
            bool jump = g.nxt() < 1.0 / blen
            i := jump or nx.get(i) < 0 ? int(math.floor(g.nxt() * n)) : nx.get(i)
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
// @function The conditions the bootstrap matches on, from weekly closes (oldest first): 13-week volatility of log returns, the 40-week trend (log of the price over its 40-week average), the distance below the 52-week high, and the sector's 13-week log return over its parent's (na when the sector or parent series is missing).
// @returns [volatility, trend, distance from high, sector strength].
export f_cond(array<float> s, array<float> x, array<float> a) =>
    int n = s.size()
    float v = na, float t = na, float h = na, float k = na
    if n > 13
        r = array.new_float()
        for i = n - 13 to n - 1
            r.push(math.log(s.get(i) / s.get(i - 1)))
        v := r.stdev()
        float x0 = x.get(n - 14), float x1 = x.last(), float a0 = a.get(n - 14), float a1 = a.last()
        k := x0 > 0 and x1 > 0 and a0 > 0 and a1 > 0 ? math.log(x1 / x0) - math.log(a1 / a0) : na
    if n >= 40
        t := math.log(s.last() / s.slice(n - 40, n).avg())
    if n >= 52
        h := s.last() / s.slice(n - 52, n).max() - 1
    [v, t, h, k]
// @function Each condition (columns c0 .. c0 + nf - 1) as its percentile within the stock's stored quarters (mid-rank of ties), row = lag (0 the open quarter).
// @returns A 128 x nf matrix, na where a quarter has no value.
export f_pctl(matrix<float> hm, int hq, int c0, int nf) =>
    pm = matrix.new<float>(128, nf, na)
    int top = math.min(hq, 127)
    for f = 0 to nf - 1
        vals = array.new_float()
        for lag = 0 to top
            float y = hm.get((hq - lag) % 128, c0 + f)
            if not na(y)
                vals.push(y)
        int nv = vals.size()
        if nv > 0
            for lag = 0 to top
                float y = hm.get((hq - lag) % 128, c0 + f)
                if not na(y)
                    int lo = 0, int eq = 0
                    for z in vals
                        lo += z < y ? 1 : 0
                        eq += z == y ? 1 : 0
                    pm.set(lag, f, (lo + 0.5 * eq) / nv)
    pm
// @function kNN weights for where the bootstrap's blocks start (Lall and Sharma 1996). A change at lag L is matched by the conditions at the start of its 4-quarter window (lags L + 1 .. L + 3) against the conditions now (lags 0 .. 2), on the percentiles pm, with the Lorentzian distance, the sum of log(1 + |x - y|). A condition-quarter with no value now is left out; a change missing one that is kept cannot be a neighbour. The k = round(sqrt(n)) nearest of the n that can, at least 4 quarters apart, get weights 1, 1/2, 1/3 ... and the rest 0.
// @returns The weights, one per change; empty (equal weights) when the effective number of neighbours (sum w)^2 / sum w^2 is under 3 or no condition is known now.
export f_knn(matrix<float> pm, array<int> lg) =>
    int nf = pm.columns()
    int n = lg.size()
    dist = array.new_float(n, na)
    int act = 0
    for t = 0 to 2
        for f = 0 to nf - 1
            act += na(pm.get(t, f)) ? 0 : 1
    int ne = 0
    if act > 0 and n > 0
        for j = 0 to n - 1
            int l0 = lg.get(j) + 1
            if l0 + 2 <= 127
                float d = 0.0
                for t = 0 to 2
                    for f = 0 to nf - 1
                        float q = pm.get(t, f)
                        if not na(q)
                            d += math.log(1 + math.abs(q - pm.get(l0 + t, f)))
                dist.set(j, d)
                ne += na(d) ? 0 : 1
    w = array.new_float(n, 0.0)
    int k = int(math.round(math.sqrt(ne)))
    ch = array.new_int()
    while ch.size() < k
        int b = -1
        for j = n - 1 to 0
            float d = dist.get(j)
            ok = not na(d) and (b < 0 or d < dist.get(math.max(b, 0)))
            for c in ch
                ok := ok and math.abs(lg.get(c) - lg.get(j)) >= 4
            b := ok ? j : b
        if b < 0
            break
        ch.push(b)
        w.set(b, 1.0 / ch.size())
    float sw = w.sum()
    float s2 = 0.0
    for y in w
        s2 += y * y
    s2 > 0 and sw * sw / s2 >= 3 ? w : array.new_float()
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
// @function A stationary-bootstrap path whose start and each jump (including where there is no next quarter, f_next) fall on a quarter with probability its weight (cumulative weights cw); otherwise as f_path.
export f_wpath(WH g, array<float> cw, array<int> nx, float blen, int h) =>
    out = array.new_int()
    int i = f_pick(cw, g.nxt())
    out.push(i)
    if h > 1
        for s = 2 to h
            bool jump = g.nxt() < 1.0 / blen
            i := jump or nx.get(i) < 0 ? f_pick(cw, g.nxt()) : nx.get(i)
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
// @function nd draws of one driver on its own with kNN start weights w (lg the changes' lags, for the pool's gaps): the changes centred on their weighted-path mean, then summed along weighted paths (f_wpath), the block length the series' own optimal one.
// @returns The nd sums, in draw order.
export f_wdraws1(WH g, array<float> ch, array<int> lg, array<float> w, int nd, int h) =>
    out = array.new_float()
    float bl = f_blen(ch, ch, ch)
    nx = f_next(lg)
    x = f_wdemean(ch, w, nx, bl, h)
    cw = f_cum(w)
    for i = 1 to nd
        float s = 0.0
        for j in f_wpath(g, cw, nx, bl, h)
            s += x.get(j)
        out.push(s)
    out
// @function nd draws of one driver on its own: the changes centred on their mean under the paths (f_wdemean, equal weights), each draw the sum along an h-step stationary-bootstrap path (f_path), the block length that series' own optimal one.
// @param lg The changes' lags (oldest first), for the pool's gaps (f_next).
// @returns The nd sums, in draw order.
export f_draws1(WH g, array<float> ch, array<int> lg, int nd, int h) =>
    out = array.new_float()
    float bl = f_blen(ch, ch, ch)
    nx = f_next(lg)
    x = f_wdemean(ch, array.new_float(ch.size(), 1.0), nx, bl, h)
    for i = 1 to nd
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

```
