# FFV Peer Check

Is the stock cheap or expensive against its peers? Add it to a daily chart of a Vietnamese stock (scroll back to the start of the history) and enter up to 12 peers from the same industry in the settings (default: 12 HOSE banks). No library needed; it uses all 40 requests. Copy everything inside the code block into a new Pine Editor tab.

```pine
//@version=6
// FFV Peer Check: is this stock cheap or expensive against its peers, on the multiples the market
// pays for them? Display only (nothing feeds FFV Pro). No library; uses all 40 requests. Run it on a
// daily chart of a Vietnamese stock, scrolled back to the start of the history, with up to 12 peers
// from the same industry in the settings (default: 12 HOSE banks).
//
// Models (Damodaran's companion variables; one regression per quarter across the peers):
//   A  log P/B on ROE (12-month EPS over the average book value per share of now and a year ago)
//   B  log P/E on 3-year EPS growth (EPS positive now and 3 years ago)
//   C  log P/B on ROE and growth, pooled over all quarters with an intercept per quarter
// A and B: Theil-Sen line per quarter (6 peers at least); the slope used is the average of the
// quarterly slopes so far (Fama-MacBeth), stable when that average is above 0 with a Newey-West
// t-statistic (3 lags) of 2 or more over 8 quarters or more. C: Huber regression with a ridge
// penalty on the standardised slopes, chosen by leave-one-peer-out error from 0, 0.1, 0.3, 1 and 3;
// quarters with 8 peers or more, 60 points or more; stable when both slopes are above 0 in the full
// fit and in each half of the history. Every past figure uses only the quarters up to that date.
// Winner: the stable model with the lowest leave-one-out error on the peer-quarters all stable models
// share, by the one-standard-error rule (a single-metric model wins unless C beats it by more than
// one standard error). Worked here?: the rank correlation of each quarter's gap (and change vs the
// usual gap) with the next 12 months' price return across the peers, averaged, Newey-West t.
//
// Data (checked with FFV Peer Data Check): prices split-adjusted, which matches TradingView's
// restated per-share history. TradingView's share count misses a bonus issue's adjustment in some
// quarters: the chart stock's book value per share is common equity over a share count that ignores
// a drop of more than 5% (restated counts do not fall) for up to 120 days; a peer's past quarter whose
// book value per share rises 7% or more and falls back 7% or more the next quarter is left out.
// Snapshots: the first bar from the 15th of Feb, May, Aug and Nov (quarterly reports are due within
// 20 days, 30 with subsidiaries: Circular 96/2020/TT-BTC).
indicator('FFV Peer Check', overlay = true)

var array<string> P = array.from(
     input.symbol('HOSE:VCB', 'Peer 1'), input.symbol('HOSE:BID', 'Peer 2'), input.symbol('HOSE:CTG', 'Peer 3'),
     input.symbol('HOSE:TCB', 'Peer 4'), input.symbol('HOSE:MBB', 'Peer 5'), input.symbol('HOSE:VPB', 'Peer 6'),
     input.symbol('HOSE:ACB', 'Peer 7'), input.symbol('HOSE:HDB', 'Peer 8'), input.symbol('HOSE:STB', 'Peer 9'),
     input.symbol('HOSE:VIB', 'Peer 10'), input.symbol('HOSE:TPB', 'Peer 11'), input.symbol('HOSE:SHB', 'Peer 12'))
string me = syminfo.prefix + ':' + syminfo.ticker

f(string s, string id, string per) =>
    request.financial(s, id, per, ignore_invalid_symbol = true)
f_px(string s) =>
    request.security(ticker.modify(s, adjustment = adjustment.splits), timeframe.period, close, ignore_invalid_symbol = true)

// ---------------------------------------------------------------- live values (entity 0: the chart stock, 1-12: the peers)
array<float> LP = array.new_float(13)
array<float> LE = array.new_float(13)
array<float> LB = array.new_float(13)
float c0 = f_px(syminfo.tickerid)
float e0 = f(syminfo.tickerid, 'EARNINGS_PER_SHARE_DILUTED', 'TTM')
float q0 = f(syminfo.tickerid, 'COMMON_EQUITY_TOTAL', 'FQ')
float n0 = f(syminfo.tickerid, 'TOTAL_SHARES_OUTSTANDING', 'FQ')
// Share count: a drop of more than 5% is ignored for up to 120 days (TradingView's missed bonus-issue adjustment).
var float sh = na
var int low_t = na
if n0 > 0
    if na(sh) or n0 >= sh * 0.95
        sh := n0
        low_t := na
    else
        if na(low_t)
            low_t := time
        if time - low_t > 120 * 86400000
            sh := n0
            low_t := na
LP.set(0, c0)
LE.set(0, e0)
LB.set(0, q0 / sh)
for i = 0 to 11
    string s = P.get(i)
    if s != '' and s != me and P.indexof(s) == i
        LP.set(i + 1, f_px(s))
        LE.set(i + 1, f(s, 'EARNINGS_PER_SHARE_DILUTED', 'TTM'))
        LB.set(i + 1, f(s, 'BOOK_VALUE_PER_SHARE', 'FQ'))

// ---------------------------------------------------------------- helpers
// Flat stores: 13 values per snapshot, index k * 13 + j.
f_g(array<float> a, int j, int k) =>
    float v = na
    int i = k * 13 + j
    if k >= 0 and i < a.size()
        v := a.get(i)
    v
f_put(array<float> a, int i, float v) =>
    if i < a.size()
        a.set(i, v)
    else
        a.push(v)
    true
f_avg(array<float> a) =>
    float s = 0.0
    int n = 0
    if a.size() > 0
        for i = 0 to a.size() - 1
            float v = a.get(i)
            if not na(v)
                s += v
                n += 1
    [n > 0 ? s / n : na, n]
f_med(array<float> a) =>
    a.size() > 0 ? a.median() : na
// log P/B, ROE, log P/E and 3-year EPS growth of entity j at snapshot k.
f_der(array<float> P_, array<float> E_, array<float> B_, int j, int k) =>
    float p = f_g(P_, j, k)
    float e = f_g(E_, j, k)
    float b = f_g(B_, j, k)
    float b4 = f_g(B_, j, k - 4)
    float e12 = f_g(E_, j, k - 12)
    float ya = p > 0 and b > 0 ? math.log(p / b) : na
    float xa = b > 0 and b4 > 0 and not na(e) ? e / ((b + b4) / 2) : na
    float yb = p > 0 and e > 0 ? math.log(p / e) : na
    float xb = e > 0 and e12 > 0 ? math.pow(e / e12, 1.0 / 3) - 1 : na
    [ya, xa, yb, xb]
f_dcol(array<float> P_, array<float> E_, array<float> B_, array<float> ya, array<float> xa, array<float> yb, array<float> xb, int k) =>
    for j = 0 to 12
        [v1, v2, v3, v4] = f_der(P_, E_, B_, j, k)
        f_put(ya, k * 13 + j, v1)
        f_put(xa, k * 13 + j, v2)
        f_put(yb, k * 13 + j, v3)
        f_put(xb, k * 13 + j, v4)
    true
// Theil-Sen: the median of the pairwise slopes, intercept the median of y - b x; point skip left out (-1: none).
f_ts(array<float> x, array<float> y, int skip) =>
    array<float> s = array.new_float()
    int n = x.size()
    if n >= 2
        for i = 0 to n - 2
            if i != skip
                for j = i + 1 to n - 1
                    if j != skip and x.get(j) != x.get(i)
                        s.push((y.get(j) - y.get(i)) / (x.get(j) - x.get(i)))
    float b = f_med(s)
    array<float> r = array.new_float()
    if not na(b)
        for i = 0 to n - 1
            if i != skip
                r.push(y.get(i) - b * x.get(i))
    [b, f_med(r)]
f_icpt(array<float> x, array<float> y, float b) =>
    array<float> r = array.new_float()
    if x.size() > 0
        for i = 0 to x.size() - 1
            r.push(y.get(i) - b * x.get(i))
    f_med(r)
f_r2(array<float> x, array<float> y, float a, float b) =>
    float m = y.avg()
    float ss = 0.0
    float st = 0.0
    for i = 0 to x.size() - 1
        ss += math.pow(y.get(i) - a - b * x.get(i), 2)
        st += math.pow(y.get(i) - m, 2)
    st > 0 ? 1 - ss / st : na
// Mean with a Newey-West t-statistic (3 lags, Bartlett weights); the t needs 8 values.
f_nw(array<float> v) =>
    int T = v.size()
    float m = T > 0 ? v.avg() : na
    float t = na
    if T >= 8
        float lr = 0.0
        for l = 0 to 3
            float g = 0.0
            for i = l to T - 1
                g += (v.get(i) - m) * (v.get(i - l) - m)
            lr += (l == 0 ? 1.0 : 2.0 * (1 - l / 4.0)) * g / T
        t := lr > 0 ? m / math.sqrt(lr / T) : na
    [m, t, T]
// Spearman rank correlation (average ranks for ties).
f_rk(array<float> a) =>
    int n = a.size()
    array<float> r = array.new_float(n, 0.0)
    for i = 0 to n - 1
        float lt = 0.0
        float eq = 0.0
        for j = 0 to n - 1
            lt += a.get(j) < a.get(i) ? 1 : 0
            eq += a.get(j) == a.get(i) ? 1 : 0
        r.set(i, lt + (eq + 1) / 2)
    r
f_sp(array<float> a, array<float> b) =>
    array<float> ra = f_rk(a)
    array<float> rb = f_rk(b)
    float ma = ra.avg()
    float mb = rb.avg()
    float sab = 0.0
    float saa = 0.0
    float sbb = 0.0
    for i = 0 to ra.size() - 1
        sab += (ra.get(i) - ma) * (rb.get(i) - mb)
        saa += math.pow(ra.get(i) - ma, 2)
        sbb += math.pow(rb.get(i) - mb, 2)
    saa > 0 and sbb > 0 ? sab / math.sqrt(saa * sbb) : na
// Mean of entity j's residuals before snapshot k (4 at least).
f_prior(array<float> R, int j, int k) =>
    float s = 0.0
    int n = 0
    if k > 0
        for t = 0 to k - 1
            float v = f_g(R, j, t)
            if not na(v)
                s += v
                n += 1
    n >= 4 ? s / n : na
// Did the gap (or its change vs the usual gap) rank next year's returns? Spearman per snapshot
// (6 peers at least) of the residual with the price return 4 snapshots later.
f_ic(array<float> R, array<float> Pp, int K, bool chg) =>
    array<float> ics = array.new_float()
    if K >= 5
        for k = 0 to K - 5
            array<float> sg = array.new_float()
            array<float> rt = array.new_float()
            for j = 1 to 12
                float s = f_g(R, j, k)
                if chg
                    s := s - f_prior(R, j, k)
                float p0 = f_g(Pp, j, k)
                float p1 = f_g(Pp, j, k + 4)
                if not na(s) and p0 > 0 and p1 > 0
                    sg.push(s)
                    rt.push(p1 / p0 - 1)
            if sg.size() >= 6
                float ic = f_sp(sg, rt)
                if not na(ic)
                    ics.push(ic)
    f_nw(ics)

// ---- model C: pooled points, quarter intercepts (weighted means), Huber weights, ridge on the slopes
f_cpts(array<float> ya, array<float> xa, array<float> xb, int k0, int k1) =>
    array<float> y = array.new_float()
    array<float> x1 = array.new_float()
    array<float> x2 = array.new_float()
    array<int> q = array.new_int()
    array<int> pj = array.new_int()
    array<int> kq = array.new_int()
    if k1 >= k0
        for k = k0 to k1
            int c = 0
            for j = 1 to 12
                if not na(f_g(ya, j, k)) and not na(f_g(xa, j, k)) and not na(f_g(xb, j, k))
                    c += 1
            if c >= 8
                int g = kq.size()
                kq.push(k)
                for j = 1 to 12
                    float a = f_g(ya, j, k)
                    float b = f_g(xa, j, k)
                    float d = f_g(xb, j, k)
                    if not na(a) and not na(b) and not na(d)
                        y.push(a)
                        x1.push(b)
                        x2.push(d)
                        q.push(g)
                        pj.push(j)
    [y, x1, x2, q, pj, kq]
f_div(array<float> a, float s) =>
    array<float> r = array.new_float()
    if a.size() > 0
        for i = 0 to a.size() - 1
            r.push(a.get(i) / s)
    r
// Per-quarter weighted intercepts for slopes b1, b2 (peer ex left out).
f_alpha(array<float> y, array<float> z1, array<float> z2, array<int> q, array<int> pj, array<float> w, int nq, float b1, float b2, int ex) =>
    array<float> sw = array.new_float(nq, 0.0)
    array<float> sr = array.new_float(nq, 0.0)
    for i = 0 to y.size() - 1
        if pj.get(i) != ex
            int g = q.get(i)
            sw.set(g, sw.get(g) + w.get(i))
            sr.set(g, sr.get(g) + w.get(i) * (y.get(i) - b1 * z1.get(i) - b2 * z2.get(i)))
    array<float> al = array.new_float(nq)
    for g = 0 to nq - 1
        if sw.get(g) > 0
            al.set(g, sr.get(g) / sw.get(g))
    al
// One weighted least-squares pass on the within-quarter deviations, ridge lam x total weight.
f_wls(array<float> y, array<float> z1, array<float> z2, array<int> q, array<int> pj, array<float> w, int nq, float lam, int ex) =>
    array<float> sw = array.new_float(nq, 0.0)
    array<float> sy = array.new_float(nq, 0.0)
    array<float> s1 = array.new_float(nq, 0.0)
    array<float> s2 = array.new_float(nq, 0.0)
    for i = 0 to y.size() - 1
        if pj.get(i) != ex
            int g = q.get(i)
            float wi = w.get(i)
            sw.set(g, sw.get(g) + wi)
            sy.set(g, sy.get(g) + wi * y.get(i))
            s1.set(g, s1.get(g) + wi * z1.get(i))
            s2.set(g, s2.get(g) + wi * z2.get(i))
    float a11 = 0.0
    float a12 = 0.0
    float a22 = 0.0
    float c1 = 0.0
    float c2 = 0.0
    float W = 0.0
    for i = 0 to y.size() - 1
        if pj.get(i) != ex
            int g = q.get(i)
            float wg = sw.get(g)
            float wi = w.get(i)
            float dy = y.get(i) - sy.get(g) / wg
            float d1 = z1.get(i) - s1.get(g) / wg
            float d2 = z2.get(i) - s2.get(g) / wg
            a11 += wi * d1 * d1
            a12 += wi * d1 * d2
            a22 += wi * d2 * d2
            c1 += wi * d1 * dy
            c2 += wi * d2 * dy
            W += wi
    float l = lam * W
    float det = (a11 + l) * (a22 + l) - a12 * a12
    float b1 = det > 1e-12 ? ((a22 + l) * c1 - a12 * c2) / det : na
    float b2 = det > 1e-12 ? ((a11 + l) * c2 - a12 * c1) / det : na
    [b1, b2]
// Huber M-estimate by iteratively reweighted least squares (k = 1.345, scale = median |residual| / 0.6745).
f_irls(array<float> y, array<float> z1, array<float> z2, array<int> q, array<int> pj, int nq, float lam, int ex) =>
    int n = y.size()
    array<float> w = array.new_float(n, 1.0)
    float b1 = na
    float b2 = na
    for it = 1 to 50
        [c1, c2] = f_wls(y, z1, z2, q, pj, w, nq, lam, ex)
        if na(c1)
            b1 := na
            b2 := na
            break
        array<float> al = f_alpha(y, z1, z2, q, pj, w, nq, c1, c2, ex)
        array<float> ar = array.new_float()
        for i = 0 to n - 1
            if pj.get(i) != ex
                ar.push(math.abs(y.get(i) - al.get(q.get(i)) - c1 * z1.get(i) - c2 * z2.get(i)))
        float sc = f_med(ar) / 0.6745
        bool done = not na(b1) and math.abs(c1 - b1) + math.abs(c2 - b2) < 1e-8
        b1 := c1
        b2 := c2
        if done or not (sc > 0)
            break
        float cut = 1.345 * sc
        for i = 0 to n - 1
            if pj.get(i) != ex
                float r = math.abs(y.get(i) - al.get(q.get(i)) - c1 * z1.get(i) - c2 * z2.get(i))
                w.set(i, r <= cut ? 1.0 : cut / r)
    [b1, b2, w]
// Leave-one-peer-out error for ridge lam: the full fit's Huber weights kept, one pass without the peer,
// its points predicted from the other peers' quarter intercepts. Returns the mean absolute error,
// the full fit's slopes and the error of each point.
f_cv(array<float> y, array<float> z1, array<float> z2, array<int> q, array<int> pj, int nq, float lam) =>
    [b1, b2, w] = f_irls(y, z1, z2, q, pj, nq, lam, -1)
    array<float> er = array.new_float(y.size())
    if not na(b1)
        for j = 1 to 12
            if pj.includes(j)
                [d1, d2] = f_wls(y, z1, z2, q, pj, w, nq, lam, j)
                if not na(d1)
                    array<float> al = f_alpha(y, z1, z2, q, pj, w, nq, d1, d2, j)
                    for i = 0 to y.size() - 1
                        if pj.get(i) == j and not na(al.get(q.get(i)))
                            er.set(i, math.abs(y.get(i) - al.get(q.get(i)) - d1 * z1.get(i) - d2 * z2.get(i)))
    [m, n] = f_avg(er)
    [m, b1, b2, er]
// Within R2: 1 - residual / total sum of squares around the (unweighted) quarter means.
f_r2c(array<float> y, array<float> z1, array<float> z2, array<int> q, int nq, float b1, float b2) =>
    array<float> cn = array.new_float(nq, 0.0)
    array<float> sy = array.new_float(nq, 0.0)
    array<float> s1 = array.new_float(nq, 0.0)
    array<float> s2 = array.new_float(nq, 0.0)
    for i = 0 to y.size() - 1
        int g = q.get(i)
        cn.set(g, cn.get(g) + 1)
        sy.set(g, sy.get(g) + y.get(i))
        s1.set(g, s1.get(g) + z1.get(i))
        s2.set(g, s2.get(g) + z2.get(i))
    float ss = 0.0
    float st = 0.0
    for i = 0 to y.size() - 1
        int g = q.get(i)
        float dy = y.get(i) - sy.get(g) / cn.get(g)
        ss += math.pow(dy - b1 * (z1.get(i) - s1.get(g) / cn.get(g)) - b2 * (z2.get(i) - s2.get(g) / cn.get(g)), 2)
        st += dy * dy
    st > 0 ? 1 - ss / st : na
// C's residuals at snapshot k for every entity: intercept the median of y - b1 ROE - b2 growth over
// the peers (8 at least).
f_cres(array<float> ya, array<float> xa, array<float> xb, int k, float b1, float b2) =>
    array<float> out = array.new_float(13)
    array<float> r = array.new_float()
    if not na(b1)
        for j = 1 to 12
            float v = f_g(ya, j, k) - b1 * f_g(xa, j, k) - b2 * f_g(xb, j, k)
            if not na(v)
                r.push(v)
        if r.size() >= 8
            float a = f_med(r)
            for j = 0 to 12
                float v = f_g(ya, j, k) - a - b1 * f_g(xa, j, k) - b2 * f_g(xb, j, k)
                out.set(j, v)
    [out, r.size()]

// ---------------------------------------------------------------- quarterly snapshots
var int last_q = -1
int qk = year * 4 + int(math.floor((month - 2) / 3))
bool snap = (month == 2 or month == 5 or month == 8 or month == 11) and dayofmonth >= 15 and qk != last_q
var array<int> ST = array.new_int()
var array<float> SP = array.new_float()
var array<float> SE = array.new_float()
var array<float> SB = array.new_float()
var array<float> DYA = array.new_float()
var array<float> DXA = array.new_float()
var array<float> DYB = array.new_float()
var array<float> DXB = array.new_float()
// Model C per snapshot (fit on the snapshots up to it): residuals, raw slopes, ridge, and the latest fit's errors.
var array<float> RC = array.new_float()
var array<float> CB1 = array.new_float()
var array<float> CB2 = array.new_float()
var array<float> CL = array.new_float()
var array<float> CE = array.new_float()
var float c_r2 = na
var int c_pts = 0
var int c_nq = 0
var float c_s1 = na
var float c_s2 = na
if snap
    last_q := qk
    ST.push(time)
    for j = 0 to 12
        SP.push(LP.get(j))
        SE.push(LE.get(j))
        SB.push(LB.get(j))
    int k = ST.size() - 1
    // A peer's book value per share that jumps 7% or more and falls back 7% or more: a missed bonus adjustment.
    if k >= 2
        for j = 1 to 12
            float b2 = f_g(SB, j, k - 2)
            float b1 = f_g(SB, j, k - 1)
            float b0 = f_g(SB, j, k)
            if b2 > 0 and b1 >= b2 * 1.07 and b0 > 0 and b0 <= b1 / 1.07
                SB.set((k - 1) * 13 + j, na)
        f_dcol(SP, SE, SB, DYA, DXA, DYB, DXB, k - 1)
    f_dcol(SP, SE, SB, DYA, DXA, DYB, DXB, k)
    [cy, cx1, cx2, cq, cj, ckq] = f_cpts(DYA, DXA, DXB, 0, k)
    float rb1 = na
    float rb2 = na
    float lam = na
    float s1 = cx1.size() > 1 ? cx1.stdev() : na
    float s2 = cx2.size() > 1 ? cx2.stdev() : na
    CE.clear()
    c_r2 := na
    c_pts := cy.size()
    c_nq := ckq.size()
    if cy.size() >= 60 and s1 > 0 and s2 > 0
        array<float> z1 = f_div(cx1, s1)
        array<float> z2 = f_div(cx2, s2)
        int nq = ckq.size()
        [m0, u0, v0, r0] = f_cv(cy, z1, z2, cq, cj, nq, 0.0)
        [m1, u1, v1, r1] = f_cv(cy, z1, z2, cq, cj, nq, 0.1)
        [m2, u2, v2, r2] = f_cv(cy, z1, z2, cq, cj, nq, 0.3)
        [m3, u3, v3, r3] = f_cv(cy, z1, z2, cq, cj, nq, 1.0)
        [m4, u4, v4, r4] = f_cv(cy, z1, z2, cq, cj, nq, 3.0)
        array<float> ms = array.from(m0, m1, m2, m3, m4)
        int ib = -1
        for i = 0 to 4
            if not na(ms.get(i)) and (ib < 0 or ms.get(i) < ms.get(ib))
                ib := i
        if ib >= 0
            float u = ib == 0 ? u0 : ib == 1 ? u1 : ib == 2 ? u2 : ib == 3 ? u3 : u4
            float v = ib == 0 ? v0 : ib == 1 ? v1 : ib == 2 ? v2 : ib == 3 ? v3 : v4
            array<float> er = ib == 0 ? r0 : ib == 1 ? r1 : ib == 2 ? r2 : ib == 3 ? r3 : r4
            lam := array.from(0.0, 0.1, 0.3, 1.0, 3.0).get(ib)
            rb1 := u / s1
            rb2 := v / s2
            c_r2 := f_r2c(cy, z1, z2, cq, nq, u, v)
            c_s1 := s1
            c_s2 := s2
            for i = 0 to 13 * (k + 1) - 1
                CE.push(na)
            for i = 0 to cy.size() - 1
                CE.set(ckq.get(cq.get(i)) * 13 + cj.get(i), er.get(i))
    CB1.push(rb1)
    CB2.push(rb2)
    CL.push(lam)
    [rck, nck] = f_cres(DYA, DXA, DXB, k, rb1, rb2)
    for j = 0 to 12
        RC.push(rck.get(j))

// ---------------------------------------------------------------- display helpers
f_pc(float x) =>
    na(x) ? 'N/A' : (x > 0 ? '+' : '') + str.tostring(x * 100, '#.#') + '%'
f_n2(float x) =>
    na(x) ? 'N/A' : str.tostring(x, '#.##')
f_wk(float m, float t, int T) =>
    string s = T < 8 ? 'N/A' : m < 0 and t <= -2 ? 'Worked' : m > 0 and t >= 2 ? 'Opposite' : 'Not clear'
    [s, T < 8 ? str.tostring(T) + ' quarters (needs 8)' : 'IC ' + f_n2(m) + ', t ' + f_n2(t) + ', ' + str.tostring(T) + ' quarters', s == 'Worked' ? color.lime : s == 'Opposite' ? color.red : color.gray]

// Line breaks at spaces, n characters a line at most, so the merged rows do not widen the table.
f_wrap(string s, int n) =>
    string out = ''
    int len = 0
    for x in str.split(s, ' ')
        int l = str.length(x)
        if len > 0 and len + 1 + l > n
            out += '\n'
            len := 0
        else if len > 0
            out += ' '
            len += 1
        out += x
        len += l
    out

var table tb = table.new(position.top_right, 12, 8, bgcolor = color.new(color.black, 10), border_width = 1)
f_c(int c, int r, string s, color col = color.white, string tt = '') =>
    table.cell(tb, c, r, s, text_color = col, text_size = size.small, text_halign = c == 0 ? text.align_left : text.align_center, tooltip = tt)

// ---------------------------------------------------------------- last bar: fits, tests, table
if barstate.islast
    int K = ST.size()
    table.clear(tb, 0, 0, 11, 7)
    if K == 0
        f_c(0, 0, 'FFV Peer Check: no quarterly snapshot yet (needs a 15 Feb / May / Aug / Nov bar on the chart)', color.orange)
    else
        // Live column K: today's prices with the latest figures; an entity whose EPS and book value per share
        // have not changed since the last snapshot keeps that snapshot's ROE and growth.
        for j = 0 to 12
            SP.push(LP.get(j))
            SE.push(LE.get(j))
            SB.push(LB.get(j))
        f_dcol(SP, SE, SB, DYA, DXA, DYB, DXB, K)
        for j = 0 to 12
            if f_g(SE, j, K) == f_g(SE, j, K - 1) and f_g(SB, j, K) == f_g(SB, j, K - 1)
                DXA.set(K * 13 + j, f_g(DXA, j, K - 1))
                DXB.set(K * 13 + j, f_g(DXB, j, K - 1))
        // Models A and B
        array<string> NM = array.from('A  P/B on ROE', 'B  P/E on growth', 'C  P/B on ROE + growth')
        array<float> slm = array.new_float(3)
        array<float> slt = array.new_float(3)
        array<int> slT = array.new_int(3, 0)
        array<float> r2 = array.new_float(3)
        array<int> nlv = array.new_int(3, 0)
        array<float> imp = array.new_float(3)
        array<float> gap = array.new_float(3)
        array<float> usu = array.new_float(3)
        array<bool> stb = array.from(false, false, false)
        array<string> why = array.from('', '', '')
        array<string> slx = array.from('N/A', 'N/A', 'N/A')
        array<float> wm = array.new_float(6)
        array<float> wt = array.new_float(6)
        array<int> wT = array.new_int(6, 0)
        array<float> RA = array.new_float(13 * (K + 1))
        array<float> RB = array.new_float(13 * (K + 1))
        array<float> EA = array.new_float(13 * K)
        array<float> EB = array.new_float(13 * K)
        for m = 0 to 1
            array<float> Y = m == 0 ? DYA : DYB
            array<float> X = m == 0 ? DXA : DXB
            array<float> R = m == 0 ? RA : RB
            array<float> ER = m == 0 ? EA : EB
            array<float> sl = array.new_float()
            array<float> sacc = array.new_float()
            array<float> r2s = array.new_float()
            float alive = na
            float blive = na
            for k = 0 to K
                array<float> xs = array.new_float()
                array<float> ys = array.new_float()
                array<int> js = array.new_int()
                for j = 1 to 12
                    float y = f_g(Y, j, k)
                    float x = f_g(X, j, k)
                    if not na(y) and not na(x)
                        xs.push(x)
                        ys.push(y)
                        js.push(j)
                int n = xs.size()
                if k == K
                    nlv.set(m, n)
                if n >= 6
                    [b, a] = f_ts(xs, ys, -1)
                    if not na(b)
                        sacc.push(b)
                        if k < K
                            sl.push(b)
                            r2s.push(f_r2(xs, ys, a, b))
                            for t = 0 to n - 1
                                [bt, at] = f_ts(xs, ys, t)
                                if not na(bt)
                                    ER.set(k * 13 + js.get(t), math.abs(ys.get(t) - at - bt * xs.get(t)))
                        float bb = sacc.avg()
                        float ab = f_icpt(xs, ys, bb)
                        if k == K
                            alive := ab
                            blive := bb
                        for j = 0 to 12
                            float y = f_g(Y, j, k)
                            float x = f_g(X, j, k)
                            if not na(y) and not na(x)
                                R.set(k * 13 + j, y - ab - bb * x)
            [fm, ft, fT] = f_nw(sl)
            slm.set(m, fm)
            slt.set(m, ft)
            slT.set(m, fT)
            [r2m, r2n] = f_avg(r2s)
            r2.set(m, r2m)
            stb.set(m, fT >= 8 and fm > 0 and ft >= 2)
            why.set(m, fT < 8 ? str.tostring(fT) + ' quarters with 6 peers (needs 8)' : not (fm > 0) ? 'slope not above 0' : not (ft >= 2) ? 'slope t ' + f_n2(ft) + ' (needs 2)' : '')
            slx.set(m, na(fm) ? 'N/A' : '+1% ' + (m == 0 ? 'ROE' : 'growth') + ': ' + (m == 0 ? 'P/B ' : 'P/E ') + f_pc(math.exp(fm * 0.01) - 1) + (na(ft) ? '' : ' (t ' + f_n2(ft) + ')'))
            float r0 = f_g(R, 0, K)
            float base = m == 0 ? f_g(SB, 0, K) : f_g(SE, 0, K)
            float x0 = f_g(X, 0, K)
            if not na(r0)
                gap.set(m, math.exp(r0) - 1)
                imp.set(m, math.exp(alive + blive * x0) * base)
            usu.set(m, f_prior(R, 0, K))
            [im, it, iT] = f_ic(R, SP, K, false)
            [cm, ct, cT] = f_ic(R, SP, K, true)
            wm.set(m * 2, im)
            wt.set(m * 2, it)
            wT.set(m * 2, iT)
            wm.set(m * 2 + 1, cm)
            wt.set(m * 2 + 1, ct)
            wT.set(m * 2 + 1, cT)
        // Model C: the latest snapshot's fit, today's intercept, halves for stability
        float cb1 = CB1.get(K - 1)
        float cb2 = CB2.get(K - 1)
        float clam = CL.get(K - 1)
        [rlive, nlive] = f_cres(DYA, DXA, DXB, K, cb1, cb2)
        nlv.set(2, nlive)
        array<float> RCX = RC.copy()
        for j = 0 to 12
            RCX.push(rlive.get(j))
        bool hok = false
        string hs = ''
        if not na(cb1)
            [hy, h1, h2, hq, hj, hkq] = f_cpts(DYA, DXA, DXB, 0, K - 1)
            int nh = hkq.size()
            int hm = int(math.floor(nh / 2))
            int ka = -1
            int kb = 0
            int kc = -1
            if nh >= 2
                ka := hkq.get(hm - 1)
                kb := hkq.get(hm)
                kc := K - 1
            [ay, a1, a2, aq, aj, akq] = f_cpts(DYA, DXA, DXB, 0, ka)
            [gy, g1_, g2_, gq, gj, gkq] = f_cpts(DYA, DXA, DXB, kb, kc)
            if ay.size() >= 30 and gy.size() >= 30
                [p1, p2, pw] = f_irls(ay, f_div(a1, c_s1), f_div(a2, c_s2), aq, aj, akq.size(), clam, -1)
                [q1, q2, qw] = f_irls(gy, f_div(g1_, c_s1), f_div(g2_, c_s2), gq, gj, gkq.size(), clam, -1)
                hok := p1 > 0 and p2 > 0 and q1 > 0 and q2 > 0
                hs := 'halves: ROE ' + f_n2(p1 / c_s1) + ' / ' + f_n2(q1 / c_s1) + ', growth ' + f_n2(p2 / c_s2) + ' / ' + f_n2(q2 / c_s2)
            else
                hs := 'halves: under 30 points each'
        stb.set(2, not na(cb1) and cb1 > 0 and cb2 > 0 and hok)
        why.set(2, na(cb1) ? 'needs 60 points in quarters with 8 peers (has ' + str.tostring(c_pts) + ')' : not (cb1 > 0 and cb2 > 0) ? 'a slope not above 0' : not hok ? 'not stable over the two halves (' + hs + ')' : '')
        slx.set(2, na(cb1) ? 'N/A' : '+1%: ROE ' + f_pc(math.exp(cb1 * 0.01) - 1) + ', growth ' + f_pc(math.exp(cb2 * 0.01) - 1))
        r2.set(2, na(cb1) ? na : c_r2)
        float rc0 = f_g(RCX, 0, K)
        if not na(rc0)
            gap.set(2, math.exp(rc0) - 1)
            imp.set(2, f_g(SP, 0, K) / math.exp(rc0))
        usu.set(2, f_prior(RCX, 0, K))
        [jm, jt, jT] = f_ic(RCX, SP, K, false)
        [km, kt, kT] = f_ic(RCX, SP, K, true)
        wm.set(4, jm)
        wt.set(4, jt)
        wT.set(4, jT)
        wm.set(5, km)
        wt.set(5, kt)
        wT.set(5, kT)
        // Errors: each model on its own points, and the winner on the points all eligible models share
        array<float> ma = array.new_float(3)
        array<int> mn = array.new_int(3, 0)
        for m = 0 to 2
            array<float> ER = m == 0 ? EA : m == 1 ? EB : CE
            [em, en] = f_avg(ER)
            ma.set(m, em)
            mn.set(m, en)
        array<bool> elig = array.new_bool(3, false)
        for m = 0 to 2
            elig.set(m, stb.get(m) and not na(gap.get(m)))
        array<float> cmn = array.new_float(3)
        array<float> cse = array.new_float(3)
        int ncom = 0
        array<float> c0a = array.new_float()
        array<float> c1a = array.new_float()
        array<float> c2a = array.new_float()
        for i = 0 to 13 * K - 1
            float ea = EA.get(i)
            float eb = EB.get(i)
            float ec = i < CE.size() ? CE.get(i) : na
            if (not elig.get(0) or not na(ea)) and (not elig.get(1) or not na(eb)) and (not elig.get(2) or not na(ec)) and (elig.get(0) or elig.get(1) or elig.get(2))
                ncom += 1
                c0a.push(ea)
                c1a.push(eb)
                c2a.push(ec)
        bool common = ncom >= 30
        int win = -1
        if elig.includes(true)
            for m = 0 to 2
                if elig.get(m)
                    array<float> e = m == 0 ? c0a : m == 1 ? c1a : c2a
                    if common
                        cmn.set(m, e.avg())
                        cse.set(m, e.stdev(false) / math.sqrt(e.size()))
                    else
                        cmn.set(m, ma.get(m))
                        array<float> ER = m == 0 ? EA : m == 1 ? EB : CE
                        array<float> ok = array.new_float()
                        for i = 0 to ER.size() - 1
                            if not na(ER.get(i))
                                ok.push(ER.get(i))
                        cse.set(m, ok.size() > 1 ? ok.stdev(false) / math.sqrt(ok.size()) : na)
            int best = -1
            for m = 0 to 2
                if elig.get(m) and (best < 0 or cmn.get(m) < cmn.get(best))
                    best := m
            float lim = cmn.get(best) + nz(cse.get(best))
            // one-standard-error rule: the simpler (single-metric) model within one SE of the best
            for m = 0 to 1
                if elig.get(m) and cmn.get(m) <= lim and (win < 0 or cmn.get(m) < cmn.get(win))
                    win := m
            if win < 0
                win := best
        // ---- table
        string tk = syminfo.ticker
        int npe = 0
        int nent = 0
        string miss = ''
        for i = 0 to 11
            string s = P.get(i)
            if s != '' and s != me and P.indexof(s) == i
                nent += 1
                if not na(LP.get(i + 1)) and not na(LB.get(i + 1)) and not na(LE.get(i + 1))
                    npe += 1
                else
                    miss += (miss == '' ? '' : ', ') + s
        f_c(0, 0, 'FFV Peer Check: ' + tk + ' vs ' + str.tostring(nent) + ' peers, ' + str.tostring(K) + ' quarterly snapshots since ' + str.format_time(ST.get(0), 'yyyy-MM', syminfo.timezone), color.yellow)
        table.merge_cells(tb, 0, 0, 11, 0)
        array<string> HD = array.from('Model', 'Peers today', 'Slope (FM avg)', 'Stable', 'Typical miss', 'R²', 'Implied price', 'Gap today', 'Usual gap', 'Change', 'Gap worked?', 'Change worked?')
        array<string> HT = array.from(
             'Each model regresses a log multiple on the metric theory says drives it (Damodaran\'s companion variables), across the peers, once a quarter. The chart stock is never part of the fit.',
             'Peers with the data for this model today (A, B: 6 needed; C: 8).',
             'Average of the quarterly slopes (Fama-MacBeth): the change in the multiple for 1 percentage point more of the metric. t: Newey-West, 3 lags (the 12-month figures overlap). C: the pooled slopes, standardised ridge chosen by leave-one-peer-out error.',
             'A, B: average slope above 0 with t 2 or more over 8 quarters or more. C: both slopes above 0 in the full fit and in each half of the history.',
             'Leave-one-out error: each peer predicted from the others, mean absolute log error shown as % of the price. The winner is chosen on the peer-quarters all stable models share (30 at least, else each on its own), by the one-standard-error rule.',
             'For reference only (it rewards fitting the peers you have). A, B: average over the quarters; C: within the quarters.',
             'The price at which the stock would sit on today\'s line: today\'s intercept (median over the peers) with the average slope so far.',
             'Today\'s price against the implied price. Negative: below the line (cheap vs peers).',
             'The stock\'s average gap over the stored quarters (4 needed), each from the line known at that date. Some stocks always sit below or above the line (governance, liquidity, state ownership).',
             'Gap today against the usual gap: the part of today\'s gap that is new.',
             'Did peers below the line beat peers above it over the next 12 months? Spearman rank correlation of each quarter\'s gap with the next 12 months\' price return across the peers (6 at least), averaged; t: Newey-West, 3 lags; 8 quarters needed. Worked: average below 0 with t -2 or lower. Opposite: above 0 with t 2 or more. Peers picked today are survivors and returns leave out cash dividends, so it leans optimistic.',
             'The same test for the change vs each peer\'s usual gap (its earlier quarters, 4 at least).')
        for c = 0 to 11
            f_c(c, 1, HD.get(c), color.yellow, HT.get(c))
        for m = 0 to 2
            int r = m + 2
            bool w = m == win
            color tc = w ? color.yellow : color.white
            [g1, g2, g3] = f_wk(wm.get(m * 2), wt.get(m * 2), wT.get(m * 2))
            [h1, h2, h3] = f_wk(wm.get(m * 2 + 1), wt.get(m * 2 + 1), wT.get(m * 2 + 1))
            float gp = gap.get(m)
            float us = usu.get(m)
            float ch = na(gp) or na(us) ? na : math.exp(math.log(1 + gp) - us) - 1
            f_c(0, r, (w ? '► ' : '') + NM.get(m), tc, m == 2 ? 'Huber regression (k 1.345) with an intercept per quarter, ridge ' + f_n2(clam) + ' on the standardised slopes; ' + str.tostring(c_pts) + ' points in ' + str.tostring(c_nq) + ' quarters. ' + hs : 'Theil-Sen line per quarter (median of the pairwise slopes): one or two odd peers barely move it.')
            f_c(1, r, str.tostring(nlv.get(m)), tc)
            f_c(2, r, slx.get(m), tc)
            f_c(3, r, stb.get(m) ? 'Yes' : 'No', stb.get(m) ? color.lime : color.gray, why.get(m))
            f_c(4, r, na(ma.get(m)) ? 'N/A' : '±' + str.tostring((math.exp(ma.get(m)) - 1) * 100, '#') + '%', tc, str.tostring(mn.get(m)) + ' peer-quarters' + (na(cmn.get(m)) ? '' : (common ? '; on the ' + str.tostring(ncom) + ' shared: ±' : '; own points: ±') + str.tostring((math.exp(cmn.get(m)) - 1) * 100, '#.#') + '% (SE ' + str.tostring(nz(cse.get(m)) * 100, '#.#') + ')'))
            f_c(5, r, na(r2.get(m)) ? 'N/A' : str.tostring(r2.get(m), '0.00'), tc)
            f_c(6, r, na(imp.get(m)) ? 'N/A' : str.tostring(imp.get(m), '#,###'), tc, m == 1 and not (f_g(SE, 0, K) > 0) ? 'EPS 0 or less' : '')
            f_c(7, r, f_pc(gp), na(gp) ? color.gray : gp < 0 ? color.lime : color.red)
            f_c(8, r, na(us) ? 'N/A' : f_pc(math.exp(us) - 1), tc)
            f_c(9, r, f_pc(ch), na(ch) ? color.gray : ch < 0 ? color.lime : color.red)
            f_c(10, r, g1, g3, g2)
            f_c(11, r, h1, h3, h2)
        string sm = ''
        if win >= 0
            float gp = gap.get(win)
            float us = usu.get(win)
            [g1, g2, g3] = f_wk(wm.get(win * 2), wt.get(win * 2), wT.get(win * 2))
            [h1, h2, h3] = f_wk(wm.get(win * 2 + 1), wt.get(win * 2 + 1), wT.get(win * 2 + 1))
            sm := tk + ' is ' + str.tostring(math.abs(gp) * 100, '#') + '% ' + (gp < 0 ? 'below' : 'above') + ' the peer line (' + NM.get(win) + ')' + (na(us) ? '; usual gap N/A' : ', usually ' + f_pc(math.exp(us) - 1) + ', so ' + f_pc(math.exp(math.log(1 + gp) - us) - 1) + ' vs usual') + '. In this sector the gap signal: ' + g1 + '; the change signal: ' + h1 + '. A question, not a buy or sell signal: check it against the fair value and the scorecard.'
        else
            sm := 'No reliable peer model for ' + tk + '. A: ' + (why.get(0) == '' ? 'N/A for this stock' : why.get(0)) + '. B: ' + (why.get(1) == '' ? 'N/A for this stock' : why.get(1)) + '. C: ' + (why.get(2) == '' ? 'N/A for this stock' : why.get(2)) + '.'
        f_c(0, 5, f_wrap(sm, 120), win >= 0 ? color.yellow : color.orange)
        table.merge_cells(tb, 0, 5, 11, 5)
        f_c(0, 6, f_wrap('Peers with price, EPS and book value today: ' + str.tostring(npe) + ' of ' + str.tostring(nent) + (miss == '' ? '' : ' (missing: ' + miss + ')'), 120), npe < 6 ? color.orange : color.gray)
        table.merge_cells(tb, 0, 6, 11, 6)
        f_c(0, 7, f_wrap('Display only. Peers only: a sector-wide bubble lifts the line too. A one-off loss or provision cuts ROE and growth for a year, so the stock can sit far above the line while the market looks through it: a large Change vs usual flags it. A peer\'s latest book value per share can be off around a bonus issue (TradingView data); the robust lines limit the effect. P/E vs past growth stands in for expected growth (no forecasts for peers); its slope is often below 0 (the market expects fast growth to fade, and in cyclical sectors P/E is lowest at the peak).', 120), color.gray)
        table.merge_cells(tb, 0, 7, 11, 7)
        // drop the live column
        for i = 1 to 13
            SP.pop()
            SE.pop()
            SB.pop()
            DYA.pop()
            DXA.pop()
            DYB.pop()
            DXB.pop()

```
