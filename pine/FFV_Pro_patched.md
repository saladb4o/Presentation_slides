# Fundamental Fair Value Pro: full patched script (phases 0–6)

Copy everything inside the code block into the Pine Editor and replace the whole script.

```pine
//@version=6
indicator('Fundamental Fair Value Pro (FF4 + McKinsey/Rev DCF) [Real-Time + Backtest]', shorttitle = 'FFV Pro (Real)', overlay = true, dynamic_requests = true)
// =====================================================================
// ARCHITECTURE: one top-to-bottom pass per bar
//   1. Helpers and types   pure maths, backtest state, the model stage: enums, the
//                          KIn / Res / Model / Claims records, engines, f_kin, f_eval
//   2. Inputs              then 2b: the model rows, one per model
//   3. Data                macro feeds; 31 financial fields through one request
//                          wrapper, released on report dates; TTM vault; claims record
//   4. Imputation engine   identity solver + firm-ratio carry, provenance tiers
//   5. Fundamentals        scores, NOPAT, invested capital, beta, cost of capital, growth
//   6. Models              the stream table, then every row through one inputs path and
//                          one claim bridge: Base on every bar, Bear/Bull on the last bar
//   7. Blends              Standard + Omnibus; track-record weights cached per quarter
//   8. Output              table (last bar), plots, backtester
// =====================================================================
// ==========================================
// 1. HELPER FUNCTIONS
// ==========================================
// Median of a sorted copy: the mean of the two middle values when the count is even.
f_median(array<float> a) =>
    int n = array.size(a)
    float r = na
    if n > 0
        array<float> s = array.copy(a)
        array.sort(s)
        r := n % 2 == 1 ? array.get(s, int(n / 2)) : (array.get(s, int(n / 2) - 1) + array.get(s, int(n / 2))) / 2.0
    r
// Average the TTM and forward legs when both exist, else take whichever does.
f_blend2(float a, float b) =>
    not na(a) and not na(b) ? (a + b) / 2 : nz(a, b)
f_harmonic_mean(array<float> a) =>
    float sr = 0.0
    int k = 0
    for v in a
        if v > 0
            sr += 1.0 / v
            k += 1
    sr > 0 ? k / sr : na
// Percentile (linear interpolation) from an ALREADY-SORTED array.
f_pct_sorted(array<float> s, float p) =>
    float idx = (array.size(s) - 1) * p
    int lo = int(math.floor(idx))
    int hi = int(math.ceil(idx))
    lo == hi ? array.get(s, lo) : array.get(s, lo) * (1 - (idx - lo)) + array.get(s, hi) * (idx - lo)
// Central tendency + both percentile legs from ONE sort. Stateless: the caller
// caches the result in the registry, recomputing only when the history changes.
f_ratio_stats(array<float> arr, bool use_mean, float dflt, float lo_p, float hi_p, int min_n) =>
    int n = array.size(arr)
    float ct = na
    float c_lo = na
    float c_hi = na
    if n > 0
        array<float> s = array.copy(arr)
        array.sort(s)
        ct := use_mean ? f_harmonic_mean(arr) : f_pct_sorted(s, 0.5)
        if n >= min_n
            c_lo := f_pct_sorted(s, lo_p)
            c_hi := f_pct_sorted(s, hi_p)
    [nz(ct, dflt), na(ct) or n < 4, c_lo, c_hi]
// Previous model stage (the shadow check in section 6 calls it; delete with the check):
// one multiple x one driver, price form, or EV form (driver x multiple - net debt) / shares.
f_apply(float drv, float mult, bool is_ev, float nd, float sh) =>
    na(drv) or drv <= 0 or na(mult) ? na : is_ev ? (drv * mult - nd) / sh : drv * mult
// Push a positive value (capped at cap), keeping at most max_n. Non-positive or na
// values are skipped, or pushed as na when keep_na: [FIX ALIGN] every array read
// pairwise against hist_px must keep index i meaning "the same quarter".
f_push(array<float> a, float v, int max_n, float cap, bool keep_na) =>
    bool ok = v > 0
    if ok or keep_na
        array.push(a, ok ? math.min(v, cap) : na)
        if array.size(a) > max_n
            array.shift(a)
// Signed version (held to +/-cap, na skipped) for histories whose medians must count the
// bad quarters too: ROE, EBIT / equity, FCFF margin.
f_push_s(array<float> a, float v, int max_n, float cap) =>
    if not na(v)
        array.push(a, math.max(math.min(v, cap), -cap))
        if array.size(a) > max_n
            array.shift(a)
// 0 below a, 1 above b, linear between: a premium phases in instead of stepping.
f_ramp(float x, float a, float b) =>
    math.min(math.max((x - a) / (b - a), 0.0), 1.0)
// Damodaran synthetic credit spread from interest cover (EBIT / interest).
f_synthetic_spread(float ebit, float interest) =>
    var array<float> cut = array.from(8.5, 6.5, 5.5, 4.25, 3.0, 2.5, 2.25, 2.0, 1.75, 1.5, 1.25, 0.8)
    var array<float> spr = array.from(0.0063, 0.0078, 0.0098, 0.0108, 0.0122, 0.0156, 0.0200, 0.0240, 0.0351, 0.0417, 0.0600, 0.0800, 0.1200)
    // Unknown EBIT or unknown interest: a mid (BBB) bucket, not the distressed or the AAA one.
    float icr = na(interest) ? 3.5 : interest > 0 ? nz(ebit / interest, 3.5) : 100.0
    int k = 0
    while k < 12 and not (icr > array.get(cut, k))
        k += 1
    array.get(spr, k)
// Scenario pick: s = 0 base, 1 bear, 2 bull.
f_sc(int s, float base, float bear, float bull) =>
    s == 0 ? base : s == 1 ? bear : bull
f_calculate_cagr_from_series(series_data, years) =>
    bool is_new_quarter = not na(series_data) and series_data != series_data[1]
    int changes_lookback = years * 4
    float past_val = ta.valuewhen(is_new_quarter, series_data, changes_lookback)
    float current_val = series_data
    float cagr = na
    if not na(current_val) and not na(past_val) and past_val > 0 and current_val > 0
        cagr := math.pow(current_val / past_val, 1.0 / years) - 1
    cagr
// ---- PREVIOUS MODEL STAGE: only the shadow check in section 6 calls the functions from
// here to f_calculate_eva; delete them with the check. The engines are in the model stage. ----
f_calculate_rim(nopat_base, invested_capital, shares, net_debt, wacc, growth_rate, terminal_growth, projection_years) =>
    float iv_rim = na
    float adjusted_term_growth = math.min(terminal_growth, wacc - 0.015)
    if not na(nopat_base) and not na(invested_capital) and invested_capital > 0 and not na(wacc) and not na(terminal_growth) and wacc > adjusted_term_growth
        capital_charge_base = invested_capital * wacc
        economic_profit_base = nopat_base - capital_charge_base
        float total_discounted_ep = 0.0
        float projected_ep = economic_profit_base
        for i = 1 to projection_years by 1
            // Stage-1 growth fades linearly to terminal, as in the DCF.
            float w = i / (projection_years + 1.0)
            projected_ep := projected_ep * (1 + growth_rate * (1 - w) + adjusted_term_growth * w)
            total_discounted_ep := total_discounted_ep + projected_ep / math.pow(1 + wacc, i)
        terminal_value_ep = projected_ep * (1 + adjusted_term_growth) / (wacc - adjusted_term_growth)
        discounted_terminal_value_ep = terminal_value_ep / math.pow(1 + wacc, projection_years)
        enterprise_value = invested_capital + total_discounted_ep + discounted_terminal_value_ep
        equity_value = enterprise_value - net_debt
        iv_rim := equity_value / shares
    iv_rim
// Value-driver DCF: FCF = NOPAT x (1 - g / RONIC). Year by year, FCF moves from today's
// (grown with NOPAT) to what is left after the reinvestment NEXT year's growth needs (this
// year's investment funds it), so heavy-investment years are not compounded forward and
// the explicit years meet the terminal value without a jump. Written on the growth path,
// not on FCF / NOPAT, so NOPAT <= 0 converges the same way (no jump at zero NOPAT).
// na ROIC: the driver is already a free cash flow (no reinvestment is charged).
f_calculate_dcf_value_driver_extended(fcf_per_share, nopat_per_share, roic_current, wacc, growth_stage1, growth_term, years_stage1) =>
    float pv_explicit = 0.0
    float cum = 1.0
    float adjusted_growth_term = math.min(growth_term, wacc - 0.015)
    // Return on new capital: today's ROIC fading to a terminal ROIC capped at 20%, neither
    // below the discount rate (a high-rate market must not turn every unit of growth into
    // value destruction). The cap binds at the terminal, not in the high-growth years.
    float roic_0 = math.max(roic_current, wacc)
    float terminal_roic = math.max(math.min(roic_current, 0.20), wacc)
    for i = 1 to years_stage1 by 1
        float weight = i / (years_stage1 + 1.0)
        float year_growth = growth_stage1 * (1.0 - weight) + adjusted_growth_term * weight
        float next_w = (i + 1) / (years_stage1 + 1.0)
        float next_growth = i < years_stage1 ? growth_stage1 * (1.0 - next_w) + adjusted_growth_term * next_w : adjusted_growth_term
        float wc = i / (years_stage1 * 1.0)
        cum *= 1 + year_growth
        float conv_target = na(roic_current) ? 1.0 : 1 - next_growth / (roic_0 * (1 - wc) + terminal_roic * wc)
        float current_fcf = fcf_per_share * cum * (1 - wc) + nopat_per_share * cum * conv_target * wc
        pv_explicit := pv_explicit + current_fcf / math.pow(1 + wacc, i)
    float current_nopat = nopat_per_share * cum
    float reinvestment_rate_term = na(roic_current) ? 0.0 : terminal_roic > 0 ? adjusted_growth_term / terminal_roic : 0.0
    float terminal_nopat = current_nopat * (1 + adjusted_growth_term)
    float terminal_fcf = terminal_nopat * (1 - reinvestment_rate_term)
    float tv_value = terminal_fcf / (wacc - adjusted_growth_term)
    float pv_tv = tv_value / math.pow(1 + wacc, years_stage1)
    float total_value = pv_explicit + pv_tv
    float implied_exit_multiple = current_nopat > 0 ? tv_value / current_nopat : na
    [total_value, implied_exit_multiple]
f_calculate_rule_of_x_fv(rev_growth, margin, total_revenue, net_debt, shares) =>
    float rule_40_score = (rev_growth + margin) * 100
    float rule_x_score = (rev_growth * 2.0 + margin) * 100
    // Continuous in both scores: 1x + 0.25x per Rule-of-40 point (floor 1.5x); the Rule-of-X
    // multiple (12x + 0.3x per point above 65, never below the base) phases in from 55 to 65.
    float base_mult = math.max(1.0 + rule_40_score * 0.25, 1.5)
    float x_mult = math.max(12.0 + (rule_x_score - 65) * 0.3, base_mult)
    float ramp = math.min(math.max((rule_x_score - 55) / 10.0, 0.0), 1.0)
    float fair_multiple = math.min(base_mult + (x_mult - base_mult) * ramp, 25.0)
    float target_ev = fair_multiple * total_revenue
    float target_equity_value = target_ev - net_debt
    shares > 0 ? target_equity_value / shares : na
f_calculate_rnpv_sotp(base_dcf_per_share, rnd_annual, shares) =>
    float capitalized_pipeline = rnd_annual * 5.0
    float risk_adjusted_pipeline_val = shares > 0 ? (capitalized_pipeline * 0.15) / shares : 0
    base_dcf_per_share + risk_adjusted_pipeline_val
// A regulated asset is worth its asset base scaled by the ratio of the return
// the regulator ALLOWS to the return investors REQUIRE:
// EV = RAB * (allowed_return - g) / (wacc - g)
f_calculate_rab_model(rab_base, allowed_return, wacc, growth, net_debt, shares) =>
    float rab_ev = na
    if not na(rab_base) and rab_base > 0 and not na(wacc) and wacc > 0
        // Keep g strictly below wacc or the perpetuity diverges.
        float g = math.min(nz(growth, 0.0), wacc - 0.005)
        float r = not na(allowed_return) and allowed_return > 0 ? allowed_return : wacc
        float rab_multiple = (r - g) / (wacc - g)
        rab_multiple := math.max(math.min(rab_multiple, 2.0), 0.5)
        rab_ev := rab_base * rab_multiple
    shares > 0 and not na(rab_ev) ? (rab_ev - net_debt) / shares : na
// Gordon growth DDM on the long-run terminal rate, held 1.5pt under the rate as in every
// other perpetuity here.
f_calculate_ddm(dps, coe, terminal_growth) =>
    float g = math.min(nz(terminal_growth, 0.02), coe - 0.015)
    not na(dps) and dps > 0 and coe > g ? (dps * (1 + g)) / (coe - g) : na
// [FIX EVA] Invested capital + PV(EVA) is FIRM value; subtract net debt for
// equity. Growth is the terminal rate, held 1.5pt under WACC like the DCF's.
f_calculate_eva(nopat, invested_capital, wacc, g_term, net_debt, shares) =>
    float g = math.min(g_term, wacc - 0.015)
    float current_eva = nopat - (invested_capital * wacc)
    float pv_eva = (current_eva * (1 + g)) / (wacc - g)
    shares > 0 ? (invested_capital + pv_eva - nz(net_debt)) / shares : na
// ==============================================================
// === UNIFIED MODEL WEIGHT (predictive, scale-free) ============
// ==============================================================
// [FIX W-PRED] One rule for every model: how well did the fair value stored at
// quarter i predict the price h quarters later? Log/relative errors only, so a
// 20 USD and a 20,000 VND quote score alike. Bias counts (MSE, not variance).
// No track record -> 0, never the maximum; callers equal-weight when nobody has one.
// algo: 0 IVW (inverse mean squared log error), 1 SMAPE, 2 MALE, 3 WMAPE, 4 RMSLE.
f_model_weight(array<float> fv, array<float> px, int algo, int h) =>
    float w = 0.0
    float e = na
    int np = math.min(array.size(fv), array.size(px)) - h
    if np >= 4
        float se = 0.0
        float sp = 0.0
        int k = 0
        for i = 0 to np - 1
            float f = array.get(fv, i)
            float p = array.get(px, i + h)
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
// [FIX TIERS] Down-weight models built on carried or guessed inputs, using
// the provenance tiers (3 reported, 2 exact identity, 1 carried, 0 guess).
f_tier_q(int t) =>
    t >= 3 ? 1.0 : t == 2 ? 0.85 : t == 1 ? 0.6 : 0.0 // tier 0 (pure guess) leaves the blend
f_wt_lbl(float w) =>
    w > 0 ? '  [' + str.tostring(w * 100, '#') + '%]' : ''
// ==============================================================
// === BACKTEST STATE (one ModelStats per registry model) =======
// ==============================================================
type PeriodStats
    int wins = 0
    int total = 0
    float gross_profit = 0.0
    float gross_loss = 0.0
    array<float> closed_returns
    array<float> closed_drawdowns
    array<float> closed_ann_returns
    array<float> closed_discounts
    array<float> closed_holds
type ModelStats
    PeriodStats is_stats
    PeriodStats oos_stats
    PeriodStats fwd_stats
    array<float> entry_prices
    array<float> floating_min_prices
    array<int> entry_bars
    array<float> entry_discounts
    array<int> entry_periods
    array<float> entry_divs
    int straddled = 0
    int last_entry = -999
f_new_period() =>
    PeriodStats.new(0, 0, 0.0, 0.0, array.new_float(), array.new_float(), array.new_float(), array.new_float(), array.new_float())
f_new_model() =>
    ModelStats.new(f_new_period(), f_new_period(), f_new_period(), array.new_float(), array.new_float(), array.new_int(), array.new_float(), array.new_int(), array.new_float())
// =====================================================================
// THE MODEL STAGE: named rows, engines, one inputs path, one claim bridge
// =====================================================================
// Each model is one ROW, declared once in section 2b with every fact about it: its level
// (which fixes the discount rate AND whether the claims ahead of common come off), its
// engine, the streams it reads, its add-on, its private scenario lever, family and Omnibus
// tick box. The ENGINES are declared here, above every input and data series, so the
// compiler stops them reading anything but the record they are handed. f_kin forms that
// record for Base, Bear and Bull on one path; f_eval runs the engine, adds the add-on and
// sends each leg through the one claim bridge. The result lands in the row's Res record for
// that scenario, which every consumer and tooltip reads.
enum Level
    firm = 'firm'
    unlev = 'unlevered'
    equity = 'equity'
    bank = 'bank'
// firm: WACC, claims come off | unlevered: the unlevered cost of capital, claims come off |
// equity: cost of equity, nothing comes off | bank: the bank RIM rate (cost of equity, at
// most 15%), nothing comes off.
enum Eng
    comp = 'blend'
    mult = 'multiple'
    vdcf = 'value-driver DCF'
    rim = 'residual income'
    eva = 'economic value added'
    perp = 'perpetuity'
    gperp = 'growing perpetuity'
    graham = 'Graham formula'
    rulex = 'Rule of 40 / X'
    ref = 'reference'
// comp: the Standard Composite row, filled by the blend and never evaluated | ref: builds on
// another row's core (rNPV on the DCF).
enum Group
    comp = 'composite'
    rel = 'relative multiple'
    sect = 'sector model'
    abs = 'absolute model'
// Relative multiples and absolute models run on every bar (the backtest reads every model);
// sector models run where the framework allocates them.
enum AddOn
    none = 'none'
    pipeline = 'pipeline'
    netco = 'NetCo'
    shield = 'tax shield'
// pipeline: rNPV, 5x annual R&D at 15% | NetCo: Unbundled, the network at a RAB multiple |
// tax shield: APV, on permanent debt. An add-on is a total, added before the claims.
enum Lever
    none = 'none'
    pctl = 'own-history percentiles'
    scale = 'scale'
    step = 'step'
// A row's private scenario rule. pctl: Bear/Bull take the low / high percentile of the
// ticker's own multiple | scale: Graham's growth x0.5 / x1.5 | step: Rule of 40's revenue
// growth -/+ a shift, Acquirer's multiple -/+ a step (Bear floor 1x).
// STREAMS: every input a model reads, each formed once per bar in the stream table
// (section 6). f_sunit and f_sown state each stream's unit and whose cash flow it is.
enum Sx
    none = '-'
    eps_b = 'EPS'
    eps_f = 'next-year EPS'
    sales_ps = 'sales per share'
    fcf_ps = 'FCF per share'
    bvps = 'book value per share'
    tbvps = 'tangible book per share'
    ebitda = 'EBITDA'
    ebitda_f = 'next-year EBITDA'
    ocf_ps = 'operating cash flow per share'
    fcff = 'unlevered FCF'
    nopat = 'NOPAT'
    ic = 'invested capital'
    roic = 'ROIC'
    fcff_s = 'ServeCo unlevered FCF'
    nopat_s = 'ServeCo NOPAT'
    ni = 'net income'
    book = 'book value'
    ni_ps = 'net income per share'
    roe_n = 'normalised ROE'
    fcfe = 'FCFE'
    dps = 'dividend per share'
    oe_ps = "owners' earnings per share"
    nopat_n = 'normalised NOPAT'
    eps_pos = 'trailing EPS'
    g_gra = 'Graham growth'
    yadj = 'bond-yield factor'
    rev = 'revenue'
    rev_g = 'revenue growth'
    fcf_margin = 'FCF margin'
    ebit = 'EBIT'
// eps_b is EPS, or 10-year inflation-adjusted EPS under CAPE. fcf_ps is also the AFFO
// proxy (there is no AFFO field). fcfe is derived on the one inputs path, NI x (1 - g / ROE),
// because it moves with the scenario's growth.
// Unit of a stream: 0 a total, 1 per share, 2 a ratio (-1 none). A row's streams share one
// unit, and a row that values the firm reads totals, because the claims are totals.
f_sunit(Sx s) =>
    switch s
        Sx.none => -1
        Sx.eps_b => 1
        Sx.eps_f => 1
        Sx.sales_ps => 1
        Sx.fcf_ps => 1
        Sx.bvps => 1
        Sx.tbvps => 1
        Sx.ocf_ps => 1
        Sx.ni_ps => 1
        Sx.fcfe => 1
        Sx.dps => 1
        Sx.oe_ps => 1
        Sx.eps_pos => 1
        Sx.roic => 2
        Sx.roe_n => 2
        Sx.g_gra => 2
        Sx.yadj => 2
        Sx.rev_g => 2
        Sx.fcf_margin => 2
        => 0
// Whose cash flow a stream is: 1 all capital providers (discounted at WACC or the unlevered
// cost), 2 common shareholders (at the cost of equity), 0 neither (a multiple's driver).
f_sown(Sx s) =>
    switch s
        Sx.fcff => 1
        Sx.nopat => 1
        Sx.ic => 1
        Sx.roic => 1
        Sx.fcff_s => 1
        Sx.nopat_s => 1
        Sx.nopat_n => 1
        Sx.ni => 2
        Sx.book => 2
        Sx.ni_ps => 2
        Sx.roe_n => 2
        Sx.fcfe => 2
        Sx.fcf_ps => 2
        Sx.dps => 2
        Sx.oe_ps => 2
        => 0
// What an engine sees, and nothing else: the rate and growths after the scenario move and
// the one terminal cap, the row's streams and its lever.
type KIn
    float rate = na
    float g1 = na
    float gT = na
    float gT0 = na
    int yrs = 10
    float cf = na
    float earn = na
    float ret = na
    float cap = na
    float drv = na
    float drv_f = na
    float mult = na
    float gx = na
    float adj = na
    float ref = na
// rate: the level's discount rate | g1: stage-1 growth | gT: terminal growth, held TCAP under
// the rate | gT0: before that cap (NetCo keeps its own 0.5pt margin) | yrs: explicit years |
// cf, earn, ret, cap: cash flow, earnings, return on new capital (na: the cash flow is
// already free), capital base | drv, drv_f, mult: a multiple's driver, next year's driver,
// the multiple | gx, adj: a rule's growth after its lever, and its second input (Graham's
// bond-yield factor, Rule of 40's FCF margin) | ref: a reference row's source core.
// One scenario's result for one row: what every consumer and tooltip reads.
type Res
    KIn x
    float core = na
    float add = 0.0
    float cl = 0.0
    float sh = na
    float spot = na
    float fwd = na
    float aux = na
    float value = na
    string why = ''
    int bar = -1
// core: the engine's output, a total (per share for a per-share row) | add: the add-on | cl:
// the claims taken off | sh: the shares divided by (na for a per-share row) | spot, fwd: the
// legs per share, the forward one discounted a year | aux: the DCF's implied exit EV / NOPAT
// | value: the row's value | why: why it is N/A | bar: the bar it was computed on.
// Index: 0 Standard Composite | 1-8 relative multiples | 9-15 sector models | 16-22 absolute
// models, in declaration order (section 2b). The blends still walk the rows in this order.
// hist: ratio history (own multiples) | fvh: stored fair values, aligned with hist_px | fw:
// the framework allocates it; on: allocated and computable this bar | std: in the Standard
// blend's scope | trk: track-record weight, re-scored once a quarter | w: Standard-blend
// share (0 outside it); om / om_w: Omnibus member and share.
type Model
    string code
    string name
    string bt_name
    Group grp = Group.abs
    Level level = Level.firm
    Eng eng = Eng.mult
    int fam = 0
    Sx s_cf = Sx.none
    Sx s_earn = Sx.none
    Sx s_ret = Sx.none
    Sx s_cap = Sx.none
    Sx s_drv = Sx.none
    Sx s_fwd = Sx.none
    Sx s_gx = Sx.none
    Sx s_adj = Sx.none
    Sx need1 = Sx.none
    Sx need2 = Sx.none
    Sx t1 = Sx.none
    Sx t2 = Sx.none
    AddOn addon = AddOn.none
    string src = ''
    Lever lk = Lever.none
    float lv_bear = 0.0
    float lv_bull = 0.0
    float lv_floor = na
    float m0 = na
    bool tick = true
    float dflt = na
    bool rkv = false
    int idx = -1
    int src_i = -1
    int held_by = -1
    bool ps = false
    array<Res> res
    array<float> hist
    array<float> fvh
    ModelStats bt
    bool fw = false
    bool on = false
    bool std = false
    int tier = 3
    float drv = na
    float avg = na
    bool syn = true
    float plo = na
    float phi = na
    float fv = na
    float lo = na
    float hi = na
    float trk = 0.0
    float w = 0.0
    bool om = false
    float om_w = 0.0
// Row fields: s_* the streams by role (cash flow, earnings, return on capital, capital,
// driver, next year's driver, a rule's growth and second input) | need1/2: streams that must
// be positive for a value (a relative multiple is off without them) | t1/t2: tier sources (the row takes the worse tier) | src: the
// row a reference row builds on | lk, lv_*: the lever, its Bear / Bull moves, a Bear floor |
// m0: a rule multiple's target | tick: Omnibus tick box | dflt: an own multiple with no
// history | rkv: P/B drops value-trap quarters. Derived on bar 0: idx, src_i, held_by (the
// row that holds this one: rNPV holds the DCF, P/FCF holds P/AFFO), ps (per-share streams).
enum Claim
    netdebt = 'net debt'
    minority = 'minority interest'
    preferred = 'preferred'
// THE CLAIMS RECORD, rebuilt every bar (section 4): what ranks ahead of common, by claim.
type Claims
    map<Claim, float> amt
    float sum = 0.0
    float shares = na
// THE ONE CLAIM BRIDGE: a firm total less the claims ahead of common, then divided once by
// the shares; an equity total is only divided; a per-share value passes through.
method bridge(Claims c, float v, bool firm, bool per_share) =>
    per_share ? v : (firm ? v - c.sum : v) / c.shares
// 'net debt, minority interest and preferred': the claims counted, for the tooltips.
method txt(Claims c) =>
    array<Claim> k = c.amt.keys()
    string t = ''
    for [i, x] in k
        t += (i == 0 ? '' : i == k.size() - 1 ? ' and ' : ', ') + str.tostring(x)
    t
// The per-bar inputs of the model stage (filled in section 6; f_kin is its only reader):
// the stream table and each stream's provenance tier, the base rate of each level, today's
// scenario shifts, growth, and the add-ons' inputs (totals).
type Drv
    map<Sx, float> s
    map<Sx, int> t
    float r_firm = na
    float r_unlev = na
    float r_eq = na
    float r_bank = na
    float sh_r = 0.0
    float sh_g = 0.0
    float sh_t = 0.0
    float g1 = na
    float gcap = na
    float gT = na
    int yrs = 10
    int yrs_rim = 10
    float fwd_disc = 1.0
    float pipe = na
    float netco_rab = na
    float allowed = 0.0
    float shield = na
method stream(Drv d, Sx k, float v, int tier) =>
    d.s.put(k, v)
    d.t.put(k, tier)
// ---------- ENGINES: pure functions, declared above every input and data series ----------
// Terminal growth reaches an engine already held TCAP under its rate (f_kin), so no engine
// caps it again.
float TCAP = 0.015
f_mult(float drv, float mult) =>
    na(drv) or drv <= 0 or na(mult) ? na : drv * mult
// Value-driver DCF: FCF = NOPAT x (1 - g / RONIC). Year by year, FCF moves from today's
// (grown with NOPAT) to what is left after the reinvestment NEXT year's growth needs (this
// year's investment funds it), so heavy-investment years are not compounded forward and
// the explicit years meet the terminal value without a jump. Written on the growth path,
// not on FCF / NOPAT, so NOPAT <= 0 converges the same way (no jump at zero NOPAT).
// na return on capital: the cash flow is already free (no reinvestment is charged).
// Return on new capital: today's fading to a terminal return capped at 20%, neither below
// the discount rate (a high-rate market must not turn every unit of growth into value
// destruction). The cap binds at the terminal, not in the high-growth years.
f_vdcf(float cf, float earn, float ret, float rate, float g1, float gT, int yrs) =>
    float pv = 0.0
    float cum = 1.0
    float r0 = math.max(ret, rate)
    float rT = math.max(math.min(ret, 0.20), rate)
    for i = 1 to yrs by 1
        float w = i / (yrs + 1.0)
        float yg = g1 * (1.0 - w) + gT * w
        float nw = (i + 1) / (yrs + 1.0)
        float ng = i < yrs ? g1 * (1.0 - nw) + gT * nw : gT
        float wc = i / (yrs * 1.0)
        cum *= 1 + yg
        float conv = na(ret) ? 1.0 : 1 - ng / (r0 * (1 - wc) + rT * wc)
        pv := pv + (cf * cum * (1 - wc) + earn * cum * conv * wc) / math.pow(1 + rate, i)
    float e_n = earn * cum
    float reinv = na(ret) ? 0.0 : rT > 0 ? gT / rT : 0.0
    float tv = e_n * (1 + gT) * (1 - reinv) / (rate - gT)
    [pv + tv / math.pow(1 + rate, yrs), e_n > 0 ? tv / e_n : na]
// Residual income: capital + PV of economic profit (stage-1 growth fading to terminal, as in
// the DCF) + its terminal value.
f_rim(float earn, float cap, float rate, float g1, float gT, int yrs) =>
    float v = na
    if not na(earn) and not na(cap) and cap > 0 and not na(rate) and not na(gT) and rate > gT
        float ep = earn - cap * rate
        float pv = 0.0
        for i = 1 to yrs by 1
            float w = i / (yrs + 1.0)
            ep := ep * (1 + g1 * (1 - w) + gT * w)
            pv := pv + ep / math.pow(1 + rate, i)
        v := cap + pv + ep * (1 + gT) / (rate - gT) / math.pow(1 + rate, yrs)
    v
// Rule of 40 / X: continuous in both scores. 1x EV / sales + 0.25x per Rule-of-40 point
// (floor 1.5x); the Rule-of-X multiple (12x + 0.3x per point above 65, never below the base)
// phases in from 55 to 65; capped at 25x. Needs a year-ago revenue (growth not na).
f_rulex(float g, float margin, float rev) =>
    float v = na
    if not na(g)
        float r40 = (g + margin) * 100
        float rx = (g * 2.0 + margin) * 100
        float base_m = math.max(1.0 + r40 * 0.25, 1.5)
        float x_m = math.max(12.0 + (rx - 65) * 0.3, base_m)
        float ramp = math.min(math.max((rx - 55) / 10.0, 0.0), 1.0)
        v := math.min(base_m + (x_m - base_m) * ramp, 25.0) * rev
    v
// A regulated asset is worth its asset base scaled by the ratio of the return the regulator
// ALLOWS to the return investors REQUIRE: RAB x (allowed - g) / (rate - g), held to 0.5-2x.
// Its growth keeps its own 0.5pt margin under the rate, as before.
f_rab(float rab, float allowed, float rate, float g) =>
    float v = na
    if not na(rab) and rab > 0 and not na(rate) and rate > 0
        float gg = math.min(nz(g, 0.0), rate - 0.005)
        float r = not na(allowed) and allowed > 0 ? allowed : rate
        v := rab * math.max(math.min((r - gg) / (rate - gg), 2.0), 0.5)
    v
// One engine per kind of model; each returns its value and an auxiliary (the DCF's implied
// exit multiple). EVA: capital + PV(EVA), EVA growing at terminal. Perpetuity: no growth.
// Growing perpetuity: Gordon growth at terminal. Graham: EPS x (8.5 + 2g) x the bond-yield
// factor. Reference: the source row's core.
f_engine(Eng e, KIn x) =>
    float v = na
    float aux = na
    if e == Eng.mult
        v := f_mult(x.drv, x.mult)
    else if e == Eng.vdcf
        [a, b] = f_vdcf(x.cf, x.earn, x.ret, x.rate, x.g1, x.gT, x.yrs)
        v := a
        aux := b
    else if e == Eng.rim
        v := f_rim(x.earn, x.cap, x.rate, x.g1, x.gT, x.yrs)
    else if e == Eng.eva
        v := x.cap + (x.earn - x.cap * x.rate) * (1 + x.gT) / (x.rate - x.gT)
    else if e == Eng.perp
        v := x.cf / x.rate
    else if e == Eng.gperp
        v := x.cf > 0 and x.rate > x.gT ? x.cf * (1 + x.gT) / (x.rate - x.gT) : na
    else if e == Eng.graham
        v := x.earn * (8.5 + 2 * x.gx * 100) * x.adj
    else if e == Eng.rulex
        v := f_rulex(x.gx, x.adj, x.drv)
    else if e == Eng.ref
        v := x.ref
    else
        runtime.error('No engine case for ' + str.tostring(e))
        v := na
    [v, aux]
// ---------- THE ROW REGISTRY ----------
var array<Model> MD = array.new<Model>()
// Model families: models that share a driver move together, so no family may hold more
// than 40% of a blend once 3+ families are present (with 2, a cap would force 50/50 and
// erase the track-record weights, so they only normalise). 0 Composite | 1 earnings / returns |
// 2 sales | 3 cash flow | 4 book | 5 EBIT(DA) | 6 dividends. (P/AFFO reads the FCF
// figure: no AFFO field exists, so it is a cash-flow model like P/FCF. Equity Cash Flow is
// net income less the equity growth needs, on ROE: an earnings model, like the bank RIM.)
// One entry per row, from its fam field.
var array<int> FAM = array.new_int()
// Declare a row: its results records (one per scenario), histories and backtest state.
f_add(Model m) =>
    m.idx := MD.size()
    m.res := array.from(Res.new(KIn.new()), Res.new(KIn.new()), Res.new(KIn.new()))
    m.hist := array.new_float()
    m.fvh := array.new_float()
    m.bt := f_new_model()
    MD.push(m)
    FAM.push(m.fam)
    m
// A row's private scenario rule, as today: Graham scales its growth x0.5 / x1.5, Rule of 40
// shifts revenue growth, Acquirer's steps its multiple (its Bear never under 1x).
f_lever(Model m, int s, float base) =>
    float v = base
    if s > 0 and m.lk == Lever.scale
        v := base * (s == 1 ? m.lv_bear : m.lv_bull)
    else if s > 0 and m.lk == Lever.step
        v := base + (s == 1 ? m.lv_bear : m.lv_bull)
        v := s == 1 and not na(m.lv_floor) ? math.max(v, m.lv_floor) : v
    v
f_rate0(Drv d, Level l) =>
    l == Level.firm ? d.r_firm : l == Level.unlev ? d.r_unlev : l == Level.equity ? d.r_eq : d.r_bank
// THE ONE INPUTS PATH, for Base (s = 0), Bear (1) and Bull (2) alike: today's scenario rules
// (Bear raises the rate and lowers both growths, Bull the reverse, the floors as they were),
// the one terminal cap, the row's lever and its streams. Fills x in place.
f_kin(Model m, Drv d, int s, KIn x) =>
    float r0 = f_rate0(d, m.level)
    x.rate := s == 0 ? r0 : s == 1 ? r0 + d.sh_r : math.max(r0 - d.sh_r, 0.02)
    x.g1 := s == 0 ? d.g1 : s == 1 ? math.max(d.g1 - d.sh_g, -0.05) : math.min(d.g1 + d.sh_g, d.gcap)
    x.gT0 := s == 0 ? d.gT : s == 1 ? math.max(d.gT - d.sh_t, 0.0) : d.gT + d.sh_t
    x.gT := math.min(x.gT0, x.rate - TCAP)
    x.yrs := m.eng == Eng.rim ? d.yrs_rim : d.yrs
    x.cf := m.s_cf == Sx.fcfe ? d.s.get(Sx.ni_ps) * (1 - x.g1 / d.s.get(Sx.roe_n)) : d.s.get(m.s_cf)
    x.earn := d.s.get(m.s_earn)
    x.ret := d.s.get(m.s_ret)
    x.cap := d.s.get(m.s_cap)
    x.drv := d.s.get(m.s_drv)
    x.drv_f := d.s.get(m.s_fwd)
    x.mult := m.lk == Lever.pctl ? f_sc(s, m.avg, m.plo, m.phi) : f_lever(m, s, m.m0)
    x.gx := f_lever(m, s, d.s.get(m.s_gx))
    x.adj := d.s.get(m.s_adj)
    x
// A row's add-on, a total: added before the claims come off and before the one division.
f_addon(AddOn a, KIn x, Drv d) =>
    switch a
        AddOn.pipeline => d.pipe
        AddOn.netco => f_rab(d.netco_rab, d.allowed, x.rate, x.gT0)
        AddOn.shield => d.shield
        => 0.0
// ONE EVALUATION of a row in scenario s: its inputs, the positive-input check, the engine,
// the add-on, then each leg through the one claim bridge and the legs blended. The result
// lands in the row's Res record for s.
f_eval(Model m, Drv d, Claims c, int s) =>
    Res r = m.res.get(s)
    KIn x = f_kin(m, d, s, r.x)
    if m.eng == Eng.ref
        Res sr = MD.get(m.src_i).res.get(s)
        x.ref := sr.bar == bar_index ? sr.core : na
    if s == 0
        m.drv := x.drv
    bool firm = m.level == Level.firm or m.level == Level.unlev
    r.bar := bar_index
    r.cl := firm ? c.sum : 0.0
    r.sh := m.ps ? na : c.shares
    r.add := f_addon(m.addon, x, d)
    r.core := na
    r.aux := na
    r.spot := na
    r.fwd := na
    r.value := na
    bool ok = (m.need1 == Sx.none or d.s.get(m.need1) > 0) and (m.need2 == Sx.none or d.s.get(m.need2) > 0)
    if ok
        [v, aux] = f_engine(m.eng, x)
        r.core := v
        r.aux := m.ps or not na(c.shares) ? aux : na
        r.spot := c.bridge(v + r.add, firm, m.ps)
        r.value := r.spot
        if m.s_fwd != Sx.none
            r.fwd := c.bridge(f_mult(x.drv_f, x.mult) + r.add, firm, m.ps) / d.fwd_disc
            r.value := f_blend2(r.spot, r.fwd)
    r.why := not ok ? 'needs positive ' + str.tostring(d.s.get(m.need1) > 0 ? m.need2 : m.need1) : not na(r.value) ? '' : m.eng == Eng.mult and not (x.drv > 0) ? 'needs positive ' + str.tostring(m.s_drv) : 'inputs missing'
    r.value
f_stier(Drv d, Sx s) =>
    s == Sx.none ? 3 : nz(d.t.get(s), 3)
// Provenance tier of a row: the worse of its tier sources' tiers.
f_tier(Model m, Drv d) =>
    math.min(f_stier(d, m.t1), f_stier(d, m.t2))
f_same_streams(Model a, Model b) =>
    a.s_cf == b.s_cf and a.s_earn == b.s_earn and a.s_ret == b.s_ret and a.s_cap == b.s_cap and a.s_drv == b.s_drv and a.s_fwd == b.s_fwd and a.s_gx == b.s_gx and a.s_adj == b.s_adj
// Bar 0: derive what the rows imply (units, reference sources, relations) and stop the
// script on a row that contradicts itself, before any value is shown.
f_rows_check() =>
    for [i, m] in MD
        string e = ''
        for [j, q] in MD
            if j != i and q.code == m.code
                e += ' shares its code with another row;'
        if m.eng != Eng.comp
            int u = -1
            for x in array.from(m.s_cf, m.s_earn, m.s_cap, m.s_drv, m.s_fwd)
                int ux = f_sunit(x)
                if ux == 0 or ux == 1
                    if u >= 0 and ux != u
                        e += ' mixes per-share and total streams;'
                    u := ux
            m.ps := u == 1
            bool firm = m.level == Level.firm or m.level == Level.unlev
            if firm and m.ps
                e += ' values the firm on per-share streams (the claims are totals);'
            if m.addon != AddOn.none and not firm
                e += ' has an add-on but is not valued at firm level;'
            if m.eng == Eng.vdcf or m.eng == Eng.rim or m.eng == Eng.eva or m.eng == Eng.perp or m.eng == Eng.gperp
                for x in array.from(m.s_cf, m.s_earn, m.s_ret, m.s_cap)
                    int o = f_sown(x)
                    if o > 0 and (o == 1) != firm
                        e += ' discounts ' + str.tostring(x) + ' at the ' + str.tostring(m.level) + ' rate;'
            if m.eng == Eng.ref
                for [j, q] in MD
                    if q.code == m.src
                        m.src_i := j
                if m.src_i < 0
                    e += ' references no row;'
                else
                    Model sm = MD.get(m.src_i)
                    if sm.eng == Eng.ref or sm.grp == Group.sect
                        e += ' references a row that is not computed on every bar;'
        if e != ''
            runtime.error('Model row ' + m.code + ':' + e)
    // Relations, derived: a reference row holds its source (rNPV holds the DCF); two rows with
    // the same streams, engine and level and no add-on are one model counted twice (P/FCF and
    // P/AFFO). The Omnibus drops the held row once its holder carries weight.
    for [i, a] in MD
        if a.eng == Eng.ref
            Model sm = MD.get(a.src_i)
            sm.held_by := i
        else if a.eng != Eng.comp
            for [j, b] in MD
                if j > i and b.eng == a.eng and b.level == a.level and a.addon == AddOn.none and b.addon == AddOn.none and f_same_streams(a, b)
                    b.held_by := i
    for [i, m] in MD
        if m.held_by > i
            runtime.error('Model row ' + m.code + ': the row holding it must be declared before it.')
    true
// Reverse DCF: the constant 10-year growth at which unlevered FCF at the discount rate,
// through the one claim bridge, equals the price. Terminal growth held TCAP under the rate,
// as in the DCF it is compared with.
f_calculate_reverse_dcf(float current_price, float fcf_total, Claims c, float discount_rate, float term_growth, int years) =>
    float low = -0.50
    float high = 1.00
    float solved_g = na
    float tg = math.min(term_growth, discount_rate - TCAP)
    if fcf_total > 0 and current_price > 0 and c.shares > 0
        for i = 0 to 14 by 1
            float mid = (low + high) / 2
            float pv = 0.0
            float curr_fcf = fcf_total
            for y = 1 to years by 1
                curr_fcf := curr_fcf * (1 + mid)
                pv := pv + curr_fcf / math.pow(1 + discount_rate, y)
            float term_val = curr_fcf * (1 + tg) / (discount_rate - tg)
            float pv_term = term_val / math.pow(1 + discount_rate, years)
            float model_price = c.bridge(pv + pv_term, true, false)
            if model_price > current_price
                high := mid
            else
                low := mid
        solved_g := (low + high) / 2
    solved_g
// Normalise the registry-ordered weights (one per row) to 1 in place, then cap each family's
// share and hand the excess to the uncapped families pro rata (a few passes converge).
f_fam_cap(array<float> w) =>
    float tot = array.sum(w)
    if tot > 0
        array<float> fs = array.new_float(7, 0.0)
        for i = 0 to array.size(w) - 1
            float x = array.get(w, i) / tot
            array.set(w, i, x)
            int f = array.get(FAM, i)
            array.set(fs, f, array.get(fs, f) + x)
        int nf = 0
        for y in fs
            nf += y > 0 ? 1 : 0
        float cap = math.max(0.4, 1.0 / nf)
        for it = 0 to 5
            float over = 0.0
            float room = 0.0
            // A family at (or within 1e-12 of) the cap is frozen there; the rest absorb the excess.
            for y in fs
                over += math.max(y - cap, 0.0)
                room += y < cap - 1e-12 ? y : 0.0
            if nf >= 3 and over > 1e-9 and room > 0
                for i = 0 to array.size(w) - 1
                    float fx = array.get(fs, array.get(FAM, i))
                    array.set(w, i, array.get(w, i) * (fx >= cap - 1e-12 ? cap / fx : 1 + over / room))
                for f = 0 to 6
                    float fx = array.get(fs, f)
                    array.set(fs, f, fx >= cap - 1e-12 ? (fx > 0 ? cap : 0.0) : fx * (1 + over / room))
    w
// Band half-width: the members' spread around the blend, weighted by their shares (w sums
// to 1), so a model with a 2% share cannot widen it like one with 40%. Floor = the 15%
// one-model default / sqrt(effective member count): a blend that is effectively one
// model keeps the one-model band instead of collapsing to zero.
f_wsd(array<float> v, array<float> w, float mu) =>
    float ss = 0.0
    float w2 = 0.0
    for [i, x] in v
        float wi = array.get(w, i)
        ss += wi * (x - mu) * (x - mu)
        w2 += wi * wi
    w2 > 0 ? math.max(math.sqrt(ss), 0.15 * mu * math.sqrt(w2)) : na
// ==========================================
// 2. INPUTS
// ==========================================
group_industry = 'Industry-Specific Valuation'
i_industry = input.string('Auto-Detect', 'Valuation Framework', options =['Auto-Detect', 'Technology', 'Healthcare (Pharma/Biotech)', 'Financials (Bank/Insurance)', 'REITs', 'Energy/Materials', 'Capital Goods/Industrials', 'Consumer Discretionary', 'Consumer Staples', 'Telecom', 'Utilities', 'General/Diversified'], group = group_industry, tooltip = 'Auto-Detect maps syminfo.sector (and syminfo.industry for Finance) to a framework.\nGeneral/Diversified enables every model.')
i_rf_ticker_manual = input.symbol('', 'Manual Risk-Free Rate Ticker (Optional)', group = group_industry, tooltip = 'If set, overrides the Auto-Detect logic. Use TVC Bond Yield tickers (e.g. TVC:VN10Y).')
i_lr_infl = input.float(0.0, 'Long-run inflation % (0 = auto by currency)', minval = 0, maxval = 15, step = 0.25, group = group_industry, tooltip = 'Replaces the CPI feed. Drives terminal growth and the CAPE inflation adjustment. 0 uses the per-currency default in the code.') / 100
i_lr_rgdp = input.float(0.0, 'Long-run real GDP growth % (0 = auto by currency)', minval = 0, maxval = 10, step = 0.25, group = group_industry, tooltip = 'Replaces the GDP feed. Only used in the nominal-growth ceiling on terminal growth.') / 100
i_financial_model_type = input.string('Auto (by industry)', 'Financials Valuation Model', options = ['Auto (by industry)', 'Equity Model (Bank/Insurer)', 'Entity Model (Brokerage/FinTech)'], group = group_industry, tooltip = 'Auto: banks and insurers use the Equity model (Net Income / Book); brokers, asset managers and lenders use the Entity model (NOPAT / Invested Capital).')
group_scen = 'Scenario Analysis (Bear / Base / Bull)'
i_scen_fair_band = input.float(15.0, 'Fair-value band +/- %', group = group_scen, minval = 0, maxval = 40, step = 1, tooltip = 'A scenario cell within this distance of the current price shades amber. Beyond it, green (price below the case) or red (price above it).\n\nSet to 0 for a hard red/green flip at the price.') / 100
i_scen_min_n = input.int(8, 'Min quarters for multiple percentiles', group = group_scen, minval = 4, maxval = 20, tooltip = 'Below this many stored observations the Bear/Bull cells stay blank instead of quoting a quartile built on a few points.')
i_scen_lo_pct = input.float(25.0, 'Bear percentile', group = group_scen, minval = 5, maxval = 45, step = 5) / 100
i_scen_hi_pct = input.float(75.0, 'Bull percentile', group = group_scen, minval = 55, maxval = 95, step = 5) / 100
i_scen_wacc_bps = input.float(100, 'DCF scenario: WACC shift (bps)', group = group_scen, minval = 0, maxval = 400, step = 25, tooltip = 'Bear raises the discount rate by this much and lowers terminal growth; Bull does the reverse.') / 10000
i_scen_g_bps = input.float(50, 'DCF scenario: terminal growth shift (bps)', group = group_scen, minval = 0, maxval = 200, step = 25) / 10000
i_scen_growth_bps = input.float(200, 'DCF scenario: explicit growth shift (bps)', group = group_scen, minval = 0, maxval = 1000, step = 50, tooltip = 'Bear lowers the stage-1 growth rate by this much, Bull raises it.') / 10000
i_scen_acq_delta = input.float(2.0, "Acquirer's Multiple: EBIT multiple +/-", group = group_scen, minval = 0, maxval = 6, step = 0.5)
i_scen_r40_bps = input.float(300, 'Rule of 40: revenue growth shift (bps)', group = group_scen, minval = 0, maxval = 1000, step = 50) / 10000
i_rab_allowed_return = input.float(0.0, 'Regulatory Allowed Return %', group = group_industry, minval = 0.0, maxval = 20.0, step = 0.25, tooltip = 'The post-tax return the regulator permits on the asset base.\n\n0 = assume the allowed return equals WACC, giving a 1.0x RAB multiple.') / 100
group_factors = 'Factor Models (VN 5-Factor)'
i_use_factors = input.bool(true, '✨ Use Live Index-Based Factor Premium', group = group_factors)
i_small_etf = input.symbol('IJR', 'Small Cap ETF (SMB Proxy)', group = group_factors, tooltip = "IJR (S&P 600) is preferred over IWM (Russell 2000) due to its profitability filter, yielding a truer size premium.")
i_value_etf = input.symbol('VTV', 'Value ETF (HML Proxy)', group = group_factors)
i_growth_etf = input.symbol('VUG', 'Growth ETF', group = group_factors)
i_mom_prem = input.float(1.0, 'Max Momentum Premium %', group = group_factors) / 100
i_liq_prem = input.float(2.0, 'Max Liquidity Premium %', group = group_factors) / 100
group_risk = 'Cost of Equity (CAPM)'
i_auto_calc_erp_crp = input.bool(true, '✨ Auto-Calculate Risk Premiums', group = group_risk, tooltip = 'ERP: half the market proxy 5-year return over its own currency 10Y (US 10Y for SPY, VN 10Y for VNINDEX) plus half a 5% long-run anchor, held to 4.5-8% (trailing returns alone overshoot after bull markets). CRP: the local-minus-US sovereign spread.')
i_erp_manual = input.float(5.0, 'Manual ERP %', group = group_risk) / 100
i_crp_manual = input.float(3.5, 'Manual Country Risk %', group = group_risk) / 100
i_rf_base = input.string('Local 10Y', 'Risk-free base', options = ['Local 10Y', 'US 10Y + CRP'], group = group_risk, tooltip = 'Local 10Y: discount local-currency cash flows at the local sovereign yield. Country risk is already inside that yield, so auto-CRP is 0 (manual CRP is still added when Auto is off).\n\nUS 10Y + CRP: a USD build -- US yield plus the local-minus-US spread (or the manual CRP). Use it when the local curve is thin or administered.')
group_proxies = 'Market Proxy (Used for Beta & Auto-ERP)'
i_mkt_bench = input.symbol('SPY', 'Market Proxy', group = group_proxies, tooltip = 'Beta is regressed on this proxy. Auto-ERP reads it as a USD index and pairs it with the US 10Y. VND charts use VNINDEX and the VN 10Y instead.')
i_beta_lookback = input.int(104, 'Regression Lookback (periods of the timeframe below)', minval = 30, group = group_proxies)
i_beta_tf = input.timeframe('W', 'Regression Timeframe', group = group_proxies)
group_calc = 'Calculation Parameters'
i_weighting_algo = input.string('IVW (Error Variance)', 'Weighting Algorithm', options = ['IVW (Error Variance)', 'SMAPE (Symmetric Error)', 'MALE (Log Error)', 'WMAPE (Weighted Error)', 'RMSLE (Root Mean Sq Log)'], group = group_calc, tooltip = 'Every model is scored on how well its stored fair value predicted the price N quarters later (see horizon below).\nIVW: inverse mean squared log error.\nSMAPE/MALE/WMAPE/RMSLE: inverse of that error metric.')
i_w_horizon = input.int(4, 'Weighting: forecast horizon (quarters)', minval = 0, maxval = 8, group = group_calc, tooltip = 'Each model is scored on how well its fair value at quarter t predicted the price at t + N. 0 = same-quarter fit.')
i_blend_mode = input.string('Standard (Relative + Sector)', 'Composite Blend Mode', options = ['Standard (Relative + Sector)', 'Omnibus (All Available Models)'], group = group_calc, tooltip = 'Standard: blends the relative multiples, the sector-specific models and the absolute models a framework is named after (Technology: DCF, RIM and Rule of 40; Financials: RIM). The other absolute models still render in the table for reference.\n\nOmnibus: blends every model the Valuation Framework enables (multiples, sector and absolute models), each weighted on its own track record.')
bool is_omnibus = i_blend_mode == 'Omnibus (All Available Models)'
// ==============================================================
// === OMNIBUS MEMBERSHIP (only read when Blend Mode = Omnibus) ==
// ==============================================================
group_omni = 'Omnibus: Selection'
group_omni_r = 'Omnibus: Relative Multiples'
group_omni_s = 'Omnibus: Sector Models'
group_omni_a = 'Omnibus: Absolute Models'
i_omni_mode = input.string('Auto (Framework Allocation)', 'Member Selection', options = ['Auto (Framework Allocation)', 'Manual (Tick Models Below)'], group = group_omni, tooltip = 'Auto: every model the sector framework enables, each a member in its own right.\n\nManual: the boxes you tick. All are ticked by default, so Manual starts equal to Auto; untick to remove a model.\n\nEither way rNPV replaces the DCF it contains, P/AFFO (an FCF proxy) gives way to P/FCF, and a member is dropped if its model returns na or a non-positive value. The table row "Omnibus Members" reports what survived.')
i_omni_strict = input.bool(true, 'Manual: still require framework approval', group = group_omni, tooltip = 'ON (default): a ticked model is used only if the sector framework ALSO enables it.\n\nOFF: the ticks override the framework; a ticked sector model is computed even outside its sector.')
i_om_comp = input.bool(false, 'Standard Composite (the whole Standard blend)', group = group_omni, tooltip = 'The Standard blend entered as a SINGLE member. Off by default: Standard and Omnibus are alternatives.\n\nWARNING: it already contains the relative multiples and sector models below, plus the absolute models the framework is named after (Technology: DCF, RIM, Rule of 40; Financials: RIM). Ticking it alongside any of them counts those models twice. The Omnibus Members row flags this as DOUBLE-COUNT.')
i_omni_sanity_x = input.float(10.0, 'Drop members beyond Nx / (1/N)x price', minval = 0, maxval = 50, step = 1, group = group_omni, tooltip = 'A member whose fair value exceeds N times the current price, or falls below 1/N of it, is excluded.\n\n0 = off. The Standard Composite member is never dropped by this test.')
i_om_pe = input.bool(true, 'Blended P/E', group = group_omni_r, inline = 'r1')
i_om_ps = input.bool(true, 'P/S', group = group_omni_r, inline = 'r1')
i_om_pfcf = input.bool(true, 'P/FCF', group = group_omni_r, inline = 'r2')
i_om_pb = input.bool(true, 'P/B', group = group_omni_r, inline = 'r2')
i_om_ptbv = input.bool(true, 'P/TBV', group = group_omni_r, inline = 'r3')
i_om_ev = input.bool(true, 'Blended EV/EBITDA', group = group_omni_r, inline = 'r3')
i_om_pcf = input.bool(true, 'P/CF', group = group_omni_r, inline = 'r4')
i_om_paffo = input.bool(true, 'P/AFFO', group = group_omni_r, inline = 'r4')
i_om_rnpv = input.bool(true, 'rNPV (Risk-Adjusted)', group = group_omni_s, inline = 's1')
i_om_ecf = input.bool(true, 'Equity Cash Flow', group = group_omni_s, inline = 's1')
i_om_affo = input.bool(true, 'AFFO DCF', group = group_omni_s, inline = 's2')
i_om_unb = input.bool(true, 'Unbundled (SOTP)', group = group_omni_s, inline = 's2')
i_om_apv = input.bool(true, 'Adjusted PV (APV)', group = group_omni_s, inline = 's3')
i_om_eva = input.bool(true, 'Economic Value Added', group = group_omni_s, inline = 's3')
i_om_ddm = input.bool(true, 'Dividend Discount (DDM)', group = group_omni_s)
i_om_dcf = input.bool(true, 'DCF (McKinsey/ROIC)', group = group_omni_a, inline = 'a1')
i_om_rim = input.bool(true, 'Residual Income (RIM)', group = group_omni_a, inline = 'a1')
i_om_epv = input.bool(true, 'EPV (Greenwald)', group = group_omni_a, inline = 'a2')
i_om_graham = input.bool(true, 'Graham', group = group_omni_a, inline = 'a2')
i_om_r40 = input.bool(true, 'Rule of 40', group = group_omni_a, inline = 'a3')
i_om_acq = input.bool(true, "Acquirer's Multiple", group = group_omni_a, inline = 'a3')
i_om_oe = input.bool(true, "Owners' Earnings", group = group_omni_a)
i_numQuarters = input.int(20, 'Number of Quarters to Average', minval = 4, maxval = 60, group = group_calc)
i_useMean = input.bool(true, 'Use Mean Instead of Median', group = group_calc)
i_ratioCap = input.float(200.0, 'Maximum Ratio Cap', minval = 50, group = group_calc)
i_useBeneishCheck = input.bool(true, '🕵️ Apply Beneish M-Score (Fraud Check)', group = group_calc)
i_use_rkv = input.bool(true, '💎 Apply Rhodes-Kropf (RKV) M/B Decomposition', group = group_calc, tooltip = 'Decomposes M/B into Mispricing and Growth Options. Drops value-trap quarters from the historical P/B average and flags current value traps.')
i_flow_ttm = input.bool(true, 'Request flows as TTM', group = group_calc, tooltip = 'Income and cash-flow items are requested as TTM directly instead of summing four FQ values. Interest and R&D have no TTM field, so they are always summed from FQ.')
group_iv = 'Intrinsic Value Models (Automated)'
i_growth_src = input.string('Auto (Consensus EPS -> Sales CAGR)', 'Forward growth source', options = ['Auto (Consensus EPS -> Sales CAGR)', 'Manual'], group = group_iv, tooltip = 'Auto: FY consensus EPS growth (EARNINGS_ESTIMATE, has history and passes the report-lag gate), else 3y sales CAGR, else the manual value.\n\nAnalyst PRICE targets are never used here: they exist only for today, so they would leak into the backtest and make the street comparison circular.')
i_analyst_growth = input.float(10.0, 'Manual forward growth %', group = group_iv, tooltip = 'Used when the source is Manual, or as the last fallback in Auto.') / 100
group_street = 'Street Consensus (analyst targets)'
i_show_street = input.bool(true, 'Show street comparison', group = group_street, tooltip = 'Uses syminfo.target_price_* and syminfo.recommendations_* (0 request slots). Display only: never enters the blend, the plot or the backtest.')
i_conf_gap = input.float(15.0, 'Agreement band: ours vs street PV (%)', minval = 1, maxval = 50, group = group_street) / 100
i_iv_projection_period = input.int(10, 'RIM Projection Period (Years)', group = group_iv, minval = 5, maxval = 20)
i_cagr_years = input.int(3, 'CAGR Lookback Years', group = group_iv, minval = 1, maxval = 10)
i_dcf_stage1_yrs = input.int(10, 'DCF: High-Growth Years (Stage 1)', group = group_iv, minval = 1, maxval = 15, tooltip = 'Used by every DCF-type model: main DCF, rNPV, AFFO DCF, Unbundled ServeCo, APV and Equity Cash Flow.')
i_strict_cap = input.bool(true, 'Strict capital structure', group = group_iv, tooltip = "ON: minority interest and preferred equity are claims ahead of common shareholders. They are added to enterprise value and subtracted from every firm-value model (EV/EBITDA, DCF, rNPV, EPV, APV, EVA, RIM, Unbundled, Rule of 40, Acquirer's Multiple); book value is common equity (ex-MI, ex-preferred) and earnings are income attributable to common (net of preferred dividends). Preferred equity = preferred dividends capitalised at the local 10Y + 2%.")
group_display = 'Display Options'
i_detail = input.string('None', 'Table detail (below the summary)', options = ['None', 'Models', 'Street', 'Health', 'Everything'], group = group_display, tooltip = 'The summary card is always shown. Pick one section to add below it.\n\nModels: every relative and intrinsic model.\nStreet: analyst targets, implied growth and P/E, ratings, confidence parts.\nHealth: every diagnostic and quality filter.\n\nEverything can run off a short chart.')
i_tablePos = input.string('top_right', 'Table Position', options = ['top_right', 'middle_right', 'bottom_right'], group = group_display)
i_textSize = input.string('normal', 'Text Size', options = ['auto', 'tiny', 'small', 'normal', 'large', 'huge'], group = group_display)
i_theme = input.string('Dark', 'Theme', options = ['Dark', 'Light'], group = group_display)
group_bt = 'Win Rate Backtester (No-Repaint)'
i_show_bt = input.bool(true, 'Show Backtest Dashboard', group = group_bt)
i_bt_all = input.bool(false, 'Show all models', group = group_bt, tooltip = 'Off: only the Composite, the models the current framework uses, and the always-in Baseline. On: every model, including the ones marked with a dot (not in the blend).')
i_bt_pos = input.string('bottom_left', 'Dashboard position', options = ['bottom_left', 'middle_left', 'top_left', 'bottom_center', 'top_center'], group = group_bt)
i_bt_val = input.int(1, 'Holding Period Length', minval = 1, group = group_bt)
i_bt_unit = input.string('Years', 'Time Unit', options = ['Days', 'Weeks', 'Months', 'Years'], group = group_bt)
i_bt_max_open = input.int(0, 'Max Open Tranches (0 = unlimited)', minval = 0, group = group_bt, tooltip = '0 = unlimited (default): every qualifying discount is sampled -- correct for SIGNAL evaluation.\n\nSet 1-5 to simulate a CAPITAL-CONSTRAINED portfolio instead.')
i_bt_margin = input.float(15.0, 'Margin of Safety %', minval = 0, tooltip = 'Buy Signal = Price < FV * (1 - Margin x downside beta), clamped 5-50%. The chart buy line uses the same number.', group = group_bt) / 100
i_bt_exit_premium = input.float(20.0, 'Exit when Price > FV + %', minval = 0, group = group_bt) / 100
i_bt_fees = input.float(0.5, 'Round-trip Fees & Slippage %', group = group_bt, tooltip = 'Deducted from every trade (e.g., 0.5%).') / 100
i_bt_win_threshold = input.float(0.0, 'Min Profit % to count as Win', group = group_bt, tooltip = 'Set to > 0 if you want to ignore tiny gains (e.g., 2%).') / 100
i_report_lag = input.int(45, 'Report lag (days)', minval = 0, maxval = 120, group = group_bt, tooltip = "request.financial returns a quarter's numbers from the START of the next period -- weeks before they were published. Each new value is released on the next earnings report date, or after this many days at most. 0 restores the old (look-ahead) behaviour. The latest value is always released on the last bar.")
i_acquirer_mult = input.float(10.0, "Acquirer's Multiple Target (EV/EBIT)", group = group_iv, tooltip = "Tobias Carlisle's standard is 10x. Raise this to 15x or 20x for large-cap/growth stocks.")
group_oos = 'Walk-Forward Matrix (IS / OOS / FWD)'
i_is_start = input.time(timestamp("2015-01-01"), "In-Sample Start", group = group_oos)
i_is_end = input.time(timestamp("2020-12-31"), "In-Sample End", group = group_oos)
i_oos_start = input.time(timestamp("2021-01-01"), "Out-of-Sample Start", group = group_oos)
i_oos_end = input.time(timestamp("2024-12-31"), "Out-of-Sample End", group = group_oos)
i_period_mode = input.string('Manual Dates', 'Period Mode', options = ['Manual Dates', 'Auto-Split', 'Full Period'], group = group_oos, tooltip = "Auto-Split divides the symbol's available history by bar count. Full Period pools everything into one bucket.")
i_split_1 = input.float(0.50, 'Auto-Split: Period 1 share', minval = 0.2, maxval = 0.8, step = 0.05, group = group_oos, tooltip = 'Default 50/25/25: you need more observations to establish a baseline than to test it.')
i_split_2 = input.float(0.25, 'Auto-Split: Period 2 share', minval = 0.1, maxval = 0.5, step = 0.05, group = group_oos)
i_bt_view = input.string('Matrix (all periods)', 'Backtest View', options = ['Matrix (all periods)', 'Focus: Period 1', 'Focus: Period 2', 'Focus: Period 3', 'Robustness verdict'], group = group_oos, tooltip = 'Focus shows one period with every metric as its own column. Robustness grades stability across all three and against the always-in baseline.')
i_bt_min_n = input.int(5, 'Minimum trades for a valid cell', minval = 1, maxval = 50, group = group_oos)
i_bt_drop_straddle = input.bool(true, 'Exclude trades that straddle a period boundary', group = group_oos, tooltip = 'A trade entered late in P1 and exited deep in P2 would otherwise credit all its P2 return to P1.')
group_rows = 'Model rows: check and inspect'
i_shadow = input.bool(true, 'Shadow check: run the previous model stage alongside', group = group_rows, tooltip = 'Runs the model stage as it was before the model rows, from the same inputs, and compares every row with it: Base on every bar, Bear and Bull on the last bar, the tiers and the DCF exit multiple. The result is the "Shadow check" row of the table.\n\nTurn it off once it reads MATCH on your symbols: it roughly doubles the model work per bar.')
i_dw_code = input.string('', 'Data window: model code', group = group_rows, tooltip = "Plots one model row's Base result record in the Data Window, bar by bar: value, engine core per share, add-on and claims per share, discount rate and both growths.\n\nCodes: PE PS FCF PB TBV EV CF AFFO RNPV ECF ADCF UNB APV EVA DDM DCF RIM EPV GRA R40 ACQ OE. Empty = off.")
// What counts as a claim ahead of common, stated once: net debt always; minority interest and
// preferred under the strict capital structure. Every strict test in the script reads this.
f_claim_on(Claim k) =>
    k == Claim.netdebt or i_strict_cap
method claim(Claims c, Claim k, float v) =>
    if f_claim_on(k)
        c.amt.put(k, v)
        c.sum := c.sum + v
// ==========================================
// FRAMEWORK: sector -> the models it allocates
// ==========================================
string selected_industry = i_industry
if i_industry == 'Auto-Detect'
    string sec = syminfo.sector
    if sec == 'Electronic Technology' or sec == 'Technology Services'
        selected_industry := 'Technology'
    else if sec == 'Health Technology' or sec == 'Health Services'
        selected_industry := 'Healthcare (Pharma/Biotech)'
    else if sec == 'Finance'
        string fin_ind = syminfo.industry
        if str.contains(fin_ind, 'Real Estate Investment Trust') or str.contains(syminfo.description, 'REIT')
            selected_industry := 'REITs'
        else if str.contains(fin_ind, 'Bank') or str.contains(fin_ind, 'Insurance') or str.contains(fin_ind, 'Brokers') or str.contains(fin_ind, 'Investment Managers') or str.contains(fin_ind, 'Finance/Rental') or str.contains(fin_ind, 'Financial Conglomerates')
            selected_industry := 'Financials (Bank/Insurance)'
        else
            // [FIX FIN-ROUTE] Property developers and other Finance-sector
            // operating companies: the bank model does not fit them.
            selected_industry := 'General/Diversified'
    else if sec == 'Energy Minerals' or sec == 'Non-Energy Minerals' or sec == 'Process Industries'
        selected_industry := 'Energy/Materials'
    else if sec == 'Producer Manufacturing' or sec == 'Transportation' or sec == 'Industrial Services' or sec == 'Distribution Services' or sec == 'Commercial Services'
        selected_industry := 'Capital Goods/Industrials'
    else if sec == 'Retail Trade' or sec == 'Consumer Services' or sec == 'Consumer Durables'
        selected_industry := 'Consumer Discretionary'
    else if sec == 'Consumer Non-Durables'
        selected_industry := 'Consumer Staples'
    else if sec == 'Communications'
        selected_industry := 'Telecom'
    else if sec == 'Utilities'
        selected_industry := 'Utilities'
    else
        selected_industry := 'General/Diversified'
// THE ALLOCATION MATRIX: 'description|codes|named'. Codes are the model rows' codes (section
// 2b) plus the quality filters (GPA gross profit / assets, ROIC
// ROIC - WACC, SLN Sloan accruals, SHY shareholder yield) and CAPE (the P/E
// driver becomes 10-year inflation-adjusted EPS). Named (optional): the absolute
// models in the description, which the Standard blend takes alongside the multiples
// and sector models.
string fw_row = switch selected_industry
    'Technology' => 'Growth: Rule of 40, DCF & RIM|PE PS FCF EV DCF RIM R40 ROIC SLN SHY|DCF RIM R40'
    'Healthcare (Pharma/Biotech)' => 'rNPV & Pipeline Focus|PE PS FCF PB EV DCF EPV ACQ RNPV ROIC SLN SHY'
    'Financials (Bank/Insurance)' => 'RIM & Equity Cash Flow|PE PB TBV RIM GRA ECF SHY|RIM'
    'REITs' => 'AFFO DCF & Property Multiples|PB EV CF AFFO ADCF SHY'
    'Energy/Materials' => 'Cyclically-Adjusted Value (CAPE)|PE FCF PB TBV EV CF EPV GRA ACQ OE CAPE ROIC SHY'
    'Capital Goods/Industrials' => 'APV & Cyclical Quality|PE FCF PB EV CF DCF EPV GRA ACQ OE APV CAPE GPA ROIC SLN'
    'Consumer Staples' => 'EVA & ROIC Spread|PE PS FCF EV CF DCF EPV GRA ACQ OE EVA GPA ROIC SHY'
    'Consumer Discretionary' => 'Brand Economics & EVA|PE PS FCF EV CF DCF EPV GRA ACQ OE EVA CAPE GPA ROIC SLN'
    'Telecom' => 'Telecom Unbundling (NetCo + ServeCo)|PE FCF PB EV CF DCF EPV GRA ACQ OE UNB ROIC SHY'
    'Utilities' => 'DDM & Regulated Returns|PE PB EV CF EPV RIM GRA ACQ OE DDM ROIC SHY'
    => 'General (All Models Active)|PE PS FCF PB TBV EV CF DCF GRA EPV RIM ACQ OE GPA ROIC SLN SHY'
array<string> fw_parts = str.split(fw_row, '|')
string active_model_desc = array.get(fw_parts, 0)
string fw_codes = ' ' + array.get(fw_parts, 1) + ' '
string fw_named = ' ' + (array.size(fw_parts) > 2 ? array.get(fw_parts, 2) : '') + ' '
bool use_cape = str.contains(fw_codes, ' CAPE ')
bool show_gpa = str.contains(fw_codes, ' GPA ')
bool show_roic_wacc = str.contains(fw_codes, ' ROIC ')
bool show_sloan = str.contains(fw_codes, ' SLN ')
bool show_shareholder = str.contains(fw_codes, ' SHY ')
bool is_financial_sector = selected_industry == 'Financials (Bank/Insurance)'
// Banks and insurers use the Equity models (RIM: NI / book at CoE; growth from ROE), the
// rest the Entity models (RIM: NOPAT / invested capital at WACC; growth from ROIC).
string _fin_ind = syminfo.industry
bool fin_bank_like = (str.contains(_fin_ind, 'Banks') and not str.contains(_fin_ind, 'Brokers')) or str.contains(_fin_ind, 'Insurance')
bool use_bank_model = is_financial_sector and (i_financial_model_type == 'Equity Model (Bank/Insurer)' or (i_financial_model_type == 'Auto (by industry)' and fin_bank_like))
// =====================================================================
// 2b. THE MODEL ROWS: each model once, with every fact about it
// =====================================================================
// Declaration order is the registry order the blends still walk: 0 Standard Composite |
// 1-8 relative multiples | 9-15 sector models | 16-22 absolute models. Everything else a
// model is comes from its row: level (rate and claims), engine, the streams it reads, the
// inputs it needs positive, its tier source, add-on, private scenario lever, family and
// Omnibus tick box. Adding a model: one row here and its tick input.
var Model M_COMP = f_add(Model.new(code = 'COMP', name = 'Standard Composite', bt_name = 'Composite (Final Blend)', grp = Group.comp, eng = Eng.comp, fam = 0, tick = i_om_comp))
var Model M_PE = f_add(Model.new(code = 'PE', name = 'Blended P/E', bt_name = 'Blended PE', grp = Group.rel, level = Level.equity, eng = Eng.mult, fam = 1, s_drv = Sx.eps_b, s_fwd = Sx.eps_f, need1 = Sx.eps_b, t1 = Sx.eps_b, lk = Lever.pctl, dflt = 15.0, tick = i_om_pe))
var Model M_PS = f_add(Model.new(code = 'PS', name = 'P/S', bt_name = 'Price / Sales', grp = Group.rel, level = Level.equity, eng = Eng.mult, fam = 2, s_drv = Sx.sales_ps, t1 = Sx.sales_ps, lk = Lever.pctl, dflt = 2.0, tick = i_om_ps))
var Model M_PFCF = f_add(Model.new(code = 'FCF', name = 'P/FCF', bt_name = 'Price / FCF', grp = Group.rel, level = Level.equity, eng = Eng.mult, fam = 3, s_drv = Sx.fcf_ps, need1 = Sx.fcf_ps, t1 = Sx.fcf_ps, lk = Lever.pctl, dflt = 15.0, tick = i_om_pfcf))
var Model M_PB = f_add(Model.new(code = 'PB', name = 'P/B', bt_name = 'Price / Book', grp = Group.rel, level = Level.equity, eng = Eng.mult, fam = 4, s_drv = Sx.bvps, t1 = Sx.bvps, lk = Lever.pctl, dflt = 1.5, rkv = true, tick = i_om_pb))
var Model M_TBV = f_add(Model.new(code = 'TBV', name = 'P/TBV', bt_name = 'Price / TBV', grp = Group.rel, level = Level.equity, eng = Eng.mult, fam = 4, s_drv = Sx.tbvps, t1 = Sx.tbvps, lk = Lever.pctl, dflt = 2.0, tick = i_om_ptbv))
var Model M_EV = f_add(Model.new(code = 'EV', name = 'Blended EV/EBITDA', bt_name = 'EV / EBITDA', grp = Group.rel, level = Level.firm, eng = Eng.mult, fam = 5, s_drv = Sx.ebitda, s_fwd = Sx.ebitda_f, t1 = Sx.ebitda, lk = Lever.pctl, dflt = 10.0, tick = i_om_ev))
var Model M_PCF = f_add(Model.new(code = 'CF', name = 'P/CF', bt_name = 'Price / OCF', grp = Group.rel, level = Level.equity, eng = Eng.mult, fam = 3, s_drv = Sx.ocf_ps, t1 = Sx.ocf_ps, lk = Lever.pctl, dflt = 10.0, tick = i_om_pcf))
var Model M_PAFFO = f_add(Model.new(code = 'AFFO', name = 'P/AFFO', bt_name = 'Price / AFFO', grp = Group.rel, level = Level.equity, eng = Eng.mult, fam = 3, s_drv = Sx.fcf_ps, t1 = Sx.fcf_ps, lk = Lever.pctl, dflt = 12.0, tick = i_om_paffo))
var Model M_RNPV = f_add(Model.new(code = 'RNPV', name = 'rNPV (Risk-Adjusted)', bt_name = 'Risk-Adj NPV', grp = Group.sect, level = Level.firm, eng = Eng.ref, fam = 3, src = 'DCF', addon = AddOn.pipeline, t1 = Sx.fcff, tick = i_om_rnpv))
var Model M_ECF = f_add(Model.new(code = 'ECF', name = 'Equity Cash Flow', bt_name = 'Equity Cash Flow', grp = Group.sect, level = Level.equity, eng = Eng.vdcf, fam = 1, s_cf = Sx.fcfe, s_earn = Sx.ni_ps, s_ret = Sx.roe_n, need1 = Sx.ni_ps, need2 = Sx.roe_n, t1 = Sx.ni_ps, t2 = Sx.roe_n, tick = i_om_ecf))
var Model M_ADCF = f_add(Model.new(code = 'ADCF', name = 'AFFO DCF', bt_name = 'AFFO DCF', grp = Group.sect, level = Level.equity, eng = Eng.vdcf, fam = 3, s_cf = Sx.fcf_ps, s_earn = Sx.fcf_ps, t1 = Sx.fcf_ps, tick = i_om_affo))
var Model M_UNB = f_add(Model.new(code = 'UNB', name = 'Unbundled (SOTP)', bt_name = 'Unbundled SOTP', grp = Group.sect, level = Level.firm, eng = Eng.vdcf, fam = 3, s_cf = Sx.fcff_s, s_earn = Sx.nopat_s, s_ret = Sx.roic, addon = AddOn.netco, t1 = Sx.fcff_s, tick = i_om_unb))
var Model M_APV = f_add(Model.new(code = 'APV', name = 'Adjusted PV (APV)', bt_name = 'Adjusted PV', grp = Group.sect, level = Level.unlev, eng = Eng.vdcf, fam = 3, s_cf = Sx.fcff, s_earn = Sx.nopat, s_ret = Sx.roic, addon = AddOn.shield, t1 = Sx.fcff, tick = i_om_apv))
var Model M_EVA = f_add(Model.new(code = 'EVA', name = 'Economic Value Added', bt_name = 'Econ Value Added', grp = Group.sect, level = Level.firm, eng = Eng.eva, fam = 1, s_earn = Sx.nopat, s_cap = Sx.ic, t1 = Sx.nopat, tick = i_om_eva))
var Model M_DDM = f_add(Model.new(code = 'DDM', name = 'Dividend Discount (DDM)', bt_name = 'Dividend Discount', grp = Group.sect, level = Level.equity, eng = Eng.gperp, fam = 6, s_cf = Sx.dps, need1 = Sx.dps, t1 = Sx.dps, tick = i_om_ddm))
var Model M_DCF = f_add(Model.new(code = 'DCF', name = 'DCF (McKinsey/ROIC)', bt_name = 'DCF (McKinsey)', grp = Group.abs, level = Level.firm, eng = Eng.vdcf, fam = 3, s_cf = Sx.fcff, s_earn = Sx.nopat, s_ret = Sx.roic, t1 = Sx.fcff, tick = i_om_dcf))
// Banks and insurers: the Equity variant (net income on book value at the bank rate, nothing
// comes off). Everyone else: the Entity variant (NOPAT on invested capital at WACC, less the
// claims). Decided once from the framework and the industry.
var Model M_RIM = f_add(Model.new(code = 'RIM', name = 'Residual Income (RIM)', bt_name = 'Residual Income', grp = Group.abs, level = use_bank_model ? Level.bank : Level.firm, eng = Eng.rim, fam = 1, s_earn = use_bank_model ? Sx.ni : Sx.nopat, s_cap = use_bank_model ? Sx.book : Sx.ic, t1 = use_bank_model ? Sx.ni : Sx.nopat, t2 = use_bank_model ? Sx.book : Sx.none, tick = i_om_rim))
var Model M_EPV = f_add(Model.new(code = 'EPV', name = 'EPV (Greenwald)', bt_name = 'EPV (Greenwald)', grp = Group.abs, level = Level.firm, eng = Eng.perp, fam = 1, s_cf = Sx.nopat_n, t1 = Sx.nopat_n, tick = i_om_epv))
var Model M_GRA = f_add(Model.new(code = 'GRA', name = 'Graham', bt_name = 'Graham Number', grp = Group.abs, level = Level.equity, eng = Eng.graham, fam = 1, s_earn = Sx.eps_pos, s_gx = Sx.g_gra, s_adj = Sx.yadj, need1 = Sx.eps_pos, t1 = Sx.eps_pos, lk = Lever.scale, lv_bear = 0.5, lv_bull = 1.5, tick = i_om_graham))
var Model M_R40 = f_add(Model.new(code = 'R40', name = 'Rule of 40', bt_name = 'Rule of 40', grp = Group.abs, level = Level.firm, eng = Eng.rulex, fam = 2, s_drv = Sx.rev, s_gx = Sx.rev_g, s_adj = Sx.fcf_margin, t1 = Sx.rev, t2 = Sx.fcf_margin, lk = Lever.step, lv_bear = -i_scen_r40_bps, lv_bull = i_scen_r40_bps, tick = i_om_r40))
var Model M_ACQ = f_add(Model.new(code = 'ACQ', name = "Acquirer's Multiple", bt_name = "Acquirer's Mult", grp = Group.abs, level = Level.firm, eng = Eng.mult, fam = 5, s_drv = Sx.ebit, need1 = Sx.ebit, t1 = Sx.ebit, lk = Lever.step, lv_bear = -i_scen_acq_delta, lv_bull = i_scen_acq_delta, lv_floor = 1.0, m0 = i_acquirer_mult, tick = i_om_acq))
var Model M_OE = f_add(Model.new(code = 'OE', name = "Owners' Earnings", bt_name = "Owners' Earnings", grp = Group.abs, level = Level.equity, eng = Eng.perp, fam = 3, s_cf = Sx.oe_ps, need1 = Sx.oe_ps, t1 = Sx.oe_ps, tick = i_om_oe))
// Bar 0: what the framework allocates, the Standard scope (every allocated multiple and
// sector model, plus the absolute models the framework is named after), then the row checks.
if barstate.isfirst
    for m in MD
        m.fw := m.grp == Group.comp or str.contains(fw_codes, ' ' + m.code + ' ')
        m.on := m.fw
        m.std := m.fw and m.grp != Group.comp and (m.grp != Group.abs or str.contains(fw_named, ' ' + m.code + ' '))
    f_rows_check()
// =====================================================================
// 3. DATA COLLECTION
// =====================================================================
// REQUEST LEDGER (hard cap = 40 per script)
// request.financial     : 31 (one wrapper, see 3.3)
// request.security      : 6  (US10Y, local 10Y, benchmark, small-cap, value, growth ETF)
// request.currency_rate : 1
// request.earnings      : 1  (report dates)
// TOTAL                 : 39 -> 1 slot free
// RULES
// R1. request.security() accepts TUPLES -> unlimited series per slot.
// R2. request.financial() does NOT -> never spend a slot on anything an
//     accounting identity can reconstruct exactly.
// R3. Never request.security() the chart's own symbol; aggregate locally.
// =====================================================================
f_locf(float val) =>
    var float last_val = na
    if not na(val)
        last_val := val
    last_val
// True on the bar a series first prints a NEW value (na-safe)
f_fresh(float v) =>
    not na(v) and (na(v[1]) or v != v[1])
// [FIX RDQ] request.earnings prints on the publication bar (1 slot): new fundamentals
// are released on the actual report date, with the fixed lag as the fallback cap.
float earn_raw = request.earnings(syminfo.tickerid, earnings.actual, ignore_invalid_symbol = true)
bool report_bar = f_fresh(earn_raw)
// ---------------------------------------------------------------------
// 3.1 MACRO TICKER ROUTING
// ---------------------------------------------------------------------
string curr = syminfo.currency
string rf_ticker_auto = switch curr
    'VND' => 'TVC:VN10Y'
    'EUR' => 'TVC:DE10Y'
    'GBP' => 'TVC:GB10Y'
    'JPY' => 'TVC:JP10Y'
    'CNY' => 'TVC:CN10Y'
    'HKD' => 'TVC:CN10Y'
    'INR' => 'TVC:IN10Y'
    'CAD' => 'TVC:CA10Y'
    'AUD' => 'TVC:AU10Y'
    => 'TVC:US10Y'
string final_rf_ticker = i_rf_ticker_manual != '' ? i_rf_ticker_manual : rf_ticker_auto
int current_tf_sec = timeframe.in_seconds(timeframe.period) > 0 ? timeframe.in_seconds(timeframe.period) : 86400
// [FIX BPY] Bars per year from the trading calendar, not 365 calendar days.
// A daily stock chart has ~252 bars a year, so "5 years" of 365-bar years
// was ~7.2 years and a "1 year" hold ~1.45.
int trading_days = syminfo.type == 'crypto' ? 365 : 252
float session_sec = syminfo.type == 'crypto' ? 86400.0 : 23400.0
int bpy = current_tf_sec < 86400 ? math.max(1, int(math.round(trading_days * session_sec / current_tf_sec))) : current_tf_sec < 604800 ? math.max(1, int(math.round(trading_days * 86400.0 / current_tf_sec))) : math.max(1, int(math.round(365.25 * 86400.0 / current_tf_sec)))
// ---------------------------------------------------------------------
// 3.2 MACRO FETCH - TUPLE-PACKED (spot, 90-day average)
// ---------------------------------------------------------------------
// >>> SECURITY SLOT 1/6 : US risk-free curve
[us_spot_r, us_sm_r] = request.security('TVC:US10Y', 'D', [close, ta.sma(close, 90)], ignore_invalid_symbol = true)
float us10y_true_raw = f_locf(us_spot_r)
float us10y_smooth = f_locf(us_sm_r)
// >>> SECURITY SLOT 2/6 : Local risk-free curve
[rf_spot_r, rf_sm_r] = request.security(final_rf_ticker, 'D', [close, ta.sma(close, 90)], ignore_invalid_symbol = true)
float local_rf_raw = f_locf(rf_spot_r)
float rf_local_avg = f_locf(rf_sm_r) // 90-day average of the LOCAL 10Y yield, in %
// Cascade: thin sovereign curves (VN10Y etc.) frequently print nothing.
if na(local_rf_raw)
    local_rf_raw := us10y_true_raw
if na(rf_local_avg)
    rf_local_avg := nz(us10y_smooth, local_rf_raw)
if na(rf_local_avg)
    rf_local_avg := 4.0
if na(local_rf_raw)
    local_rf_raw := rf_local_avg
if na(us10y_true_raw)
    us10y_true_raw := rf_local_avg
// ---------------------------------------------------------------------
// 3.2b MACRO ASSUMPTIONS (replaces the CPI + GDP requests -- 0 slots)
// ---------------------------------------------------------------------
// Terminal growth is a long-run assumption, so a stable input is more
// defensible than last year's CPI print. Defaults are starting points:
// review them for your market.
float dflt_infl = curr == 'VND' ? 0.035 : curr == 'INR' ? 0.045 : curr == 'JPY' ? 0.010 : curr == 'EUR' ? 0.020 : curr == 'CNY' or curr == 'HKD' ? 0.020 : curr == 'CAD' ? 0.020 : 0.025
float dflt_rgdp = curr == 'VND' ? 0.060 : curr == 'INR' ? 0.060 : curr == 'CNY' or curr == 'HKD' ? 0.045 : curr == 'JPY' ? 0.007 : curr == 'EUR' ? 0.012 : curr == 'GBP' ? 0.013 : curr == 'AUD' ? 0.023 : 0.018
float lr_infl = i_lr_infl > 0 ? i_lr_infl : dflt_infl
float lr_rgdp = i_lr_rgdp > 0 ? i_lr_rgdp : dflt_rgdp
// =====================================================================
// 3.3 FUNDAMENTAL FETCH - 31 FIELDS, ONE request.financial WRAPPER
// =====================================================================
// 31 calls to one wrapper, then one loop for the release logic. Field kind:
// 0 flow (TTM, or FQ summed in the vault when 'Request flows as TTM' is off),
// 1 flow with no TTM field (always FQ + vault: interest, R&D, preferred dividends),
// 2 balance-sheet item (FQ), 3 fiscal-year consensus.
// [FIX TTM] Capex and cash-flow D&A have no TTM field: capex = FCF - OCF (the
// solver's identity), D&A from the income statement.
// [FIX EST] Fiscal-year consensus, not a sum of four quarterly estimates.
f_fin(string id, string per) =>
    request.financial(syminfo.tickerid, id, per, ignore_invalid_symbol = true, currency = syminfo.currency)
var array<int> FIN_KIND = array.from(0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3)
string flow_per = i_flow_ttm ? 'TTM' : 'FQ'
// Requests stay outside the loop: Pine rejects loop variables in a request's field/period.
array<float> fin_raw = array.from(f_fin('TOTAL_REVENUE', flow_per), f_fin('COST_OF_GOODS', flow_per), f_fin('EBIT', flow_per),
     f_fin('PRETAX_INCOME', flow_per), f_fin('INCOME_TAX', flow_per), f_fin('EARNINGS_PER_SHARE_DILUTED', flow_per), f_fin('INTEREST_EXPENSE_ON_DEBT', 'FQ'),
     f_fin('RESEARCH_AND_DEV', 'FQ'), f_fin('PREFERRED_DIVIDENDS', 'FQ'), f_fin('DPS_COMMON_STOCK_PRIM_ISSUE', flow_per), f_fin('CASH_F_OPERATING_ACTIVITIES', flow_per),
     f_fin('FREE_CASH_FLOW', flow_per), f_fin('DEP_AMORT_EXP_INCOME_S', flow_per), f_fin('NET_INCOME', flow_per), f_fin('MINORITY_INTEREST', 'FQ'),
     f_fin('DILUTED_SHARES_OUTSTANDING', 'FQ'), f_fin('TOTAL_SHARES_OUTSTANDING', 'FQ'), f_fin('TOTAL_ASSETS', 'FQ'), f_fin('TOTAL_LIABILITIES', 'FQ'),
     f_fin('TOTAL_CURRENT_ASSETS', 'FQ'), f_fin('TOTAL_CURRENT_LIABILITIES', 'FQ'), f_fin('TOTAL_DEBT', 'FQ'), f_fin('CASH_N_SHORT_TERM_INVEST', 'FQ'),
     f_fin('TOTAL_INVENTORY', 'FQ'), f_fin('ACCOUNTS_RECEIVABLES_NET', 'FQ'), f_fin('RETAINED_EARNINGS', 'FQ'), f_fin('PPE_TOTAL_GROSS', 'FQ'),
     f_fin('ACCUM_DEPREC_TOTAL', 'FQ'), f_fin('TOTAL_NON_CURRENT_ASSETS', 'FQ'), f_fin('INTANGIBLES_NET', 'FQ'), f_fin('EARNINGS_ESTIMATE', 'FY'))
// [FIX LOOKAHEAD] request.financial returns a quarter's numbers from the START of the
// next period, weeks before publication. A new value is released on the next report
// date, or i_report_lag days after it first appeared at most, and always on the last bar.
var array<float> fin_pend = array.new_float(31, na)
var array<float> fin_known = array.new_float(31, na)
var array<int> fin_seen = array.new_int(31, 0)
for i = 0 to 30
    float raw = array.get(fin_raw, i)
    float pend = array.get(fin_pend, i)
    if not na(raw) and (na(pend) or raw != pend)
        pend := raw
        array.set(fin_pend, i, raw)
        array.set(fin_seen, i, time)
    int seen = array.get(fin_seen, i)
    if not na(pend) and (time - seen >= i_report_lag * 86400000 or barstate.islast or (report_bar and time > seen))
        array.set(fin_known, i, pend)
// ---------------------------------------------------------------------
// 3.4 QUARTER TRIGGER - DEBOUNCED MULTI-WITNESS
// ---------------------------------------------------------------------
float rev_fq = array.get(fin_known, 0)
float pretax_fq = array.get(fin_known, 3)
float eps_fq = array.get(fin_known, 5)
float ocf_fq = array.get(fin_known, 10)
float total_assets_fq = array.get(fin_known, 17)
int min_gap_bars = math.max(1, int(bpy * 45 / 365.25))
var int last_trig_bar = -100000
// Every witness runs on every bar: 'or' is lazy in v6 and f_fresh keeps its own history.
bool fr_rv = f_fresh(rev_fq), bool fr_pt = f_fresh(pretax_fq), bool fr_as = f_fresh(total_assets_fq)
bool fr_ep = f_fresh(eps_fq), bool fr_oc = f_fresh(ocf_fq)
bool is_new_quarter = (fr_rv or fr_pt or fr_as or fr_ep or fr_oc) and (bar_index - last_trig_bar) >= min_gap_bars
if is_new_quarter
    last_trig_bar := bar_index
// ---------------------------------------------------------------------
// 3.5 TTM VAULT (FQ flows -> trailing four quarters)
// ---------------------------------------------------------------------
// One 4 x 14 matrix holds the last four quarters of every flow, newest in row 0.
// [FIX SEASONAL] A missing (or unchanged, i.e. carried) quarter repeats the same
// quarter last year. Partial vaults annualise the MEAN of what is held.
var matrix<float> vault = matrix.new<float>(4, 14, na)
var array<int> vault_n = array.new_int(14, 0)
array<float> fin = array.copy(fin_known)
for i = 0 to 13
    if array.get(FIN_KIND, i) == 1 or not i_flow_ttm
        float x = array.get(fin_known, i)
        int n = array.get(vault_n, i)
        if is_new_quarter or barstate.isfirst
            float v = n >= 4 and (na(x) or x == matrix.get(vault, 0, i)) ? matrix.get(vault, 3, i) : x
            if not na(v)
                for r = 3 to 1
                    matrix.set(vault, r, i, matrix.get(vault, r - 1, i))
                matrix.set(vault, 0, i, v)
                n := math.min(n + 1, 4)
                array.set(vault_n, i, n)
        float s = 0.0
        for r = 0 to math.max(n - 1, 0)
            s += nz(matrix.get(vault, r, i))
        array.set(fin, i, n == 0 ? na : n == 4 ? s : s / n * 4.0)
float total_revenue_ttm = array.get(fin, 0)
float cogs_ttm = array.get(fin, 1)
float ebit_ttm = array.get(fin, 2)
float pretax_income_ttm = array.get(fin, 3)
float income_tax_ttm = array.get(fin, 4)
float eps_ttm = array.get(fin, 5)
float interest_expense_ttm = array.get(fin, 6)
float rnd_ttm = array.get(fin, 7)
float pref_div_ttm = array.get(fin, 8)
float div_per_share_ttm = array.get(fin, 9)
float ocf_ttm = array.get(fin, 10)
float fcf_rep_ttm = array.get(fin, 11)
float depr_amort_ttm_raw = array.get(fin, 12)
float ni_rep_ttm = array.get(fin, 13) // attributable to the parent
float minority_fq = array.get(fin, 14)
float shares_dil_fq = array.get(fin, 15)
float shares_basic_fq = array.get(fin, 16)
float total_liab_fq = array.get(fin, 18)
float curr_assets_fq = array.get(fin, 19)
float curr_liab_fq = array.get(fin, 20)
float total_debt_latest = array.get(fin, 21)
float cash_latest = array.get(fin, 22)
float inventory_fq = array.get(fin, 23)
float receiv_fq = array.get(fin, 24)
float retained_fq = array.get(fin, 25)
float ppe_gross_fq = array.get(fin, 26)
float accum_dep_fq = array.get(fin, 27)
float noncurr_assets_fq = array.get(fin, 28)
float intangibles_latest = array.get(fin, 29) // includes goodwill
float eps_est_ttm = array.get(fin, 30)
// ---------------------------------------------------------------------
// 3.6 PRE-ENGINE DERIVATIONS
// ---------------------------------------------------------------------
// Larger of period-end and weighted diluted count: the weighted average lags new issues.
float shares_out_latest = math.max(nz(shares_dil_fq), nz(shares_basic_fq))
shares_out_latest := shares_out_latest > 0 ? shares_out_latest : na
// Reported NI (after minority interest) first; pretax - tax includes the minority share.
float net_income_ttm = not na(ni_rep_ttm) ? ni_rep_ttm : not na(pretax_income_ttm) and not na(income_tax_ttm) ? pretax_income_ttm - income_tax_ttm : na
// NI tier: 3 reported; pretax - tax is exact only without minority interest (2), else 1.
int ni_src_t = not na(ni_rep_ttm) ? 3 : nz(minority_fq) == 0 ? 2 : 1
float div_yield = f_locf(close > 0 and not na(div_per_share_ttm) ? div_per_share_ttm / close : na)
// Raw copy kept for the CAPE history; the solver builds the rest.
float eps_fy_curr = eps_ttm
float accounts_receivable_ttm = receiv_fq
float gp_ttm = na
float total_equity_latest = na
float ebitda_ttm = na
// [FIX 1.4] max_bars_back — ta.valuewhen(is_new_quarter, x, 12) reaches ~3y back.
max_bars_back(eps_fq, 4000)
max_bars_back(rev_fq, 4000)
max_bars_back(eps_ttm, 4000)
max_bars_back(total_revenue_ttm, 4000)
max_bars_back(eps_fy_curr, 3000)
max_bars_back(ebit_ttm, 4000)
max_bars_back(ebitda_ttm, 4000)
max_bars_back(total_assets_fq, 4000)
max_bars_back(total_debt_latest, 4000)
max_bars_back(accounts_receivable_ttm, 4000)
max_bars_back(cogs_ttm, 4000)
max_bars_back(total_equity_latest, 4000)
max_bars_back(net_income_ttm, 4000)
// ==========================================
// THE QUANT IMPUTATION ENGINE (IDENTITY SOLVER + FIRM-RATIO CARRY)
// ==========================================
// Fill order, best first. Tier = worst input tier, so a guess never looks like a fact.
//   1. Requested value (3). A field frozen for 2+ new quarters counts as missing.
//   2. Exact identities, solved in any order (tier of the inputs).
//   3. Near-exact rules: EBIT ~ pretax + interest, capex ~ 1y change in net PPE + D&A (tier <= 1).
//   4. The firm's own last ratio: flows x revenue, balance items x assets (tier <= 1).
//   5. Rough rules: D&A ~ OCF - NI, OCF ~ NI + D&A (tier <= 1).
//   6. Last latched value (tier 1). 7. Generic constants behind the firebreak (tier 0).
int iAS = 0, int iLI = 1, int iEQ = 2, int iCA = 3, int iNCA = 4, int iRV = 5, int iCG = 6
int iGP = 7, int iEB = 8, int iDA = 9, int iED = 10, int iOC = 11, int iFC = 12, int iCX = 13
int iPG = 14, int iAD = 15, int iPN = 16, int iNI = 17, int iCS = 18, int iRC = 19, int iDB = 20
// Exact identities as triples: x[a] = x[b] + x[c]
// Assets = Liab + Equity | Assets = Current + Non-current | Revenue = COGS + GP
// EBITDA = EBIT + D&A | FCF = OCF + Capex (capex < 0) | Gross PPE = Accum. dep. + Net PPE
var array<int> id3 = array.from(iAS, iLI, iEQ, iAS, iCA, iNCA, iRV, iCG, iGP, iED, iEB, iDA, iFC, iOC, iCX, iPG, iAD, iPN)
// Ratio base per item: flows scale with revenue, balance items with assets, -1 = none
var array<int> fill_base = array.from(iRV, iAS, iAS, iAS, iAS, -1, iRV, iRV, iRV, iRV, iRV, iRV, iRV, iRV, iAS, iAS, iAS, iRV, iAS, iAS, iAS)
var array<float> eng_mem = array.new_float(21, na)
var array<float> eng_ratio = array.new_float(21, na)
var array<float> last_raw = array.new_float(21, na)
var array<int> same_n = array.new_int(21, 0)
var float mem_shares = na
var float int_rate = na
array<float> eng_v = array.new_float(21, na)
array<int> eng_t = array.new_int(21, 0)
f_g(int i) =>
    array.get(eng_v, i)
f_tg(int i) =>
    array.get(eng_t, i)
f_put(int i, float x, int tier) =>
    if na(f_g(i)) and not na(x)
        array.set(eng_v, i, x)
        array.set(eng_t, i, tier)
// --- 1. SHARES (period-end/diluted -> NI / EPS -> memory) ---
int t_shares = 0, int t_rev = 0, int t_ni = 0, int t_eps = 0
int t_ebit = 0, int t_ebitda = 0, int t_ocf = 0, int t_equity = 0
float calc_shares = shares_out_latest
t_shares := not na(calc_shares) ? 3 : 0
if na(calc_shares) and not na(net_income_ttm) and not na(eps_ttm) and eps_ttm != 0 and net_income_ttm / eps_ttm > 0
    calc_shares := net_income_ttm / eps_ttm
    t_shares := 2
if na(calc_shares) and not na(mem_shares)
    calc_shares := mem_shares
    t_shares := 1
float safe_close = close > 0 ? close : na
float current_mc = safe_close * calc_shares
// Interest: carry the firm's last interest rate on debt when interest is missing
if not na(interest_expense_ttm) and nz(total_debt_latest) > 0
    int_rate := interest_expense_ttm / total_debt_latest
else if na(interest_expense_ttm) and nz(total_debt_latest) > 0
    interest_expense_ttm := total_debt_latest * int_rate
// --- 2. LOAD REQUESTED VALUES (tier 3; NI tier from its source) ---
array<float> eng_raw = array.from(total_assets_fq, total_liab_fq, float(na), curr_assets_fq, noncurr_assets_fq, total_revenue_ttm, cogs_ttm, float(na), ebit_ttm, depr_amort_ttm_raw, float(na), ocf_ttm, fcf_rep_ttm, float(na), ppe_gross_fq, math.abs(accum_dep_fq), float(na), net_income_ttm, cash_latest, accounts_receivable_ttm, total_debt_latest)
for i = 0 to 20
    float x = array.get(eng_raw, i)
    if is_new_quarter and not na(x)
        array.set(same_n, i, x == array.get(last_raw, i) ? array.get(same_n, i) + 1 : 0)
        array.set(last_raw, i, x)
    if array.get(same_n, i) < 2
        f_put(i, x, i == iNI ? ni_src_t : 3)
// [SANITY] A 10x quarter-on-quarter jump in revenue or assets is held at tier 1 for that
// quarter (no latch); NI far from EPS x shares flags a unit or share-count problem.
float rv_prev = ta.valuewhen(is_new_quarter, total_revenue_ttm, 1)
float as_prev = ta.valuewhen(is_new_quarter, total_assets_fq, 1)
bool jump_rv = rv_prev > 0 and total_revenue_ttm > 0 and math.abs(math.log(total_revenue_ttm / rv_prev)) > math.log(10)
bool jump_as = as_prev > 0 and total_assets_fq > 0 and math.abs(math.log(total_assets_fq / as_prev)) > math.log(10)
if jump_rv
    array.set(eng_t, iRV, math.min(f_tg(iRV), 1))
if jump_as
    array.set(eng_t, iAS, math.min(f_tg(iAS), 1))
bool ni_eps_gap = not na(ni_rep_ttm) and not na(eps_ttm) and not na(calc_shares) and ni_rep_ttm != 0 and math.abs(eps_ttm * calc_shares / ni_rep_ttm - 1) > 0.5
bool data_suspect = jump_rv or jump_as or ni_eps_gap
if na(f_g(iNI)) and not na(eps_ttm) and not na(calc_shares)
    f_put(iNI, eps_ttm * calc_shares, math.min(t_shares, 2))
// --- 3-7. FILL STAGES, one pass each: 0 identities only, 1 firm's own last ratios
// (revenue carried first), 2 last latched value, 3 generic constants behind the firebreak
// (tier 0), 4 final solve. Every stage then re-solves the identities and runs the rules:
// near-exact EBIT ~ pretax + interest, capex ~ 1y change in net PPE + D&A; from stage 1
// also rough D&A ~ OCF - NI and OCF ~ NI + D&A. All rule output is tier <= 1.
float pn_1y = ta.valuewhen(is_new_quarter, ppe_gross_fq - math.abs(accum_dep_fq), 4)
bool has_any_real_fundamental = not na(total_assets_fq) or not na(rev_fq) or not na(eps_fq) or not na(ocf_fq)
// Lifeline triples: item = base x k
var array<int> lf_i = array.from(iAS, iRV, iCS, iPG, iPN, iRC, iCA, iNI, iDA, iCX)
var array<int> lf_b = array.from(iRV, iAS, iAS, iAS, iPG, iRV, iAS, iRV, iRV, iDA)
var array<float> lf_k = array.from(1.5, 0.5, 0.05, 0.3, 0.8, 0.1, 0.4, 0.05, 0.05, -1.0)
for st = 0 to 4
    if st == 1 or st == 2
        f_put(iRV, array.get(eng_mem, iRV), 1)
        for i = 0 to 20
            int b = array.get(fill_base, i)
            f_put(i, st == 2 ? array.get(eng_mem, i) : b >= 0 ? f_g(b) * array.get(eng_ratio, i) : na, st == 2 or b < 0 ? 1 : math.min(f_tg(b), 1))
    if st == 3 and not na(calc_shares) and has_any_real_fundamental
        for k = 0 to 9
            int i = array.get(lf_i, k)
            // Capex = D&A is the standard maintenance-capex assumption on the firm's own D&A: tier 1, not a guess.
            f_put(i, f_g(array.get(lf_b, k)) * array.get(lf_k, k), i == iCX ? math.min(f_tg(iDA), 1) : 0)
            if i == iAS
                f_put(iEQ, f_g(iAS) - nz(f_g(iLI), nz(f_g(iDB))), 0)
    for p = 0 to 2
        for k = 0 to 5
            int a = array.get(id3, 3 * k), int b = array.get(id3, 3 * k + 1), int c = array.get(id3, 3 * k + 2)
            float va = f_g(a), float vb = f_g(b), float vc = f_g(c)
            if (na(va) ? 1 : 0) + (na(vb) ? 1 : 0) + (na(vc) ? 1 : 0) == 1
                int j = na(va) ? a : na(vb) ? b : c
                array.set(eng_v, j, na(va) ? vb + vc : na(vb) ? va - vc : va - vb)
                array.set(eng_t, j, math.min(j == a ? f_tg(b) : f_tg(a), j == c ? f_tg(b) : f_tg(c)))
    if st < 4
        f_put(iEB, nz(pretax_income_ttm, f_g(iNI) + nz(income_tax_ttm)) + nz(interest_expense_ttm), not na(pretax_income_ttm) ? 1 : math.min(f_tg(iNI), 1))
        f_put(iCX, -math.max(f_g(iPN) - pn_1y + f_g(iDA), 0), math.min(math.min(f_tg(iPN), f_tg(iDA)), 1))
        if st > 0
            f_put(iDA, math.max(f_g(iOC) - f_g(iNI), 0), math.min(math.min(f_tg(iOC), f_tg(iNI)), 1))
            f_put(iOC, f_g(iNI) + f_g(iDA), math.min(math.min(f_tg(iNI), f_tg(iDA)), 1))
// --- 8. STALENESS: no new report for 2+ quarters -> tier 1, 4+ quarters -> tier 0 ---
var int bars_since_real = 0
bars_since_real := is_new_quarter ? 0 : bars_since_real + 1
float qtrs_stale = bars_since_real / float(math.max(1, int(bpy / 4)))
int stale_cap = qtrs_stale > 4 ? 0 : qtrs_stale > 2 ? 1 : 3
for i = 0 to 20
    array.set(eng_t, i, math.min(f_tg(i), stale_cap))
t_shares := math.min(t_shares, stale_cap)
// --- 9. OUTPUTS ---
float calc_assets = f_g(iAS)
float calc_total_liab = f_g(iLI)
float calc_equity = f_g(iEQ)
float calc_curr_assets = f_g(iCA)
float calc_rev = f_g(iRV)
float calc_gp = f_g(iGP)
float calc_ebit = f_g(iEB)
float calc_da = f_g(iDA)
float calc_ebitda = f_g(iED)
float calc_ocf = f_g(iOC)
float calc_capex = f_g(iCX)
float calc_ni = f_g(iNI)
float calc_cash = f_g(iCS)
float calc_debt = nz(f_g(iDB))
float calc_ppe_net = f_g(iPN)
float calc_eps = nz(eps_ttm, calc_ni / calc_shares)
t_equity := f_tg(iEQ)
t_rev := f_tg(iRV)
t_ni := f_tg(iNI)
t_ebit := f_tg(iEB)
t_ebitda := f_tg(iED)
t_ocf := na(f_g(iCX)) ? f_tg(iOC) : math.min(f_tg(iOC), f_tg(iCX)) // FCF models: the weaker of OCF and capex
int t_cfo = f_tg(iOC) // P/CF reads operating cash flow alone
t_eps := math.min(not na(eps_ttm) ? 3 : math.min(math.min(t_ni, t_shares), 2), stale_cap)
shares_out_latest := calc_shares
total_revenue_ttm := calc_rev
gp_ttm := calc_gp
cogs_ttm := f_g(iCG)
accounts_receivable_ttm := f_g(iRC)
// [AUDIT FIX D] Income attributable to common when strict capital structure is on.
net_income_ttm := f_claim_on(Claim.preferred) ? (calc_ni - nz(pref_div_ttm, 0)) : calc_ni
eps_ttm := calc_eps
ebit_ttm := calc_ebit
ebitda_ttm := calc_ebitda
ocf_ttm := calc_ocf
float capex_ttm = calc_capex
total_equity_latest := calc_equity
total_debt_latest := calc_debt
cash_latest := calc_cash
total_assets_fq := calc_assets
ppe_gross_fq := f_g(iPG)
float ppe_net_fq = calc_ppe_net
float true_fcf = calc_ocf - math.abs(calc_capex)
float fcf_ttm = true_fcf
float net_debt_robust = calc_debt - nz(calc_cash, 0)
// Claims ahead of common: net debt, plus minority interest and preferred equity under the
// strict capital structure (f_claim_on). Preferred has no balance field in the request
// budget: its dividends capitalised at the local 10Y + 2% stand in for it.
float pref_equity = nz(pref_div_ttm) / math.max(rf_local_avg / 100 + 0.02, 0.04)
// THE CLAIMS RECORD, rebuilt every bar: the only definition of what ranks ahead of common.
// The claim bridge and current EV read it; nothing else subtracts a claim.
var Claims CL = Claims.new(map.new<Claim, float>())
CL.amt.clear()
CL.sum := 0.0
CL.shares := shares_out_latest
CL.claim(Claim.netdebt, net_debt_robust)
CL.claim(Claim.minority, nz(minority_fq))
CL.claim(Claim.preferred, pref_equity)
float ev_now = close * CL.shares + CL.sum
// Equity of the parent's shareholders (ex minority interest; ex preferred when the strict
// structure also takes preferred dividends out of earnings): the base of ROE.
float parent_equity = total_equity_latest - nz(minority_fq) - (f_claim_on(Claim.preferred) ? pref_equity : 0.0)
// --- 10. MEMORY + RATIOS: only reported or exact values (tier >= 2) latch ---
if t_shares >= 2
    mem_shares := calc_shares
// Carry ratio = median of the last 8 quarters (one slot per quarter, the latest
// reported value wins within a quarter), so one odd quarter cannot set the carry.
var matrix<float> ratio_h = matrix.new<float>(8, 21, na)
var int ratio_row = 0
if is_new_quarter
    ratio_row := (ratio_row + 1) % 8
    for i = 0 to 20
        matrix.set(ratio_h, ratio_row, i, na)
for i = 0 to 20
    int b = array.get(fill_base, i)
    if f_tg(i) >= 2
        array.set(eng_mem, i, f_g(i))
        float q_new = b >= 0 and f_tg(b) >= 2 and f_g(b) > 0 ? f_g(i) / f_g(b) : na
        float q_old = matrix.get(ratio_h, ratio_row, i)
        // The median only moves when this quarter's slot does.
        if not na(q_new) and (na(q_old) or q_new != q_old)
            matrix.set(ratio_h, ratio_row, i, q_new)
            array<float> col = array.new_float(0)
            for r = 0 to 7
                float q = matrix.get(ratio_h, r, i)
                if not na(q)
                    array.push(col, q)
            array.set(eng_ratio, i, f_median(col))
// =====================================================================
// 3.8 DERIVED SCORES (Altman / Piotroski computed locally)
// =====================================================================
float _ta = calc_assets
float _tl = calc_total_liab
float _ca = calc_curr_assets
float _cl = curr_liab_fq
float _re = retained_fq
float _mve = current_mc
float _x1 = not na(_ca) and not na(_cl) and not na(_ta) and _ta > 0 ? (_ca - _cl) / _ta : na
float _x2 = not na(_re) and not na(_ta) and _ta > 0 ? _re / _ta : na
float _x3 = not na(calc_ebit) and not na(_ta) and _ta > 0 ? calc_ebit / _ta : na
float _x4 = not na(_mve) and not na(_tl) and _tl > 0 ? _mve / _tl : na
float _x5 = not na(calc_rev) and not na(_ta) and _ta > 0 ? calc_rev / _ta : na
float altman_z = na
if not na(_x1) and not na(_x2) and not na(_x3) and not na(_x4) and not na(_x5)
    altman_z := 1.2 * _x1 + 1.4 * _x2 + 3.3 * _x3 + 0.6 * _x4 + 1.0 * _x5
// Z''-EM variant: drops asset turnover (banks, REITs, utilities, VN names).
float _x4b = not na(calc_equity) and not na(_tl) and _tl > 0 ? calc_equity / _tl : na
float altman_z_dd = na
if not na(_x1) and not na(_x2) and not na(_x3) and not na(_x4b)
    altman_z_dd := 3.25 + 6.56 * _x1 + 3.26 * _x2 + 6.72 * _x3 + 1.05 * _x4b
bool _is_bank_like = not na(_tl) and not na(_ta) and _ta > 0 and (_tl / _ta) > 0.80
bool altman_is_em = false
if _is_bank_like and not na(altman_z_dd)
    altman_z := altman_z_dd
    altman_is_em := true
// [FIX Z-EM] Z''-EM (with the +3.25 constant) has its own zones: safe > 5.85,
// distress < 4.35. The original Z's 1.8 / 3.0 made every EM score look safe.
var bool z_is_em = false
if not na(altman_z)
    z_is_em := altman_is_em
altman_z := f_locf(altman_z)
float z_safe_cut = z_is_em ? 4.35 : 1.8
float z_gold_cut = z_is_em ? 5.85 : 3.0
// --- PIOTROSKI F-SCORE: 9 signals, all locally computed ---
// A missing input leaves its signal untested (no nz): banks have no gross margin.
float _roa = not na(_ta) and _ta > 0 ? calc_ni / _ta : na
float _roa_prev = ta.valuewhen(is_new_quarter, _roa, 4)
float _cr = not na(_ca) and not na(_cl) and _cl > 0 ? _ca / _cl : na
float _cr_prev = ta.valuewhen(is_new_quarter, _cr, 4)
float _lev = not na(_ta) and _ta > 0 ? nz(calc_debt) / _ta : na
float _lev_prev = ta.valuewhen(is_new_quarter, _lev, 4)
float _gm = not na(calc_rev) and calc_rev > 0 ? calc_gp / calc_rev : na
float _gm_prev = ta.valuewhen(is_new_quarter, _gm, 4)
float _at = not na(_ta) and _ta > 0 ? calc_rev / _ta : na
float _at_prev = ta.valuewhen(is_new_quarter, _at, 4)
float _sh_prev = ta.valuewhen(is_new_quarter, calc_shares, 4)
// [NEUTRAL] An untestable signal no longer counts as a fail: score = passes x 9 / tested
// (needs 5+ testable signals).
array<float> _pio = array.from(_roa > 0 ? 1.0 : 0.0, calc_ocf > 0 ? 1.0 : 0.0, _roa > _roa_prev ? 1.0 : 0.0, calc_ocf > calc_ni ? 1.0 : 0.0, _lev < _lev_prev ? 1.0 : 0.0, _cr > _cr_prev ? 1.0 : 0.0, calc_shares <= _sh_prev * 1.001 ? 1.0 : 0.0, _gm > _gm_prev ? 1.0 : 0.0, _at > _at_prev ? 1.0 : 0.0)
array<float> _pio_in = array.from(_roa, calc_ocf, _roa + _roa_prev, calc_ocf + calc_ni, _lev + _lev_prev, _cr + _cr_prev, calc_shares + _sh_prev, _gm + _gm_prev, _at + _at_prev)
int _f = 0, int _n = 0
for k = 0 to 8
    if not na(array.get(_pio_in, k))
        _n += 1
        _f += int(array.get(_pio, k))
float piotroski_f_score = has_any_real_fundamental and _n >= 5 ? math.round(_f * 9.0 / _n) : na
// --- Forward growth anchor from the FY consensus estimate ---
float fwd_eps_growth = not na(eps_est_ttm) and not na(eps_ttm) and eps_ttm > 0 ? eps_est_ttm / eps_ttm - 1 : na
fwd_eps_growth := na(fwd_eps_growth) ? na : math.max(math.min(fwd_eps_growth, 0.60), -0.50)
// --- 8. MARGIN & RETURN ADJUSTMENTS ---
float ebit_1y_ago = ta.valuewhen(is_new_quarter, ebit_ttm, 4)
float ebit_2y_ago = ta.valuewhen(is_new_quarter, ebit_ttm, 8)
float ebit_normalized = ebit_ttm
if not na(ebit_1y_ago) and not na(ebit_2y_ago)
    ebit_normalized := (ebit_ttm + ebit_1y_ago + ebit_2y_ago) / 3.0
else if not na(ebit_1y_ago)
    ebit_normalized := (ebit_ttm + ebit_1y_ago) / 2.0
// R&D is capitalised over 3 years, straight line. A year with no R&D figure (before the
// history, or before the field starts) is taken as 10% below the year after it, so every
// vintage is amortised: the history is read on the raw series, where missing is na, not 0.
float safe_rnd = nz(rnd_ttm, 0)
float rnd_1y_ago = nz(ta.valuewhen(is_new_quarter, rnd_ttm, 4), safe_rnd * 0.9)
float rnd_2y_ago = nz(ta.valuewhen(is_new_quarter, rnd_ttm, 8), rnd_1y_ago * 0.9)
float rnd_3y_ago = nz(ta.valuewhen(is_new_quarter, rnd_ttm, 12), rnd_2y_ago * 0.9)
float rnd_amortization = (rnd_1y_ago + rnd_2y_ago + rnd_3y_ago) / 3.0
// The unamortised part is an asset: with it outside invested capital, ROIC (and EVA / RIM)
// would count the capitalised R&D in NOPAT against a capital base that leaves it out.
float research_asset = safe_rnd + rnd_1y_ago * 2.0 / 3.0 + rnd_2y_ago / 3.0
// A missing tax line falls back to 21% as a loss year does (it made NOPAT and WACC na).
float effective_tax = pretax_income_ttm > 0 ? math.min(math.max(nz(income_tax_ttm / pretax_income_ttm, 0.21), 0.0), 0.35) : 0.21
float nopat_adjusted = (ebit_ttm + safe_rnd - rnd_amortization) * (1 - effective_tax)
// EPV capitalises NORMALISED earnings: EBIT averaged over up to three years.
float nopat_norm = (ebit_normalized + safe_rnd - rnd_amortization) * (1 - effective_tax)
// Unlevered FCF for the firm-value DCFs: OCF is after interest paid, so the after-tax
// interest goes back in (else the debt is charged once in the cash flow and again as claims).
float fcff = true_fcf + nz(interest_expense_ttm) * (1 - effective_tax)
float working_capital_proxy = nz(receiv_fq, nz(calc_rev) * 0.1) + nz(inventory_fq, nz(calc_rev) * 0.1) - nz(calc_rev) * 0.15
float ic_equity_method = total_equity_latest + total_debt_latest - nz(cash_latest, 0)
// Operating assets at NET PPE: NOPAT is after depreciation, so the capital it earns on is too
// (gross PPE keeps fully depreciated assets in the base and understates ROIC).
float ppe_ic = nz(ppe_net_fq, nz(ppe_gross_fq, 0))
float invested_capital_adj = total_equity_latest < 0 ? ppe_ic + math.max(working_capital_proxy, 0) : ic_equity_method
// [FIX HGM-2] Invested capital floored at the operating assets deployed.
float ic_operating_floor = math.max(ppe_ic + math.max(nz(working_capital_proxy, 0), 0), nz(total_assets_fq, 0) * 0.05, 1.0)
invested_capital_adj := math.max(nz(invested_capital_adj, ic_operating_floor), nz(total_debt_latest, 0), ic_operating_floor) + research_asset
float roic_adj = nopat_adjusted / invested_capital_adj
roic_adj := na(roic_adj) ? na : math.max(math.min(roic_adj, 1.50), -1.50)
// === MARKET DATA FETCHING ===
string final_mkt_bench = (curr == 'VND') ? 'HOSE:VNINDEX' : i_mkt_bench
// [FIX BETA-ALIGN] Both legs are sampled on the SAME bar: the first chart bar
// of each new beta-timeframe period, holding the PREVIOUS period's close.
// Before, the stock leg updated on the first bar of the week and the benchmark
// (lookahead_off) on the last bar, so the two return series never moved on the
// same bar: beta -> ~0 (0.33 after Blume), downside beta -> 0.
string beta_tf = timeframe.in_seconds(i_beta_tf) <= timeframe.in_seconds(timeframe.period) ? timeframe.period : i_beta_tf
bool beta_sample = ta.change(time(beta_tf)) != 0
float asset_p = f_locf(close[1])
// >>> SECURITY SLOT 3/6 : benchmark, non-repainting (close[1] + lookahead_on)
float bench_c = request.security(final_mkt_bench, beta_tf, close[1], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
float mkt_bench_p = f_locf(bench_c)
max_bars_back(asset_p, 5000)
max_bars_back(mkt_bench_p, 5000)
// One return pair per beta-timeframe period. i_beta_lookback counts PERIODS.
var array<float> beta_ra = array.new_float(0)
var array<float> beta_rb = array.new_float(0)
var float beta_last_a = na
var float beta_last_b = na
if beta_sample and not na(asset_p) and not na(mkt_bench_p)
    if not na(beta_last_a) and beta_last_a > 0 and not na(beta_last_b) and beta_last_b > 0
        array.push(beta_ra, asset_p / beta_last_a - 1)
        array.push(beta_rb, mkt_bench_p / beta_last_b - 1)
        if array.size(beta_ra) > i_beta_lookback
            array.shift(beta_ra)
            array.shift(beta_rb)
    beta_last_a := asset_p
    beta_last_b := mkt_bench_p
// Full beta and downside beta from the same sampled pairs. Needs 12+ pairs.
f_beta_pair(array<float> ra, array<float> rb, bool downside_only) =>
    float sa = 0.0
    float sb = 0.0
    int n = 0
    int sz = array.size(rb)
    float out = na
    if sz > 0
        for i = 0 to sz - 1
            float b = array.get(rb, i)
            if not downside_only or b < 0
                sa += array.get(ra, i)
                sb += b
                n += 1
        if n >= 12
            float ma = sa / n
            float mb = sb / n
            float cov = 0.0
            float vb = 0.0
            for i = 0 to sz - 1
                float b = array.get(rb, i)
                if not downside_only or b < 0
                    cov += (array.get(ra, i) - ma) * (b - mb)
                    vb += (b - mb) * (b - mb)
            out := vb > 0 ? cov / vb : na
    out
var float downside_beta = na
var float raw_beta_s = na
if beta_sample
    raw_beta_s := f_beta_pair(beta_ra, beta_rb, false)
    downside_beta := f_beta_pair(beta_ra, beta_rb, true)
// ==========================================
// AUTO-PREMIUM CALCULATION
// ==========================================
// Annualised over the window actually used: intraday charts cap it below 5 years.
f_get_cagr_optimized(current_price_series, bars_back_5y) =>
    float p_now = current_price_series
    float p_old = current_price_series[bars_back_5y]
    if not na(p_now) and not na(p_old) and p_old > 0
        math.pow(p_now / p_old, bpy / float(bars_back_5y)) - 1.0
    else
        0.08
int bars_in_5y = math.min(5 * bpy, 4900)
cagr_mkt = f_get_cagr_optimized(mkt_bench_p, bars_in_5y)
string auto_small_etf = (curr == 'VND') ? 'HOSE:VNSML' : i_small_etf
// >>> SECURITY SLOT 4/6 : size factor
float small_c = request.security(auto_small_etf, i_beta_tf, close, ignore_invalid_symbol = true)
float small_p = f_locf(small_c)
max_bars_back(small_p, 5000)
cagr_small = f_get_cagr_optimized(small_p, bars_in_5y)
float live_smb_spread = not na(cagr_small) and not na(cagr_mkt) ? cagr_small - cagr_mkt : 0.02
live_smb_spread := math.max(math.min(live_smb_spread, 0.05), -0.02)
// [FIX HML] HML from the value and growth ETFs (the old line reused the SMB
// spread). Value-vs-market is roughly half the value-vs-growth spread.
// No VN value/growth proxy exists, so VND uses the 1.5% long-run default.
// >>> SECURITY SLOTS 5-6/6 : value and growth ETFs
float value_c = curr == 'VND' ? na : request.security(i_value_etf, i_beta_tf, close, ignore_invalid_symbol = true)
float growth_c = curr == 'VND' ? na : request.security(i_growth_etf, i_beta_tf, close, ignore_invalid_symbol = true)
float value_p = f_locf(value_c)
float growth_p = f_locf(growth_c)
max_bars_back(value_p, 5000)
max_bars_back(growth_p, 5000)
float cagr_value = f_get_cagr_optimized(value_p, bars_in_5y)
float cagr_growth = f_get_cagr_optimized(growth_p, bars_in_5y)
float live_hml_spread = na(value_p) or na(growth_p) ? 0.015 : (cagr_value - cagr_growth) * 0.5
live_hml_spread := math.max(math.min(live_hml_spread, 0.05), -0.02)
// Trailing returns run high after bull markets, the opposite of forward returns: half the
// 5-year excess return plus half a 5% long-run anchor, held to 4.5-8%. The excess is over
// the proxy's OWN currency's 10Y (VNINDEX: VN 10Y; the default SPY: US 10Y): a USD return
// less a local yield overstated the premium in low-yield currencies and understated it in
// high-yield ones. The premium then sits on the local base rate.
float erp_rf = curr == 'VND' ? rf_local_avg : nz(us10y_smooth, us10y_true_raw)
float auto_erp = math.min(math.max(0.5 * (cagr_mkt - erp_rf / 100) + 0.025, 0.045), 0.08)
float auto_crp_raw = local_rf_raw > us10y_true_raw ? (local_rf_raw - us10y_true_raw) / 100 : 0.0
bool rf_local = i_rf_base == 'Local 10Y'
// [FIX CRP-1] In the local build the spread is already inside the base rate.
float auto_crp = (curr == 'USD' or rf_local) ? 0.0 : auto_crp_raw
float calc_erp = i_auto_calc_erp_crp ? auto_erp : i_erp_manual
float calc_crp = i_auto_calc_erp_crp ? auto_crp : i_crp_manual
// --- Derived Metrics ---
sales_ps_ttm = shares_out_latest > 0 ? total_revenue_ttm / shares_out_latest : na
fcf_ps_ttm = shares_out_latest > 0 ? fcf_ttm / shares_out_latest : na
ocf_ps_ttm = shares_out_latest > 0 ? ocf_ttm / shares_out_latest : na
// AFFO proxy = FCF (no AFFO field): P/AFFO and AFFO DCF read the FCF per share stream.
affo_ps_ttm = fcf_ps_ttm
book_value = f_claim_on(Claim.minority) ? parent_equity : total_equity_latest
// [CLEAN SURPLUS] Roll book value forward between reports: + earnings - dividends
// accrued since the last report (Ohlson 1995), capped at half a year.
float cs_years = math.min(bars_since_real / float(bpy), 0.5)
if book_value > 0 and not na(net_income_ttm) and not na(shares_out_latest)
    book_value += (net_income_ttm - nz(div_per_share_ttm) * shares_out_latest) * cs_years
bvps_ttm = shares_out_latest > 0 ? book_value / shares_out_latest : na
tangible_book_value = book_value - nz(intangibles_latest)
tbvps_ttm = shares_out_latest > 0 ? tangible_book_value / shares_out_latest : na
market_cap_latest = close * shares_out_latest
// =====================================================================
// 6. QUARTERLY HISTORIES (the model rows are declared in section 2b)
// =====================================================================
var array<float> hist_px = array.new_float(0)
var array<float> hist_fcff_margins = array.new_float(0)
var array<float> hist_roe = array.new_float(0)
var array<float> hist_op = array.new_float(0)
int w_algo = switch i_weighting_algo
    'SMAPE (Symmetric Error)' => 1
    'MALE (Log Error)' => 2
    'WMAPE (Weighted Error)' => 3
    'RMSLE (Root Mean Sq Log)' => 4
    => 0
// ROE on AVERAGE parent equity (now and four quarters earlier).
f_roe_avg() =>
    float eq_1y = ta.valuewhen(is_new_quarter, parent_equity, 4)
    float avg_eq = not na(eq_1y) and eq_1y > 0 and parent_equity > 0 ? (parent_equity + eq_1y) / 2 : parent_equity
    not na(net_income_ttm) and avg_eq > 0 ? net_income_ttm / avg_eq : na
float roe_avg = f_roe_avg()
float cyclically_adjusted_eps = na
if use_cape
    float total_inflation_adj_eps = 0.0
    int valid_eps_count = 0
    // Constant-inflation CPI: the ratio CPI(now)/CPI(i years ago) is (1+infl)^i.
    for i = 0 to 9 by 1
        int offset = i * bpy
        if offset < bar_index and offset < 2999
            float historical_eps = eps_fy_curr[offset]
            if not na(historical_eps)
                total_inflation_adj_eps := total_inflation_adj_eps + historical_eps * math.pow(1 + lr_infl, i)
                valid_eps_count := valid_eps_count + 1
    if valid_eps_count > 0
        cyclically_adjusted_eps := total_inflation_adj_eps / valid_eps_count
// CAPE frameworks value on 10-year inflation-adjusted EPS. Its P/E history is kept on the
// same EPS (a Shiller P/E), so the multiple and the driver always match.
bool cape_on = use_cape and not na(cyclically_adjusted_eps)
float earnings_base = cape_on ? cyclically_adjusted_eps : eps_ttm
// On each new quarter, BEFORE this bar's models run: store the ratios of the period
// just ended and every model's last fair value (m.fv still holds the previous bar's),
// then re-score each track record. Histories change here and only here, so the
// weights are exact between quarters without being recomputed on every bar.
if is_new_quarter
    float price_at_period_end = close[1]
    float ev_hist = ev_now[1]
    float op_val = not na(ebit_ttm[1]) and not na(total_equity_latest[1]) and total_equity_latest[1] > 0 ? ebit_ttm[1] / total_equity_latest[1] : na
    // --- RHODES-KROPF (RKV) HISTORICAL FILTER --- (P/B row only, via m.rkv)
    // Cost-of-equity proxy on the LOCAL 10Y (+5%): the US yield misjudged every other market.
    float hist_coe_proxy = nz(rf_local_avg[1], 4.0) / 100 + 0.05
    bool rkv_trip = i_use_rkv and not na(roe_avg[1]) and roe_avg[1] < hist_coe_proxy
    // Each own-history multiple on the period just ended: m.drv still holds the previous
    // bar's driver, and a firm-level multiple is priced on EV.
    for m in MD
        if m.lk == Lever.pctl
            float r = m.drv > 0 ? (m.level == Level.firm ? ev_hist : price_at_period_end) / m.drv : na
            // [FIX RKV-FLOOR] A low P/B earned by sub-CoE returns is a deserved
            // discount. Flooring it at 1.0 pushed the average P/B UP and made value
            // traps look cheap. Drop the observation instead.
            if m.rkv and rkv_trip and not na(r) and r < 1.2
                r := na
            f_push(m.hist, r, i_numQuarters, i_ratioCap, false)
    // Loss quarters stay in: dropping them biased the medians (ROE, FCFF margin) upward.
    f_push_s(hist_roe, roe_avg, 20, 10.0)
    f_push_s(hist_op, op_val, 20, 10.0)
    f_push_s(hist_fcff_margins, not na(total_revenue_ttm) and total_revenue_ttm > 0 ? fcff / total_revenue_ttm : na, 20, 1.0)
    f_push(hist_px, close[1], 20, 999999, true)
    for m in MD
        f_push(m.fvh, m.fv, 20, 999999, true)
        [tw, te] = f_model_weight(m.fvh, hist_px, w_algo, i_w_horizon)
        m.trk := tw
// --- ROLLING BETA ENGINE --- (sampled pairs, see FIX BETA-ALIGN) + Blume adjustment
float beta_mkt = not na(raw_beta_s) ? (0.67 * raw_beta_s) + 0.33 : 1.0
// 5. Fundamental Metrics
float rev_growth = na
float total_revenue_ttm_prev = ta.valuewhen(is_new_quarter, total_revenue_ttm, 4)
if not na(total_revenue_ttm) and not na(total_revenue_ttm_prev) and total_revenue_ttm_prev != 0
    rev_growth := (total_revenue_ttm - total_revenue_ttm_prev) / math.abs(total_revenue_ttm_prev)
float total_assets_prev = ta.valuewhen(is_new_quarter, total_assets_fq, 4)
float asset_growth = na
if not na(total_assets_fq) and not na(total_assets_prev) and total_assets_prev > 0
    asset_growth := (total_assets_fq - total_assets_prev) / total_assets_prev
float ebitda_prev = ta.valuewhen(is_new_quarter, ebitda_ttm, 4)
float ebitda_growth = na
if not na(ebitda_ttm) and not na(ebitda_prev) and ebitda_prev > 0
    ebitda_growth := (ebitda_ttm - ebitda_prev) / ebitda_prev
bool investment_dummy = false
if not na(asset_growth)
    if not na(ebitda_growth)
        // [FIX HGM-1] Empire building requires the asset base to actually GROW.
        investment_dummy := asset_growth > 0 and asset_growth > ebitda_growth
    else if ebitda_ttm <= 0 and asset_growth > 0
        investment_dummy := true
bool is_deteriorating = not na(asset_growth) and not na(ebitda_growth) and asset_growth < 0 and ebitda_growth < asset_growth
// ==========================================
// COST OF EQUITY: VN LIQUIDITY-AUGMENTED 4-FACTOR MODEL
// ==========================================
// [FIX RF] One base: local 10Y (90d avg) for local-currency cash flows, or US 10Y + CRP.
float base_rf_for_calc = rf_local ? rf_local_avg / 100 : us10y_true_raw / 100
float standard_capm_coe = base_rf_for_calc + (beta_mkt * calc_erp) + calc_crp
// [FIX FX] Live rate (1 request slot) instead of a hardcoded 25000 / 0.93 / 0.79.
// fx_rate = local currency units per 1 USD.
float fx_to_usd = request.currency_rate(curr, 'USD', ignore_invalid_currency = true)
float fx_rate = not na(fx_to_usd) and fx_to_usd > 0 ? 1.0 / fx_to_usd : ((curr == 'VND') ? 25000.0 : (curr == 'EUR' ? 0.93 : (curr == 'GBP' ? 0.79 : 1.0)))
float mc_usd_billions = not na(market_cap_latest) ? (market_cap_latest / fx_rate) / 1e9 : 100.0
float size_premium = 0.0
if i_use_factors
    if mc_usd_billions < 1.0
        size_premium := live_smb_spread
    else if mc_usd_billions < 4.0
        size_premium := live_smb_spread * (1.0 - ((mc_usd_billions - 1.0) / 3.0))
float hml_premium = 0.0
float current_bm = not na(bvps_ttm) and close > 0 ? bvps_ttm / close : 0.0
// Each factor premium phases in over a band around its threshold (f_ramp): B/M and the
// 11-month return move with the price on every bar, so a step made the fair value jump
// whenever either crossed its line.
if i_use_factors
    // Loading = B/M / 2 (0.4-1.0: even the deepest value decile loads about 1 on HML),
    // phasing in from B/M 0.7 to 0.9.
    hml_premium := live_hml_spread * math.min(current_bm, 2.0) / 2 * f_ramp(current_bm, 0.7, 0.9)
float px_1m_ago = close[math.min(math.max(1, int(bpy / 12)), 4900)]
float px_12m_ago = close[math.min(bpy, 4900)]
float mom_premium = 0.0
float mom_hurdle = (curr == 'VND') ? 0.45 : 0.30
if i_use_factors and not na(px_1m_ago) and not na(px_12m_ago) and px_12m_ago > 0
    float trailing_11m_ret = (px_1m_ago - px_12m_ago) / px_12m_ago
    // None inside 0.8x the hurdle, the full premium beyond 1.2x.
    mom_premium := i_mom_prem * (f_ramp(trailing_11m_ret, 0.8 * mom_hurdle, 1.2 * mom_hurdle) - f_ramp(-trailing_11m_ret, 0.8 * mom_hurdle, 1.2 * mom_hurdle))
float microstructure_premium = 0.0
// Liquidity on a DAILY basis whatever the chart timeframe: a bar spans days_per_bar trading
// days, so per-bar turnover is divided by it and the per-bar Amihud ratio scaled by its
// square root (|return| grows with the square root of time, volume in proportion to it).
// The windows are in days too (90 days, 1 year), so a daily chart is unchanged.
float days_per_bar = trading_days / float(bpy)
int liq_n90 = math.max(math.min(int(math.round(90 / days_per_bar)), 4900), 5)
int liq_n252 = math.max(math.min(int(math.round(252 / days_per_bar)), 4900), 5)
if i_use_factors
    float safe_vol = nz(volume, 1.0)
    float dollar_vol_usd = (close * safe_vol) / fx_rate
    float bar_ret_abs = math.abs(ta.change(close) / nz(close[1], close))
    float amihud_raw = dollar_vol_usd > 0 ? (bar_ret_abs / dollar_vol_usd) * 1e6 * math.sqrt(days_per_bar) : 0.0
    float amihud_90d = ta.sma(amihud_raw, liq_n90)
    float illiq_penalty = i_liq_prem * nz(f_ramp(amihud_90d, 0.1, 0.5))
    // ta.sma runs on every bar: inside the share-count condition it averaged only qualifying bars.
    float avg_turnover_12m = ta.sma(shares_out_latest > 0 ? nz(volume) / shares_out_latest : na, liq_n252) / days_per_bar
    float spec_penalty = not na(volume) and shares_out_latest > 0 ? i_liq_prem * nz(f_ramp(avg_turnover_12m, 0.01, 0.02)) : 0.0
    microstructure_premium := math.max(illiq_penalty, spec_penalty)
float rmw_premium = 0.0
float current_op = not na(ebit_ttm) and total_equity_latest > 0 ? ebit_ttm / total_equity_latest : 0.0
if i_use_factors
    // [FIX RMW] In Fama-French 5 robust profitability earns a POSITIVE premium: a robust
    // firm loads positively on RMW, so its required return goes up. +1.5% phases in as
    // operating profitability goes from 17.5% to 22.5%, -1.5% as it falls from 7.5% to 2.5%.
    rmw_premium := 0.015 * (f_ramp(current_op, 0.175, 0.225) - f_ramp(-current_op, -0.075, -0.025))
float cost_of_equity = standard_capm_coe + size_premium + hml_premium + mom_premium + rmw_premium + microstructure_premium
float min_equity_return = base_rf_for_calc + 0.03
cost_of_equity := math.max(cost_of_equity, min_equity_return)
float equity_weight = not na(market_cap_latest) and not na(total_debt_latest) and market_cap_latest + total_debt_latest > 0 ? market_cap_latest / (market_cap_latest + total_debt_latest) : 1.0
float debt_weight = 1.0 - equity_weight
float auto_credit_spread = f_synthetic_spread(ebit_normalized, interest_expense_ttm)
// [FIX CRP-2] CRP is charged once, in the cost of equity. Debt = same base + synthetic spread.
float cost_of_debt_synthetic = base_rf_for_calc + auto_credit_spread + (rf_local ? 0.0 : calc_crp)
float final_wacc_auto = equity_weight * cost_of_equity + debt_weight * nz(cost_of_debt_synthetic, 0.05) * (1 - effective_tax)
float final_discount_rate = nz(final_wacc_auto, cost_of_equity)
// ==============================================
// 4. TRIANGULATED ROBUST GROWTH & TERMINAL RATES
// ==============================================
float retention_ratio = 1.0
if not na(div_per_share_ttm) and not na(eps_ttm) and eps_ttm > 0
    payout = div_per_share_ttm / eps_ttm
    retention_ratio := 1.0 - math.min(payout, 1.0)
float median_roe = f_median(hist_roe)
float median_op = f_median(hist_op)
// [FIX SGR] Sustainable growth = ROE x retention. EBIT/equity is pre-interest and pre-tax.
// No positive profitability on record -> no sustainable-growth leg (it was a 5% guess).
float base_profitability = median_roe > 0 ? median_roe : median_op > 0 ? median_op * (1 - effective_tax) : na
float normalized_sgr = base_profitability * retention_ratio
float sales_cagr_3y = f_calculate_cagr_from_series(total_revenue_ttm, 3)
// Reinvestment = NOPAT - FCFF: both unlevered (the levered FCF also nets out interest).
// A bank's operating cash flow swings with loans and deposits, so its fundamental growth
// is ROE x retention, not ROIC x reinvestment.
float reinvestment_rate = nopat_adjusted > 0 ? (nopat_adjusted - fcff) / nopat_adjusted : 0.0
float roic_sgr = use_bank_model ? normalized_sgr : math.max(roic_adj * reinvestment_rate, 0.0)
// [MACRO] The CPI/GDP macro adjustment is gone with the feeds.
// [STREET-1] Forward growth leg: consensus EPS growth (historical, lag-gated),
// then sales CAGR, then the manual value. Replaces the fixed 10% input.
bool g_manual = i_growth_src == 'Manual'
float fwd_growth_leg = g_manual ? i_analyst_growth : not na(fwd_eps_growth) ? fwd_eps_growth : not na(sales_cagr_3y) ? sales_cagr_3y : i_analyst_growth
string fwd_growth_src = g_manual ? 'Manual' : not na(fwd_eps_growth) ? 'Consensus EPS' : not na(sales_cagr_3y) ? 'Sales CAGR' : 'Manual (fallback)'
// Triangulation: sustainable growth 15%, ROIC x reinvestment 40%, the forward leg 15%, the
// 3-year sales CAGR 30%. A leg with no data leaves and the others are re-weighted (the sales
// leg used to enter at a guessed 5%). The forward leg always exists, so the blend does too.
array<float> g_leg = array.from(normalized_sgr, roic_sgr, fwd_growth_leg, sales_cagr_3y)
array<float> g_wt = array.from(0.15, 0.40, 0.15, 0.30)
float g_num = 0.0
float g_den = 0.0
for [i, x] in g_leg
    if not na(x)
        g_num += x * array.get(g_wt, i)
        g_den += array.get(g_wt, i)
float base_triangulated_growth = g_num / g_den
float calc_growth_triangulated = math.min(math.max(base_triangulated_growth, -0.10), 0.35)
float dynamic_growth_cap = 0.25
if selected_industry == 'Technology' or selected_industry == 'Healthcare (Pharma/Biotech)' or selected_industry == 'Consumer Discretionary'
    dynamic_growth_cap := 0.40
else if selected_industry == 'Utilities' or selected_industry == 'REITs' or selected_industry == 'Consumer Staples'
    dynamic_growth_cap := 0.15
float final_growth_rate = math.min(calc_growth_triangulated, dynamic_growth_cap)
final_growth_rate := math.max(final_growth_rate, -0.05) // [FIX G-FLOOR] shrinking firms may shrink
float nominal_gdp_ceiling = math.max(nz(rf_local_avg / 100, 0.04), lr_infl + lr_rgdp)
float unbiased_dynamic_g = lr_infl + 0.005
unbiased_dynamic_g := math.max(unbiased_dynamic_g, 0.015)
unbiased_dynamic_g := math.min(unbiased_dynamic_g, 0.035)
float final_terminal_growth = math.min(unbiased_dynamic_g, nominal_gdp_ceiling)
// ==============================================================
// === THE MODEL STAGE: the stream table, then every row on one path
// ==============================================================
// Own multiples: Base = the ticker's own average multiple x the driver (TTM and forward legs
// blended); Bear/Bull = its own low / high percentile multiples on the same driver.
// A trailing multiple on NEXT year's driver is a price one year out, so the forward leg
// is discounted back at CoE less the dividend yield, as the street targets are. A CAPE
// driver (a 10-year average) has no forward leg.
bool rs_dirty = is_new_quarter or barstate.isfirst
float fwd_disc = 1 + math.max(cost_of_equity - nz(div_yield, 0), 0.0)
float eps_f1_proj = not na(final_growth_rate) and not cape_on ? earnings_base * (1 + final_growth_rate) : na
// No sales CAGR on record -> no forward EBITDA leg (TTM only), not a guessed 5%.
float sales_cagr = f_calculate_cagr_from_series(total_revenue_ttm, i_cagr_years)
float final_sales_f1 = total_revenue_ttm * (1 + sales_cagr)
float ebitda_margin_ttm = total_revenue_ttm > 0 ? ebitda_ttm / total_revenue_ttm : na
float est_ebitda_fwd = not na(final_sales_f1) and not na(ebitda_margin_ttm) ? final_sales_f1 * ebitda_margin_ttm : na
// Discount rates: one base per level (a row's level picks one). WACC for the firm is floored
// at 2%, so Bull is never above Base.
float wacc_base = math.max(final_discount_rate, 0.02)
// Hamada on MARKET leverage, the weights WACC uses (book equity overstates D/E). The
// unlevered cost of capital keeps every premium in the cost of equity (country, size,
// value, liquidity ...) and strips only the leverage part of beta.
float de_mkt = nz(total_debt_latest) / (market_cap_latest > 0 ? market_cap_latest : math.max(nz(total_equity_latest), 1.0))
float unlevered_beta = beta_mkt / (1 + (1 - effective_tax) * de_mkt)
float unlevered_coe = math.max(cost_of_equity - (beta_mkt - unlevered_beta) * calc_erp, math.min(nz(cost_of_debt_synthetic, base_rf_for_calc + 0.01), cost_of_equity), 0.02)
float total_debt_1y_ago = ta.valuewhen(is_new_quarter, total_debt_latest, 4)
// Equity Cash Flow: net income per share and a normalised ROE (5-year median, else today's).
float ni_ps = net_income_ttm / shares_out_latest
float roe_n = nz(median_roe, roe_avg)
// Telecom unbundling: NetCo share = net PPE / invested capital (held to 30-90%; no PPE, no
// split). NetCo = that share of invested capital (the network, net PPE) at a RAB multiple;
// ServeCo = the rest of the unlevered FCF and NOPAT through the value-driver DCF. The two
// shares match, so at allowed return = ROIC = WACC the parts add up to the whole. Both are
// firm values: the claims come off once.
float netco_sh = ppe_net_fq > 0 ? math.min(math.max(ppe_net_fq / invested_capital_adj, 0.3), 0.9) : na
float netco_rab = netco_sh * invested_capital_adj
// Reverse DCF input (median unlevered FCF margin; no history -> N/A, not a guessed 10%) and
// the Rule of 40 margin.
float median_fcf_margin = f_median(hist_fcff_margins)
float dcf_input_fcf_total_rev = total_revenue_ttm * median_fcf_margin
float true_fcf_margin_ttm = true_fcf / total_revenue_ttm
// [FIX GRAHAM] No revenue-based EPS fallback: Graham needs real positive earnings.
float base_eps = eps_ttm > 0 ? eps_ttm : na
float graham_y = rf_local_avg > 0 ? rf_local_avg : 4.0
// 4.4 / Y rescales for bond yields. Below 4.4% it multiplied value UP (x4.4
// at a 1% yield), so it is capped at 1.0: it may only penalise high yields.
float graham_yield_adj = math.min(4.4 / graham_y, 1.0)
// Graham meant a 7-10 year growth rate; cap at 15% so the 2g term cannot run away.
float graham_g = math.max(math.min(final_growth_rate, 0.15), 0.0)
// Owners' earnings = OCF - maintenance capex; growth capex = sales growth x net PPE / sales
// (Greenwald: the capital a unit of new sales ties up; gross PPE counts retired assets).
float oe_per_share = na
bool oe_ok = false
if ppe_net_fq > 0 and total_revenue_ttm > 0 and not na(total_revenue_ttm_prev)
    float abs_total_capex = math.abs(capex_ttm)
    float growth_capex = math.min(math.max(0, (total_revenue_ttm - total_revenue_ttm_prev) * (ppe_net_fq / total_revenue_ttm)), abs_total_capex)
    float owners_earnings = ocf_ttm - (abs_total_capex - growth_capex)
    oe_per_share := shares_out_latest > 0 ? owners_earnings / shares_out_latest : na
    oe_ok := owners_earnings > 0 and cost_of_equity > 0
bool omni_manual = i_omni_mode == 'Manual (Tick Models Below)'
bool om_free = is_omnibus and omni_manual and not i_omni_strict
// THE STREAM TABLE: every input a model reads, formed once per bar (unit and owner in
// f_sunit / f_sown), each with the provenance tier a row that reads it inherits. Then the
// base rate of each level, today's scenario shifts, growth and the add-ons' inputs.
var Drv D = Drv.new(map.new<Sx, float>(), map.new<Sx, int>())
D.stream(Sx.eps_b, earnings_base, t_eps)
D.stream(Sx.eps_f, eps_f1_proj, t_eps)
D.stream(Sx.sales_ps, sales_ps_ttm, t_rev)
D.stream(Sx.fcf_ps, fcf_ps_ttm, t_ocf)
D.stream(Sx.bvps, bvps_ttm, t_equity)
D.stream(Sx.tbvps, tbvps_ttm, t_equity)
D.stream(Sx.ebitda, ebitda_ttm, t_ebitda)
D.stream(Sx.ebitda_f, est_ebitda_fwd, t_ebitda)
D.stream(Sx.ocf_ps, ocf_ps_ttm, t_cfo)
D.stream(Sx.fcff, fcff, t_ocf)
D.stream(Sx.nopat, nopat_adjusted, t_ebit)
D.stream(Sx.ic, invested_capital_adj, 3)
D.stream(Sx.roic, roic_adj, 3)
D.stream(Sx.fcff_s, fcff * (1 - netco_sh), t_ocf)
D.stream(Sx.nopat_s, nopat_adjusted * (1 - netco_sh), t_ebit)
D.stream(Sx.ni, net_income_ttm, t_ni)
D.stream(Sx.book, book_value, t_equity)
D.stream(Sx.ni_ps, ni_ps, t_ni)
D.stream(Sx.roe_n, roe_n, t_equity)
D.stream(Sx.dps, div_per_share_ttm, stale_cap)
D.stream(Sx.oe_ps, oe_ok ? oe_per_share : na, t_ocf)
D.stream(Sx.nopat_n, nopat_norm, t_ebit)
D.stream(Sx.eps_pos, base_eps, t_eps)
D.stream(Sx.g_gra, graham_g, 3)
D.stream(Sx.yadj, graham_yield_adj, 3)
D.stream(Sx.rev, total_revenue_ttm, t_rev)
D.stream(Sx.rev_g, rev_growth, t_rev)
D.stream(Sx.fcf_margin, true_fcf_margin_ttm, t_ocf)
D.stream(Sx.ebit, ebit_ttm, t_ebit)
D.r_firm := wacc_base
D.r_unlev := unlevered_coe
D.r_eq := cost_of_equity
D.r_bank := math.min(cost_of_equity, 0.15)
D.sh_r := i_scen_wacc_bps
D.sh_g := i_scen_growth_bps
D.sh_t := i_scen_g_bps
D.g1 := final_growth_rate
D.gcap := dynamic_growth_cap
D.gT := final_terminal_growth
D.yrs := i_dcf_stage1_yrs
D.yrs_rim := i_iv_projection_period
D.fwd_disc := fwd_disc
D.pipe := nz(rnd_ttm) * 5.0 * 0.15
D.netco_rab := netco_rab
D.allowed := i_rab_allowed_return
D.shield := nz(total_debt_latest) * effective_tax
// Own-history multiples: ratio statistics, recomputed only when the history changes.
if rs_dirty
    for m in MD
        if m.lk == Lever.pctl
            [a, sy, plo, phi] = f_ratio_stats(m.hist, i_useMean, m.dflt, i_scen_lo_pct, i_scen_hi_pct, i_scen_min_n)
            m.avg := a, m.syn := sy, m.plo := plo, m.phi := phi
// Every row through f_eval. Base on every bar; Bear and Bull on the last bar only, the one
// place anything reads them. Reference rows (rNPV) run after the rows they build on. A
// sector model runs where the framework allocates it, or where a non-strict Manual Omnibus
// ticks it.
int n_sc = barstate.islast ? 3 : 1
for pass = 0 to 1
    for m in MD
        if m.eng != Eng.comp and (m.eng == Eng.ref) == (pass == 1)
            m.fv := na
            m.lo := na
            m.hi := na
            if m.grp != Group.sect or m.fw or (om_free and m.tick)
                for s = 0 to n_sc - 1
                    float v = f_eval(m, D, CL, s)
                    if s == 0
                        m.fv := v
                    else if s == 1
                        m.lo := v
                    else
                        m.hi := v
            else
                Res r0 = m.res.get(0)
                r0.value := na
                r0.why := 'not allocated by the framework'
float implied_exit_multiple = M_DCF.res.get(0).aux
// Provenance tier of each row: the worse of its tier sources' tiers. A relative multiple is on
// when the framework allocates it and the inputs it needs are positive (P/E: EPS, P/FCF: FCF);
// every other row, when allocated.
for m in MD
    m.tier := f_tier(m, D)
    m.on := m.fw and (m.grp != Group.rel or m.need1 == Sx.none or D.s.get(m.need1) > 0)
    // 🛡️ ZERO-BOUND: [FIX NEG] a negative or na base value never enters any blend.
    m.fv := m.fv > 0 ? m.fv : na
// ==============================================================
// === SHADOW CHECK (this version only): the previous model stage alongside
// ==============================================================
// The model stage as it was before the rows, run from the same inputs into SHM (scenario x
// row) and compared with the rows: Base on every bar, Bear and Bull on the last bar, each
// within 1e-9 of the larger of the value and the price, na only against na; the tiers and
// the DCF's exit multiple too. Delete this block, f_apply and the f_calculate_* functions
// once it reads MATCH.
var matrix<float> SHM = matrix.new<float>(3, MD.size(), na)
var int sh_n = 0
var int sh_bad = 0
var float sh_max = 0.0
var string sh_first = ''
float sh_bar = na
if i_shadow
    SHM.fill(na)
    float claims_o = net_debt_robust + (i_strict_cap ? nz(minority_fq) + pref_equity : 0.0)
    float sh_ev = math.max(shares_out_latest, 1)
    array<float> drvs = array.from(earnings_base, sales_ps_ttm, fcf_ps_ttm, bvps_ttm, tbvps_ttm, ebitda_ttm, ocf_ps_ttm, affo_ps_ttm)
    for k = 1 to 8
        Model m = MD.get(k)
        float dk = array.get(drvs, k - 1)
        float dfk = k == 1 ? eps_f1_proj : k == 6 ? est_ebitda_fwd : na
        for s = 0 to 2
            float mu = f_sc(s, m.avg, m.plo, m.phi)
            SHM.set(s, k, f_blend2(f_apply(dk, mu, k == 6, claims_o, sh_ev), f_apply(dfk, mu, k == 6, claims_o, sh_ev) / fwd_disc))
    float wacc_bear = wacc_base + i_scen_wacc_bps
    float wacc_bull = math.max(wacc_base - i_scen_wacc_bps, 0.02)
    float coe_bear = cost_of_equity + i_scen_wacc_bps
    float coe_bull = math.max(cost_of_equity - i_scen_wacc_bps, 0.02)
    float tg_bear = math.max(final_terminal_growth - i_scen_g_bps, 0.0)
    float tg_bull = final_terminal_growth + i_scen_g_bps
    // [FIX SCEN-G] Bear/Bull also move stage-1 growth.
    float g_bear = math.max(final_growth_rate - i_scen_growth_bps, -0.05)
    float g_bull = math.min(final_growth_rate + i_scen_growth_bps, dynamic_growth_cap)
    // RIM inputs: the Equity model for banks and insurers, the Entity model for the rest.
    float rim_nopat_proxy = use_bank_model ? net_income_ttm : nopat_adjusted
    float rim_capital_proxy = use_bank_model ? book_value : invested_capital_adj
    float rim_discount_proxy = use_bank_model ? math.min(cost_of_equity, 0.15) : wacc_base
    float rim_debt_proxy = use_bank_model ? 0.0 : claims_o
    float nopat_ps = nopat_adjusted / shares_out_latest
    float fcff_ps = fcff / shares_out_latest
    float claims_ps_o = claims_o / shares_out_latest
    bool acq_ok = ebit_ttm > 0 and shares_out_latest > 0
    float sh_iem = na
    for s = 0 to 2
        float wc = f_sc(s, wacc_base, wacc_bear, wacc_bull)
        float ce = f_sc(s, cost_of_equity, coe_bear, coe_bull)
        float gs = f_sc(s, final_growth_rate, g_bear, g_bull)
        float tg = f_sc(s, final_terminal_growth, tg_bear, tg_bull)
        // Extended value-driver DCF (McKinsey) on unlevered FCF, less the claims; the base case
        // also reports the implied exit multiple. rNPV adds the pipeline to this same DCF.
        [dcf_v, dcf_m] = f_calculate_dcf_value_driver_extended(fcff_ps, nopat_ps, roic_adj, wc, gs, tg, i_dcf_stage1_yrs)
        float dcf_eq = dcf_v - claims_ps_o
        SHM.set(s, M_DCF.idx, dcf_eq)
        if s == 0
            sh_iem := dcf_m
        // --- Sector models ---
        if M_RNPV.fw or (om_free and i_om_rnpv)
            SHM.set(s, M_RNPV.idx, f_calculate_rnpv_sotp(dcf_eq, nz(rnd_ttm), shares_out_latest))
        if M_ECF.fw or (om_free and i_om_ecf)
            // FCFE = NI less the equity reinvestment growth needs (g / ROE): the value driver on
            // the equity side, at CoE. A bank borrows as raw material, so net borrowing is not a
            // cash flow to its shareholders; the equity it must retain to grow is.
            [ec_v, ec_m] = f_calculate_dcf_value_driver_extended(ni_ps * (1 - gs / roe_n), ni_ps, roe_n, ce, gs, tg, i_dcf_stage1_yrs)
            SHM.set(s, M_ECF.idx, ni_ps > 0 and roe_n > 0 ? ec_v : na)
        if M_ADCF.fw or (om_free and i_om_affo)
            // FCF is already after capex: the terminal value takes no second reinvestment charge.
            [af_v, af_m] = f_calculate_dcf_value_driver_extended(affo_ps_ttm, affo_ps_ttm, float(na), ce, gs, tg, i_dcf_stage1_yrs)
            SHM.set(s, M_ADCF.idx, af_v)
        if M_UNB.fw or (om_free and i_om_unb)
            float netco = f_calculate_rab_model(netco_rab, i_rab_allowed_return, wc, tg, 0.0, shares_out_latest)
            [sv_v, sv_m] = f_calculate_dcf_value_driver_extended(fcff_ps * (1 - netco_sh), nopat_ps * (1 - netco_sh), roic_adj, wc, gs, tg, i_dcf_stage1_yrs)
            SHM.set(s, M_UNB.idx, netco + sv_v - claims_ps_o)
        if M_APV.fw or (om_free and i_om_apv)
            // Unlevered FCF through the same two-stage DCF at the unlevered cost of capital, plus
            // the tax shield on permanent debt (debt x tax), less the claims ahead of common.
            [ap_v, ap_m] = f_calculate_dcf_value_driver_extended(fcff_ps, nopat_ps, roic_adj, f_sc(s, unlevered_coe, unlevered_coe + i_scen_wacc_bps, math.max(unlevered_coe - i_scen_wacc_bps, 0.02)), gs, tg, i_dcf_stage1_yrs)
            SHM.set(s, M_APV.idx, ap_v + nz(total_debt_latest) * effective_tax / shares_out_latest - claims_ps_o)
        if M_EVA.fw or (om_free and i_om_eva)
            SHM.set(s, M_EVA.idx, f_calculate_eva(nopat_adjusted, invested_capital_adj, wc, tg, claims_o, shares_out_latest))
        if M_DDM.fw or (om_free and i_om_ddm)
            SHM.set(s, M_DDM.idx, f_calculate_ddm(div_per_share_ttm, ce, tg))
        // --- Absolute models (the DCF is above) ---
        SHM.set(s, M_RIM.idx, f_calculate_rim(rim_nopat_proxy, rim_capital_proxy, shares_out_latest, rim_debt_proxy, f_sc(s, rim_discount_proxy, rim_discount_proxy + i_scen_wacc_bps, math.max(rim_discount_proxy - i_scen_wacc_bps, 0.02)), gs, tg, i_iv_projection_period))
        // EPV (Greenwald): no-growth perpetuity of NORMALISED NOPAT, less the claims.
        SHM.set(s, M_EPV.idx, (nopat_norm / wc - claims_o) / shares_out_latest)
        // Graham: Bear/Bull halve / add half the growth term.
        SHM.set(s, M_GRA.idx, base_eps * (8.5 + 2 * (graham_g * f_sc(s, 1.0, 0.5, 1.5)) * 100) * graham_yield_adj)
        // Rule of 40 needs a year-ago revenue: no guessed growth (the old fallback was 10%).
        // Bear = growth less the shift, not floored at 0: the floor lifted a shrinking firm's
        // Bear case above its Base.
        SHM.set(s, M_R40.idx, na(rev_growth) ? na : f_calculate_rule_of_x_fv(f_sc(s, rev_growth, rev_growth - i_scen_r40_bps, rev_growth + i_scen_r40_bps), true_fcf_margin_ttm, total_revenue_ttm, claims_o, shares_out_latest))
        // 🌟 THE ACQUIRER'S MULTIPLE (EV / EBIT): Bear/Bull move the target multiple.
        if acq_ok
            SHM.set(s, M_ACQ.idx, (ebit_ttm * f_sc(s, i_acquirer_mult, math.max(i_acquirer_mult - i_scen_acq_delta, 1.0), i_acquirer_mult + i_scen_acq_delta) - claims_o) / shares_out_latest)
        // Owners' earnings are after interest (an equity cash flow): no-growth perpetuity at CoE.
        if oe_ok
            SHM.set(s, M_OE.idx, oe_per_share / ce)
    array<int> tiers_o = array.from(3, t_eps, t_rev, t_ocf, t_equity, t_equity, t_ebitda, t_cfo, t_ocf, t_ocf, math.min(t_ni, t_equity), t_ocf, t_ocf, t_ocf, t_ebit, stale_cap, t_ocf, use_bank_model ? math.min(t_ni, t_equity) : t_ebit, t_ebit, t_eps, math.min(t_rev, t_ocf), t_ebit, t_ocf)
    string sh_day = str.format_time(time, 'yyyy-MM-dd')
    float bar_max = 0.0
    for [k, m] in MD
        if m.eng != Eng.comp
            for s = 0 to n_sc - 1
                float o = SHM.get(s, k)
                o := s == 0 and not (o > 0) ? na : o
                float n = s == 0 ? m.fv : s == 1 ? m.lo : m.hi
                float rel = na(o) or na(n) ? na : math.abs(n - o) / math.max(math.abs(o), close)
                bool same = na(o) ? na(n) : not na(n) and rel <= 1e-9
                sh_n += 1
                bar_max := math.max(bar_max, nz(rel))
                if not same
                    sh_bad += 1
                    if sh_first == ''
                        sh_first := m.code + ' ' + (s == 0 ? 'Base' : s == 1 ? 'Bear' : 'Bull') + ' on ' + sh_day + ': previous ' + str.tostring(o) + ', rows ' + str.tostring(n)
        if m.tier != array.get(tiers_o, k)
            sh_bad += 1
            if sh_first == ''
                sh_first := m.code + ' tier on ' + sh_day + ': previous ' + str.tostring(array.get(tiers_o, k)) + ', rows ' + str.tostring(m.tier)
    bool iem_same = na(sh_iem) ? na(implied_exit_multiple) : not na(implied_exit_multiple) and math.abs(implied_exit_multiple - sh_iem) <= 1e-9 * math.max(math.abs(sh_iem), 1.0)
    sh_n += 1
    if not iem_same
        sh_bad += 1
        if sh_first == ''
            sh_first := 'DCF exit multiple on ' + sh_day + ': previous ' + str.tostring(sh_iem) + ', rows ' + str.tostring(implied_exit_multiple)
    sh_max := math.max(sh_max, bar_max)
    sh_bar := bar_max
// ==============================================================
// === STANDARD BLEND: multiples + sector models + named absolute =
// ==============================================================
// Weight = track record x provenance. Weight 0 = no track record yet: if NO model
// has one (young listing), fall back to equal weights x provenance.
float blend_sc_sum = 0.0
for m in MD
    if m.grp != Group.comp
        m.w := m.on and m.std and m.fv > 0 ? m.trk * f_tier_q(m.tier) : 0.0
        blend_sc_sum += m.w
bool blend_eq = blend_sc_sum <= 0
float blend_w_tot = 0.0
for m in MD
    if m.grp != Group.comp
        m.w := m.fv > 0 ? (blend_eq ? (m.on and m.std ? f_tier_q(m.tier) : 0.0) : m.w) : 0.0
        blend_w_tot += m.w
float compositeFairValue = na
float compositeLo = na
float compositeHi = na
array<float> blend_vals = array.new_float(0)
array<float> blend_ws = array.new_float(0)
if blend_w_tot > 0
    array<float> bw = array.new_float(MD.size(), 0.0)
    for [k, m] in MD
        if m.grp != Group.comp
            array.set(bw, k, m.w)
    f_fam_cap(bw)
    compositeFairValue := 0.0, compositeLo := 0.0, compositeHi := 0.0
    for [k, m] in MD
        if m.grp != Group.comp
            m.w := array.get(bw, k) // normalised, family-capped share, read by the table
            if m.w > 0
                compositeFairValue += m.fv * m.w
                compositeLo += math.max(nz(m.lo, m.fv), 0.0) * m.w
                compositeHi += nz(m.hi, m.fv) * m.w
                array.push(blend_vals, m.fv)
                array.push(blend_ws, m.w)
float fv_stddev = nz(f_wsd(blend_vals, blend_ws, compositeFairValue), compositeFairValue * 0.15)
M_COMP.fv := compositeFairValue, M_COMP.lo := compositeLo, M_COMP.hi := compositeHi
// ==========================================
// BENEISH M-SCORE (5-Variable Adjusted)
// ==========================================
// Year-ago revenue, assets and debt reuse total_revenue_ttm_prev, total_assets_prev
// and total_debt_1y_ago (same trigger, same lag).
float rec_prev = ta.valuewhen(is_new_quarter, accounts_receivable_ttm, 4)
float cogs_prev = ta.valuewhen(is_new_quarter, cogs_ttm, 4)
bool is_manipulator = false
float m_score = na
if i_useBeneishCheck
    float rev_t = total_revenue_ttm
    float rev_prev = total_revenue_ttm_prev
    float dsri = (accounts_receivable_ttm / rev_t) / (rec_prev / rev_prev)
    float gmi = ((rev_prev - cogs_prev) / rev_prev) / ((rev_t - cogs_ttm) / rev_t)
    float sgi = rev_t / rev_prev
    float lvgi = (total_debt_latest / total_assets_fq) / math.max((total_debt_1y_ago / total_assets_prev), 0.001)
    float tata = (net_income_ttm - ocf_ttm) / total_assets_fq
    // [NEUTRAL] A missing index = 1.0 (no change), missing accruals = 0; needs sales growth.
    dsri := math.min(math.max(nz(dsri, 1.0), 0.5), 3.0)
    gmi := math.min(math.max(nz(gmi, 1.0), 0.5), 3.0)
    sgi := math.min(math.max(sgi, 0.5), 3.0)
    lvgi := math.min(math.max(nz(lvgi, 1.0), 0.5), 3.0)
    tata := nz(tata)
    m_score := -4.49 + (0.920 * dsri) + (0.528 * gmi) + (0.892 * sgi) + (4.679 * tata) - (0.327 * lvgi)
    is_manipulator := m_score > -1.78
// Provisional only; bands and verdict are resolved after the Omnibus.
float finalFairValue = compositeFairValue > 0 ? compositeFairValue : na
// ==============================================================
// === GRAND MASTER BLEND (Multi-Algo Smart Omnibus) ============
// ==============================================================
// Every model is a member in its own right, weighted on its own track record. Auto: every
// model the framework enables. Manual: the ticked boxes, gated by the framework unless
// strict is off. The Standard Composite holds every model with a Standard weight: only
// Manual can tick it, and it is flagged as a double count next to any of them.
bool omni_sane_on = i_omni_sanity_x >= 1.5 and close > 0
float omni_w_sum = 0.0
for m in MD
    float v = m.fv
    bool comp = m.grp == Group.comp
    bool ok = omni_manual ? m.tick and (not i_omni_strict or m.on) : not comp and m.on
    // Sanity: drop a member beyond N x / (1/N) x the price (never the Composite).
    m.om := ok and v > 0 and (not omni_sane_on or comp or (v <= close * i_omni_sanity_x and v * i_omni_sanity_x >= close))
    m.om_w := m.om ? m.trk * f_tier_q(m.tier) : 0.0
    omni_w_sum += m.om_w
// m.om_w becomes each member's final share: track record (or, when no member has one,
// equal) x tier, family-capped. A held row gives way once its holder carries weight: the
// relations are derived from the rows on bar 0 (rNPV contains the DCF; P/AFFO reads the
// same FCF stream as P/FCF). A member left with no share leaves the blend.
array<float> ow = array.new_float(MD.size(), 0.0)
for [k, m] in MD
    bool dup = m.held_by >= 0 and array.get(ow, m.held_by) > 0
    array.set(ow, k, m.om and not dup ? (omni_w_sum > 0 ? m.om_w : f_tier_q(m.tier)) : 0.0)
f_fam_cap(ow)
float raw_omnibus_fv = 0.0, float raw_omnibus_lo = 0.0, float raw_omnibus_hi = 0.0
int omni_n = 0, int omni_sub = 0
array<float> omni_vals = array.new_float(0)
array<float> omni_ws = array.new_float(0)
for [k, m] in MD
    m.om_w := array.get(ow, k)
    m.om := m.om and m.om_w > 0
    if m.om
        omni_n += 1
        omni_sub += m.w > 0 ? 1 : 0
        raw_omnibus_fv += m.fv * m.om_w
        raw_omnibus_lo += math.max(nz(m.lo, m.fv), 0.0) * m.om_w
        raw_omnibus_hi += nz(m.hi, m.fv) * m.om_w
        array.push(omni_vals, m.fv)
        array.push(omni_ws, m.om_w)
bool omni_dupe = M_COMP.om and omni_sub > 0
string omni_dupe_tt = omni_dupe ? 'WARNING: the Standard Composite is in the blend alongside ' + str.tostring(omni_sub) + ' of the models it already contains. Those are counted twice.' : ''
bool omni_active = is_omnibus and omni_n > 0
if omni_active
    finalFairValue := raw_omnibus_fv
    compositeLo := raw_omnibus_lo
    compositeHi := raw_omnibus_hi
    fv_stddev := nz(f_wsd(omni_vals, omni_ws, raw_omnibus_fv), raw_omnibus_fv * 0.15)
// ==========================================
// RHODES-KROPF (RKV) M/B DECOMPOSITION & VALUE TRAP DETECTION (on the value shown)
// ==========================================
float rkv_mispricing_mv = na
float rkv_growth_vb = na
bool is_rkv_value_trap = false
bool is_rkv_deep_value = false
float current_pb_val = bvps_ttm > 0 ? close / bvps_ttm : na
if i_use_rkv and finalFairValue > 0 and bvps_ttm > 0
    rkv_mispricing_mv := close / finalFairValue
    rkv_growth_vb := finalFairValue / bvps_ttm
    if current_pb_val < 1.5
        if rkv_growth_vb < 1.0
            is_rkv_value_trap := true
        else if rkv_mispricing_mv < 0.85
            is_rkv_deep_value := true
// ==============================================================
// === RESOLVE: BANDS + VERDICT (after the blend is final) ======
// ==============================================================
float upperBound = na(finalFairValue) ? na : finalFairValue + nz(fv_stddev, finalFairValue * 0.15)
float lowerBound = na(finalFairValue) ? na : finalFairValue - nz(fv_stddev, finalFairValue * 0.15)
upperBound := upperBound > 0 ? upperBound : na
lowerBound := lowerBound > 0 ? lowerBound : na
float fv_band = math.max(nz(finalFairValue, 0) * 0.03, 0.0)
string valuation_status = na(finalFairValue) ? 'N/A' : close > upperBound ? 'Very Overvalued' : close > finalFairValue + fv_band ? 'Overvalued' : close < lowerBound ? 'Very Undervalued' : close < finalFairValue - fv_band ? 'Undervalued' : 'Fairly Valued'
// Track record of the value actually shown (Omnibus or Standard), aligned with hist_px:
// the confidence score grades this, not the Standard composite alone.
var array<float> hist_final = array.new_float(0)
if is_new_quarter
    f_push(hist_final, finalFairValue[1], 20, 999999, true)
// Reverse DCF: the 10-year growth the current price implies. Table only -> last bar only.
float implied_market_growth = na
// The same 10-year average our own DCF assumes (stage-1 growth fading to terminal), so the
// price is judged against a like-for-like horizon, not a one-year growth rate.
float our_path_g = na
if barstate.islast
    implied_market_growth := f_calculate_reverse_dcf(close, dcf_input_fcf_total_rev, CL, wacc_base, final_terminal_growth, 10)
    float g_t = math.min(final_terminal_growth, wacc_base - TCAP)
    float prod = 1.0
    for t = 1 to 10
        float w = t / (i_dcf_stage1_yrs + 1.0)
        prod *= 1 + (t <= i_dcf_stage1_yrs ? final_growth_rate * (1 - w) + g_t * w : g_t)
    our_path_g := math.pow(prod, 0.1) - 1
// ==============================================================
// === STREET CONSENSUS: BEAR / BASE / BULL + CONFIDENCE =========
// ==============================================================
// Snapshot data (same value on every bar). Display only: the loops below
// (reverse DCF, percentile rank, error) run on the last bar only.
f_clamp01(float x) =>
    na(x) ? na : math.max(math.min(x, 1.0), 0.0)
// Percentile rank of x inside a ratio history (0..1).
f_pct_rank(array<float> a, float x) =>
    int n = array.size(a)
    float r = na
    if n >= 4 and not na(x)
        int below = 0
        for v in a
            below += v < x ? 1 : 0
        r := below / float(n)
    r
f_st_growth(float pv) =>
    barstate.islast and pv > 0 ? f_calculate_reverse_dcf(pv, dcf_input_fcf_total_rev, CL, wacc_base, final_terminal_growth, 10) : na
f_st_pe(float t) =>
    not na(t) and eps_est_ttm > 0 ? t / eps_est_ttm : na
// ==============================================================
// ⚙️ QUANTITATIVE QUALITY & MANAGEMENT RATIOS
// ==============================================================
float safe_shares_prev = not na(_sh_prev) ? _sh_prev : calc_shares
float safe_debt_prev = not na(total_debt_1y_ago) ? total_debt_1y_ago : nz(calc_debt, 0)
float gpa_ratio = not na(calc_assets) and calc_assets > 0 ? nz(calc_gp, 0) / calc_assets : na
float roic_wacc_spread = not na(roic_adj) and not na(final_discount_rate) ? roic_adj - final_discount_rate : na
float sloan_ratio = not na(calc_assets) and calc_assets > 0 ? (nz(calc_ni, 0) - nz(calc_ocf, 0)) / calc_assets : na
float buyback_yield = safe_shares_prev > 0 ? (safe_shares_prev - calc_shares) / safe_shares_prev : 0.0
float debt_paydown_yield = not na(current_mc) and current_mc > 0 ? (safe_debt_prev - nz(calc_debt, 0)) / current_mc : 0.0
float shareholder_yield = nz(div_yield, 0.0) + math.max(buyback_yield, 0.0) + math.max(debt_paydown_yield, 0.0)
// ==========================================
// TABLE DISPLAY
// ==========================================
// [FIX FPT-3] Auto-split anchored to the first bar with USABLE data.
var int bt_first_data_bar = na
if na(bt_first_data_bar) and has_any_real_fundamental and not na(finalFairValue)
    bt_first_data_bar := bar_index
color color_bg = i_theme == 'Dark' ? color.new(#1e222d, 0) : color.new(#f0f3fa, 0)
color color_text = i_theme == 'Dark' ? color.white : color.black
color color_header = i_theme == 'Dark' ? color.new(color.gray, 50) : color.new(color.gray, 80)
color color_value = color.new(color.orange, 20)
color color_over = color.new(color.red, 40)
color color_under = color.new(color.green, 40)
var table T = table.new(position.top_right, 4, 80, border_width = 1)
// 88,601 | 123 | 4.56
f_px(float v) =>
    na(v) ? '-' : math.abs(v) >= 1000 ? str.tostring(math.round(v), '#,###') : math.abs(v) >= 100 ? str.tostring(math.round(v)) : str.tostring(v, '#.##')
f_scen_txt(float v) =>
    na(v) or v <= 0 ? '-' : f_px(v)
// GREEN price below this case | AMBER within the band | RED price above it.
f_scen_col(float v, float px, bool is_base) =>
    color out = color_bg
    if v > 0
        float dev = px / v - 1
        if math.abs(dev) <= i_scen_fair_band
            out := is_base ? color.new(color.orange, 15) : color.new(color.orange, 40)
        else if dev > 0
            out := is_base ? color.new(color.red, 15) : color_over
        else
            out := is_base ? color.new(color.green, 15) : color_under
    out
// One cell of the main table in the chosen text size.
f_cell(int col, int row, string txt, color tc, color bg, string tt = '') =>
    table.cell(T, col, row, txt, text_color = tc, bgcolor = bg, text_size = i_textSize, tooltip = tt)
// Bear | Base | Bull | vs Price, in one call.
f_model_row(int row, string label, float lo, float base, float hi, string tt) =>
    float v = base > 0 ? (close / base - 1) * 100 : na
    f_cell(0, row, label, color_text, color_bg, tt + (na(v) ? '' : '\n\nPrice vs Base: ' + (v > 0 ? '+' : '') + str.tostring(math.round(v)) + '%'))
    f_cell(1, row, f_scen_txt(lo), color_text, f_scen_col(lo, close, false))
    f_cell(2, row, na(base) ? 'N/A' : f_px(base), color.white, f_scen_col(base, close, true))
    f_cell(3, row, f_scen_txt(hi), color_text, f_scen_col(hi, close, false))
f_mult_tt(float avgr, float cur, float plo, float phi) =>
    'Avg ratio (base): ' + str.tostring(avgr, '#.##') + 'x\nCurrent: ' + (na(cur) ? 'N/A' : str.tostring(cur, '#.##') + 'x') +
         '\n\nBear multiple: ' + (na(plo) ? 'n/a' : str.tostring(plo, '#.##') + 'x') +
         '\nBull multiple: ' + (na(phi) ? 'n/a' : str.tostring(phi, '#.##') + 'x') +
         "\n\nBear/Bull are percentiles of this ticker's own stored ratio history applied to the same per-share base. Blank = too few observations.\nP/E and EV/EBITDA also blend in next year's driver, discounted one year at CoE less the dividend yield.\n[xx%] = weight in the live blend."
f_gtxt(float g) => na(g) ? '-' : str.tostring(g * 100, '#.#') + '%'
f_petxt(float pe) => na(pe) ? '-' : str.tostring(pe, '#.#') + 'x'
f_ctxt(float c) => na(c) ? '-' : str.tostring(c, '#')
f_ccol(float c) => na(c) ? color_bg : c >= 60 ? color_under : c >= 40 ? color.new(color.orange, 40) : color_over
f_stxt(float c) => na(c) ? '-' : str.tostring(c, '#.00')
// ==========================================
// TABLE: SUMMARY CARD + ONE DETAIL SECTION
// ==========================================
// The summary (fair value + health) is always drawn; 'Table detail' adds one
// section below it. Street and health numbers are computed once on the last
// bar into the two objects below, and both the summary and the detail rows
// read them.
type StreetView
    bool has = false
    float n = 0.0
    float lo_t = na
    float md_t = na
    float hi_t = na
    float lo = na
    float md = na
    float hi = na
    float g_lo = na
    float g_md = na
    float g_hi = na
    float our_g = na
    float pe_lo = na
    float pe_md = na
    float pe_hi = na
    float rank_md = na
    float rank_hi = na
    float overlap = na
    float our_conf = na
    float st_conf = na
    float gap = na
    float cw_fv = na
    float rc_buy = 0.0
    float rc_hold = 0.0
    float rc_sell = 0.0
    float rc_score = na
    float age_d = na
    string verdict = 'No coverage'
    string conf_tt = ''
    string verdict_tt = ''
    array<float> co
    array<float> cs
    array<string> ctt
type HealthView
    float nd = na
    string nd_txt = 'N/A'
    color nd_col
    string pio_txt = 'N/A'
    color pio_col
    bool zm_on = false
    string zm_txt = 'N/A'
    color zm_col
    string zm_tt = ''
    string inv_txt = 'Efficient'
    color inv_col
    string inv_tt = ''
    string rkv_txt = 'Neutral'
    color rkv_col
    string rkv_tt = ''
    string wacc_flag = 'Normal'
    string wacc_tt = ''
    int q_pass = 0
    int q_tot = 0
    string q_tt = ''
    int n_flags = 0
    bool severe = false
    string flag1 = ''
    string flags_tt = ''
// Section header: four grey cells, tooltip on the first.
f_hdr(int row, string a, string b, string c, string d, string tt) =>
    f_cell(0, row, a, color_text, color_header, tt)
    f_cell(1, row, b, color_text, color_header)
    f_cell(2, row, c, color_text, color_header)
    f_cell(3, row, d, color_text, color_header)
// Label + three cells; tooltips on the label and on the status cell. A colour
// left na falls back to the theme text (c) or background (b).
f_row4(int row, string lbl, string ltt, string v1, string v2, string v3, color c1 = na, color b1 = na, color c2 = na, color b2 = na, color c3 = na, color b3 = na, string stt = '') =>
    f_cell(0, row, lbl, color_text, color_bg, ltt)
    f_cell(1, row, v1, na(c1) ? color_text : c1, na(b1) ? color_bg : b1)
    f_cell(2, row, v2, na(c2) ? color_text : c2, na(b2) ? color_bg : b2)
    f_cell(3, row, v3, na(c3) ? color_text : c3, na(b3) ? color_bg : b3, stt)
// White text on a status colour, the theme text colour on the plain background.
f_on(float c) =>
    na(c) ? color_text : color.white
// The quality filters the framework switches on: [on, name, value, target, pass].
f_qf() =>
    [array.from(show_gpa, show_roic_wacc, show_sloan, show_shareholder), array.from('Gross Profit / Assets (GPA)', 'ROIC vs WACC Spread', 'Sloan Accrual Ratio', 'True Shareholder Yield'), array.from(f_gtxt(gpa_ratio), (roic_wacc_spread > 0 ? '+' : '') + f_gtxt(roic_wacc_spread), f_gtxt(sloan_ratio), f_gtxt(shareholder_yield)), array.from('> 33%', '> +5%', '< 0%', '> 5%'), array.from(gpa_ratio > 0.33, roic_wacc_spread > 0.05, sloan_ratio < 0, shareholder_yield > 0.05)]
// Sloan (index 2) is an accruals flag, the rest pass/fail filters.
f_qword(int j, bool p) =>
    p ? (j == 2 ? 'SAFE' : 'PASS') : (j == 2 ? 'HIGH ACCRUALS' : 'FAIL')
// ---------- last-bar calculations ----------
f_street_calc() =>
    float md_t = nz(syminfo.target_price_median, syminfo.target_price_average)
    float st_n = nz(syminfo.target_price_estimates, 0)
    bool has = md_t > 0
    float lo_t = has ? nz(syminfo.target_price_low, md_t) : na
    float hi_t = has ? nz(syminfo.target_price_high, md_t) : na
    // 12-month targets -> today: discount at CoE less the dividend carry (fwd_disc).
    float st_lo = has ? lo_t / fwd_disc : na
    float st_md = has ? md_t / fwd_disc : na
    float st_hi = has ? hi_t / fwd_disc : na
    // Range overlap (ours Bear-Bull vs street Bear-Bull), 0..1.
    float our_lo_r = nz(compositeLo, finalFairValue)
    float our_hi_r = nz(compositeHi, finalFairValue)
    float rng_union = has and not na(finalFairValue) ? math.max(our_hi_r, st_hi) - math.min(our_lo_r, st_lo) : na
    float overlap = na(rng_union) ? na : rng_union <= 0 ? 1.0 : math.max(math.min(our_hi_r, st_hi) - math.max(our_lo_r, st_lo), 0.0) / rng_union
    // --- OUR confidence ---
    int our_n_models = omni_active ? omni_n : 0
    bool our_track = omni_active ? omni_w_sum > 0 : not blend_eq
    if not omni_active
        for m in MD
            our_n_models += m.fv > 0 and m.w > 0 ? 1 : 0
    float oc_agree = finalFairValue > 0 ? f_clamp01(1 - (nz(fv_stddev, finalFairValue * 0.15) / finalFairValue) / 0.5) : na
    float oc_depth = f_clamp01(our_n_models / 8.0) * (our_track ? 1.0 : 0.5)
    [our_w, our_err] = f_model_weight(hist_final, hist_px, 4, i_w_horizon) // RMS log error
    float oc_rel = na(our_err) ? 0.3 : math.exp(-our_err / 0.3)
    float oc_tier = (f_tier_q(t_eps) + f_tier_q(t_rev) + f_tier_q(t_ocf) + f_tier_q(t_equity) + f_tier_q(t_ebit)) / 5.0
    float oc_flags = (is_rkv_value_trap ? 0.2 : 0.0) + (i_useBeneishCheck and is_manipulator ? 0.2 : 0.0) + (altman_z < z_safe_cut ? 0.2 : 0.0) + (data_suspect ? 0.2 : 0.0)
    float oc_qual = f_clamp01(oc_tier - oc_flags)
    float our_conf = na(oc_agree) ? na : 100 * (0.35 * oc_agree + 0.20 * oc_depth + 0.25 * oc_rel + 0.20 * oc_qual)
    // --- STREET confidence ---
    float sc_agree = has ? f_clamp01(1 - ((hi_t - lo_t) / md_t) / 0.8) : na
    float sc_depth = has ? f_clamp01(math.sqrt(math.max(st_n, 1)) / math.sqrt(10)) : na
    float age_d = has and not na(syminfo.target_price_date) ? (timenow - syminfo.target_price_date) / 86400000.0 : na
    float sc_fresh = na(age_d) ? (has ? 0.5 : na) : age_d <= 30 ? 1.0 : math.max(1.0 - (age_d - 30) / 150 * 0.8, 0.2)
    float rc_buy = nz(syminfo.recommendations_buy, 0) + nz(syminfo.recommendations_buy_strong, 0)
    float rc_hold = nz(syminfo.recommendations_hold, 0)
    float rc_sell = nz(syminfo.recommendations_sell, 0) + nz(syminfo.recommendations_sell_strong, 0)
    float rc_tot = rc_buy + rc_hold + rc_sell
    float sc_conv = has ? (rc_tot > 0 ? math.max(rc_buy, rc_hold, rc_sell) / rc_tot : 0.5) : na
    float st_conf = has ? 100 * (0.35 * sc_agree + 0.20 * sc_depth + 0.25 * sc_fresh + 0.20 * sc_conv) : na
    // 1 = strong buy ... 5 = strong sell
    float rc_score = rc_tot > 0 ? (1 * nz(syminfo.recommendations_buy_strong, 0) + 2 * nz(syminfo.recommendations_buy, 0) + 3 * rc_hold + 4 * nz(syminfo.recommendations_sell, 0) + 5 * nz(syminfo.recommendations_sell_strong, 0)) / rc_tot : na
    // --- Verdict + confidence-weighted value ---
    float gap = has and not na(finalFairValue) ? finalFairValue / st_md - 1 : na
    string verdict = has ? 'No fair value' : 'No coverage'
    if has and not na(our_conf)
        bool agree_v = math.abs(gap) <= i_conf_gap
        if our_conf >= 60 and st_conf >= 60
            verdict := agree_v ? 'High conviction' : 'Real disagreement'
        else if our_conf < 40 and st_conf < 40
            verdict := 'Low information'
        else if our_conf - st_conf >= 20
            verdict := agree_v ? 'Agree (ours stronger)' : 'Trust ours'
        else if st_conf - our_conf >= 20
            verdict := agree_v ? 'Agree (street stronger)' : 'Trust street'
        else
            verdict := agree_v ? 'Agree' : 'Mixed'
    float cw_fv = has and not na(our_conf) and our_conf + st_conf > 0 ? (finalFairValue * our_conf + st_md * st_conf) / (our_conf + st_conf) : na
    // Component breakdown: summary tooltip + Street detail rows.
    array<string> cl = array.from('Agreement', 'Depth', 'Reliability / Freshness', 'Quality / Conviction')
    array<float> co = array.from(oc_agree, oc_depth, oc_rel, oc_qual)
    array<float> cs = array.from(sc_agree, sc_depth, sc_fresh, sc_conv)
    array<string> ctt = array.from('Ours: model dispersion (stdev / FV). Street: (high - low) / median.', 'Ours: ' + str.tostring(our_n_models) + ' models' + (our_track ? '' : ', no track record (x0.5)') + '. Street: sqrt(analysts) / sqrt(10).', 'Ours: exp(-log error / 0.3). Street: target age ' + (na(age_d) ? 'unknown' : str.tostring(age_d, '#') + ' days') + '.', 'Ours: data-quality tier less 0.2 per red flag (value trap, M-score, distress, data sanity). Street: share of ratings in the largest bucket.')
    string conf_tt = 'Score 0-100 = Agreement 35% + Depth 20% + Reliability 25% + Quality 20%.\n\nComponent: ours / street'
    for j = 0 to 3
        conf_tt += '\n' + array.get(cl, j) + ':  ' + f_stxt(array.get(co, j)) + ' / ' + f_stxt(array.get(cs, j))
    conf_tt += '\n'
    for j = 0 to 3
        conf_tt += '\n' + array.get(cl, j) + ' - ' + array.get(ctt, j)
    conf_tt += '\n\nOur reliability is earned: composite log error vs price ' + str.tostring(i_w_horizon) + 'Q later' + (na(our_err) ? ' (not enough history, set to 0.3)' : ' = ' + str.tostring(our_err, '#.##')) + '. The street has no history, so FRESHNESS of the targets stands in.'
    string verdict_tt = 'Gap ours vs street PV: ' + (na(gap) ? 'N/A' : (gap > 0 ? '+' : '') + str.tostring(gap * 100, '#') + '%') + ' (agree band +/-' + str.tostring(i_conf_gap * 100, '#') + '%).' + (na(rc_score) ? '' : '\nRating score: ' + str.tostring(rc_score, '#.0') + ' (1 strong buy - 5 strong sell), ' + str.tostring(rc_tot, '#') + ' ratings.')
    float pe_md = f_st_pe(md_t)
    float pe_hi = f_st_pe(hi_t)
    StreetView.new(has = has, n = st_n, lo_t = lo_t, md_t = md_t, hi_t = hi_t, lo = st_lo, md = st_md, hi = st_hi, g_lo = f_st_growth(st_lo), g_md = f_st_growth(st_md), g_hi = f_st_growth(st_hi), our_g = f_st_growth(finalFairValue), pe_lo = f_st_pe(lo_t), pe_md = pe_md, pe_hi = pe_hi, rank_md = f_pct_rank(M_PE.hist, pe_md), rank_hi = f_pct_rank(M_PE.hist, pe_hi), overlap = overlap, our_conf = our_conf, st_conf = st_conf, gap = gap, cw_fv = cw_fv, rc_buy = rc_buy, rc_hold = rc_hold, rc_sell = rc_sell, rc_score = rc_score, age_d = age_d, verdict = verdict, conf_tt = conf_tt, verdict_tt = verdict_tt, co = co, cs = cs, ctt = ctt)
f_health_calc() =>
    // Leverage
    float nd = ebitda_ttm > 0 ? nz(net_debt_robust, 0) / ebitda_ttm : na
    string nd_txt = 'N/A'
    color nd_col = color_bg
    if not na(nd)
        nd_txt := nd < 0 ? 'Net Cash' : nd <= 1.5 ? 'Conservative' : nd <= 3.0 ? 'Moderate' : nd <= 4.5 ? 'Elevated' : 'High'
        nd_col := nd <= 1.5 ? color_under : nd <= 3.0 ? color_bg : nd <= 4.5 ? color.new(color.orange, 40) : color_over
    // Piotroski
    string pio_txt = na(piotroski_f_score) ? 'N/A' : piotroski_f_score >= 7 ? 'Strong' : piotroski_f_score <= 3 ? 'Weak' : 'Neutral'
    color pio_col = na(piotroski_f_score) ? color_bg : piotroski_f_score >= 7 ? color_under : piotroski_f_score <= 3 ? color_over : color_bg
    // Z + M quadrant
    bool zm_on = i_useBeneishCheck and not na(altman_z) and not na(m_score)
    string zm_txt = 'N/A'
    color zm_col = color_bg
    string zm_tt = ''
    if zm_on
        bool z_ok = altman_z >= z_safe_cut
        if z_ok and not is_manipulator
            zm_txt := altman_z >= z_gold_cut ? 'Golden Standard' : 'Safe & Honest'
            zm_col := color_under
            zm_tt := 'Quadrant 1: Safe & Honest\nSafe from bankruptcy & honest accounting.'
        else if not is_manipulator
            zm_txt := 'Failing / Honest'
            zm_col := color.new(color.orange, 40)
            zm_tt := 'Quadrant 4: Failing but Honest\nHigh distress risk, but financials are truthful. (Value Trap or Turnaround)'
        else if z_ok
            zm_txt := 'Fake Safe (Enron)'
            zm_col := color_over
            zm_tt := 'Quadrant 3: Fake Safe\nLooks financially healthy, but earnings are likely manipulated. DO NOT TRUST.'
        else
            zm_txt := 'Desperation Spiral'
            zm_col := color.new(color.red, 0)
            zm_tt := 'Quadrant 2: Desperation Spiral\nHigh distress AND accounting manipulation. Extreme Danger.'
        zm_tt += (z_is_em ? "\n\nScore is Z''-EM: safe > 5.85, distress < 4.35." : '\n\nScore is Altman Z: safe > 3.0, distress < 1.8.') + '\nM-Score cutoff: -1.78.'
    // Capital allocation
    string inv_txt = investment_dummy ? 'Empire Builder' : is_deteriorating ? 'Deteriorating' : 'Efficient'
    color inv_col = investment_dummy or is_deteriorating ? color_over : color_under
    string inv_tt = 'Asset growth YoY ' + f_gtxt(asset_growth) + ' | EBITDA growth YoY ' + f_gtxt(ebitda_growth) + '.\n\n' + (investment_dummy ? 'DANGER: asset growth strictly exceeds EBITDA growth.' : is_deteriorating ? 'Assets are shrinking and EBITDA is shrinking faster.' : 'Core cash generation (EBITDA) is keeping pace with or exceeding asset expansion.')
    // Rhodes-Kropf
    string rkv_txt = is_rkv_value_trap ? 'Value Trap' : is_rkv_deep_value ? 'True Deep Value' : 'Neutral'
    color rkv_col = is_rkv_value_trap ? color_over : is_rkv_deep_value ? color_under : color_bg
    string rkv_tt = 'Rhodes-Kropf M/B decomposition:\n\nGrowth options (V/B): ' + str.tostring(rkv_growth_vb, '#.##') + 'x -- fair value vs book. Below 1.0x the business is worth less than its balance sheet.\n\nMispricing (P/V): ' + str.tostring(rkv_mispricing_mv, '#.##') + 'x -- price vs fair value.'
    // Discount rate (+ the macro assumptions behind terminal growth)
    string wacc_flag = final_discount_rate < 0.05 ? 'Too Low' : final_discount_rate > 0.20 ? 'Extreme' : 'Normal'
    string wacc_tt = 'CAPM Beta: ' + str.tostring(beta_mkt, '#.##') + '\nDownside Beta: ' + (na(downside_beta) ? 'N/A' : str.tostring(downside_beta, '#.##')) + '\nRisk-free base: ' + i_rf_base + ' = ' + str.tostring(base_rf_for_calc * 100, '#.##') + '%\nERP: ' + str.tostring(calc_erp * 100, '#.#') + '%\nCRP: ' + str.tostring(calc_crp * 100, '#.#') + '% (local-US spread: ' + str.tostring(auto_crp_raw * 100, '#.#') + '%)\nCost of Debt (synthetic): ' + str.tostring(cost_of_debt_synthetic * 100, '#.#') + '%\nEffective tax: ' + str.tostring(effective_tax * 100, '#.#') + '%\n\nMacro (manual): inflation ' + str.tostring(lr_infl * 100, '#.##') + '%, real GDP ' + str.tostring(lr_rgdp * 100, '#.##') + '% -> terminal growth ' + str.tostring(final_terminal_growth * 100, '#.##') + '%.'
    // Quality: Piotroski + the quant filters the framework switches on
    int q_pass = 0
    int q_tot = 0
    string q_tt = 'Piotroski F-score: ' + (na(piotroski_f_score) ? 'N/A' : str.tostring(piotroski_f_score, '#') + ' / 9 (' + pio_txt + ')') + '\n'
    [qon, qnm, qvl, qtg, qps] = f_qf()
    for j = 0 to 3
        if array.get(qon, j)
            bool p = array.get(qps, j)
            q_tot += 1
            q_pass += p ? 1 : 0
            q_tt += '\n' + array.get(qnm, j) + ' ' + array.get(qvl, j) + ' (' + array.get(qtg, j) + '): ' + f_qword(j, p)
    // Red flags: one list, short names for the cell, full text for the tooltip.
    array<string> fl = array.new_string(0)
    string flags_tt = ''
    bool severe = false
    if nd > 4.5
        array.push(fl, 'Leverage')
        flags_tt += '\nLeverage: net debt ' + str.tostring(nd, '#.#') + 'x EBITDA (> 4.5x).'
    if zm_on and zm_txt != 'Golden Standard' and zm_txt != 'Safe & Honest'
        array.push(fl, 'Z+M')
        flags_tt += '\nZ+M matrix: ' + zm_txt + '.'
        severe := severe or is_manipulator
    else if not zm_on and i_useBeneishCheck and is_manipulator
        array.push(fl, 'M-score')
        flags_tt += '\nBeneish M-score ' + str.tostring(m_score, '#.##') + ' > -1.78: earnings manipulation risk.'
        severe := true
    if piotroski_f_score <= 3
        array.push(fl, 'Piotroski')
        flags_tt += '\nPiotroski F-score ' + str.tostring(piotroski_f_score, '#') + ' (3 or less).'
    if investment_dummy or is_deteriorating
        array.push(fl, 'Capital alloc')
        flags_tt += '\nCapital allocation: ' + inv_txt + '.'
    if i_use_rkv and is_rkv_value_trap
        array.push(fl, 'Value trap')
        flags_tt += '\nRhodes-Kropf value trap (V/B ' + str.tostring(rkv_growth_vb, '#.##') + 'x).'
    if wacc_flag != 'Normal'
        array.push(fl, 'WACC')
        flags_tt += '\nDiscount rate ' + str.tostring(final_discount_rate * 100, '#.#') + '% (' + wacc_flag + ').'
    if implied_exit_multiple > 30
        array.push(fl, 'Exit multiple')
        flags_tt += '\nImplied exit EV/NOPAT ' + str.tostring(implied_exit_multiple, '#.#') + 'x (> 30x): the DCF leans on a rich terminal value.'
    if show_sloan and sloan_ratio >= 0
        array.push(fl, 'Accruals')
        flags_tt += '\nSloan accruals ' + f_gtxt(sloan_ratio) + ': earnings running ahead of cash.'
    int n_flags = array.size(fl)
    flags_tt := n_flags == 0 ? 'Nothing tripped. Checks: leverage, Z+M, Piotroski, capital allocation, RKV value trap, discount rate, exit multiple, accruals.' : str.tostring(n_flags) + ' flag(s):' + flags_tt
    HealthView.new(nd = nd, nd_txt = nd_txt, nd_col = nd_col, pio_txt = pio_txt, pio_col = pio_col, zm_on = zm_on, zm_txt = zm_txt, zm_col = zm_col, zm_tt = zm_tt, inv_txt = inv_txt, inv_col = inv_col, inv_tt = inv_tt, rkv_txt = rkv_txt, rkv_col = rkv_col, rkv_tt = rkv_tt, wacc_flag = wacc_flag, wacc_tt = wacc_tt, q_pass = q_pass, q_tot = q_tot, q_tt = q_tt, n_flags = n_flags, severe = severe, flag1 = n_flags > 0 ? array.get(fl, 0) : '', flags_tt = flags_tt)
// ---------- summary card ----------
f_tbl_head() =>
    table.set_position(T, i_tablePos == 'top_right' ? position.top_right : i_tablePos == 'middle_right' ? position.middle_right : position.bottom_right)
    table.clear(T, 0, 0, 3, 79)
    color hc = color.new(color.purple, 20)
    f_cell(0, 0, active_model_desc, color.white, hc, 'Valuation framework in use (Industry-Specific Valuation). Values are live on the last bar.\n\nScenario cells: green = price below that case, amber = within +/-' + str.tostring(i_scen_fair_band * 100, '#') + '%, red = price above it.\n\nMore rows: Display Options > Table detail.')
    f_cell(1, 0, 'Price', color.white, hc)
    f_cell(2, 0, f_px(close), color.white, hc)
    f_cell(3, 0, 'REAL-TIME', color.white, hc)
    1
// Members of the live blend (base value, weight) for the "Ours" tooltip.
f_members_tt() =>
    string t = ''
    for m in MD
        if omni_active ? m.om : m.w > 0
            float sh = omni_active ? m.om_w : m.w
            t += '\n' + m.name + ': ' + f_px(m.fv) + '  (' + str.tostring(sh * 100, '#') + '%)'
    t
f_sum_val(StreetView s, int r0) =>
    int row_idx = r0
    f_hdr(row_idx, 'Fair Value', 'Bear', 'Base', 'Bull', '')
    row_idx += 1
    // Ours
    string lbl = omni_active ? 'Ours: Omnibus ' + str.tostring(omni_n) + '/' + str.tostring(MD.size()) + (omni_dupe ? ' (!)' : '') : is_omnibus ? 'Ours (Standard)' : 'Ours (composite)'
    string tt = omni_active ? 'Omnibus blend. ' + (omni_w_sum > 0 ? 'Weight = inverse prediction error against price ' + str.tostring(i_w_horizon) + ' quarters later, x data-quality tier.' : 'No member has 4+ paired quarters yet, so the weights are equal x data-quality tier.') : (is_omnibus ? 'Omnibus unavailable (no member survived gating), so this is the Standard composite.\n\n' : '') + (blend_eq ? 'No model has a predictive track record yet, so the blend is EQUAL-WEIGHTED (x data-quality tier).' : 'Weights = inverse error of each model fair value against the price ' + str.tostring(i_w_horizon) + ' quarters later, x data-quality tier.')
    if omni_dupe
        tt += '\n\n' + omni_dupe_tt
    tt += '\nBear/Bull apply the same weights to each model own bear and bull case.\n\nMembers (base value, weight):' + f_members_tt() + '\n\nEvery model: Table detail > Models.'
    f_model_row(row_idx, lbl, compositeLo, finalFairValue, compositeHi, tt)
    row_idx += 1
    // Price vs ours
    color valuation_color = valuation_status == 'Overvalued' or valuation_status == 'Very Overvalued' ? color_over : valuation_status == 'Undervalued' or valuation_status == 'Very Undervalued' ? color_under : color_bg
    float variance_pct = na(finalFairValue) ? na : (close / finalFairValue - 1) * 100
    float band_w = not na(compositeLo) and not na(compositeHi) and finalFairValue > 0 ? (compositeHi - compositeLo) / finalFairValue * 100 : na
    f_row4(row_idx, 'Price vs FV', 'Price against OUR base value above. Width = (Bull - Bear) / Base: under 30% tight, over 60% wide.', na(variance_pct) ? 'N/A' : (variance_pct > 0 ? '+' : '') + str.tostring(math.round(variance_pct)) + '%', valuation_status, na(band_w) ? 'N/A' : 'Width ' + str.tostring(math.round(band_w)) + '%', c1 = na(variance_pct) ? color_text : variance_pct > 0 ? color.red : color.green, b2 = valuation_color, c3 = na(band_w) ? color_text : band_w < 30 ? color.green : band_w < 60 ? color.orange : color.red)
    row_idx += 1
    if i_show_street
        if s.has
            f_model_row(row_idx, 'Street PV (' + str.tostring(s.n, '#') + ')', s.lo, s.md, s.hi, str.tostring(s.n, '#') + ' analysts. 12-month targets (' + f_px(s.lo_t) + ' / ' + f_px(s.md_t) + ' / ' + f_px(s.hi_t) + ') discounted to today at CoE ' + str.tostring(cost_of_equity * 100, '#.#') + '% less dividend yield, so they compare with our value. Display only: never in the blend, the plot or the backtest.\n\nRange overlap with ours: ' + (na(s.overlap) ? 'N/A' : str.tostring(s.overlap * 100, '#') + '%') + '.')
            row_idx += 1
            if not na(s.cw_fv)
                float cw_dev = (close / s.cw_fv - 1) * 100
                f_row4(row_idx, 'Conf-weighted FV', '(Ours x our score + Street PV x street score) / sum of scores. Display only.', '', f_px(s.cw_fv), 'Price ' + (cw_dev > 0 ? '+' : '') + str.tostring(cw_dev, '#') + '%', c2 = color.white, b2 = f_scen_col(s.cw_fv, close, true), c3 = cw_dev > 0 ? color.red : color.green)
                row_idx += 1
        else
            f_row4(row_idx, 'Street PV', 'TradingView has no analyst targets for this symbol.', 'No coverage', '', '')
            row_idx += 1
        bool v_plain = s.verdict == 'No coverage' or s.verdict == 'No fair value'
        color vcol = v_plain ? color_bg : s.verdict == 'High conviction' or str.startswith(s.verdict, 'Agree') ? color_under : s.verdict == 'Real disagreement' or s.verdict == 'Low information' ? color_over : color.new(color.orange, 40)
        f_row4(row_idx, 'Confidence', s.conf_tt, 'Ours ' + f_ctxt(s.our_conf), 'Street ' + f_ctxt(s.st_conf), s.verdict, f_on(s.our_conf), f_ccol(s.our_conf), f_on(s.st_conf), f_ccol(s.st_conf), v_plain ? color_text : color.white, vcol, s.verdict_tt)
        row_idx += 1
    row_idx
f_sum_health(HealthView h, int r0) =>
    int row_idx = r0
    f_hdr(row_idx, 'Health', 'Value', 'Detail', 'Status', 'Hover a row for its breakdown. Every row: Table detail > Health.')
    row_idx += 1
    // Balance sheet: leverage value + status; Z / M in the middle, shaded by quadrant.
    string zm_cell = h.zm_on ? 'Z ' + str.tostring(altman_z, '#.#') + ' | M ' + str.tostring(m_score, '#.#') : na(altman_z) ? 'Z -' : 'Z ' + str.tostring(altman_z, '#.#')
    string bs_tt = 'Net debt / EBITDA: ' + (na(h.nd) ? 'N/A' : str.tostring(h.nd, '#.#') + 'x') + ' (' + h.nd_txt + ').\n<0 net cash | <1.5 conservative | 1.5-3 moderate | 3-4.5 elevated | >4.5 high.' + (h.zm_on ? '\n\nZ+M matrix: ' + h.zm_txt + '\n' + h.zm_tt : '')
    f_row4(row_idx, 'Balance sheet', bs_tt, na(h.nd) ? 'N/A' : str.tostring(h.nd, '#.#') + 'x', zm_cell, h.nd_txt, c1 = h.nd > 3.0 ? color.red : color_text, c2 = h.zm_on ? color.white : color_text, b2 = h.zm_on ? h.zm_col : color_bg, b3 = h.nd_col, stt = bs_tt)
    row_idx += 1
    // Quality: Piotroski + pass count of the quant filters
    color q_bg = h.q_tot == 0 ? color_bg : h.q_pass * 3 >= h.q_tot * 2 ? color_under : h.q_pass * 3 >= h.q_tot ? color.new(color.orange, 40) : color_over
    f_row4(row_idx, 'Quality', h.q_tt, 'F-score ' + (na(piotroski_f_score) ? '-' : str.tostring(piotroski_f_score, '#')), h.q_tot > 0 ? 'Filters ' + str.tostring(h.q_pass) + '/' + str.tostring(h.q_tot) : 'Filters -', h.pio_txt, c2 = h.q_tot > 0 ? color.white : color_text, b2 = q_bg, b3 = h.pio_col, stt = h.q_tt)
    row_idx += 1
    // Discount rate
    f_row4(row_idx, 'Discount rate', h.wacc_tt, 'WACC ' + str.tostring(final_discount_rate * 100, '#.#') + '%', 'CoE ' + str.tostring(cost_of_equity * 100, '#.#') + '% | g ' + str.tostring(final_terminal_growth * 100, '#.#') + '%', h.wacc_flag, b1 = color_value, c3 = color.white, b3 = h.wacc_flag == 'Normal' ? color_under : color_over, stt = h.wacc_tt)
    row_idx += 1
    // Growth the price implies (reverse DCF) vs the 10-year growth our DCF assumes
    bool g_na = na(implied_market_growth) or na(our_path_g)
    bool demanding = not g_na and implied_market_growth > our_path_g
    string g_tt = 'Reverse DCF: the 10-year growth the current price implies, vs the 10-year average our DCF assumes (stage-1 growth ' + f_gtxt(final_growth_rate) + ' fading to terminal ' + f_gtxt(final_terminal_growth) + ').\n\nForward growth leg (' + fwd_growth_src + '): ' + f_gtxt(fwd_growth_leg) + '.\nImplied exit EV/NOPAT in year ' + str.tostring(i_dcf_stage1_yrs) + ': ' + f_petxt(implied_exit_multiple) + '.'
    f_row4(row_idx, 'Growth priced in', g_tt, f_gtxt(implied_market_growth), 'Ours ' + f_gtxt(our_path_g), g_na ? 'N/A' : demanding ? 'Demanding' : 'Achievable', b1 = color_value, c3 = g_na ? color_text : color.white, b3 = g_na ? color_bg : demanding ? color_over : color_under, stt = g_tt)
    row_idx += 1
    // Red flags
    color fl_bg = h.n_flags == 0 ? color_under : h.severe ? color.new(color.red, 0) : color.new(color.orange, 40)
    f_row4(row_idx, 'Red flags', h.flags_tt, str.tostring(h.n_flags), h.n_flags == 0 ? '-' : h.flag1 + (h.n_flags > 1 ? ' +' + str.tostring(h.n_flags - 1) : ''), h.n_flags == 0 ? 'Clean' : h.severe ? 'Danger' : 'Review', c3 = color.white, b3 = fl_bg, stt = h.flags_tt)
    row_idx += 1
    row_idx
// 5.2T | 41.2B | 88.6M, else as f_px: totals in a tooltip.
f_big(float v) =>
    float a = math.abs(v)
    na(v) ? '-' : a >= 1e12 ? str.tostring(v / 1e12, '#.##') + 'T' : a >= 1e9 ? str.tostring(v / 1e9, '#.##') + 'B' : a >= 1e6 ? str.tostring(v / 1e6, '#.##') + 'M' : f_px(v)
// 'net debt 8.4B, minority interest 0.6B, preferred 0.2B': the claims counted, with amounts.
f_claims_brk() =>
    string t = ''
    for [k, v] in CL.amt
        t += (t == '' ? '' : ', ') + str.tostring(k) + ' ' + f_big(v)
    t
// The Base result record in one line: from the engine's total through the claim bridge to
// the value shown, and the rate and growths the engine was handed.
f_res_tt(Model m) =>
    Res r = m.res.get(0)
    KIn x = r.x
    bool firm = m.level == Level.firm or m.level == Level.unlev
    string t = '\n\nBase: '
    if na(r.value)
        t += 'N/A, ' + (r.why == '' ? 'inputs missing' : r.why) + '.'
    else if m.ps
        t += f_px(r.value) + ' per share' + (na(r.fwd) ? '' : ', the average of spot ' + f_px(r.spot) + ' and forward ' + f_px(r.fwd)) + '.'
    else
        t += (firm ? 'firm value ' : 'equity value ') + f_big(r.core) + (r.add != 0 ? ' + ' + str.tostring(m.addon) + ' ' + f_big(r.add) : '') + (firm ? ' - ' + f_claims_brk() : '') + ', / ' + f_big(r.sh) + ' shares = ' + f_px(r.spot) + (na(r.fwd) ? '' : '; forward leg ' + f_px(r.fwd) + ', blended ' + f_px(r.value)) + '.'
    bool disc = m.eng == Eng.vdcf or m.eng == Eng.rim or m.eng == Eng.eva or m.eng == Eng.perp or m.eng == Eng.gperp
    t + (disc and not na(r.value) ? ' Rate (' + str.tostring(m.level) + ') ' + f_gtxt(x.rate) + (m.eng == Eng.perp ? '' : ', growth ' + f_gtxt(x.g1) + ' fading to ' + f_gtxt(x.gT)) + '.' : '')
// The rows in a display order given by their codes; rows the list leaves out follow in
// declaration order, so a new model shows without editing the list.
f_order(string codes) =>
    array<Model> out = array.new<Model>()
    for c in str.split(codes, ' ')
        for m in MD
            if m.code == c
                out.push(m)
    for m in MD
        if not str.contains(' ' + codes + ' ', ' ' + m.code + ' ')
            out.push(m)
    out
// ---------- detail sections ----------
f_det_models(int r0) =>
    int row_idx = r0
    f_hdr(row_idx, 'Relative Valuation', 'Bear', 'Base', 'Bull', '[xx%] = weight in the live blend (Standard or Omnibus). * = synthetic base multiple (under 4 quarters of history).')
    row_idx += 1
    for m in MD
        if m.grp == Group.rel and (m.on or m.om) and m.fv > 0
            float cur = m.drv > 0 ? (m.level == Level.firm ? ev_now : close) / m.drv : na
            f_model_row(row_idx, m.name + (m.syn ? ' *' : '') + f_wt_lbl(omni_active ? m.om_w : m.w), m.lo, m.fv, m.hi, (m.syn ? 'SYNTHETIC: fewer than 4 quarters of history, so the base multiple is a default (none stored) or the average of the few quarters stored.\n\n' : '') + (m.s_drv == Sx.eps_b and cape_on ? 'CAPE: 10-year inflation-adjusted EPS, against a history of the same (Shiller) P/E.\n\n' : '') + f_mult_tt(m.avg, cur, m.plo, m.phi) + f_res_tt(m))
            row_idx += 1
    f_hdr(row_idx, 'Intrinsic Models', 'Bear', 'Base', 'Bull', '')
    row_idx += 1
    // Rule of 40, or Rule of 65 once growth x 2 + FCF margin reaches 65.
    float r40_score = not na(rev_growth) and not na(true_fcf_margin_ttm) ? (rev_growth + true_fcf_margin_ttm) * 100 : 0.0
    float rx_score = not na(rev_growth) and not na(true_fcf_margin_ttm) ? ((rev_growth * 2.0) + true_fcf_margin_ttm) * 100 : 0.0
    bool super_stock = rx_score >= 65
    float ddm_yield = close > 0 and not na(div_per_share_ttm) ? div_per_share_ttm / close * 100 : na
    string cl_txt = CL.txt()
    // Absolute models show whenever allocated (even N/A); Acquirer's and the sector
    // models only once they produce a value.
    for m in f_order('RIM R40 GRA ACQ DCF EPV RNPV ECF ADCF UNB APV EVA DDM')
        if m.grp != Group.rel and m.grp != Group.comp and (m.on or m.om) and ((m.grp == Group.abs and m.code != 'ACQ') or not na(m.fv))
            string lbl = m.code == 'R40' ? (super_stock ? '🌟 Rule of 65 (Super Stock)' : 'Rule of 40 Value') : m.code == 'ACQ' ? "Acquirer's Mult (" + str.tostring(i_acquirer_mult) + "x EBIT)" : m.name
            string tt = switch m.code
                'R40' => (super_stock ? 'Rule of 65 Score: ' + str.tostring(rx_score, '#.#') + '%\n(Hyper-Growth Premium Unlocked!)' : 'Rule of 40 Score: ' + (na(rev_growth) ? 'N/A (needs a year-ago revenue)' : str.tostring(r40_score, '#.#') + '%')) + '\n\nASSUMPTION: fixed EV/Sales rule -- 1x + 0.25x per Rule-of-40 point (floor 1.5x); the Rule-of-X multiple (12x + 0.3x per point above 65, never below that base) phases in as Rule-of-X goes from 55 to 65; capped at 25x.'
                'GRA' => 'Needs positive EPS. Growth capped at 15%; the 4.4/Y bond-yield factor is capped at 1.0.'
                'ACQ' => 'Bear/Bull shift the EBIT multiple by +/-' + str.tostring(i_scen_acq_delta) + 'x.'
                'RNPV' => 'ASSUMPTION (not fitted, no trial-outcome data): pipeline = 5x annual R&D, 15% risk-adjusted, added to the DCF firm value. In the Omnibus it replaces the DCF, which it contains.'
                'UNB' => 'NetCo share ' + str.tostring(netco_sh * 100, '#') + '% = net PPE / invested capital (30-90%). NetCo = that share of invested capital (the network) at a RAB multiple; ServeCo = the rest of the unlevered FCF and NOPAT through the DCF at WACC. Less ' + cl_txt + ', once.'
                'DCF' => 'Unlevered FCF (FCF + after-tax interest) and NOPAT at WACC, less ' + cl_txt + '. Over stage 1, FCF moves from the current cash flow to what is left after the reinvestment next-year growth needs, NOPAT x (1 - g / RONIC); RONIC moves from the current ROIC to a terminal ROIC capped at 20% (never below WACC).\n\nBear/Bull move the discount rate, terminal growth AND stage-1 growth.'
                'RIM' => (use_bank_model ? 'Equity model: net income - CoE x book value' : 'Entity model: NOPAT - WACC x invested capital (incl. capitalised R&D)') + ', growing at the stage-1 rate and fading to terminal over ' + str.tostring(i_iv_projection_period) + ' years, plus ' + (use_bank_model ? 'book value.' : 'invested capital, less ' + cl_txt + '.')
                'ECF' => 'FCFE = net income x (1 - g / ROE): the equity a firm must retain to grow comes off, two-stage at the cost of equity. ROE ' + f_gtxt(roe_n) + ' (5-year median). For a bank, debt is raw material, not financing, so net borrowing is not counted as cash to shareholders.'
                'ADCF' => 'FCF (the AFFO proxy) at the cost of equity. FCF is already after capex, so the terminal value takes no second reinvestment charge.'
                'APV' => 'Unlevered FCF through the two-stage DCF at the unlevered cost of capital ' + f_gtxt(unlevered_coe) + ' (the cost of equity less the leverage part of beta), plus the tax shield on debt (debt x tax), less ' + cl_txt + '.'
                'EPV' => 'Normalised NOPAT (EBIT averaged over up to 3 years) / WACC, no growth, less ' + cl_txt + '.'
                'OE' => 'OCF less maintenance capex (growth capex = sales growth x net PPE / sales): after interest, so a no-growth perpetuity at the cost of equity.'
                'EVA' => 'Invested capital (incl. capitalised R&D) + PV(EVA), less ' + cl_txt + '.'
                'DDM' => 'Gordon growth on the trailing dividend.\nDPS: ' + str.tostring(div_per_share_ttm, '#.##') + '\nYield: ' + (na(ddm_yield) ? 'N/A' : str.tostring(ddm_yield, '#.##') + '%') + '\nCost of equity: ' + str.tostring(cost_of_equity * 100, '#.#') + '%\nTerminal growth: ' + str.tostring(final_terminal_growth * 100, '#.#') + '%'
                => ''
            f_model_row(row_idx, lbl + f_wt_lbl(omni_active ? m.om_w : m.w), m.lo, m.fv, m.hi, tt + f_res_tt(m))
            row_idx += 1
    row_idx
f_det_omni(int r0) =>
    int row_idx = r0
    if is_omnibus
        string omni_tt = omni_n == 0 ? 'No member survived gating, so the fair value is the Standard composite, not an Omnibus value.' : (omni_w_sum > 0 ? 'Share of the blend. Weight = inverse prediction error against price ' + str.tostring(i_w_horizon) + ' quarters later, x data-quality tier.\n\n' : 'No member has 4+ paired quarters yet, so the weights are equal x data-quality tier.\n\n')
        if omni_dupe
            omni_tt += omni_dupe_tt + '\n\n'
        for m in MD
            if m.om
                omni_tt += m.name + '  ' + str.tostring(m.om_w * 100, '#.#') + '%\n'
        f_cell(0, row_idx, 'Omnibus Members', color_text, color_header)
        f_cell(1, row_idx, str.tostring(omni_n) + ' / ' + str.tostring(MD.size()), omni_dupe ? color.orange : omni_n >= 3 ? color.green : omni_n > 0 ? color.orange : color.red, color_bg, omni_tt)
        f_cell(2, row_idx, omni_manual ? (i_omni_strict ? 'Manual (strict)' : 'Manual') : 'Auto', color_text, color_bg)
        f_cell(3, row_idx, omni_n == 0 ? 'INACTIVE' : omni_dupe ? 'DOUBLE-COUNT' : omni_w_sum > 0 ? 'Weighted' : 'Equal wt', omni_n == 0 ? color.red : omni_dupe ? color.orange : color_text, color_bg)
        row_idx += 1
    row_idx
f_det_street(StreetView s, int r0) =>
    int row_idx = r0
    f_hdr(row_idx, 'Street detail' + (s.has ? ' (' + str.tostring(s.n, '#') + ' analysts)' : ''), 'Bear', 'Base', 'Bull', 'Analyst targets are 12-month-forward prices; the summary PV row discounts them to today. Display only.')
    row_idx += 1
    if not s.has
        f_row4(row_idx, 'No analyst coverage', 'TradingView has no analyst targets for this symbol.', '', '', '')
        row_idx += 1
    else
        f_model_row(row_idx, 'Target (12M)', s.lo_t, s.md_t, s.hi_t, s.n <= 1 ? '1 analyst: no range.' : 'Low / median / high analyst target.')
        row_idx += 1
        f_row4(row_idx, 'Implied growth', 'Reverse DCF on each street PV. Ours: implied ' + f_gtxt(s.our_g) + ', model explicit growth ' + f_gtxt(final_growth_rate) + '.', f_gtxt(s.g_lo), f_gtxt(s.g_md), f_gtxt(s.g_hi))
        row_idx += 1
        string pe_tt = 'Target / FY consensus EPS. Percentile in the stock own P/E history: Base ' + (na(s.rank_md) ? 'N/A' : str.tostring(s.rank_md * 100, '#') + 'th') + ', Bull ' + (na(s.rank_hi) ? 'N/A' : str.tostring(s.rank_hi * 100, '#') + 'th') + '. Red = above the 90th.'
        f_row4(row_idx, 'Implied fwd P/E', pe_tt, f_petxt(s.pe_lo), f_petxt(s.pe_md), f_petxt(s.pe_hi), c2 = s.rank_md > 0.9 ? color.red : color_text, c3 = s.rank_hi > 0.9 ? color.red : color_text, stt = pe_tt)
        row_idx += 1
        float rc_tot = s.rc_buy + s.rc_hold + s.rc_sell
        string rt_tt = rc_tot > 0 ? 'Rating score ' + str.tostring(s.rc_score, '#.0') + ' (1 strong buy - 5 strong sell), ' + str.tostring(rc_tot, '#') + ' ratings.' : 'No buy / hold / sell ratings on TradingView.'
        f_row4(row_idx, 'Ratings', rt_tt, 'Buy ' + str.tostring(s.rc_buy, '#'), 'Hold ' + str.tostring(s.rc_hold, '#'), 'Sell ' + str.tostring(s.rc_sell, '#'), stt = rt_tt)
        row_idx += 1
        f_row4(row_idx, 'Target age / overlap', 'Age of the latest target (freshness drives street reliability). Overlap = the shared part of our Bear-Bull range and the street range; near 0% means we disagree on the whole distribution.', na(s.age_d) ? 'Age -' : str.tostring(s.age_d, '#') + ' days', 'Overlap ' + (na(s.overlap) ? '-' : str.tostring(s.overlap * 100, '#') + '%'), '')
        row_idx += 1
    f_hdr(row_idx, 'Confidence parts', 'Ours', 'Street', 'Weight', s.conf_tt)
    row_idx += 1
    array<string> cl = array.from('Agreement', 'Depth', 'Reliability / Freshness', 'Quality / Conviction')
    array<string> cwt = array.from('35%', '20%', '25%', '20%')
    for j = 0 to 3
        f_row4(row_idx, array.get(cl, j), array.get(s.ctt, j), f_stxt(array.get(s.co, j)), f_stxt(array.get(s.cs, j)), array.get(cwt, j))
        row_idx += 1
    row_idx
f_det_health1(HealthView h, int r0) =>
    int row_idx = r0
    f_hdr(row_idx, 'Diagnostics', 'Value', 'Detail', 'Status', '')
    row_idx += 1
    f_row4(row_idx, 'Net Debt / EBITDA', 'Net debt as a multiple of TTM EBITDA.\n\n<0 net cash | <1.5 conservative | 1.5-3 moderate | 3-4.5 elevated | >4.5 high.\n\nCapital-intensive sectors run structurally higher.', na(h.nd) ? 'N/A' : str.tostring(h.nd, '#.#') + 'x', 'Leverage', h.nd_txt, c1 = h.nd > 3.0 ? color.red : color_text, b3 = h.nd_col)
    row_idx += 1
    if h.zm_on
        f_row4(row_idx, 'Z+M Risk Matrix', h.zm_tt, 'Z: ' + str.tostring(altman_z, '#.#') + ' | M: ' + str.tostring(m_score, '#.#'), 'Risk Profile', h.zm_txt, c3 = color.white, b3 = h.zm_col, stt = h.zm_tt)
        row_idx += 1
    f_row4(row_idx, 'Asset / EBITDA growth YoY', h.inv_tt, str.tostring(math.round(nz(asset_growth, 0) * 100)) + '% / ' + str.tostring(math.round(nz(ebitda_growth, 0) * 100)) + '%', 'Capital Allocation', h.inv_txt, c1 = investment_dummy ? color.red : color_text, b3 = h.inv_col, stt = h.inv_tt)
    row_idx += 1
    if i_use_rkv
        f_row4(row_idx, 'Rhodes-Kropf V/B (Growth)', h.rkv_tt, str.tostring(rkv_growth_vb, '#.##') + 'x', 'RKV Diagnosis', h.rkv_txt, c1 = is_rkv_deep_value ? color.green : is_rkv_value_trap ? color.red : color_text, b3 = h.rkv_col, stt = h.rkv_tt)
        row_idx += 1
    string macro_src = (i_lr_infl > 0 ? 'input' : 'auto') + ' / ' + (i_lr_rgdp > 0 ? 'input' : 'auto')
    f_row4(row_idx, 'Macro (manual)', 'Long-run inflation and real GDP growth are assumptions, not feeds. Set them in Industry-Specific Valuation. auto = per-currency default.', 'Infl ' + str.tostring(lr_infl * 100, '#.##') + '% | GDP ' + str.tostring(lr_rgdp * 100, '#.##') + '%', macro_src, 'Terminal g ' + str.tostring(final_terminal_growth * 100, '#.##') + '%', b1 = color_value)
    row_idx += 1
    if M_OE.on
        float oe_yield_pct = close > 0 ? nz(oe_per_share) / close * 100 : 0.0
        float yield_spread = oe_yield_pct - rf_local_avg
        string coupon_status = yield_spread >= 3.0 ? 'SCREAMING BUY' : yield_spread > 0 ? 'BUY (Positive Carry)' : 'PASS (Yield < Bond)'
        color coupon_color = yield_spread >= 3.0 ? color.new(color.green, 0) : yield_spread > 0 ? color_under : color_over
        string coupon_tt = 'Owner Earnings yield: ' + str.tostring(oe_yield_pct, '#.##') + '%\n10Y hurdle: ' + str.tostring(rf_local_avg, '#.##') + '%\nSpread: ' + (yield_spread > 0 ? '+' : '') + str.tostring(yield_spread, '#.##') + '%'
        f_row4(row_idx, 'Buffett Coupon vs 10Y', coupon_tt, str.tostring(oe_yield_pct, '#.##') + '%', (yield_spread > 0 ? '+' : '') + str.tostring(yield_spread, '#.##') + '%', coupon_status, b1 = color_value, c2 = yield_spread > 0 ? color.green : color.red, c3 = color.white, b3 = coupon_color, stt = coupon_tt)
        row_idx += 1
    bool is_crazy_exit = implied_exit_multiple > 30.0
    f_row4(row_idx, 'Implied exit EV/NOPAT (Yr' + str.tostring(i_dcf_stage1_yrs) + ')', 'Terminal value / final-year NOPAT inside the DCF: a firm-value multiple, not a P/E. Above 30x the value leans on a rich exit.', f_petxt(implied_exit_multiple), 'Sanity Check', is_crazy_exit ? 'High' : 'Safe', b1 = color_value, c3 = is_crazy_exit ? color.red : color.green)
    row_idx += 1
    row_idx
f_det_health2(HealthView h, int r0) =>
    int row_idx = r0
    f_hdr(row_idx, 'Quant Quality Filters', 'Value', 'Target', 'Status', '')
    row_idx += 1
    f_row4(row_idx, 'Piotroski F-Score', 'Nine binary tests of profitability, leverage / liquidity and operating efficiency.', na(piotroski_f_score) ? 'N/A' : str.tostring(piotroski_f_score, '#'), '7 or more', h.pio_txt, b3 = h.pio_col)
    row_idx += 1
    [qon, qnm, qvl, qtg, qps] = f_qf()
    for j = 0 to 3
        if array.get(qon, j)
            bool p = array.get(qps, j)
            f_row4(row_idx, array.get(qnm, j), j == 2 ? '(Net Income - Operating Cash Flow) / Total Assets.\n\nSloan (1996) is a RETURNS anomaly, not a fraud test. Beneish M-Score in the Z+M row is the manipulation model.' : '', array.get(qvl, j), array.get(qtg, j), f_qword(j, p), c1 = p ? color.green : j == 3 ? color_text : color.red, c3 = color.white, b3 = p ? color_under : color_over)
            row_idx += 1
    row_idx
// Shadow check result (section 6): how many values were compared, the largest relative
// difference, and the first mismatch.
f_shadow_row(int r0) =>
    int row_idx = r0
    string mx = sh_max <= 0 ? '0' : '1e' + str.tostring(math.floor(math.log10(sh_max)))
    string tt = 'The previous model stage runs alongside the model rows from the same inputs: Base on every bar, Bear and Bull on the last bar, plus the tiers and the DCF exit multiple. A value matches within 1e-9 of the larger of itself and the price; na matches only na.\n\nCompared: ' + str.tostring(sh_n) + '. Largest relative difference: ' + mx + '.' + (sh_bad == 0 ? '' : '\nFirst mismatch: ' + sh_first)
    f_row4(row_idx, 'Shadow check', tt, str.tostring(sh_n) + ' compared', 'max diff ' + mx, sh_bad == 0 ? 'MATCH' : str.tostring(sh_bad) + ' DIFF', c3 = color.white, b3 = sh_bad == 0 ? color_under : color_over, stt = tt)
    row_idx + 1
if barstate.islast
    StreetView sv = StreetView.new()
    if i_show_street
        sv := f_street_calc()
    HealthView hv = f_health_calc()
    int r_ = f_tbl_head()
    r_ := f_sum_val(sv, r_)
    r_ := f_sum_health(hv, r_)
    if i_shadow
        r_ := f_shadow_row(r_)
    bool all_ = i_detail == 'Everything'
    if all_ or i_detail == 'Models'
        r_ := f_det_models(r_)
        r_ := f_det_omni(r_)
    if i_show_street and (all_ or i_detail == 'Street')
        r_ := f_det_street(sv, r_)
    if all_ or i_detail == 'Health'
        r_ := f_det_health1(hv, r_)
        r_ := f_det_health2(hv, r_)
// ==========================================
// 7. PLOTTING (MARGIN OF SAFETY ZONES)
// ==========================================
// [FIX ZONE] ONE entry margin, used by both the chart and the backtester.
// Input margin x downside beta (min 0.5x), clamped 5%..50%.
float entry_margin = math.min(math.max(i_bt_margin * math.max(nz(downside_beta, beta_mkt), 0.5), 0.05), 0.50)
float sell_zone_line = finalFairValue * (1.0 + i_bt_exit_premium)
float buy_zone_line = finalFairValue * (1.0 - entry_margin)
p_fv = plot(finalFairValue, 'Fair Value', color = color.new(color.blue, 0), linewidth = 2)
p_sell = plot(sell_zone_line, 'Sell Target (Overvalued)', color = color.new(color.red, 30), linewidth = 1, style = plot.style_circles)
p_buy = plot(buy_zone_line, 'Buy Zone (Discount)', color = color.new(color.green, 30), linewidth = 1, style = plot.style_circles)
fill(p_fv, p_sell, color = color.new(color.red, 90), title = 'Overvaluation Cloud')
fill(p_fv, p_buy, color = color.new(color.green, 90), title = 'Margin of Safety Cloud')
bool is_screaming_buy = close < buy_zone_line
bool is_screaming_sell = close > sell_zone_line
barcolor(is_screaming_buy ? color.new(color.green, 0) : is_screaming_sell ? color.new(color.red, 0) : na, title = "Zone Bar Highlights")
// One model row's Base result record in the Data Window, bar by bar (Model rows: Data window).
var int dw_i = -1
if barstate.isfirst and str.trim(i_dw_code) != ''
    for [k, m] in MD
        if m.code == str.upper(str.trim(i_dw_code))
            dw_i := k
float dw_val = na
float dw_core = na
float dw_add = na
float dw_cl = na
float dw_rate = na
float dw_g1 = na
float dw_gT = na
if dw_i >= 0
    Model dm = MD.get(dw_i)
    Res dr = dm.res.get(0)
    float per = dm.ps ? 1.0 : dr.sh
    dw_val := dr.value
    dw_core := dr.core / per
    dw_add := dr.add / per
    dw_cl := dr.cl / per
    dw_rate := dr.x.rate * 100
    dw_g1 := dr.x.g1 * 100
    dw_gT := dr.x.gT * 100
plot(dw_val, 'Row: value', display = display.data_window)
plot(dw_core, 'Row: engine core / share', display = display.data_window)
plot(dw_add, 'Row: add-on / share', display = display.data_window)
plot(dw_cl, 'Row: claims / share', display = display.data_window)
plot(dw_rate, 'Row: rate %', display = display.data_window)
plot(dw_g1, 'Row: stage-1 growth %', display = display.data_window)
plot(dw_gT, 'Row: terminal growth %', display = display.data_window)
plot(sh_bar, 'Shadow: largest relative difference', display = display.data_window)
// ==========================================
// 8. TRUE ROLLING BACKTESTER
// ==========================================
// [FIX BPY] Holding period in bars from bars-per-year, not calendar days / bar length.
float hold_years = i_bt_unit == 'Days' ? i_bt_val / 365.25 : i_bt_unit == 'Weeks' ? i_bt_val * 7 / 365.25 : i_bt_unit == 'Months' ? i_bt_val / 12.0 : i_bt_val * 1.0
int bars_to_hold = math.max(math.min(int(math.round(hold_years * bpy)), 4800), 1)
// --- HELPER: ARRAY CORRELATION (FOR TIME-SERIES IC) ---
f_array_correl(array<float> arr_x, array<float> arr_y) =>
    int n = array.size(arr_x)
    float res = na
    if n > 1
        float mean_x = array.avg(arr_x)
        float mean_y = array.avg(arr_y)
        float num = 0.0, float den_x = 0.0, float den_y = 0.0
        for i = 0 to n - 1
            float dx = array.get(arr_x, i) - mean_x
            float dy = array.get(arr_y, i) - mean_y
            num += (dx * dy)
            den_x += (dx * dx)
            den_y += (dy * dy)
        if den_x > 0 and den_y > 0
            res := num / math.sqrt(den_x * den_y)
    res
// Period resolution, computed once per bar for all models.
int bt_period = 0
if i_period_mode == 'Full Period'
    bt_period := 1
else if i_period_mode == 'Auto-Split'
    int span_start = nz(bt_first_data_bar, 0)
    int span = math.max(last_bar_index - span_start, 1)
    int p1_end = span_start + int(span * i_split_1)
    int p2_end = span_start + int(span * (i_split_1 + i_split_2))
    bt_period := bar_index < span_start ? 0 : bar_index <= p1_end ? 1 : bar_index <= p2_end ? 2 : 3
else
    bt_period := time >= i_is_start and time <= i_is_end ? 1 : (time >= i_oos_start and time <= i_oos_end ? 2 : (time > i_oos_end ? 3 : 0))
int bt_cooldown = math.max(1, int(bpy / 12))
f_rolling_update(ModelStats stats_obj, current_fv, current_close, current_low, exit_prem, max_hold, max_open, int current_period) =>
    int open_trades = array.size(stats_obj.entry_prices)
    bool target_hit = current_fv > 0 and current_close >= current_fv * (1.0 + exit_prem)
    // Dividends accrue per bar at the trailing DPS known on that bar (not the exit-day yield).
    float dps_bar = nz(div_per_share_ttm) / bpy
    if open_trades > 0
        for i = open_trades - 1 to 0
            float e_price = array.get(stats_obj.entry_prices, i)
            int e_bar = array.get(stats_obj.entry_bars, i)
            int e_period = array.get(stats_obj.entry_periods, i)
            array.set(stats_obj.entry_divs, i, array.get(stats_obj.entry_divs, i) + dps_bar)
            float new_min = math.min(array.get(stats_obj.floating_min_prices, i), current_low)
            array.set(stats_obj.floating_min_prices, i, new_min)
            int bars_held = bar_index - e_bar
            if target_hit or bars_held >= max_hold
                bool straddles = (current_period > 0) and (current_period != e_period)
                bool skip_trade = straddles and i_bt_drop_straddle
                if straddles
                    stats_obj.straddled += 1
                PeriodStats active_stats = e_period == 1 ? stats_obj.is_stats : (e_period == 2 ? stats_obj.oos_stats : stats_obj.fwd_stats)
                active_stats.total += skip_trade ? 0 : 1
                float years_held = math.max(bars_held / float(bpy), 0.083)
                float collected_dividends = array.get(stats_obj.entry_divs, i)
                float raw_exit_price = current_close + collected_dividends
                float net_return_pct = ((raw_exit_price - e_price) / e_price) - i_bt_fees
                float ann_ret_pct = (math.pow(1.0 + math.max(net_return_pct, -0.999), 1.0 / years_held) - 1.0) * 100
                float max_dd_pct = ((new_min - e_price) / e_price) * 100
                if not skip_trade
                    if net_return_pct > 0
                        active_stats.gross_profit += net_return_pct
                    else
                        active_stats.gross_loss += math.abs(net_return_pct)
                    if net_return_pct > i_bt_win_threshold
                        active_stats.wins += 1
                    array.push(active_stats.closed_returns, net_return_pct)
                    array.push(active_stats.closed_drawdowns, max_dd_pct)
                    array.push(active_stats.closed_ann_returns, ann_ret_pct)
                    array.push(active_stats.closed_discounts, array.get(stats_obj.entry_discounts, i))
                    array.push(active_stats.closed_holds, years_held)
                // [PERF] SWAP-AND-POP (loop runs descending, order is never read).
                int lastx = array.size(stats_obj.entry_prices) - 1
                if i != lastx
                    array.set(stats_obj.entry_prices, i, array.get(stats_obj.entry_prices, lastx))
                    array.set(stats_obj.floating_min_prices, i, array.get(stats_obj.floating_min_prices, lastx))
                    array.set(stats_obj.entry_bars, i, array.get(stats_obj.entry_bars, lastx))
                    array.set(stats_obj.entry_discounts, i, array.get(stats_obj.entry_discounts, lastx))
                    array.set(stats_obj.entry_periods, i, array.get(stats_obj.entry_periods, lastx))
                    array.set(stats_obj.entry_divs, i, array.get(stats_obj.entry_divs, lastx))
                array.pop(stats_obj.entry_prices)
                array.pop(stats_obj.floating_min_prices)
                array.pop(stats_obj.entry_bars)
                array.pop(stats_obj.entry_discounts)
                array.pop(stats_obj.entry_periods)
                array.pop(stats_obj.entry_divs)
    // Entry Logic (max_open 0 = unlimited)
    int n_open = array.size(stats_obj.entry_prices)
    if current_period > 0 and current_fv > 0 and (max_open <= 0 or n_open < max_open)
        float buy_limit = current_fv * (1.0 - entry_margin)
        if current_close <= buy_limit and (n_open == 0 or (bar_index - stats_obj.last_entry) >= bt_cooldown)
            array.push(stats_obj.entry_prices, current_close)
            array.push(stats_obj.floating_min_prices, current_close)
            array.push(stats_obj.entry_bars, bar_index)
            array.push(stats_obj.entry_discounts, (current_fv - current_close) / current_close)
            array.push(stats_obj.entry_periods, current_period)
            array.push(stats_obj.entry_divs, 0.0)
            stats_obj.last_entry := bar_index
// The backtest deliberately IGNORES the allocation matrix: it is the evidence you use
// to DECIDE an allocation. Every model row trades; the Composite row trades the final blend.
// [BASELINE] fv = 10x price: always "cheap", never hits target, so it buys on every
// cooldown and exits at max hold -- a buy-and-hold proxy.
var ModelStats base_stats = f_new_model()
if i_show_bt
    for m in MD
        f_rolling_update(m.bt, m.grp == Group.comp ? finalFairValue : m.fv, close, low, i_bt_exit_premium, bars_to_hold, i_bt_max_open, bt_period)
    f_rolling_update(base_stats, close * 10, close, low, i_bt_exit_premium, bars_to_hold, i_bt_max_open, bt_period)
f_calc_vacagr(PeriodStats stats) =>
    float geo_cagr = na
    int n_ann = array.size(stats.closed_ann_returns)
    if n_ann > 0
        float comp_mult = 1.0
        for r in stats.closed_ann_returns
            comp_mult *= math.max(1.0 + r / 100.0, 0.001)
        geo_cagr := (math.pow(comp_mult, 1.0 / n_ann) - 1.0) * 100.0
    geo_cagr
// =====================================================================
// BACKTEST RENDERER -- 3 VIEWS
// =====================================================================
type PMetrics
    int n = 0
    float wr = na
    float expectancy = na
    float mae = na
    float ic = na
    float med_ret = na
    float avg_hold = na
    float vacagr = na
f_period_metrics(PeriodStats stats) =>
    int n = stats.total
    float wr = n > 0 ? (stats.wins / float(n)) * 100.0 : na
    float avg_win = stats.wins > 0 ? (stats.gross_profit / stats.wins) : 0.0
    float avg_loss = (n - stats.wins) > 0 ? (stats.gross_loss / (n - stats.wins)) : 0.0
    float expectancy = n > 0 ? ((wr / 100.0) * avg_win) - ((1.0 - (wr / 100.0)) * avg_loss) : na
    float mae = array.size(stats.closed_drawdowns) > 0 ? array.min(stats.closed_drawdowns) : na
    float ic = f_array_correl(stats.closed_discounts, stats.closed_returns)
    float med_ret = f_median(stats.closed_returns)
    float avg_hold = array.size(stats.closed_holds) > 0 ? array.avg(stats.closed_holds) : na
    PMetrics.new(n, wr, expectancy, mae, ic, med_ret, avg_hold, f_calc_vacagr(stats))
// Median trade annualised over the average hold (floor 3 months), in %: comparable across
// holding periods, unlike a raw median (scales with hold) or VACAGR (short holds dominate).
f_med_ann(PMetrics p) =>
    na(p.med_ret) ? na : (math.pow(1 + math.max(p.med_ret, -0.999), 1 / math.max(nz(p.avg_hold, 1.0), 0.25)) - 1) * 100
f_conf_col(int n) =>
    n == 0 ? color.new(color.gray, 85) : n < i_bt_min_n ? color.new(color.gray, 75) : color(na)
// Period 1 = in-sample, 2 = out-of-sample, 3 = forward.
f_ps(ModelStats m, int which) =>
    which == 1 ? m.is_stats : which == 2 ? m.oos_stats : m.fwd_stats
f_format_period(PeriodStats stats) =>
    PMetrics p = f_period_metrics(stats)
    if p.n == 0
        ["N/A", "No trades in this period.", color.new(color.gray, 80), color.gray]
    else
        float md = nz(f_med_ann(p))
        string main_txt = str.tostring(md, "#.0") + "%/y (" + str.tostring(p.wr, "#.0") + "%) n=" + str.tostring(p.n)
        string tt = "Trades: " + str.tostring(p.n) +
             "\nIC (Alpha): " + (not na(p.ic) ? str.tostring(p.ic, "#.00") : "N/A") +
             "\nExpectancy: " + (not na(p.expectancy) ? str.tostring(p.expectancy * 100, "#.0") + "%" : "N/A") +
             "\nMedian trade: " + (not na(p.med_ret) ? str.tostring(p.med_ret * 100, "#.0") + "%" : "N/A") +
             "\nMean trade: " + str.tostring(array.avg(stats.closed_returns) * 100, "#.0") + "%" +
             "\nVACAGR: " + (not na(p.vacagr) ? str.tostring(p.vacagr, "#.0") + "%" : "N/A") +
             "\nAvg hold: " + (not na(p.avg_hold) ? str.tostring(p.avg_hold, "#.0") + "y" : "N/A") +
             "\nMAE (per-trade): " + (not na(p.mae) ? str.tostring(p.mae, "#.0") + "%" : "N/A") +
             "\n\nHeadline = median trade (after fees, dividends accrued) annualised over the average hold. VACAGR annualizes each trade with a 1-month floor, so short holds dominate it."
        color dim_col = f_conf_col(p.n)
        color bg_col = not na(dim_col) ? dim_col : md >= 15.0 ? color.new(color.yellow, 0) : md > 0 ? color.new(color.green, 70) : color.new(color.red, 70)
        color txt_col = not na(dim_col) ? color.silver : md >= 15.0 ? color.black : color.white
        [main_txt, tt, bg_col, txt_col]
var table bt_tbl = table.new(position.bottom_left, 9, 32, border_width = 1)
// One dashboard cell (small text) and the left-aligned model-name cell.
f_btc(int c, int r, string t, color bg, color tc, string tt = '') =>
    table.cell(bt_tbl, c, r, t, bgcolor = bg, text_color = tc, text_size = size.small, tooltip = tt)
f_btn(int r, string name) =>
    table.cell(bt_tbl, 0, r, name, bgcolor = color.new(color.black, 50), text_color = color.white, text_size = size.small, text_halign = text.align_left)
// --- VIEW 1: MATRIX (all three periods) ---
f_fill_matrix_row(int row, string name, ModelStats m) =>
    f_btn(row, name)
    for c = 1 to 3
        [txt, tt, bg, tcol] = f_format_period(f_ps(m, c))
        f_btc(c, row, txt, bg, tcol, tt)
// --- VIEW 2: FOCUS (one period, metrics as columns) ---
f_fill_focus_row(int row, string name, ModelStats m, int which) =>
    PMetrics p = f_period_metrics(f_ps(m, which))
    color grey = f_conf_col(p.n)
    color base = not na(grey) ? grey : color.new(color.black, 70)
    color txt = not na(grey) ? color.silver : color.white
    f_btn(row, name)
    f_btc(1, row, p.n == 0 ? "-" : str.tostring(p.n), base, txt, m.straddled > 0 ? "straddling trades excluded: " + str.tostring(m.straddled) : "")
    f_btc(2, row, na(p.ic) ? "-" : str.tostring(p.ic, "#.00"), not na(grey) ? grey : na(p.ic) ? color.new(color.gray, 80) : p.ic > 0.3 ? color.new(color.green, 30) : p.ic > 0 ? color.new(color.green, 70) : color.new(color.red, 60), txt, "Correlation between entry discount and realised return. Near zero = the fair value carries no predictive information.")
    f_btc(3, row, na(p.expectancy) ? "-" : str.tostring(p.expectancy * 100, "#.0") + "%", not na(grey) ? grey : na(p.expectancy) ? color.new(color.gray, 80) : p.expectancy > 0 ? color.new(color.green, 60) : color.new(color.red, 60), txt)
    f_btc(4, row, na(p.med_ret) ? "-" : str.tostring(p.med_ret * 100, "#.0") + "%", base, txt)
    f_btc(5, row, na(p.wr) ? "-" : str.tostring(p.wr, "#.0") + "%", base, txt)
    f_btc(6, row, na(p.avg_hold) ? "-" : str.tostring(p.avg_hold, "#.1") + "y", base, txt)
    f_btc(7, row, na(p.mae) ? "-" : str.tostring(p.mae, "#.0") + "%", base, txt)
    f_btc(8, row, na(p.vacagr) ? "-" : str.tostring(p.vacagr, "#.0") + "%", base, txt, "VACAGR floors holding period at 1 month. Read with Median and Hold.")
// --- VIEW 3: ROBUSTNESS VERDICT (vs the always-in baseline) ---
f_fill_robust_row(int row, string name, ModelStats m, ModelStats b) =>
    array<float> v = array.new_float(0)
    array<int> n = array.new_int(0)
    float edge_sum = 0.0
    bool beats_all = true
    for w = 1 to 3
        PMetrics p = f_period_metrics(f_ps(m, w))
        // [FIX BASELINE] "Stable" also requires beating simply being invested.
        // Annualised median trade (%/y), the same headline as the matrix.
        float q = nz(f_med_ann(f_period_metrics(f_ps(b, w))))
        float pv = f_med_ann(p)
        array.push(v, pv)
        array.push(n, p.n)
        edge_sum += nz(pv) - q
        beats_all := beats_all and nz(pv) > q
    float v1 = array.get(v, 0), float v2 = array.get(v, 1), float v3 = array.get(v, 2)
    float edge = edge_sum / 3.0
    bool enough = array.min(n) >= i_bt_min_n
    float spread = math.max(nz(v1, 0), nz(v2, 0), nz(v3, 0)) - math.min(nz(v1, 0), nz(v2, 0), nz(v3, 0))
    string verdict = "Insufficient"
    color vcol = color.new(color.gray, 60)
    string vtip = "Fewer than " + str.tostring(i_bt_min_n) + " trades in at least one period. No verdict is defensible."
    if enough
        bool all_pos = nz(v1, -1) > 0 and nz(v2, -1) > 0 and nz(v3, -1) > 0
        bool monotone_down = v1 > v2 and v2 > v3
        bool front_loaded = v1 > 0 and (nz(v2, 0) <= 0 or nz(v3, 0) <= 0)
        if front_loaded
            verdict := "Overfit"
            vcol := color.new(color.red, 20)
            vtip := "Strong in period 1, weak or negative later. The parameters fit the first window, not the phenomenon."
        else if monotone_down and spread > 10
            verdict := "Decaying"
            vcol := color.new(color.orange, 30)
            vtip := "Monotonically falling across periods. The edge may be closing."
        else if all_pos and spread < 20 and beats_all
            verdict := "Stable"
            vcol := color.new(color.green, 20)
            vtip := "Positive in all three periods, contained dispersion, and ahead of the always-in baseline in each."
        else if all_pos and spread < 20
            verdict := "No edge"
            vcol := color.new(color.orange, 40)
            vtip := "Stable and positive, but not better than simply being invested."
        else
            verdict := "Mixed"
            vcol := color.new(color.gray, 40)
            vtip := "No clean pattern. Treat as unproven rather than broken."
    f_btn(row, name)
    for c = 1 to 3
        float vc = array.get(v, c - 1)
        int nc = array.get(n, c - 1)
        f_btc(c, row, na(vc) ? "-" : str.tostring(vc, "#.0"), color.new(color.black, 70), nc < i_bt_min_n ? color.silver : color.white, "n=" + str.tostring(nc))
    f_btc(4, row, enough ? str.tostring(spread, "#.0") : "-", color.new(color.black, 70), color.white)
    f_btc(5, row, verdict, vcol, color.white, vtip)
    f_btc(6, row, enough ? (edge > 0 ? "+" : "") + str.tostring(edge, "#.0") : "-", enough ? (edge > 0 ? color.new(color.green, 60) : color.new(color.red, 60)) : color.new(color.black, 70), color.white)
    f_btc(7, row, "", color.new(color.black, 100), color.white)
    f_btc(8, row, "", color.new(color.black, 100), color.white)
// --- DISPATCHER ---
f_bt_row(int row, string name, ModelStats m) =>
    if i_bt_view == 'Matrix (all periods)'
        f_fill_matrix_row(row, name, m)
    else if i_bt_view == 'Robustness verdict'
        f_fill_robust_row(row, name, m, base_stats)
    else
        f_fill_focus_row(row, name, m, i_bt_view == 'Focus: Period 1' ? 1 : i_bt_view == 'Focus: Period 2' ? 2 : 3)
// Dashboard order: Composite, the classic intrinsic models, the multiples, Acquirer's
// Multiple and Owners' Earnings, then the sector models. Rows the list leaves out follow;
// the Baseline closes the list.
string BT_ORDER = 'COMP DCF GRA EPV RIM R40 PE PS FCF PB TBV EV CF AFFO ACQ OE RNPV ECF ADCF UNB APV EVA DDM'
// --- DASHBOARD RENDERER ---
f_bt_table() =>
    table.set_position(bt_tbl, i_bt_pos == 'top_left' ? position.top_left : i_bt_pos == 'middle_left' ? position.middle_left : i_bt_pos == 'bottom_center' ? position.bottom_center : i_bt_pos == 'top_center' ? position.top_center : position.bottom_left)
    table.clear(bt_tbl, 0, 0, 8, 31)
    string mode_tag = i_period_mode == 'Auto-Split' ? " [auto-split]" : i_period_mode == 'Full Period' ? " [pooled]" : ""
    bool v_mx = i_bt_view == 'Matrix (all periods)'
    bool v_rb = i_bt_view == 'Robustness verdict'
    array<string> hd = v_mx ? array.from('Valuation Model Matrix', 'Period 1\n(In-Sample)', 'Period 2\n(Out-of-Sample)', 'Period 3\n(Forward)') : v_rb ? array.from('Robustness', 'P1', 'P2', 'P3', 'Spread', 'Verdict', 'vs Base') : array.from(i_bt_view, 'n', 'IC', 'Expect', 'Median', 'Win%', 'Hold', 'MAE', 'VACAGR')
    for c = 0 to array.size(hd) - 1
        string tt = c == 0 ? 'The inputs were chosen after seeing this whole history, so for the SETTINGS every period is in-sample. Read P2/P3 as a stability check, not proof of an edge.' : v_mx ? 'Median trade, annualised over the average hold (%/y) (Win%) n=trades' : v_rb ? (c == 6 ? 'Average median-trade edge over the always-in baseline across the three periods.' : '') : c == 2 ? 'Discount-to-return correlation: does a bigger discount predict a bigger return?' : c == 7 ? 'Per-trade maximum adverse excursion, NOT portfolio drawdown.' : ''
        f_btc(c, 0, array.get(hd, c) + (c == 0 ? mode_tag : ''), c == 0 ? color.new(color.purple, 30) : color.new(color.blue, 20), c == 0 ? color.yellow : color.white, tt)
    // A dot marks a model the current framework does NOT allocate. Compact view (default):
    // the Composite, the allocated models and the Baseline. Sector models stay hidden until
    // they have produced trades.
    int btrowidx = 1
    int bt_hidden = 0
    for m in f_order(BT_ORDER)
        bool eligible = m.grp != Group.sect or m.fw or m.bt.is_stats.total > 0 or m.bt.oos_stats.total > 0
        if i_bt_all ? eligible : m.fw
            f_bt_row(btrowidx, (m.fw ? '' : '· ') + m.bt_name, m.bt)
            btrowidx += 1
        else if eligible
            bt_hidden += 1
    f_bt_row(btrowidx, 'Baseline (always in)', base_stats)
    btrowidx += 1
    // Footer: what compact mode hides (doubles as the padding row TV needs)
    table.cell(bt_tbl, 0, btrowidx, bt_hidden > 0 ? '+' + str.tostring(bt_hidden) + ' hidden (Show all)' : " ", bgcolor = color.new(color.black, 100), text_color = bt_hidden > 0 ? color.gray : color.new(color.white, 100), text_size = size.tiny, text_halign = text.align_left)
    for c = 1 to 3
        table.cell(bt_tbl, c, btrowidx, " ", bgcolor = color.new(color.black, 100), text_color = color.new(color.white, 100))
    true
if barstate.islast and i_show_bt
    f_bt_table()
```
