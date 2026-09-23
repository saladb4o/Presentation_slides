# Fundamental Fair Value Pro: full patched script (phases 0–6)

Copy everything inside the code block into the Pine Editor and replace the whole script.

```pine
//@version=6
indicator('Fundamental Fair Value Pro (FF4 + McKinsey/Rev DCF) [Real-Time + Backtest]', shorttitle = 'FFV Pro (Real)', overlay = true, max_lines_count = 50, dynamic_requests = true)
// ==========================================
// 1. HELPER FUNCTIONS
// ==========================================
f_median(array_id) =>
    if array.size(array_id) > 0
        sorted_array = array.copy(array_id)
        array.sort(sorted_array)
        array.get(sorted_array, math.floor(array.size(sorted_array) / 2))
    else
        na
// Average the TTM and forward legs when both exist, else take whichever does.
f_blend2(float a, float b) =>
    not na(a) and not na(b) ? (a + b) / 2 : nz(a, b)
f_harmonic_mean(array_id) =>
    int n = array.size(array_id)
    if n > 0
        float sum_reciprocals = 0.0
        int valid_count = 0
        for i = 0 to n - 1 by 1
            val = array.get(array_id, i)
            if not na(val) and val > 0
                sum_reciprocals := sum_reciprocals + 1.0 / val
                valid_count := valid_count + 1
        sum_reciprocals > 0 ? valid_count / sum_reciprocals : na
    else
        na
// [PERF] Percentile from an ALREADY-SORTED copy, so one sort can serve the
// central tendency and both scenario legs.
f_pct_sorted(array<float> s, float p) =>
    int n = array.size(s)
    float idx = (n - 1) * p
    int lo = int(math.floor(idx))
    int hi = int(math.ceil(idx))
    float frac = idx - lo
    lo == hi ? array.get(s, lo) : array.get(s, lo) * (1 - frac) + array.get(s, hi) * frac
// [PERF] Central tendency + both percentile legs from ONE sort.
// Stateless: the CALLER caches into the Mult object, which survives bars
// because MULTS is `var`.
f_ratio_stats(array<float> arr, bool use_mean, float dflt, float lo_p, float hi_p, int min_n) =>
    int n = array.size(arr)
    float ct = na
    float c_lo = na
    float c_hi = na
    if n > 0
        array<float> s = array.copy(arr)
        array.sort(s)
        ct := use_mean ? f_harmonic_mean(arr) : array.get(s, math.floor(n / 2))
        if n >= min_n
            c_lo := f_pct_sorted(s, lo_p)
            c_hi := f_pct_sorted(s, hi_p)
    [nz(ct, dflt), na(ct) or n < 4, c_lo, c_hi]
// =====================================================================
// THE MULTIPLE UDT — one shape for all eight relative multiples
// =====================================================================
// drv TTM driver (per-share, or EBITDA for the EV row)
// drv_f forward driver, na when the model has no forward leg
// is_ev enterprise-value form: (driver x multiple - net debt) / shares
// rkv apply the Rhodes-Kropf book-value filter (P/B only)
type Mult
    string name
    float dflt
    bool is_ev = false
    bool rkv = false
    array<float> hist
    array<float> fvhist
    bool on = false
    float drv = na
    float drv_f = na
    float avg = na
    bool syn = true
    float plo = na
    float phi = na
    float fv = na
    float lo = na
    float hi = na
    float score = 0.0
// =====================================================================
// THE OMNIBUS MEMBER UDT - one shape for every blend candidate
// =====================================================================
// hist this member's own stored fair-value history (aligned to hist_px_tracker)
// on resolved membership AFTER framework / manual / sanity gating
// w final blend weight; 0 means "no track record", not "worthless"
type Omni
    string name
    array<float> hist
    bool on = false
    float fv = na
    float lo = na
    float hi = na
    float w = 0.0
// One multiple x one driver leg. Collapses the price-form and the EV-form
// into a single expression so the loop needs no branch.
f_apply(float drv, float mult, bool is_ev, float nd, float sh) =>
    na(drv) or drv <= 0 or na(mult) ? na : (is_ev ? (drv * mult - nd) / sh : drv * mult)
f_cell(table_id, col, row, txt, txt_color, bg_color, size) =>
    table.cell(table_id, col, row, str.tostring(txt), text_color = txt_color, bgcolor = bg_color, text_size = size)
f_update_ratio_array(array_id, value, max_size, cap) =>
    if not na(value) and value > 0
        array.push(array_id, math.min(value, cap))
        if array.size(array_id) > max_size
            array.shift(array_id)
// [FIX ALIGN] Companion to the above, for every array later read PAIRWISE
// against hist_px_tracker. Pushing na keeps index i meaning "the same
// quarter" in every array; the error helpers skip na pairs.
f_push_aligned(array_id, value, max_size, cap) =>
    array.push(array_id, not na(value) and value > 0 ? math.min(value, cap) : na)
    if array.size(array_id) > max_size
        array.shift(array_id)
f_series_to_array(id_series, len) =>
    arr = array.new_float(0)
    for i = 0 to len - 1 by 1
        array.unshift(arr, id_series[i])
    arr
f_get_synthetic_spread_damodaran(ebit, interest_exp) =>
    float icr = not na(interest_exp) and interest_exp > 0 ? ebit / interest_exp : 100.0
    float spread = 0.0
    if icr > 8.5
        spread := 0.0063
    else if icr > 6.5
        spread := 0.0078
    else if icr > 5.5
        spread := 0.0098
    else if icr > 4.25
        spread := 0.0108
    else if icr > 3.0
        spread := 0.0122
    else if icr > 2.5
        spread := 0.0156
    else if icr > 2.25
        spread := 0.0200
    else if icr > 2.0
        spread := 0.0240
    else if icr > 1.75
        spread := 0.0351
    else if icr > 1.5
        spread := 0.0417
    else if icr > 1.25
        spread := 0.0600
    else if icr > 0.8
        spread := 0.0800
    else
        spread := 0.1200
    spread
f_calculate_cagr_from_series(series_data, years) =>
    bool is_new_quarter = not na(series_data) and series_data != series_data[1]
    int changes_lookback = years * 4
    float past_val = ta.valuewhen(is_new_quarter, series_data, changes_lookback)
    float current_val = series_data
    float cagr = na
    if not na(current_val) and not na(past_val) and past_val > 0 and current_val > 0
        cagr := math.pow(current_val / past_val, 1.0 / years) - 1
    cagr
f_calculate_rim(nopat_base, invested_capital, shares, net_debt, wacc, growth_rate, terminal_growth, projection_years) =>
    float iv_rim = na
    float adjusted_term_growth = math.min(terminal_growth, wacc - 0.015)
    if not na(nopat_base) and not na(invested_capital) and invested_capital > 0 and not na(wacc) and not na(terminal_growth) and wacc > adjusted_term_growth
        capital_charge_base = invested_capital * wacc
        economic_profit_base = nopat_base - capital_charge_base
        float total_discounted_ep = 0.0
        float projected_ep = economic_profit_base
        for i = 1 to projection_years by 1
            projected_ep := projected_ep * (1 + growth_rate)
            total_discounted_ep := total_discounted_ep + projected_ep / math.pow(1 + wacc, i)
        terminal_value_ep = projected_ep * (1 + adjusted_term_growth) / (wacc - adjusted_term_growth)
        discounted_terminal_value_ep = terminal_value_ep / math.pow(1 + wacc, projection_years)
        enterprise_value = invested_capital + total_discounted_ep + discounted_terminal_value_ep
        equity_value = enterprise_value - net_debt
        iv_rim := equity_value / shares
    iv_rim
f_calculate_dcf_value_driver_extended(fcf_per_share, nopat_per_share, roic_current, wacc, growth_stage1, growth_term, years_stage1) =>
    float pv_explicit = 0.0
    float current_fcf = fcf_per_share
    float current_nopat = nopat_per_share
    float adjusted_growth_term = math.min(growth_term, wacc - 0.015)
    for i = 1 to years_stage1 by 1
        float weight = i / (years_stage1 + 1.0)
        float year_growth = growth_stage1 * (1.0 - weight) + adjusted_growth_term * weight
        current_fcf := current_fcf * (1 + year_growth)
        current_nopat := current_nopat * (1 + year_growth)
        pv_explicit := pv_explicit + current_fcf / math.pow(1 + wacc, i)
    float terminal_roic = math.min(math.max(roic_current, wacc), 0.20)
    float reinvestment_rate_term = terminal_roic > 0 ? adjusted_growth_term / terminal_roic : 0.0
    float terminal_nopat = current_nopat * (1 + adjusted_growth_term)
    float terminal_fcf = terminal_nopat * (1 - reinvestment_rate_term)
    float tv_value = terminal_fcf / (wacc - adjusted_growth_term)
    float pv_tv = tv_value / math.pow(1 + wacc, years_stage1)
    float total_value = pv_explicit + pv_tv
    float implied_exit_multiple = current_nopat > 0 ? tv_value / current_nopat : na
    [total_value, implied_exit_multiple]
f_calculate_reverse_dcf(current_price, fcf_total, shares, discount_rate, term_growth, years) =>
    float low = -0.50
    float high = 1.00
    float solved_g = na
    if fcf_total > 0 and current_price > 0
        for i = 0 to 14 by 1
            float mid = (low + high) / 2
            float pv = 0.0
            float curr_fcf = fcf_total
            for y = 1 to years by 1
                curr_fcf := curr_fcf * (1 + mid)
                pv := pv + curr_fcf / math.pow(1 + discount_rate, y)
            float term_val = curr_fcf * (1 + term_growth) / (discount_rate - term_growth)
            float pv_term = term_val / math.pow(1 + discount_rate, years)
            float model_price = (pv + pv_term) / shares
            if model_price > current_price
                high := mid
            else
                low := mid
        solved_g := (low + high) / 2
    solved_g
f_calculate_rule_of_x_fv(rev_growth, margin, total_revenue, net_debt, shares) =>
    float rule_40_score = (rev_growth + margin) * 100
    float rule_x_score = (rev_growth * 2.0 + margin) * 100
    float fair_multiple = na
    if rule_x_score >= 65
        fair_multiple := 12.0 + (rule_x_score - 65) * 0.3
    else if rule_40_score < 10
        fair_multiple := 1.5
    else
        fair_multiple := 1.0 + rule_40_score * 0.25
    fair_multiple := math.min(fair_multiple, 25.0)
    float target_ev = fair_multiple * total_revenue
    float target_equity_value = target_ev - net_debt
    shares > 0 ? target_equity_value / shares : na
f_calculate_rnpv_sotp(base_dcf_per_share, rnd_annual, shares) =>
    float capitalized_pipeline = rnd_annual * 5.0
    float risk_adjusted_pipeline_val = shares > 0 ? (capitalized_pipeline * 0.15) / shares : 0
    base_dcf_per_share + risk_adjusted_pipeline_val
// [FIX ECF] Two-stage FCFE. The old version had no D&A add-back, compounded
// with the near-term growth rate forever, and divided a year-1 perpetuity by
// (1+coe)^5 as if it started in year 5.
f_calculate_ecf(net_income, da, capex, net_borrowing, coe, g1, g_term, years, shares) =>
    float fcfe0 = net_income + nz(da) - math.abs(nz(capex)) + nz(net_borrowing)
    float val = na
    if not na(fcfe0) and fcfe0 > 0 and shares > 0 and coe > g_term
        float pv = 0.0
        float cf = fcfe0
        for t = 1 to years
            float w = t / (years + 1.0)
            cf := cf * (1 + g1 * (1 - w) + g_term * w)
            pv += cf / math.pow(1 + coe, t)
        float tv = cf * (1 + g_term) / (coe - g_term)
        val := (pv + tv / math.pow(1 + coe, years)) / shares
    val
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
// Gordon growth DDM on the long-run terminal rate.
f_calculate_ddm(dps, coe, terminal_growth) =>
    float g = math.min(nz(terminal_growth, 0.02), coe - 0.01)
    not na(dps) and dps > 0 and coe > g ? (dps * (1 + g)) / (coe - g) : na
// [FIX APV] Perpetuity at TERMINAL growth (was the 15-40% explicit rate over
// a floored 1% spread), and cash added back.
f_calculate_apv(fcf, total_debt, cash, tax_rate, unlevered_coe, g_term, shares) =>
    float ku = math.max(unlevered_coe, g_term + 0.01)
    float unlev_firm_val = fcf * (1 + g_term) / (ku - g_term)
    float pv_tax_shield = total_debt * tax_rate
    shares > 0 and fcf > 0 ? (unlev_firm_val + pv_tax_shield - total_debt + nz(cash)) / shares : na
// [FIX EVA] Invested capital + PV(EVA) is FIRM value; subtract net debt for
// equity. Growth is the terminal rate.
f_calculate_eva(nopat, invested_capital, wacc, g_term, net_debt, shares) =>
    float current_eva = nopat - (invested_capital * wacc)
    float pv_eva = (current_eva * (1 + g_term)) / math.max(wacc - g_term, 0.01)
    shares > 0 ? (invested_capital + pv_eva - nz(net_debt)) / shares : na
// ==============================================================
// === ERROR METRIC (SMAPE, MALE, WMAPE, RMSLE) =================
// ==============================================================
// Price arrays vs fair value arrays. Returns [error, usable pairs].
f_get_price_error_metric(hist_fv, hist_px, algo) =>
    float sum_err = 0.0
    float sum_denom = 0.0
    int valid_count = 0
    int n_fv = array.size(hist_fv)
    int n_px = array.size(hist_px)
    int n = math.min(n_fv, n_px)
    if n > 0
        for i = 0 to n - 1 by 1
            float fv_val = array.get(hist_fv, i)
            float px_val = array.get(hist_px, i)
            if not na(fv_val) and not na(px_val) and fv_val > 0 and px_val > 0
                if algo == 'SMAPE'
                    sum_err += math.abs(fv_val - px_val) / ((math.abs(fv_val) + math.abs(px_val)) / 2.0)
                else if algo == 'MALE'
                    sum_err += math.abs(math.log(fv_val) - math.log(px_val))
                else if algo == 'WMAPE'
                    sum_err += math.abs(fv_val - px_val)
                    sum_denom += math.abs(px_val)
                else if algo == 'RMSLE'
                    sum_err += math.pow(math.log(fv_val) - math.log(px_val), 2)
                valid_count += 1
    float final_error = na
    if valid_count > 0
        if algo == 'SMAPE' or algo == 'MALE'
            final_error := sum_err / valid_count
        else if algo == 'WMAPE'
            final_error := sum_denom > 0 ? (sum_err / sum_denom) : na
        else if algo == 'RMSLE'
            final_error := math.sqrt(sum_err / valid_count)
    [final_error, valid_count]
// ==============================================================
// === UNIFIED MODEL WEIGHT (predictive, scale-free) ============
// ==============================================================
// [FIX W-PRED] One rule for every model: how well did the fair value stored
// at quarter i predict the price `horizon` quarters later? Log/relative errors
// only, so a 20 USD and a 20,000 VND quote score alike. Bias counts (MSE, not
// variance). No track record -> 0, never the maximum; callers equal-weight
// when nobody has one.
f_model_weight(array<float> hist_fv, array<float> hist_px, string selected_algo, int horizon) =>
    float weight = 0.0
    int n = math.min(array.size(hist_fv), array.size(hist_px))
    int np = n - horizon
    if np >= 4
        array<float> fv_s = array.slice(hist_fv, 0, np)
        array<float> px_s = array.slice(hist_px, horizon, horizon + np)
        if selected_algo == 'IVW (Error Variance)'
            float sse = 0.0
            int k = 0
            for i = 0 to np - 1
                float f = array.get(fv_s, i)
                float p = array.get(px_s, i)
                if not na(f) and not na(p) and f > 0 and p > 0
                    sse += math.pow(math.log(p / f), 2)
                    k += 1
            if k >= 4
                // Floor = a 5% RMS miss; nothing resolves price tighter.
                weight := 1.0 / math.max(sse / k, 0.0025)
                weight *= math.min(k / 12.0, 1.0)
        else
            string base_algo = str.contains(selected_algo, 'SMAPE') ? 'SMAPE' : str.contains(selected_algo, 'MALE') ? 'MALE' : str.contains(selected_algo, 'WMAPE') ? 'WMAPE' : 'RMSLE'
            [err, kk] = f_get_price_error_metric(fv_s, px_s, base_algo)
            if not na(err) and kk >= 4
                weight := 1.0 / math.max(err, 0.02)
                weight *= math.min(kk / 12.0, 1.0)
    weight
// [FIX TIERS] Down-weight models built on carried or guessed inputs, using
// the provenance tiers (3 reported, 2 exact identity, 1 carried, 0 guess).
f_tier_q(int t) =>
    t >= 3 ? 1.0 : t == 2 ? 0.85 : t == 1 ? 0.6 : 0.3
f_wt_lbl(float w) =>
    w > 0 ? '  [' + str.tostring(w * 100, '#') + '%]' : ''
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
i_auto_calc_erp_crp = input.bool(true, '✨ Auto-Calculate Risk Premiums', group = group_risk, tooltip = 'Calculates ERP and CRP dynamically based on market proxy performance and sovereign bond spread.')
i_erp_manual = input.float(5.0, 'Manual ERP %', group = group_risk) / 100
i_crp_manual = input.float(3.5, 'Manual Country Risk %', group = group_risk) / 100
i_rf_base = input.string('Local 10Y', 'Risk-free base', options = ['Local 10Y', 'US 10Y + CRP'], group = group_risk, tooltip = 'Local 10Y: discount local-currency cash flows at the local sovereign yield. Country risk is already inside that yield, so auto-CRP is 0 (manual CRP is still added when Auto is off).\n\nUS 10Y + CRP: a USD build -- US yield plus the local-minus-US spread (or the manual CRP). Use it when the local curve is thin or administered.')
group_proxies = 'Market Proxy (Used for Beta & Auto-ERP)'
i_mkt_bench = input.symbol('SPY', 'Market Proxy', group = group_proxies)
i_beta_lookback = input.int(104, 'Regression Lookback (periods of the timeframe below)', minval = 30, group = group_proxies)
i_beta_tf = input.timeframe('W', 'Regression Timeframe', group = group_proxies)
group_calc = 'Calculation Parameters'
i_weighting_algo = input.string('IVW (Error Variance)', 'Weighting Algorithm', options = ['IVW (Error Variance)', 'SMAPE (Symmetric Error)', 'MALE (Log Error)', 'WMAPE (Weighted Error)', 'RMSLE (Root Mean Sq Log)'], group = group_calc, tooltip = 'Every model is scored on how well its stored fair value predicted the price N quarters later (see horizon below).\nIVW: inverse mean squared log error.\nSMAPE/MALE/WMAPE/RMSLE: inverse of that error metric.')
i_w_horizon = input.int(4, 'Weighting: forecast horizon (quarters)', minval = 0, maxval = 8, group = group_calc, tooltip = 'Each model is scored on how well its fair value at quarter t predicted the price at t + N. 0 = same-quarter fit.')
i_blend_mode = input.string('Standard (Relative + Sector)', 'Composite Blend Mode', options = ['Standard (Relative + Sector)', 'Omnibus (All Available Models)'], group = group_calc, tooltip = 'Standard: blends the relative multiples and the sector-specific models only. The absolute intrinsic models still render in the table for reference.\n\nOmnibus: blends the Standard composite with every absolute model the Valuation Framework has enabled.')
bool is_omnibus = i_blend_mode == 'Omnibus (All Available Models)'
// ==============================================================
// === OMNIBUS MEMBERSHIP (only read when Blend Mode = Omnibus) ==
// ==============================================================
group_omni = 'Omnibus: Selection'
group_omni_r = 'Omnibus: Relative Multiples'
group_omni_s = 'Omnibus: Sector Models'
group_omni_a = 'Omnibus: Absolute Models'
i_omni_mode = input.string('Auto (Framework Allocation)', 'Member Selection', options = ['Auto (Framework Allocation)', 'Manual (Tick Models Below)'], group = group_omni, tooltip = 'Auto: the Standard Composite as one member, plus whichever absolute models the sector framework enables.\n\nManual: membership is exactly the boxes you tick, across all 23 models.\n\nEither way a member is dropped if its model returns na or a non-positive value. The table row "Omnibus Members" reports what survived.')
i_omni_strict = input.bool(false, 'Manual: still require framework approval', group = group_omni, tooltip = 'ON: a ticked model is used only if the sector framework ALSO allows it.\n\nOFF (default): manual selection overrides the framework.')
i_om_comp = input.bool(true, 'Standard Composite (the whole relative + sector blend)', group = group_omni, tooltip = 'The Standard blend entered as a SINGLE member.\n\nWARNING: it already contains every relative multiple and sector model below. Ticking it alongside any of them counts those models twice. The Omnibus Members row flags this as DOUBLE-COUNT.')
i_omni_sanity_x = input.float(10.0, 'Drop members beyond Nx / (1/N)x price', minval = 0, maxval = 50, step = 1, group = group_omni, tooltip = 'A member whose fair value exceeds N times the current price, or falls below 1/N of it, is excluded.\n\n0 = off. The Standard Composite member is never dropped by this test.')
i_om_pe = input.bool(false, 'Blended P/E', group = group_omni_r, inline = 'r1')
i_om_ps = input.bool(false, 'P/S', group = group_omni_r, inline = 'r1')
i_om_pfcf = input.bool(false, 'P/FCF', group = group_omni_r, inline = 'r2')
i_om_pb = input.bool(false, 'P/B', group = group_omni_r, inline = 'r2')
i_om_ptbv = input.bool(false, 'P/TBV', group = group_omni_r, inline = 'r3')
i_om_ev = input.bool(false, 'Blended EV/EBITDA', group = group_omni_r, inline = 'r3')
i_om_pcf = input.bool(false, 'P/CF', group = group_omni_r, inline = 'r4')
i_om_paffo = input.bool(false, 'P/AFFO', group = group_omni_r, inline = 'r4')
i_om_rnpv = input.bool(false, 'rNPV (Risk-Adjusted)', group = group_omni_s, inline = 's1')
i_om_ecf = input.bool(false, 'Equity Cash Flow', group = group_omni_s, inline = 's1')
i_om_affo = input.bool(false, 'AFFO DCF', group = group_omni_s, inline = 's2')
i_om_unb = input.bool(false, 'Unbundled (SOTP)', group = group_omni_s, inline = 's2')
i_om_apv = input.bool(false, 'Adjusted PV (APV)', group = group_omni_s, inline = 's3')
i_om_eva = input.bool(false, 'Economic Value Added', group = group_omni_s, inline = 's3')
i_om_ddm = input.bool(false, 'Dividend Discount (DDM)', group = group_omni_s)
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
i_sbc_proxy = input.bool(false, 'Subtract Non-cash items as SBC proxy', group = group_calc, tooltip = 'Pine has no stock-based-compensation field. NON_CASH_ITEMS also holds impairments, deferred tax, FX and fair-value moves, so subtracting it from FCF is a guess. Off by default.')
i_flow_ttm = input.bool(true, 'Request flows as TTM', group = group_calc, tooltip = 'Income and cash-flow items are requested as TTM directly instead of summing four FQ values. If a financial ID errors on TTM for your market, switch this off.')
group_iv = 'Intrinsic Value Models (Automated)'
i_analyst_growth = input.float(10.0, 'Analyst Consensus Growth %', group = group_iv) / 100
i_iv_projection_period = input.int(10, 'RIM Projection Period (Years)', group = group_iv, minval = 5, maxval = 20)
i_cagr_years = input.int(3, 'CAGR Lookback Years', group = group_iv, minval = 1, maxval = 10)
i_dcf_stage1_yrs = input.int(10, 'DCF: High-Growth Years (Stage 1)', group = group_iv, minval = 1, maxval = 15, tooltip = 'Used by every DCF-type model: main DCF, rNPV, AFFO DCF, Unbundled ServeCo and ECF.')
i_strict_cap = input.bool(false, 'Strict capital structure', group = group_iv, tooltip = "ON: add minority interest to enterprise value, use common equity (ex-MI) as book value, and use income attributable to common (net of preferred dividends) as the earnings numerator.\n\nThis shifts P/B, EV/EBITDA, Acquirer's Multiple and every earnings multiple.")
group_display = 'Display Options'
i_tableMode = input.string('Full', 'Table Mode', options = ['Full', 'Simple'], group = group_display)
i_tablePos = input.string('top_right', 'Table Position', options = ['top_right', 'middle_right', 'bottom_right'], group = group_display)
i_textSize = input.string('normal', 'Text Size', options = ['auto', 'tiny', 'small', 'normal', 'large', 'huge'], group = group_display)
i_theme = input.string('Dark', 'Theme', options = ['Dark', 'Light'], group = group_display)
group_bt = 'Win Rate Backtester (No-Repaint)'
i_show_bt = input.bool(true, 'Show Backtest Dashboard', group = group_bt)
i_bt_val = input.int(1, 'Holding Period Length', minval = 1, group = group_bt)
i_bt_unit = input.string('Years', 'Time Unit', options = ['Days', 'Weeks', 'Months', 'Years'], group = group_bt)
i_bt_max_open = input.int(0, 'Max Open Tranches (0 = unlimited)', minval = 0, group = group_bt, tooltip = '0 = unlimited (default): every qualifying discount is sampled -- correct for SIGNAL evaluation.\n\nSet 1-5 to simulate a CAPITAL-CONSTRAINED portfolio instead.')
i_bt_margin = input.float(15.0, 'Margin of Safety %', minval = 0, tooltip = 'Buy Signal = Price < FV * (1 - Margin x downside beta), clamped 5-50%. The chart buy line uses the same number.', group = group_bt) / 100
i_bt_exit_premium = input.float(20.0, 'Exit when Price > FV + %', minval = 0, group = group_bt) / 100
i_bt_fees = input.float(0.5, 'Round-trip Fees & Slippage %', group = group_bt, tooltip = 'Deducted from every trade (e.g., 0.5%).') / 100
i_bt_win_threshold = input.float(0.0, 'Min Profit % to count as Win', group = group_bt, tooltip = 'Set to > 0 if you want to ignore tiny gains (e.g., 2%).') / 100
i_report_lag = input.int(45, 'Report lag (days)', minval = 0, maxval = 120, group = group_bt, tooltip = "request.financial returns a quarter's numbers from the START of the next period -- weeks before they were published. Each new value is held back this many days before the script may use it. 0 restores the old (look-ahead) behaviour. The latest value is always released on the last bar.")
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
// =====================================================================
// 3. DATA COLLECTION — REQUEST-BUDGET OPTIMIZED FQ VAULT
// =====================================================================
// REQUEST LEDGER (hard cap = 40 per script)
// request.security      : 4  (US10Y, local 10Y, benchmark, small-cap ETF)
// request.currency_rate : 1
// request.financial     : 31
// TOTAL                 : 36 -> 4 slots free
// (best use of a free slot: request.earnings() for real report dates)
// RULES
// R1. request.security() accepts TUPLES -> unlimited series per slot.
// R2. request.financial() does NOT -> never spend a slot on anything an
// accounting identity can reconstruct exactly.
// R3. Never request.security() the chart's own symbol; aggregate locally.
// =====================================================================
// ---------------------------------------------------------------------
// 3.0 HELPERS
// ---------------------------------------------------------------------
f_locf(val) =>
    var float last_val = na
    if not na(val)
        last_val := val
    last_val
// True on the bar a series first prints a NEW value (na-safe)
f_fresh(float v) =>
    not na(v) and (na(v[1]) or v != v[1])
// Single wrapper for every fundamental pull: 1 request slot per CALL SITE.
// [FIX LOOKAHEAD] A new value is only "known" i_report_lag days after it first
// appears. Stateful per call site (var), so every f_fin() call gates on its own.
f_fin(simple string id, simple string per) =>
    float raw = request.financial(syminfo.tickerid, id, per, ignore_invalid_symbol = true, currency = syminfo.currency)
    var float pending = na
    var float known = na
    var int seen_t = na
    if not na(raw) and (na(pending) or raw != pending)
        pending := raw
        seen_t := time
    if not na(pending) and (time - seen_t >= i_report_lag * 86400000 or barstate.islast)
        known := pending
    known
f_cagr_gen(float now_v, float old_v, float yrs) =>
    float r = na
    if not na(now_v) and not na(old_v) and old_v > 0 and now_v > 0
        r := math.pow(now_v / old_v, 1.0 / yrs) - 1.0
    r
// [FIX 2.4] Provenance tiers: 3 = reported, 2 = exact identity, 1 = carried,
// 0 = heuristic guess (NOT valuation-grade).
f_latch(float mem_in, float val, int tier) =>
    tier >= 2 and not na(val) ? val : mem_in
// ---------------------------------------------------------------------
// 3.1 MACRO TICKER ROUTING
// ---------------------------------------------------------------------
string curr = syminfo.currency
string rf_ticker_auto = 'TVC:US10Y'
if curr == 'VND'
    rf_ticker_auto := 'TVC:VN10Y'
else if curr == 'EUR'
    rf_ticker_auto := 'TVC:DE10Y'
else if curr == 'GBP'
    rf_ticker_auto := 'TVC:GB10Y'
else if curr == 'JPY'
    rf_ticker_auto := 'TVC:JP10Y'
else if curr == 'CNY' or curr == 'HKD'
    rf_ticker_auto := 'TVC:CN10Y'
else if curr == 'INR'
    rf_ticker_auto := 'TVC:IN10Y'
else if curr == 'CAD'
    rf_ticker_auto := 'TVC:CA10Y'
else if curr == 'AUD'
    rf_ticker_auto := 'TVC:AU10Y'
string final_rf_ticker = i_rf_ticker_manual != '' ? i_rf_ticker_manual : rf_ticker_auto
int current_tf_sec = timeframe.in_seconds(timeframe.period) > 0 ? timeframe.in_seconds(timeframe.period) : 86400
// [FIX BPY] Bars per year from the trading calendar, not 365 calendar days.
// A daily stock chart has ~252 bars a year, so "5 years" of 365-bar years
// was ~7.2 years and a "1 year" hold ~1.45.
int trading_days = syminfo.type == 'crypto' ? 365 : 252
int bpy = current_tf_sec < 86400 ? math.max(1, int(math.round(trading_days * 23400.0 / current_tf_sec))) : current_tf_sec < 604800 ? math.max(1, int(math.round(trading_days * 86400.0 / current_tf_sec))) : math.max(1, int(math.round(365.25 * 86400.0 / current_tf_sec)))
// ---------------------------------------------------------------------
// 3.2 MACRO FETCH — TUPLE-PACKED (2 security slots)
// ---------------------------------------------------------------------
// >>> SECURITY SLOT 1/4 : US risk-free curve
[us_spot_r, us_sm_r, us_1y_r] = request.security('TVC:US10Y', 'D', [close, ta.sma(close, 90), close[252]], ignore_invalid_symbol = true)
float us10y_true_raw = f_locf(us_spot_r)
float us10y_smooth = f_locf(us_sm_r)
float us10y_1y_ago = f_locf(us_1y_r)
// >>> SECURITY SLOT 2/4 : Local risk-free curve
[rf_spot_r, rf_sm_r, rf_1y_r] = request.security(final_rf_ticker, 'D', [close, ta.sma(close, 90), close[252]], ignore_invalid_symbol = true)
float local_rf_raw = f_locf(rf_spot_r)
float us10y_yield = f_locf(rf_sm_r) // NOTE: 90d avg of the LOCAL yield; name kept for compatibility
float local_rf_1y = f_locf(rf_1y_r)
// Cascade: thin sovereign curves (VN10Y etc.) frequently print nothing.
if na(local_rf_raw)
    local_rf_raw := us10y_true_raw
if na(us10y_yield)
    us10y_yield := nz(us10y_smooth, local_rf_raw)
if na(local_rf_1y)
    local_rf_1y := us10y_1y_ago
if na(us10y_yield)
    us10y_yield := 4.0
if na(local_rf_raw)
    local_rf_raw := us10y_yield
if na(us10y_true_raw)
    us10y_true_raw := us10y_yield
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
float inflation_rate = lr_infl
float real_gdp_growth = lr_rgdp
// Synthetic CPI index compounding at lr_infl, so the CAPE block (which reads
// cpi_series[offset]) keeps working. Constant-inflation adjustment.
float cpi_raw = math.pow(1 + lr_infl, (time - timestamp(2000, 1, 1)) / (365.25 * 86400000.0))
// =====================================================================
// 3.3 FUNDAMENTAL FETCH — 31 SLOTS
// =====================================================================
// [FIX TTM] Flows are requested as TTM (or FQ + vault when switched off).
string flow_per = i_flow_ttm ? 'TTM' : 'FQ'
// --- INCOME STATEMENT (11) ---
float rev_fq = f_fin('TOTAL_REVENUE', flow_per) // 1
float cogs_fq = f_fin('COST_OF_GOODS', flow_per) // 2
float ebit_fq = f_fin('EBIT', flow_per) // 3
float pretax_fq = f_fin('PRETAX_INCOME', flow_per) // 4
float inc_tax_fq = f_fin('INCOME_TAX', flow_per) // 5
float eps_fq = f_fin('EARNINGS_PER_SHARE_DILUTED', flow_per) // 6
float interest_fq = f_fin('INTEREST_EXPENSE_ON_DEBT', flow_per) // 7
float rnd_fq = f_fin('RESEARCH_AND_DEV', flow_per) // 8
float pref_div_fq = f_fin('PREFERRED_DIVIDENDS', 'FQ') // 9
float div_ps_fq = f_fin('DPS_COMMON_STOCK_PRIM_ISSUE', 'FQ') // 10
float minority_fq = f_fin('MINORITY_INTEREST', 'FQ') // 11
// --- CASH FLOW (4) ---
float ocf_fq = f_fin('CASH_F_OPERATING_ACTIVITIES', flow_per) // 12
float capex_fq = f_fin('CAPITAL_EXPENDITURES', flow_per) // 13
float da_fq = f_fin('CASH_FLOW_DEPRECATION_N_AMORTIZATION', flow_per) // 14
float noncash_fq = f_fin('NON_CASH_ITEMS', flow_per) // 15 (optional SBC proxy)
// --- BALANCE SHEET (15) ---
float shares_dil_fq = f_fin('DILUTED_SHARES_OUTSTANDING', 'FQ') // 16
float shares_basic_fq = f_fin('TOTAL_SHARES_OUTSTANDING', 'FQ') // 17
float total_assets_fq = f_fin('TOTAL_ASSETS', 'FQ') // 18
float total_liab_fq = f_fin('TOTAL_LIABILITIES', 'FQ') // 19
float curr_assets_fq = f_fin('TOTAL_CURRENT_ASSETS', 'FQ') // 20
float curr_liab_fq = f_fin('TOTAL_CURRENT_LIABILITIES', 'FQ') // 21
float total_debt_fq = f_fin('TOTAL_DEBT', 'FQ') // 22
float cash_fq = f_fin('CASH_N_SHORT_TERM_INVEST', 'FQ') // 23
float inventory_fq = f_fin('TOTAL_INVENTORY', 'FQ') // 24
float receiv_fq = f_fin('ACCOUNTS_RECEIVABLES_NET', 'FQ') // 25
float retained_fq = f_fin('RETAINED_EARNINGS', 'FQ') // 26
float ppe_gross_fq = f_fin('PPE_TOTAL_GROSS', 'FQ') // 27
float accum_dep_fq = f_fin('ACCUM_DEPREC_TOTAL', 'FQ') // 28
float goodwill_fq = f_fin('GOODWILL', 'FQ') // 29
float intangibles_fq = f_fin('INTANGIBLES_NET', 'FQ') // 30
// --- FORWARD-LOOKING (1) ---
// [FIX EST] Fiscal-year consensus, not a sum of four quarterly estimates.
float eps_est_fq = f_fin('EARNINGS_ESTIMATE', 'FY') // 31
// ---------------------------------------------------------------------
// 3.4 QUARTER TRIGGER — DEBOUNCED MULTI-WITNESS
// ---------------------------------------------------------------------
int min_gap_bars = math.max(1, int(bpy * 45 / 365.25))
var int last_trig_bar = -100000
bool raw_trigger = f_fresh(rev_fq) or f_fresh(pretax_fq) or f_fresh(total_assets_fq) or f_fresh(eps_fq) or f_fresh(ocf_fq)
bool is_new_quarter = raw_trigger and (bar_index - last_trig_bar) >= min_gap_bars
if is_new_quarter
    last_trig_bar := bar_index
// ---------------------------------------------------------------------
// 3.5 TTM VAULT
// ---------------------------------------------------------------------
// Partial vaults annualize the MEAN of what is held.
f_ttm_vault(float fq_val, bool trigger) =>
    var a = array.new_float(0)
    var float last_valid_val = na
    if not na(fq_val)
        last_valid_val := fq_val
    if trigger or barstate.isfirst
        float val_to_push = not na(fq_val) ? fq_val : last_valid_val
        if not na(val_to_push)
            array.unshift(a, val_to_push)
            if array.size(a) > 4
                array.pop(a)
    float ttm = na
    int n = array.size(a)
    if n > 0
        float s = 0.0
        for i = 0 to n - 1
            s += nz(array.get(a, i))
        ttm := n == 4 ? s : (s / n) * 4.0
    ttm
// TTM request -> hold the value; FQ request -> sum the vault.
f_flow(float x, bool trig) =>
    float vault = f_ttm_vault(x, trig)
    float held = f_locf(x)
    i_flow_ttm ? held : vault
float total_revenue_ttm = f_flow(rev_fq, is_new_quarter)
float cogs_ttm = f_flow(cogs_fq, is_new_quarter)
float ebit_ttm = f_flow(ebit_fq, is_new_quarter)
float pretax_income_ttm = f_flow(pretax_fq, is_new_quarter)
float income_tax_ttm = f_flow(inc_tax_fq, is_new_quarter)
float eps_ttm = f_flow(eps_fq, is_new_quarter)
float interest_expense_ttm = f_flow(interest_fq, is_new_quarter)
float rnd_ttm = f_flow(rnd_fq, is_new_quarter)
float pref_div_ttm = f_ttm_vault(pref_div_fq, is_new_quarter)
float div_per_share_ttm = f_ttm_vault(div_ps_fq, is_new_quarter)
float ocf_ttm = f_flow(ocf_fq, is_new_quarter)
float capex_ttm = f_flow(capex_fq, is_new_quarter)
float depr_amort_ttm_raw = f_flow(da_fq, is_new_quarter)
float noncash_ttm = f_flow(noncash_fq, is_new_quarter)
float eps_est_ttm = f_locf(eps_est_fq)
// =====================================================================
// 3.6 DERIVATION BLOCK — THE RETIRED REQUESTS, REBUILT
// =====================================================================
// (a) GROSS PROFIT = Revenue - COGS
float gp_ttm = not na(total_revenue_ttm) and not na(cogs_ttm) ? total_revenue_ttm - cogs_ttm : na
// (b) SHARES then NET INCOME
float shares_out_latest = not na(shares_dil_fq) and shares_dil_fq > 0 ? shares_dil_fq : shares_basic_fq
float net_income_ttm = not na(pretax_income_ttm) and not na(income_tax_ttm) ? pretax_income_ttm - income_tax_ttm : na
if na(net_income_ttm) and not na(eps_ttm) and not na(shares_out_latest)
    net_income_ttm := eps_ttm * shares_out_latest
// (c) TOTAL EQUITY = Assets - Liabilities [exact identity]
float total_equity_latest = not na(total_assets_fq) and not na(total_liab_fq) ? total_assets_fq - total_liab_fq : na
// (d) EBITDA = EBIT + D&A
float ebitda_ttm = not na(ebit_ttm) and not na(depr_amort_ttm_raw) ? ebit_ttm + depr_amort_ttm_raw : na
// (e) DIVIDEND YIELD = DPS_ttm / price
float div_yield = close > 0 and not na(div_per_share_ttm) ? div_per_share_ttm / close : na
div_yield := f_locf(div_yield)
// (f) [FIX SBC] Optional SBC proxy from non-cash items, clamped to 15% of revenue
float sbc_ttm = i_sbc_proxy ? math.max(nz(noncash_ttm, 0), 0) : 0.0
sbc_ttm := math.min(sbc_ttm, math.max(nz(total_revenue_ttm, 0) * 0.15, 0))
// --- COMPATIBILITY ALIASES ---
float total_debt_latest = total_debt_fq
float cash_latest = cash_fq
float accounts_receivable_fq = receiv_fq
float goodwill_latest = goodwill_fq
float intangibles_latest = intangibles_fq
float cpi_series = cpi_raw
float eps_fy_curr = eps_ttm
float rev_fy = total_revenue_ttm
float accounts_receivable_ttm = f_locf(receiv_fq)
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
// THE QUANT IMPUTATION ENGINE (STRICT ACCOUNTING PIPELINE)
// ==========================================
// --- 1. THE POST-ALGEBRA MEMORY BANKS ---
var float mem_shares = na
var float mem_assets = na
var float mem_debt = na
var float mem_equity = na
var float mem_cash = na
var float mem_ppe_gross = na
var float mem_ppe_net = na
var float mem_rev = na
var float mem_gp = na
var float mem_cogs = na
var float mem_ni = na
var float mem_pretax = na
var float mem_tax = na
var float mem_eps = na
var float mem_ebit = na
var float mem_ebitda = na
var float mem_da = na
var float mem_ocf = na
var float mem_capex = na
var float mem_rec = na
var float mem_curr_assets = na
var float mem_total_liab = na
// --- 2. BASE METRICS (Strict NA Propagation) ---
int t_shares = 0, int t_rev = 0, int t_ni = 0, int t_eps = 0
int t_ebit = 0, int t_ebitda = 0, int t_ocf = 0, int t_assets = 0, int t_equity = 0
float calc_shares = shares_out_latest
t_shares := not na(calc_shares) and calc_shares > 0 ? 3 : 0
// Witness 2: NI / EPS (independent requests)
if na(calc_shares) or calc_shares <= 0
    if not na(net_income_ttm) and not na(eps_ttm) and eps_ttm != 0
        float s2 = net_income_ttm / eps_ttm
        if s2 > 0
            calc_shares := s2
            t_shares := 2
// Witness 3: basic share count
if na(calc_shares) or calc_shares <= 0
    if not na(shares_basic_fq) and shares_basic_fq > 0
        calc_shares := shares_basic_fq
        t_shares := 3
// Witness 4: memory
if na(calc_shares) or calc_shares <= 0
    calc_shares := mem_shares
    t_shares := not na(calc_shares) ? 1 : 0
// Genuine halt: nothing can be valued per-share without a share count.
if na(calc_shares) or calc_shares <= 0
    calc_shares := na
    t_shares := 0
float safe_close = close > 0 ? close : na
float current_mc = safe_close * calc_shares
// --- 3. BALANCE SHEET (Triangles -> Extrapolation -> Lifeline) ---
float calc_assets = total_assets_fq
float calc_debt = total_debt_latest
float calc_equity = total_equity_latest
float calc_cash = cash_latest
float calc_ppe_gross = ppe_gross_fq
float _accum_dep = math.abs(nz(f_locf(accum_dep_fq), na))
float calc_ppe_net = not na(calc_ppe_gross) and not na(_accum_dep) ? math.max(calc_ppe_gross - _accum_dep, 0.0) : (not na(calc_ppe_gross) ? calc_ppe_gross * 0.8 : na)
float calc_rec = f_locf(accounts_receivable_fq)
float calc_curr_assets = curr_assets_fq
float calc_total_liab = total_liab_fq
// Triangle 1: Assets, Debt, Equity
if na(calc_equity) and not na(calc_assets) and not na(calc_total_liab)
    calc_equity := calc_assets - calc_total_liab
else if na(calc_equity) and not na(calc_assets) and not na(calc_debt)
    calc_equity := calc_assets - calc_debt
if na(calc_assets) and not na(calc_equity) and not na(calc_debt)
    calc_assets := calc_equity + calc_debt
if na(calc_debt) and not na(calc_assets) and not na(calc_equity)
    calc_debt := calc_assets - calc_equity
// Triangle 1.5: Total Liabilities Reverse Engineering
if na(calc_total_liab) and not na(calc_assets) and not na(calc_equity)
    calc_total_liab := calc_assets - calc_equity
// Triangle 1.6: Current Assets = Total Assets - (PPE + Goodwill + Intangibles)
if na(calc_curr_assets) and not na(calc_assets)
    float inferred_lt_assets = nz(calc_ppe_net, 0) + nz(goodwill_latest, 0) + nz(intangibles_latest, 0)
    if inferred_lt_assets > 0 and inferred_lt_assets < calc_assets
        calc_curr_assets := calc_assets - inferred_lt_assets
// [AUDIT FIX A] TIER SNAPSHOT.
t_assets := not na(calc_assets) ? 3 : 0
t_equity := not na(calc_equity) ? 3 : 0
// Extrapolation (0% Growth for Balance Sheet items)
if na(calc_assets)
    calc_assets := mem_assets
if na(calc_debt)
    calc_debt := nz(mem_debt, 0)
if na(calc_equity)
    calc_equity := mem_equity
if na(calc_cash)
    calc_cash := mem_cash
if na(calc_ppe_gross)
    calc_ppe_gross := mem_ppe_gross
if na(calc_ppe_net)
    calc_ppe_net := mem_ppe_net
if na(calc_curr_assets)
    calc_curr_assets := mem_curr_assets
if na(calc_total_liab)
    calc_total_liab := mem_total_liab
// --- 4. INCOME STATEMENT (Triangles -> Extrapolation -> Lifeline) ---
float calc_rev = total_revenue_ttm
float calc_cogs = cogs_ttm
float calc_gp = gp_ttm
float calc_ni = net_income_ttm
float calc_pretax = pretax_income_ttm
float calc_tax = income_tax_ttm
float calc_eps = eps_ttm
float calc_ebit = ebit_ttm
float calc_ebitda = ebitda_ttm
float calc_interest = interest_expense_ttm
// [FIX 2.4-b] THE PRICE-TAUTOLOGY FIREBREAK: seed from market cap ONLY when a
// real statement item exists.
bool has_any_real_fundamental = not na(total_assets_fq) or not na(rev_fq) or not na(eps_fq) or not na(ocf_fq)
if not na(calc_shares) and has_any_real_fundamental
    if na(calc_assets) and not na(calc_rev)
        calc_assets := calc_rev * 1.5
        t_assets := 0
    if na(calc_equity) and not na(calc_assets)
        calc_equity := calc_assets - nz(calc_total_liab, nz(calc_debt, 0))
        t_equity := 2
    if na(calc_cash) and not na(calc_assets)
        calc_cash := calc_assets * 0.05
    if na(calc_ppe_gross) and not na(calc_assets)
        calc_ppe_gross := calc_assets * 0.3
    if na(calc_ppe_net) and not na(calc_ppe_gross)
        calc_ppe_net := calc_ppe_gross * 0.8
    if na(calc_rec) and not na(calc_rev)
        calc_rec := calc_rev * 0.1
    if na(calc_total_liab)
        calc_total_liab := nz(calc_assets) - nz(calc_equity)
    if na(calc_curr_assets)
        calc_curr_assets := nz(calc_assets) * 0.40
// Triangle 2: Revenue, GP, COGS
if na(calc_rev) and not na(calc_gp) and not na(calc_cogs)
    calc_rev := calc_gp + calc_cogs
if na(calc_gp) and not na(calc_rev) and not na(calc_cogs)
    calc_gp := calc_rev - calc_cogs
if na(calc_cogs) and not na(calc_rev) and not na(calc_gp)
    calc_cogs := calc_rev - calc_gp
// Triangle 3: NI, Pretax, Tax
if na(calc_ni) and not na(calc_pretax) and not na(calc_tax)
    calc_ni := calc_pretax - calc_tax
if na(calc_pretax) and not na(calc_ni) and not na(calc_tax)
    calc_pretax := calc_ni + calc_tax
if na(calc_tax) and not na(calc_pretax) and not na(calc_ni)
    calc_tax := calc_pretax - calc_ni
// Triangle 4: NI, EPS, Shares
if na(calc_ni) and not na(calc_eps) and not na(calc_shares)
    calc_ni := calc_eps * calc_shares
if na(calc_eps) and not na(calc_ni) and not na(calc_shares)
    calc_eps := calc_ni / calc_shares
// Triangle 5: EBIT, NI, Tax, Interest
if na(calc_ebit) and not na(calc_ni)
    calc_ebit := calc_ni + nz(calc_tax, 0) + nz(calc_interest, 0)
if na(calc_ni) and not na(calc_ebit)
    calc_ni := calc_ebit - nz(calc_tax, 0) - nz(calc_interest, 0)
// [AUDIT FIX B] TIER SNAPSHOT.
t_rev := not na(calc_rev) ? 3 : 0
t_ni := not na(calc_ni) ? 3 : 0
t_eps := not na(calc_eps) ? 3 : 0
t_ebit := not na(calc_ebit) ? 3 : 0
t_ebitda := not na(calc_ebitda) ? 3 : 0
// [FIX 1.3] QUARTER-GATED EXTRAPOLATION (+1% per stale quarter, max 8).
var int bars_since_real = 0
int bars_per_qtr = math.max(1, int(bpy / 4))
float qtrs_stale = bars_since_real / float(bars_per_qtr)
float stale_mult = math.pow(1.01, math.min(qtrs_stale, 8.0))
if is_new_quarter
    bars_since_real := 0
else
    bars_since_real += 1
float ext_growth = stale_mult
if na(calc_rev)
    calc_rev := mem_rev * ext_growth
    t_rev := 1
if na(calc_ni)
    calc_ni := mem_ni * ext_growth
    t_ni := 1
if na(calc_eps) and not na(calc_shares)
    calc_eps := calc_ni / calc_shares
    t_eps := math.min(t_ni, 2)
if na(calc_ebit)
    calc_ebit := mem_ebit * ext_growth
    t_ebit := 1
if na(calc_ebitda)
    calc_ebitda := mem_ebitda * ext_growth
    t_ebitda := 1
// Terminal Lifeline -- gated by the firebreak
if not na(calc_shares) and has_any_real_fundamental
    if na(calc_rev)
        calc_rev := nz(calc_assets) * 0.5
        t_rev := 0
    if na(calc_ni)
        calc_ni := nz(calc_rev) * 0.05
        t_ni := 0
    if na(calc_eps)
        calc_eps := nz(calc_ni) / calc_shares
        t_eps := 0
    if na(calc_ebit)
        calc_ebit := nz(calc_ni) + nz(calc_tax, calc_ni * 0.2) + nz(calc_interest, nz(calc_debt) * 0.05)
        t_ebit := 0
// --- 5. CASH FLOW & D&A (Triangles -> Extrapolation -> Lifeline) ---
float calc_ocf = ocf_ttm
float calc_capex = capex_ttm
float calc_da = depr_amort_ttm_raw
// Triangle 6: D&A Reverse Engineering
if not na(calc_ebitda) and not na(calc_ebit)
    calc_da := calc_ebitda - calc_ebit
else if not na(calc_ocf) and not na(calc_ni)
    calc_da := calc_ocf - calc_ni
// Triangle 7: EBITDA from D&A
if na(calc_ebitda) and not na(calc_ebit) and not na(calc_da)
    calc_ebitda := calc_ebit + calc_da
// Triangle 8: OCF from D&A
if na(calc_ocf) and not na(calc_ni) and not na(calc_da)
    calc_ocf := calc_ni + calc_da
// Triangle 9: CapEx via Change in Net PPE
if na(calc_capex) and not na(calc_ppe_net) and not na(mem_ppe_net) and not na(calc_da)
    calc_capex := -math.abs((calc_ppe_net - mem_ppe_net) + calc_da)
// [AUDIT FIX C] TIER SNAPSHOT.
t_ocf := not na(calc_ocf) ? 3 : 0
if not na(calc_ebitda) and t_ebitda < 2
    t_ebitda := 3
// Extrapolation
if na(calc_da)
    calc_da := mem_da
if na(calc_ebitda)
    calc_ebitda := mem_ebitda * ext_growth
    t_ebitda := 1
if na(calc_ocf)
    calc_ocf := mem_ocf * ext_growth
    t_ocf := 1
if na(calc_capex)
    calc_capex := mem_capex
// Terminal Lifeline -- gated by the firebreak
if not na(calc_shares) and has_any_real_fundamental
    if na(calc_ebitda)
        calc_ebitda := nz(calc_ebit) + (nz(calc_rev) * 0.05)
    if na(calc_da)
        calc_da := nz(calc_ebitda) - nz(calc_ebit)
    if na(calc_ocf)
        calc_ocf := nz(calc_ni) + nz(calc_da)
    if na(calc_capex)
        calc_capex := -nz(calc_da)
// --- 6. OVERRIDE ORIGINAL VARIABLES FOR DOWNSTREAM ---
shares_out_latest := calc_shares
total_revenue_ttm := calc_rev
gp_ttm := calc_gp
cogs_ttm := calc_cogs
accounts_receivable_ttm := calc_rec
// [AUDIT FIX D] Income attributable to common when strict capital structure is on.
net_income_ttm := i_strict_cap ? (calc_ni - nz(pref_div_ttm, 0)) : calc_ni
eps_ttm := calc_eps
ebit_ttm := calc_ebit
ebitda_ttm := calc_ebitda
ocf_ttm := calc_ocf
capex_ttm := calc_capex
total_equity_latest := calc_equity
total_debt_latest := calc_debt
cash_latest := calc_cash
total_assets_fq := calc_assets
ppe_gross_fq := calc_ppe_gross
float ppe_net_fq = calc_ppe_net
float true_fcf = calc_ocf - math.abs(calc_capex) - nz(sbc_ttm, 0)
float fcf_ttm = calc_ocf - math.abs(calc_capex)
float safe_affo = calc_ocf - math.abs(calc_capex)
float net_debt_robust = calc_debt - nz(calc_cash, 0)
// --- 7. UPDATE POST-ALGEBRA MEMORY BANKS ---
// [FIX 2.4-c] Only observed or algebraically exact values (tier >= 2) latch.
mem_shares := f_latch(mem_shares, calc_shares, t_shares)
mem_rev := f_latch(mem_rev, calc_rev, t_rev)
mem_ni := f_latch(mem_ni, calc_ni, t_ni)
mem_eps := f_latch(mem_eps, calc_eps, t_eps)
mem_ebit := f_latch(mem_ebit, calc_ebit, t_ebit)
mem_ebitda := f_latch(mem_ebitda, calc_ebitda, t_ebitda)
mem_ocf := f_latch(mem_ocf, calc_ocf, t_ocf)
mem_assets := f_latch(mem_assets, calc_assets, t_assets)
mem_equity := f_latch(mem_equity, calc_equity, t_equity)
mem_debt := nz(calc_debt, mem_debt)
mem_cash := nz(calc_cash, mem_cash)
mem_ppe_gross := nz(calc_ppe_gross, mem_ppe_gross)
mem_ppe_net := nz(calc_ppe_net, mem_ppe_net)
mem_gp := nz(calc_gp, mem_gp)
mem_cogs := nz(calc_cogs, mem_cogs)
mem_pretax := nz(calc_pretax, mem_pretax)
mem_tax := nz(calc_tax, mem_tax)
mem_da := nz(calc_da, mem_da)
mem_capex := nz(calc_capex, mem_capex)
mem_rec := nz(calc_rec, mem_rec)
mem_curr_assets := nz(calc_curr_assets, mem_curr_assets)
mem_total_liab := nz(calc_total_liab, mem_total_liab)
// =====================================================================
// 3.8 DERIVED SCORES (Altman / Piotroski computed locally)
// =====================================================================
float _ta = calc_assets
float _tl = calc_total_liab
float _ca = calc_curr_assets
float _cl = f_locf(curr_liab_fq)
float _re = f_locf(retained_fq)
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
float _roa = not na(_ta) and _ta > 0 ? nz(calc_ni) / _ta : na
float _roa_prev = ta.valuewhen(is_new_quarter, _roa, 4)
float _cr = not na(_ca) and not na(_cl) and _cl > 0 ? _ca / _cl : na
float _cr_prev = ta.valuewhen(is_new_quarter, _cr, 4)
float _lev = not na(_ta) and _ta > 0 ? nz(calc_debt) / _ta : na
float _lev_prev = ta.valuewhen(is_new_quarter, _lev, 4)
float _gm = not na(calc_rev) and calc_rev > 0 ? nz(calc_gp) / calc_rev : na
float _gm_prev = ta.valuewhen(is_new_quarter, _gm, 4)
float _at = not na(_ta) and _ta > 0 ? nz(calc_rev) / _ta : na
float _at_prev = ta.valuewhen(is_new_quarter, _at, 4)
float _sh_prev = ta.valuewhen(is_new_quarter, calc_shares, 4)
int _f = 0
_f += (not na(_roa) and _roa > 0) ? 1 : 0
_f += (not na(calc_ocf) and calc_ocf > 0) ? 1 : 0
_f += (not na(_roa) and not na(_roa_prev) and _roa > _roa_prev) ? 1 : 0
_f += (not na(calc_ocf) and not na(calc_ni) and calc_ocf > calc_ni) ? 1 : 0
_f += (not na(_lev) and not na(_lev_prev) and _lev < _lev_prev) ? 1 : 0
_f += (not na(_cr) and not na(_cr_prev) and _cr > _cr_prev) ? 1 : 0
_f += (not na(calc_shares) and not na(_sh_prev) and calc_shares <= _sh_prev * 1.001) ? 1 : 0
_f += (not na(_gm) and not na(_gm_prev) and _gm > _gm_prev) ? 1 : 0
_f += (not na(_at) and not na(_at_prev) and _at > _at_prev) ? 1 : 0
float piotroski_f_score = has_any_real_fundamental ? _f * 1.0 : na
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
float safe_rnd = nz(rnd_ttm, 0)
float rnd_1y_ago = ta.valuewhen(is_new_quarter, safe_rnd, 4)
float rnd_2y_ago = ta.valuewhen(is_new_quarter, safe_rnd, 8)
float rnd_3y_ago = ta.valuewhen(is_new_quarter, safe_rnd, 12)
float rnd_amortization = (nz(rnd_1y_ago) + nz(rnd_2y_ago) + nz(rnd_3y_ago)) / 3.0
if rnd_amortization == 0
    rnd_amortization := safe_rnd * 0.8
float effective_tax = pretax_income_ttm > 0 ? math.min(math.max(income_tax_ttm / pretax_income_ttm, 0.0), 0.35) : 0.21
float nopat_adjusted = (ebit_ttm + safe_rnd - rnd_amortization) * (1 - effective_tax)
float working_capital_proxy = nz(f_locf(accounts_receivable_fq), nz(calc_rev) * 0.1) + nz(f_locf(inventory_fq), nz(calc_rev) * 0.1) - nz(calc_rev) * 0.15
float ic_equity_method = total_equity_latest + total_debt_latest - nz(cash_latest, 0)
float invested_capital_adj = total_equity_latest < 0 ? ppe_gross_fq + math.max(working_capital_proxy, 0) : ic_equity_method
// [FIX HGM-2] Invested capital floored at the operating assets deployed.
float ic_operating_floor = math.max(nz(ppe_gross_fq, 0) + math.max(nz(working_capital_proxy, 0), 0), nz(total_assets_fq, 0) * 0.05, 1.0)
invested_capital_adj := math.max(nz(invested_capital_adj, ic_operating_floor), nz(total_debt_latest, 0), ic_operating_floor)
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
// >>> SECURITY SLOT 3/4 : benchmark, non-repainting (close[1] + lookahead_on)
[bench_c] = request.security(final_mkt_bench, beta_tf, [close[1]], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
float mkt_bench_p = f_locf(bench_c)
max_bars_back(asset_p, 500)
max_bars_back(mkt_bench_p, 500)
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
f_get_cagr_optimized(current_price_series, bars_back_5y) =>
    float p_now = current_price_series
    float p_old = current_price_series[bars_back_5y]
    if not na(p_now) and not na(p_old) and p_old > 0
        math.pow(p_now / p_old, 1.0 / 5.0) - 1.0
    else
        0.08
int bars_in_5y = 5 * bpy
cagr_mkt = f_get_cagr_optimized(mkt_bench_p, bars_in_5y)
string auto_small_etf = (curr == 'VND') ? 'HOSE:VNSML' : i_small_etf
// >>> SECURITY SLOT 4/4 : size factor
[small_c] = request.security(auto_small_etf, i_beta_tf, [close], ignore_invalid_symbol = true)
float small_p = f_locf(small_c)
cagr_small = f_get_cagr_optimized(small_p, bars_in_5y)
float live_smb_spread = not na(cagr_small) and not na(cagr_mkt) ? cagr_small - cagr_mkt : 0.02
live_smb_spread := math.max(math.min(live_smb_spread, 0.05), -0.02)
// HML approximation: the value-vs-market spread is roughly half the value-vs-growth spread.
float live_hml_spread = na(small_p) ? 0.015 : (cagr_small - cagr_mkt) * 0.5 + 0.01
live_hml_spread := math.max(math.min(live_hml_spread, 0.05), -0.02)
float auto_erp = math.max(cagr_mkt - (us10y_yield / 100), 0.045) // Floor at 4.5%
yield_local_daily = local_rf_raw
yield_us_daily = us10y_true_raw
float auto_crp_raw = (yield_local_daily > yield_us_daily) ? (yield_local_daily - yield_us_daily) / 100 : 0.0
bool rf_local = i_rf_base == 'Local 10Y'
// [FIX CRP-1] In the local build the spread is already inside the base rate.
float auto_crp = (curr == 'USD' or rf_local) ? 0.0 : auto_crp_raw
float calc_erp = i_auto_calc_erp_crp ? auto_erp : i_erp_manual
float calc_crp = i_auto_calc_erp_crp ? auto_crp : i_crp_manual
// --- Derived Metrics ---
sales_ps_ttm = shares_out_latest > 0 ? total_revenue_ttm / shares_out_latest : na
fcf_ps_ttm = shares_out_latest > 0 ? fcf_ttm / shares_out_latest : na
ocf_ps_ttm = shares_out_latest > 0 ? ocf_ttm / shares_out_latest : na
affo_ttm = safe_affo
affo_ps_ttm = shares_out_latest > 0 ? affo_ttm / shares_out_latest : na
book_value = i_strict_cap ? (nz(total_equity_latest) - nz(minority_fq, 0)) : total_equity_latest
bvps_ttm = shares_out_latest > 0 ? book_value / shares_out_latest : na
tangible_book_value = book_value - nz(goodwill_latest) - nz(intangibles_latest)
tbvps_ttm = shares_out_latest > 0 ? tangible_book_value / shares_out_latest : na
market_cap_latest = close * shares_out_latest
ev_latest = market_cap_latest + nz(net_debt_robust) + (i_strict_cap ? nz(minority_fq, 0) : 0.0)
// === Historical Ratio Calculation ===
// Order is load-bearing: same order in the score loop, blender, table and backtester.
var array<Mult> MULTS = array.from(
     Mult.new('Blended P/E', 15.0, false, false, array.new_float(0), array.new_float(0)),
     Mult.new('P/S', 2.0, false, false, array.new_float(0), array.new_float(0)),
     Mult.new('P/FCF', 15.0, false, false, array.new_float(0), array.new_float(0)),
     Mult.new('P/B', 1.5, false, true, array.new_float(0), array.new_float(0)),
     Mult.new('P/TBV', 2.0, false, false, array.new_float(0), array.new_float(0)),
     Mult.new('Blended EV/EBITDA', 10.0, true, false, array.new_float(0), array.new_float(0)),
     Mult.new('P/CF', 10.0, false, false, array.new_float(0), array.new_float(0)),
     Mult.new('P/AFFO', 12.0, false, false, array.new_float(0), array.new_float(0)))
var array<float> hist_fcf_margins = array.new_float(0)
var array<float> hist_roe = array.new_float(0)
var array<float> hist_op = array.new_float(0)
var int last_ratio_push_bar = -1
bool can_push_ratios = is_new_quarter and bar_index != last_ratio_push_bar
if can_push_ratios
    last_ratio_push_bar := bar_index
if can_push_ratios
    price_at_period_end = close[1]
    ev_hist = price_at_period_end * shares_out_latest[1] + net_debt_robust[1]
    fcf_margin = not na(total_revenue_ttm) and total_revenue_ttm > 0 ? true_fcf / total_revenue_ttm : na
    roe_val = not na(net_income_ttm) and not na(total_equity_latest) and total_equity_latest > 0 ? net_income_ttm / total_equity_latest : na
    op_val = not na(ebit_ttm[1]) and not na(total_equity_latest[1]) and total_equity_latest[1] > 0 ? ebit_ttm[1] / total_equity_latest[1] : na
    // --- RHODES-KROPF (RKV) HISTORICAL FILTER --- (P/B row only, via m.rkv)
    float hist_coe_proxy = (not na(us10y_true_raw[1]) ? us10y_true_raw[1] / 100 : 0.04) + 0.05
    bool rkv_trip = i_use_rkv and not na(roe_val) and roe_val < hist_coe_proxy
    array<float> hdrv = array.from(eps_ttm[1], sales_ps_ttm[1], fcf_ps_ttm[1], bvps_ttm[1], tbvps_ttm[1], na, ocf_ps_ttm[1], affo_ps_ttm[1])
    for k = 0 to 7
        Mult m = array.get(MULTS, k)
        float b = array.get(hdrv, k)
        float r = m.is_ev ? (ebitda_ttm[1] > 0 ? ev_hist / ebitda_ttm[1] : na) : (b > 0 ? price_at_period_end / b : na)
        // [FIX RKV-FLOOR] A low P/B earned by sub-CoE returns is a deserved
        // discount. Flooring it at 1.0 pushed the average P/B UP and made value
        // traps look cheap. Drop the observation instead.
        if m.rkv and rkv_trip and not na(r) and r < 1.2
            r := na
        f_update_ratio_array(m.hist, r, i_numQuarters, i_ratioCap)
        // m.fv here is still last bar's value (this block runs before the loop that assigns it).
        f_push_aligned(m.fvhist, m.fv, 20, 999999)
    f_update_ratio_array(hist_roe, roe_val, 20, 10.0)
    if not na(op_val)
        f_update_ratio_array(hist_op, op_val, 20, 10.0)
    f_update_ratio_array(hist_fcf_margins, fcf_margin, 20, 1.0)
// === Final Calculation ===
float finalFairValue = na
float upperBound = na
float lowerBound = na
string valuation_status = ''
// --- ROLLING BETA ENGINE --- (sampled pairs, see FIX BETA-ALIGN) + Blume adjustment
float beta_rolling = not na(raw_beta_s) ? (0.67 * raw_beta_s) + 0.33 : 1.0
var float beta_mkt = na
beta_mkt := beta_rolling
// 1. Initialize Configuration Flags
bool use_pe = false
bool use_ps = false
bool use_pfcf = false
bool use_pb = false
bool use_ptbv = false
bool use_ev_ebitda = false
bool use_pcf = false
bool use_paffo = false
bool use_dcf = false
bool use_graham = false
bool use_epv = false
bool use_paper_ivm = false
bool use_rule40 = false
bool use_acquirer = false
bool use_oe = false
bool use_rnpv = false
bool use_ecf = false
bool use_affo_dcf = false
bool use_unbundled = false
bool use_apv = false
bool use_eva = false
bool use_ddm = false
bool show_gpa = false
bool show_roic_wacc = false
bool show_sloan = false
bool show_shareholder = false
bool use_cape = false
string active_model_desc = 'General (All Models Active)'
// 2. Resolve the framework
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
// 3. THE ALLOCATION MATRIX
if selected_industry == 'Technology'
    active_model_desc := 'Growth: Rule of 40, DCF & RIM'
    use_pe := true, use_ps := true, use_pfcf := true, use_ev_ebitda := true
    use_dcf := true, use_paper_ivm := true, use_rule40 := true
    show_roic_wacc := true, show_sloan := true, show_shareholder := true
else if selected_industry == 'Healthcare (Pharma/Biotech)'
    active_model_desc := 'rNPV & Pipeline Focus'
    use_pe := true, use_ps := true, use_pfcf := true, use_pb := true, use_ev_ebitda := true
    use_dcf := true, use_epv := true, use_acquirer := true
    use_rnpv := true
    show_roic_wacc := true, show_sloan := true, show_shareholder := true
else if selected_industry == 'Financials (Bank/Insurance)'
    active_model_desc := 'RIM & Equity Cash Flow'
    use_pe := true, use_pb := true, use_ptbv := true
    use_paper_ivm := true, use_graham := true
    use_ecf := true
    show_shareholder := true
else if selected_industry == 'REITs'
    active_model_desc := 'AFFO DCF & Property Multiples'
    use_pb := true, use_ev_ebitda := true, use_pcf := true, use_paffo := true
    use_affo_dcf := true
    show_shareholder := true
else if selected_industry == 'Energy/Materials'
    active_model_desc := 'Cyclically-Adjusted Value (CAPE)'
    use_pe := true, use_pfcf := true, use_pb := true, use_ptbv := true, use_ev_ebitda := true, use_pcf := true
    use_epv := true, use_graham := true, use_acquirer := true, use_oe := true
    use_cape := true
    show_roic_wacc := true, show_shareholder := true
else if selected_industry == 'Capital Goods/Industrials'
    active_model_desc := 'APV & Cyclical Quality'
    use_pe := true, use_pfcf := true, use_pb := true, use_ev_ebitda := true, use_pcf := true
    use_dcf := true, use_epv := true, use_graham := true, use_acquirer := true, use_oe := true
    use_apv := true
    use_cape := true
    show_gpa := true, show_roic_wacc := true, show_sloan := true
else if selected_industry == 'Consumer Staples'
    active_model_desc := 'EVA & ROIC Spread'
    use_pe := true, use_ps := true, use_pfcf := true, use_ev_ebitda := true, use_pcf := true
    use_dcf := true, use_epv := true, use_graham := true, use_acquirer := true, use_oe := true
    use_eva := true
    show_gpa := true, show_roic_wacc := true, show_shareholder := true
else if selected_industry == 'Consumer Discretionary'
    active_model_desc := 'Brand Economics & EVA'
    use_pe := true, use_ps := true, use_pfcf := true, use_ev_ebitda := true, use_pcf := true
    use_dcf := true, use_epv := true, use_graham := true, use_acquirer := true, use_oe := true
    use_eva := true
    use_cape := true
    show_gpa := true, show_roic_wacc := true, show_sloan := true
else if selected_industry == 'Telecom'
    active_model_desc := 'Telecom Unbundling (NetCo + ServeCo)'
    use_pe := true, use_pfcf := true, use_pb := true, use_ev_ebitda := true, use_pcf := true
    use_dcf := true, use_epv := true, use_graham := true, use_acquirer := true, use_oe := true
    use_unbundled := true
    show_roic_wacc := true, show_shareholder := true
else if selected_industry == 'Utilities'
    active_model_desc := 'DDM & Regulated Returns'
    use_pe := true, use_pb := true, use_ev_ebitda := true, use_pcf := true
    use_epv := true, use_paper_ivm := true, use_graham := true, use_acquirer := true, use_oe := true
    use_ddm := true
    show_roic_wacc := true, show_shareholder := true
else
    active_model_desc := 'General (All Models Active)'
    use_pe := true, use_ps := true, use_pfcf := true, use_pb := true, use_ptbv := true
    use_ev_ebitda := true, use_pcf := true, use_paffo := true
    use_dcf := true, use_graham := true, use_epv := true, use_paper_ivm := true
    use_acquirer := true, use_oe := true
    show_gpa := true, show_roic_wacc := true, show_sloan := true, show_shareholder := true
// 4. Define Critical Variables
bool is_financial_sector = selected_industry == 'Financials (Bank/Insurance)'
// 5. Fundamental Metrics
float cash_conv_ratio = na
if not na(ocf_ttm) and not na(eps_ttm) and shares_out_latest > 0
    cash_conv_ratio := ocf_ttm / (eps_ttm * shares_out_latest)
float rev_growth = na
float total_revenue_ttm_prev = ta.valuewhen(is_new_quarter, total_revenue_ttm, 4)
if not na(total_revenue_ttm) and not na(total_revenue_ttm_prev) and total_revenue_ttm_prev != 0
    rev_growth := (total_revenue_ttm - total_revenue_ttm_prev) / math.abs(total_revenue_ttm_prev)
float rec_growth = na
float accounts_receivable_ttm_prev = ta.valuewhen(is_new_quarter, accounts_receivable_ttm, 4)
if not na(accounts_receivable_ttm) and not na(accounts_receivable_ttm_prev) and accounts_receivable_ttm_prev != 0
    rec_growth := (accounts_receivable_ttm - accounts_receivable_ttm_prev) / math.abs(accounts_receivable_ttm_prev)
int eq_score = 0
if not na(cash_conv_ratio)
    eq_score := eq_score + (cash_conv_ratio > 1.2 ? 1 : cash_conv_ratio < 0.8 ? -1 : 0)
if not na(rev_growth)
    eq_score := eq_score + (rev_growth > 0.15 ? 1 : rev_growth < 0 ? -1 : 0)
if not na(rec_growth) and not na(rev_growth)
    eq_score := eq_score + (rec_growth - rev_growth > 0.1 ? -1 : 0)
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
float base_rf_for_calc = rf_local ? us10y_yield / 100 : us10y_true_raw / 100
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
if i_use_factors and current_bm > 0.8
    hml_premium := live_hml_spread * math.min(current_bm, 2.0)
float px_1m_ago = close[math.max(1, int(bpy / 12))]
float px_12m_ago = close[bpy]
float mom_premium = 0.0
float mom_hurdle = (curr == 'VND') ? 0.45 : 0.30
if i_use_factors and not na(px_1m_ago) and not na(px_12m_ago) and px_12m_ago > 0
    float trailing_11m_ret = (px_1m_ago - px_12m_ago) / px_12m_ago
    if trailing_11m_ret > mom_hurdle
        mom_premium := i_mom_prem
    else if trailing_11m_ret < -mom_hurdle
        mom_premium := -i_mom_prem
float microstructure_premium = 0.0
if i_use_factors
    float safe_vol = nz(volume, 1.0)
    float dollar_vol_usd = (close * safe_vol) / fx_rate
    float daily_ret_abs = math.abs(ta.change(close) / nz(close[1], close))
    float amihud_raw = dollar_vol_usd > 0 ? (daily_ret_abs / dollar_vol_usd) * 1e6 : 0.0
    float amihud_90d = ta.sma(amihud_raw, 90)
    float illiq_penalty = 0.0
    if not na(amihud_90d)
        if amihud_90d > 0.5
            illiq_penalty := i_liq_prem
        else if amihud_90d > 0.1
            illiq_penalty := i_liq_prem * (amihud_90d / 0.5)
    float spec_penalty = 0.0
    if not na(volume) and shares_out_latest > 0
        float daily_turnover = volume / shares_out_latest
        float avg_turnover_12m = ta.sma(daily_turnover, 252)
        if avg_turnover_12m > 0.01
            spec_penalty := i_liq_prem * math.min((avg_turnover_12m - 0.01) / 0.01, 1.0)
    microstructure_premium := math.max(illiq_penalty, spec_penalty)
float rmw_premium = 0.0
float current_op = not na(ebit_ttm) and total_equity_latest > 0 ? ebit_ttm / total_equity_latest : 0.0
if i_use_factors
    // [FIX RMW] In Fama-French 5 robust profitability earns a POSITIVE premium:
    // a robust firm loads positively on RMW, so its required return goes up.
    if current_op > 0.20
        rmw_premium := 0.015
    else if current_op < 0.05
        rmw_premium := -0.015
float cost_of_equity = standard_capm_coe + size_premium + hml_premium + mom_premium + rmw_premium + microstructure_premium
float min_equity_return = base_rf_for_calc + 0.03
cost_of_equity := math.max(cost_of_equity, min_equity_return)
float effective_tax_rate = effective_tax // [FIX TAX] same 0-35% clamp as NOPAT
float equity_weight = not na(market_cap_latest) and not na(total_debt_latest) and market_cap_latest + total_debt_latest > 0 ? market_cap_latest / (market_cap_latest + total_debt_latest) : 1.0
float debt_weight = 1.0 - equity_weight
float auto_credit_spread = f_get_synthetic_spread_damodaran(ebit_normalized, interest_expense_ttm)
// [FIX CRP-2] CRP is charged once, in the cost of equity. Debt = same base + synthetic spread.
float cost_of_debt_synthetic = base_rf_for_calc + auto_credit_spread + (rf_local ? 0.0 : calc_crp)
float final_wacc_auto = equity_weight * cost_of_equity + debt_weight * nz(cost_of_debt_synthetic, 0.05) * (1 - effective_tax_rate)
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
float base_profitability = not na(median_roe) and median_roe > 0 ? median_roe : (not na(median_op) and median_op > 0 ? median_op * (1 - effective_tax) : 0.05)
float normalized_sgr = base_profitability * retention_ratio
float sales_cagr_3y = f_calculate_cagr_from_series(total_revenue_ttm, 3)
float effective_sgr = base_profitability > 0 ? normalized_sgr : nz(sales_cagr_3y, 0.05)
float reinvestment_rate = nopat_adjusted > 0 ? (nopat_adjusted - true_fcf) / nopat_adjusted : 0.0
float roic_sgr = math.max(roic_adj * reinvestment_rate, 0.0)
// [MACRO] The CPI/GDP macro adjustment is gone with the feeds.
float base_triangulated_growth = (effective_sgr * 0.15) + (roic_sgr * 0.40) + (i_analyst_growth * 0.15) + (nz(sales_cagr_3y, 0.05) * 0.30)
float final_explicit_growth = base_triangulated_growth
float calc_growth_triangulated = math.min(math.max(final_explicit_growth, -0.10), 0.35)
float dynamic_growth_cap = 0.25
if selected_industry == 'Technology' or selected_industry == 'Healthcare (Pharma/Biotech)' or selected_industry == 'Consumer Discretionary'
    dynamic_growth_cap := 0.40
else if selected_industry == 'Utilities' or selected_industry == 'REITs' or selected_industry == 'Consumer Staples'
    dynamic_growth_cap := 0.15
float final_growth_rate = math.min(calc_growth_triangulated, dynamic_growth_cap)
final_growth_rate := math.max(final_growth_rate, -0.05) // [FIX G-FLOOR] shrinking firms may shrink
float nominal_gdp_ceiling = math.max(nz(us10y_yield / 100, 0.04), inflation_rate + real_gdp_growth)
float unbiased_dynamic_g = inflation_rate + 0.005
unbiased_dynamic_g := math.max(unbiased_dynamic_g, 0.015)
unbiased_dynamic_g := math.min(unbiased_dynamic_g, 0.035)
float final_terminal_growth = math.min(unbiased_dynamic_g, nominal_gdp_ceiling)
float cyclically_adjusted_eps = na
if use_cape
    float total_inflation_adj_eps = 0.0
    int valid_eps_count = 0
    if array.size(f_series_to_array(cpi_series, 1)) > 0
        float current_cpi = cpi_series[0]
        for i = 0 to 9 by 1
            int offset = i * bpy
            if offset < bar_index and offset < 2999
                float historical_eps = eps_fy_curr[offset]
                float historical_cpi = cpi_series[offset]
                if not na(historical_eps) and not na(historical_cpi) and historical_cpi > 0
                    total_inflation_adj_eps := total_inflation_adj_eps + historical_eps * (current_cpi / historical_cpi)
                    valid_eps_count := valid_eps_count + 1
        if valid_eps_count > 0
            cyclically_adjusted_eps := total_inflation_adj_eps / valid_eps_count
// Multiples: one cached, single-sort call per multiple. Bear/Bull come from
// THIS ticker's own ratio history.
bool rs_dirty = can_push_ratios or barstate.isfirst
earnings_base = use_cape and not na(cyclically_adjusted_eps) ? cyclically_adjusted_eps : eps_ttm
eps_f1_proj = not na(final_growth_rate) ? earnings_base * (1 + final_growth_rate) : na
float sales_cagr = nz(f_calculate_cagr_from_series(total_revenue_ttm, i_cagr_years), 0.05)
float final_sales_f1 = total_revenue_ttm * (1 + sales_cagr)
float ebitda_margin_ttm = total_revenue_ttm > 0 ? ebitda_ttm / total_revenue_ttm : na
float est_ebitda_fwd = not na(final_sales_f1) and not na(ebitda_margin_ttm) ? final_sales_f1 * ebitda_margin_ttm : na
float sh_ev = math.max(shares_out_latest, 1)
array<float> drvs = array.from(earnings_base, sales_ps_ttm, fcf_ps_ttm, bvps_ttm, tbvps_ttm, ebitda_ttm, ocf_ps_ttm, affo_ps_ttm)
array<float> drvs_f = array.from(eps_f1_proj, na, na, na, na, est_ebitda_fwd, na, na)
array<bool> ons = array.from(use_pe, use_ps, use_pfcf, use_pb, use_ptbv, use_ev_ebitda, use_pcf, use_paffo)
array<bool> guards = array.from(eps_ttm > 0, true, fcf_ttm > 0, true, true, true, true, true)
for k = 0 to 7
    Mult m = array.get(MULTS, k)
    m.drv := array.get(drvs, k)
    m.drv_f := array.get(drvs_f, k)
    m.on := array.get(ons, k) and array.get(guards, k)
    if rs_dirty
        [a, sy, plo, phi] = f_ratio_stats(m.hist, i_useMean, m.dflt, i_scen_lo_pct, i_scen_hi_pct, i_scen_min_n)
        m.avg := a, m.syn := sy, m.plo := plo, m.phi := phi
    m.fv := f_blend2(f_apply(m.drv, m.avg, m.is_ev, net_debt_robust, sh_ev), f_apply(m.drv_f, m.avg, m.is_ev, net_debt_robust, sh_ev))
    m.lo := f_blend2(f_apply(m.drv, m.plo, m.is_ev, net_debt_robust, sh_ev), f_apply(m.drv_f, m.plo, m.is_ev, net_debt_robust, sh_ev))
    m.hi := f_blend2(f_apply(m.drv, m.phi, m.is_ev, net_debt_robust, sh_ev), f_apply(m.drv_f, m.phi, m.is_ev, net_debt_robust, sh_ev))
Mult M_PE = array.get(MULTS, 0), Mult M_PS = array.get(MULTS, 1)
Mult M_PFCF = array.get(MULTS, 2), Mult M_PB = array.get(MULTS, 3)
Mult M_PTBV = array.get(MULTS, 4), Mult M_EV = array.get(MULTS, 5)
Mult M_PCF = array.get(MULTS, 6), Mult M_PAFFO = array.get(MULTS, 7)
float blended_fv_pe = M_PE.fv
float fv_ps = M_PS.fv, float fv_pfcf = M_PFCF.fv, float fv_pb = M_PB.fv
float fv_ptbv = M_PTBV.fv, float blended_fv_ev_ebitda = M_EV.fv
float fv_pcf = M_PCF.fv, float fv_paffo = M_PAFFO.fv
// ==============================================================
// === SECTOR-SPECIFIC MODELS ===================================
// ==============================================================
float fv_ecf = na, float fv_rnpv = na, float fv_ddm = na
float fv_affo_dcf = na, float fv_unbundled = na, float fv_apv = na, float fv_eva = na
float fv_ecf_lo = na, float fv_ecf_hi = na, float fv_rnpv_lo = na, float fv_rnpv_hi = na
float fv_ddm_lo = na, float fv_ddm_hi = na, float fv_affo_lo = na, float fv_affo_hi = na
float fv_unb_lo = na, float fv_unb_hi = na, float fv_apv_lo = na, float fv_apv_hi = na
float fv_eva_lo = na, float fv_eva_hi = na
float wacc_bear = final_wacc_auto + i_scen_wacc_bps
float wacc_bull = math.max(final_wacc_auto - i_scen_wacc_bps, 0.02)
float coe_bear = cost_of_equity + i_scen_wacc_bps
float coe_bull = math.max(cost_of_equity - i_scen_wacc_bps, 0.02)
float tg_bear = math.max(final_terminal_growth - i_scen_g_bps, 0.0)
float tg_bull = final_terminal_growth + i_scen_g_bps
// [FIX SCEN-G] Bear/Bull also move stage-1 growth.
float g_bear = math.max(final_growth_rate - i_scen_growth_bps, -0.05)
float g_bull = math.min(final_growth_rate + i_scen_growth_bps, dynamic_growth_cap)
float unlevered_beta = beta_mkt / (1 + ((1 - effective_tax) * (total_debt_latest / math.max(total_equity_latest, 1.0))))
float unlevered_coe = base_rf_for_calc + (unlevered_beta * calc_erp)
float total_debt_1y_ago = ta.valuewhen(is_new_quarter, total_debt_latest, 4)
if use_rnpv
    float nopat_ps_r = nopat_adjusted / math.max(shares_out_latest, 1)
    // [FIX G-CLAMP] final_growth_rate (clamped) instead of the raw final_explicit_growth.
    [base_dcf, rnpv_mult] = f_calculate_dcf_value_driver_extended(fcf_ps_ttm, nopat_ps_r, roic_adj, final_wacc_auto, final_growth_rate, final_terminal_growth, i_dcf_stage1_yrs)
    fv_rnpv := f_calculate_rnpv_sotp(base_dcf, nz(rnd_ttm), shares_out_latest)
    [bd_lo, m_lo] = f_calculate_dcf_value_driver_extended(fcf_ps_ttm, nopat_ps_r, roic_adj, wacc_bear, g_bear, tg_bear, i_dcf_stage1_yrs)
    [bd_hi, m_hi] = f_calculate_dcf_value_driver_extended(fcf_ps_ttm, nopat_ps_r, roic_adj, wacc_bull, g_bull, tg_bull, i_dcf_stage1_yrs)
    fv_rnpv_lo := f_calculate_rnpv_sotp(bd_lo, nz(rnd_ttm), shares_out_latest)
    fv_rnpv_hi := f_calculate_rnpv_sotp(bd_hi, nz(rnd_ttm), shares_out_latest)
if use_ecf
    // [FIX IND-3] No prior-year debt -> assume flat, not zero.
    float ecf_debt_prev = nz(total_debt_1y_ago, nz(total_debt_latest, 0))
    float ecf_nb = nz(total_debt_latest, 0) - ecf_debt_prev
    fv_ecf := f_calculate_ecf(net_income_ttm, calc_da, capex_ttm, ecf_nb, cost_of_equity, final_growth_rate, final_terminal_growth, i_dcf_stage1_yrs, shares_out_latest)
    fv_ecf_lo := f_calculate_ecf(net_income_ttm, calc_da, capex_ttm, ecf_nb, coe_bear, g_bear, tg_bear, i_dcf_stage1_yrs, shares_out_latest)
    fv_ecf_hi := f_calculate_ecf(net_income_ttm, calc_da, capex_ttm, ecf_nb, coe_bull, g_bull, tg_bull, i_dcf_stage1_yrs, shares_out_latest)
if use_affo_dcf
    [affo_dcf_val, affo_mult] = f_calculate_dcf_value_driver_extended(affo_ps_ttm, affo_ps_ttm, roic_adj, cost_of_equity, final_growth_rate, final_terminal_growth, i_dcf_stage1_yrs)
    fv_affo_dcf := affo_dcf_val
    [affo_lo_v, affo_lo_m] = f_calculate_dcf_value_driver_extended(affo_ps_ttm, affo_ps_ttm, roic_adj, coe_bear, g_bear, tg_bear, i_dcf_stage1_yrs)
    [affo_hi_v, affo_hi_m] = f_calculate_dcf_value_driver_extended(affo_ps_ttm, affo_ps_ttm, roic_adj, coe_bull, g_bull, tg_bull, i_dcf_stage1_yrs)
    fv_affo_lo := affo_lo_v
    fv_affo_hi := affo_hi_v
if use_unbundled
    float netco_ppe = nz(ppe_net_fq) * 0.80
    float netco_debt = nz(net_debt_robust) * 0.80
    float netco_value = f_calculate_rab_model(netco_ppe, i_rab_allowed_return, final_wacc_auto, final_terminal_growth, netco_debt, shares_out_latest)
    float serveco_fcf = true_fcf * 0.60
    float sc_ps = serveco_fcf / math.max(shares_out_latest, 1)
    float np_ps = nopat_adjusted / math.max(shares_out_latest, 1)
    [serveco_value, serveco_mult] = f_calculate_dcf_value_driver_extended(sc_ps, np_ps, roic_adj, cost_of_equity, final_growth_rate, final_terminal_growth, i_dcf_stage1_yrs)
    fv_unbundled := netco_value + serveco_value
    float netco_lo = f_calculate_rab_model(netco_ppe, i_rab_allowed_return, wacc_bear, tg_bear, netco_debt, shares_out_latest)
    float netco_hi = f_calculate_rab_model(netco_ppe, i_rab_allowed_return, wacc_bull, tg_bull, netco_debt, shares_out_latest)
    [sv_lo, sm_lo] = f_calculate_dcf_value_driver_extended(sc_ps, np_ps, roic_adj, coe_bear, g_bear, tg_bear, i_dcf_stage1_yrs)
    [sv_hi, sm_hi] = f_calculate_dcf_value_driver_extended(sc_ps, np_ps, roic_adj, coe_bull, g_bull, tg_bull, i_dcf_stage1_yrs)
    fv_unb_lo := nz(netco_lo) + nz(sv_lo)
    fv_unb_hi := nz(netco_hi) + nz(sv_hi)
if use_apv
    fv_apv := f_calculate_apv(true_fcf, nz(total_debt_latest), nz(cash_latest), effective_tax, unlevered_coe, final_terminal_growth, shares_out_latest)
    fv_apv_lo := f_calculate_apv(true_fcf, nz(total_debt_latest), nz(cash_latest), effective_tax, unlevered_coe + i_scen_wacc_bps, tg_bear, shares_out_latest)
    fv_apv_hi := f_calculate_apv(true_fcf, nz(total_debt_latest), nz(cash_latest), effective_tax, math.max(unlevered_coe - i_scen_wacc_bps, 0.02), tg_bull, shares_out_latest)
if use_eva
    fv_eva := f_calculate_eva(nopat_adjusted, invested_capital_adj, final_wacc_auto, final_terminal_growth, net_debt_robust, shares_out_latest)
    fv_eva_lo := f_calculate_eva(nopat_adjusted, invested_capital_adj, wacc_bear, tg_bear, net_debt_robust, shares_out_latest)
    fv_eva_hi := f_calculate_eva(nopat_adjusted, invested_capital_adj, wacc_bull, tg_bull, net_debt_robust, shares_out_latest)
if use_ddm
    fv_ddm := f_calculate_ddm(div_per_share_ttm, cost_of_equity, final_terminal_growth)
    fv_ddm_lo := f_calculate_ddm(div_per_share_ttm, coe_bear, tg_bear)
    fv_ddm_hi := f_calculate_ddm(div_per_share_ttm, coe_bull, tg_bull)
// ==============================================================
// === HISTORICAL TRACKERS (FOR ALL SECTOR & OMNIBUS MODELS) ====
// ==============================================================
float iv_graham = na
float iv_buffett_dcf = na
float iv_epv = na
float iv_paper = na
float iv_rule40 = na
float implied_exit_multiple = na
float compositeFairValue = na
float compositeLo = na
float compositeHi = na
float iv_acquirer = na
float iv_acq_lo = na
float iv_acq_hi = na
float fv_stddev = na
float iv_owners_earnings = na
float iv_oe_lo = na
float iv_oe_hi = na
var array<float> hist_px_tracker = array.new_float(0)
var array<float> hist_fv_rnpv = array.new_float(0)
var array<float> hist_fv_ecf = array.new_float(0)
var array<float> hist_fv_affo_dcf = array.new_float(0)
var array<float> hist_fv_unbundled = array.new_float(0)
var array<float> hist_fv_apv = array.new_float(0)
var array<float> hist_fv_eva = array.new_float(0)
var array<float> hist_fv_ddm = array.new_float(0)
var array<float> hist_iv_comp = array.new_float(0)
var array<float> hist_iv_dcf = array.new_float(0)
var array<float> hist_iv_paper = array.new_float(0)
var array<float> hist_iv_epv = array.new_float(0)
var array<float> hist_iv_graham = array.new_float(0)
var array<float> hist_iv_rule40 = array.new_float(0)
var array<float> hist_iv_acquirer = array.new_float(0)
var array<float> hist_iv_oe = array.new_float(0)
var int last_iv_push_bar = -1
bool can_push_iv = is_new_quarter and bar_index != last_iv_push_bar
if can_push_iv
    last_iv_push_bar := bar_index
if can_push_iv
    f_push_aligned(hist_px_tracker, close[1], 20, 999999)
    f_push_aligned(hist_fv_rnpv, fv_rnpv[1], 20, 999999)
    f_push_aligned(hist_fv_ecf, fv_ecf[1], 20, 999999)
    f_push_aligned(hist_fv_affo_dcf, fv_affo_dcf[1], 20, 999999)
    f_push_aligned(hist_fv_unbundled, fv_unbundled[1], 20, 999999)
    f_push_aligned(hist_fv_apv, fv_apv[1], 20, 999999)
    f_push_aligned(hist_fv_eva, fv_eva[1], 20, 999999)
    f_push_aligned(hist_fv_ddm, fv_ddm[1], 20, 999999)
    f_push_aligned(hist_iv_comp, compositeFairValue[1], 20, 999999)
    f_push_aligned(hist_iv_dcf, iv_buffett_dcf[1], 20, 999999)
    f_push_aligned(hist_iv_paper, iv_paper[1], 20, 999999)
    f_push_aligned(hist_iv_epv, iv_epv[1], 20, 999999)
    f_push_aligned(hist_iv_graham, iv_graham[1], 20, 999999)
    f_push_aligned(hist_iv_rule40, iv_rule40[1], 20, 999999)
    f_push_aligned(hist_iv_acquirer, iv_acquirer[1], 20, 999999)
    f_push_aligned(hist_iv_oe, iv_owners_earnings[1], 20, 999999)
// ==============================================================
// === UNIFIED WEIGHTING ENGINE =================================
// ==============================================================
// Provenance of each model's main input. Same order as MULTS.
array<int> mult_tier = array.from(t_eps, t_rev, t_ocf, t_equity, t_equity, t_ebitda, t_ocf, t_ocf)
for k = 0 to 7
    Mult m = array.get(MULTS, k)
    m.score := m.on and not na(m.fv) and m.fv > 0 ? f_model_weight(m.fvhist, hist_px_tracker, i_weighting_algo, i_w_horizon) * f_tier_q(array.get(mult_tier, k)) : 0.0
f_sector_w(float fv, array<float> h, array<float> px, int tier) =>
    not na(fv) and fv > 0 ? f_model_weight(h, px, i_weighting_algo, i_w_horizon) * f_tier_q(tier) : 0.0
float s_rnpv = f_sector_w(fv_rnpv, hist_fv_rnpv, hist_px_tracker, t_ocf)
float s_ecf = f_sector_w(fv_ecf, hist_fv_ecf, hist_px_tracker, t_ni)
float s_affo_dcf = f_sector_w(fv_affo_dcf, hist_fv_affo_dcf, hist_px_tracker, t_ocf)
float s_unbundled = f_sector_w(fv_unbundled, hist_fv_unbundled, hist_px_tracker, t_ocf)
float s_apv = f_sector_w(fv_apv, hist_fv_apv, hist_px_tracker, t_ocf)
float s_eva = f_sector_w(fv_eva, hist_fv_eva, hist_px_tracker, t_ebit)
float s_ddm = f_sector_w(fv_ddm, hist_fv_ddm, hist_px_tracker, 3)
float total_weighted_value = 0.0
float total_weighted_lo = 0.0
float total_weighted_hi = 0.0
array<float> valid_fvs_for_stddev = array.new_float(0)
// 15 blend slots: 8 multiples, then 7 sector models.
array<float> blend_sc = array.from(s_rnpv, s_ecf, s_affo_dcf, s_unbundled, s_apv, s_eva, s_ddm)
array<float> blend_bv = array.from(fv_rnpv, fv_ecf, fv_affo_dcf, fv_unbundled, fv_apv, fv_eva, fv_ddm)
array<float> blend_lo = array.from(fv_rnpv_lo, fv_ecf_lo, fv_affo_lo, fv_unb_lo, fv_apv_lo, fv_eva_lo, fv_ddm_lo)
array<float> blend_hi = array.from(fv_rnpv_hi, fv_ecf_hi, fv_affo_hi, fv_unb_hi, fv_apv_hi, fv_eva_hi, fv_ddm_hi)
array<float> blend_tq = array.from(f_tier_q(t_ocf), f_tier_q(t_ni), f_tier_q(t_ocf), f_tier_q(t_ocf), f_tier_q(t_ocf), f_tier_q(t_ebit), 1.0)
array<bool> blend_on = array.from(use_rnpv, use_ecf, use_affo_dcf, use_unbundled, use_apv, use_eva, use_ddm)
for k = 7 to 0
    Mult m = array.get(MULTS, k)
    array.unshift(blend_sc, m.score)
    array.unshift(blend_bv, m.fv)
    array.unshift(blend_lo, m.lo)
    array.unshift(blend_hi, m.hi)
    array.unshift(blend_tq, f_tier_q(array.get(mult_tier, k)))
    array.unshift(blend_on, m.on)
// [FIX NEG] Negative or na values never enter the blend.
// Weight 0 = no track record yet. If NO model has one (young listing), fall
// back to equal weights x provenance instead of printing no fair value.
float blend_sc_sum = 0.0
for i = 0 to 14
    float b_i = array.get(blend_bv, i)
    if not na(b_i) and b_i > 0
        blend_sc_sum += array.get(blend_sc, i)
bool blend_eq = blend_sc_sum <= 0
array<float> blend_w = array.new_float(15, 0.0)
float blend_w_tot = 0.0
for i = 0 to 14
    float b_i = array.get(blend_bv, i)
    float w_i = 0.0
    if not na(b_i) and b_i > 0
        w_i := blend_eq ? (array.get(blend_on, i) ? array.get(blend_tq, i) : 0.0) : array.get(blend_sc, i)
    array.set(blend_w, i, w_i)
    blend_w_tot += w_i
if blend_w_tot > 0
    for i = 0 to 14
        float w_i = array.get(blend_w, i)
        if w_i > 0
            float b = array.get(blend_bv, i)
            float w = w_i / blend_w_tot
            array.set(blend_w, i, w) // normalised share, read by the table
            total_weighted_value += b * w
            total_weighted_lo += math.max(nz(array.get(blend_lo, i), b), 0.0) * w
            total_weighted_hi += nz(array.get(blend_hi, i), b) * w
            array.push(valid_fvs_for_stddev, b)
    compositeFairValue := total_weighted_value
    compositeLo := total_weighted_lo
    compositeHi := total_weighted_hi
if array.size(valid_fvs_for_stddev) > 1
    fv_stddev := array.stdev(valid_fvs_for_stddev)
else if not na(compositeFairValue)
    fv_stddev := compositeFairValue * 0.15
// ==========================================
// RHODES-KROPF (RKV) M/B DECOMPOSITION & VALUE TRAP DETECTION
// ==========================================
float rkv_mispricing_mv = na
float rkv_growth_vb = na
bool is_rkv_value_trap = false
bool is_rkv_deep_value = false
float current_pb_val = bvps_ttm > 0 ? close / bvps_ttm : na
if i_use_rkv and not na(compositeFairValue) and not na(bvps_ttm) and bvps_ttm > 0 and compositeFairValue > 0
    rkv_mispricing_mv := close / compositeFairValue
    rkv_growth_vb := compositeFairValue / bvps_ttm
    if current_pb_val < 1.5
        if rkv_growth_vb < 1.0
            is_rkv_value_trap := true
        else if rkv_mispricing_mv < 0.85
            is_rkv_deep_value := true
// ==========================================
// BENEISH M-SCORE (5-Variable Adjusted)
// ==========================================
float rec_t = accounts_receivable_ttm
float rec_prev = ta.valuewhen(is_new_quarter, rec_t, 4)
float rev_t = total_revenue_ttm
float rev_prev = ta.valuewhen(is_new_quarter, rev_t, 4)
float cogs_t = cogs_ttm
float cogs_prev = ta.valuewhen(is_new_quarter, cogs_t, 4)
float debt_t = total_debt_latest
float debt_prev = ta.valuewhen(is_new_quarter, debt_t, 4)
float assets_t = total_assets_fq
float assets_prev = ta.valuewhen(is_new_quarter, assets_t, 4)
bool is_manipulator = false
float m_score = na
if i_useBeneishCheck
    float dsri = (rec_t / rev_t) / (rec_prev / rev_prev)
    float gm_t = rev_t - cogs_t
    float gm_prev = rev_prev - cogs_prev
    float gmi = (gm_prev / rev_prev) / (gm_t / rev_t)
    float sgi = rev_t / rev_prev
    float lvgi = (debt_t / assets_t) / math.max((debt_prev / assets_prev), 0.001)
    float tata = (net_income_ttm - ocf_ttm) / assets_t
    dsri := math.min(math.max(dsri, 0.5), 3.0)
    gmi := math.min(math.max(gmi, 0.5), 3.0)
    sgi := math.min(math.max(sgi, 0.5), 3.0)
    lvgi := math.min(math.max(lvgi, 0.5), 3.0)
    m_score := -4.49 + (0.920 * dsri) + (0.528 * gmi) + (0.892 * sgi) + (4.679 * tata) - (0.327 * lvgi)
    is_manipulator := m_score > -1.78
// Provisional only; bands and verdict are resolved after the Omnibus.
finalFairValue := compositeFairValue
string _fin_ind = syminfo.industry
bool fin_bank_like = (str.contains(_fin_ind, 'Banks') and not str.contains(_fin_ind, 'Brokers')) or str.contains(_fin_ind, 'Insurance')
bool use_bank_model = is_financial_sector and (i_financial_model_type == 'Equity Model (Bank/Insurer)' or (i_financial_model_type == 'Auto (by industry)' and fin_bank_like))
float rim_nopat_proxy = use_bank_model ? net_income_ttm : nopat_adjusted
float rim_capital_proxy = use_bank_model ? total_equity_latest : invested_capital_adj
float rim_discount_proxy = use_bank_model ? math.min(cost_of_equity, 0.15) : final_discount_rate
float rim_debt_proxy = use_bank_model ? 0.0 : net_debt_robust
float rim_growth_proxy = math.max(final_growth_rate, 0.02)
// 1. EPV (Greenwald)
float epv_firm = nopat_adjusted / math.max(final_discount_rate, 0.01)
float epv_equity = epv_firm - net_debt_robust
iv_epv := epv_equity / shares_out_latest
float iv_epv_lo = (nopat_adjusted / math.max(final_discount_rate + i_scen_wacc_bps, 0.01) - net_debt_robust) / shares_out_latest
float iv_epv_hi = (nopat_adjusted / math.max(final_discount_rate - i_scen_wacc_bps, 0.02) - net_debt_robust) / shares_out_latest
// 2. Residual Income Model
iv_paper := f_calculate_rim(rim_nopat_proxy, rim_capital_proxy, shares_out_latest, rim_debt_proxy, rim_discount_proxy, rim_growth_proxy, final_terminal_growth, i_iv_projection_period)
float iv_paper_lo = f_calculate_rim(rim_nopat_proxy, rim_capital_proxy, shares_out_latest, rim_debt_proxy, rim_discount_proxy + i_scen_wacc_bps, rim_growth_proxy, math.max(final_terminal_growth - i_scen_g_bps, 0.0), i_iv_projection_period)
float iv_paper_hi = f_calculate_rim(rim_nopat_proxy, rim_capital_proxy, shares_out_latest, rim_debt_proxy, math.max(rim_discount_proxy - i_scen_wacc_bps, 0.02), rim_growth_proxy, final_terminal_growth + i_scen_g_bps, i_iv_projection_period)
float nopat_ps = nopat_adjusted / shares_out_latest
float true_fcf_ps = true_fcf / shares_out_latest
// 3. Extended Value Driver DCF
[dcf_val, exit_mult] = f_calculate_dcf_value_driver_extended(true_fcf_ps, nopat_ps, roic_adj, math.max(final_discount_rate, 0.01), final_growth_rate, final_terminal_growth, i_dcf_stage1_yrs)
iv_buffett_dcf := dcf_val
implied_exit_multiple := exit_mult
[dcf_lo_v, dcf_lo_m] = f_calculate_dcf_value_driver_extended(true_fcf_ps, nopat_ps, roic_adj, math.max(final_discount_rate + i_scen_wacc_bps, 0.01), g_bear, math.max(final_terminal_growth - i_scen_g_bps, 0.0), i_dcf_stage1_yrs)
[dcf_hi_v, dcf_hi_m] = f_calculate_dcf_value_driver_extended(true_fcf_ps, nopat_ps, roic_adj, math.max(final_discount_rate - i_scen_wacc_bps, 0.02), g_bull, final_terminal_growth + i_scen_g_bps, i_dcf_stage1_yrs)
float iv_dcf_lo = dcf_lo_v
float iv_dcf_hi = dcf_hi_v
// 4. Reverse DCF (Market Implied Growth)
float median_fcf_margin = nz(f_median(hist_fcf_margins), 0.10)
float dcf_input_fcf_total_rev = total_revenue_ttm * median_fcf_margin
float implied_market_growth = f_calculate_reverse_dcf(close, dcf_input_fcf_total_rev, shares_out_latest, math.max(final_discount_rate, 0.01), final_terminal_growth, 10)
float true_fcf_margin_ttm = true_fcf / total_revenue_ttm
// 5. RULE OF 40
float safe_rev_growth = not na(rev_growth) ? rev_growth : 0.10
iv_rule40 := f_calculate_rule_of_x_fv(safe_rev_growth, true_fcf_margin_ttm, total_revenue_ttm, net_debt_robust, shares_out_latest)
float iv_r40_lo = f_calculate_rule_of_x_fv(math.max(safe_rev_growth - i_scen_r40_bps, 0.0), true_fcf_margin_ttm, total_revenue_ttm, net_debt_robust, shares_out_latest)
float iv_r40_hi = f_calculate_rule_of_x_fv(safe_rev_growth + i_scen_r40_bps, true_fcf_margin_ttm, total_revenue_ttm, net_debt_robust, shares_out_latest)
// 6. GRAHAM NUMBER
// [FIX GRAHAM] No revenue-based EPS fallback: Graham needs real positive earnings.
float base_eps = eps_ttm > 0 ? eps_ttm : na
float safe_us10y = us10y_yield > 0 ? us10y_yield : 4.0
// 4.4 / Y rescales for bond yields. Below 4.4% it multiplied value UP (x4.4
// at a 1% yield), so it is capped at 1.0: it may only penalise high yields.
float graham_yield_adj = math.min(4.4 / safe_us10y, 1.0)
// Graham meant a 7-10 year growth rate; cap at 15% so the 2g term cannot run away.
float graham_g = math.max(math.min(final_growth_rate, 0.15), 0.0)
iv_graham := base_eps * (8.5 + 2 * graham_g * 100) * graham_yield_adj
float iv_graham_lo = base_eps * (8.5 + 2 * (graham_g * 0.5) * 100) * graham_yield_adj
float iv_graham_hi = base_eps * (8.5 + 2 * (graham_g * 1.5) * 100) * graham_yield_adj
// ==============================================================
// 🌟 THE ACQUIRER'S MULTIPLE (EV / EBIT)
// ==============================================================
if ebit_ttm > 0 and shares_out_latest > 0
    float target_ev_acquirer = ebit_ttm * i_acquirer_mult
    float target_equity_acquirer = target_ev_acquirer - net_debt_robust
    iv_acquirer := target_equity_acquirer / shares_out_latest
    iv_acq_lo := (ebit_ttm * math.max(i_acquirer_mult - i_scen_acq_delta, 1.0) - net_debt_robust) / shares_out_latest
    iv_acq_hi := (ebit_ttm * (i_acquirer_mult + i_scen_acq_delta) - net_debt_robust) / shares_out_latest
float oe_per_share = na
float maint_capex_est = na
if not na(ppe_gross_fq) and not na(rev_fy) and rev_fy > 0 and not na(total_revenue_ttm) and not na(total_revenue_ttm_prev)
    float ppe_ratio = ppe_gross_fq / rev_fy
    float sales_growth_abs = total_revenue_ttm - total_revenue_ttm_prev
    float growth_capex = sales_growth_abs * ppe_ratio
    float abs_total_capex = math.abs(capex_ttm)
    growth_capex := math.max(0, growth_capex)
    growth_capex := math.min(growth_capex, abs_total_capex)
    maint_capex_est := abs_total_capex - growth_capex
    float owners_earnings = ocf_ttm - maint_capex_est
    oe_per_share := shares_out_latest > 0 ? owners_earnings / shares_out_latest : na
    if owners_earnings > 0 and final_discount_rate > 0
        iv_owners_earnings := oe_per_share / final_discount_rate
        iv_oe_lo := oe_per_share / math.max(final_discount_rate + i_scen_wacc_bps, 0.01)
        iv_oe_hi := oe_per_share / math.max(final_discount_rate - i_scen_wacc_bps, 0.02)
// =======================================================
// 🛡️ ZERO-BOUND CLAMPS
// =======================================================
iv_epv := iv_epv > 0 ? iv_epv : na
iv_paper := iv_paper > 0 ? iv_paper : na
iv_buffett_dcf := iv_buffett_dcf > 0 ? iv_buffett_dcf : na
iv_rule40 := iv_rule40 > 0 ? iv_rule40 : na
iv_graham := iv_graham > 0 ? iv_graham : na
iv_owners_earnings := iv_owners_earnings > 0 ? iv_owners_earnings : na
iv_acquirer := iv_acquirer > 0 ? iv_acquirer : na
fv_rnpv := fv_rnpv > 0 ? fv_rnpv : na
fv_ecf := fv_ecf > 0 ? fv_ecf : na
fv_affo_dcf := fv_affo_dcf > 0 ? fv_affo_dcf : na
fv_unbundled := fv_unbundled > 0 ? fv_unbundled : na
fv_apv := fv_apv > 0 ? fv_apv : na
fv_eva := fv_eva > 0 ? fv_eva : na
fv_ddm := fv_ddm > 0 ? fv_ddm : na
finalFairValue := finalFairValue > 0 ? finalFairValue : na
// ==============================================================
// === GRAND MASTER BLEND (Multi-Algo Smart Omnibus) ============
// ==============================================================
var array<Omni> OMNI = array.from(
     Omni.new('Standard Composite', hist_iv_comp),
     Omni.new('Blended P/E', M_PE.fvhist),
     Omni.new('P/S', M_PS.fvhist),
     Omni.new('P/FCF', M_PFCF.fvhist),
     Omni.new('P/B', M_PB.fvhist),
     Omni.new('P/TBV', M_PTBV.fvhist),
     Omni.new('Blended EV/EBITDA', M_EV.fvhist),
     Omni.new('P/CF', M_PCF.fvhist),
     Omni.new('P/AFFO', M_PAFFO.fvhist),
     Omni.new('rNPV (Risk-Adjusted)', hist_fv_rnpv),
     Omni.new('Equity Cash Flow', hist_fv_ecf),
     Omni.new('AFFO DCF', hist_fv_affo_dcf),
     Omni.new('Unbundled (SOTP)', hist_fv_unbundled),
     Omni.new('Adjusted PV (APV)', hist_fv_apv),
     Omni.new('Economic Value Added', hist_fv_eva),
     Omni.new('Dividend Discount', hist_fv_ddm),
     Omni.new('DCF (McKinsey/ROIC)', hist_iv_dcf),
     Omni.new('Residual Income (RIM)', hist_iv_paper),
     Omni.new('EPV (Greenwald)', hist_iv_epv),
     Omni.new('Graham', hist_iv_graham),
     Omni.new('Rule of 40', hist_iv_rule40),
     Omni.new('Acquirer Multiple', hist_iv_acquirer),
     Omni.new('Owners Earnings', hist_iv_oe))
array<float> omni_bv = array.from(compositeFairValue, M_PE.fv, M_PS.fv, M_PFCF.fv, M_PB.fv, M_PTBV.fv, M_EV.fv, M_PCF.fv, M_PAFFO.fv, fv_rnpv, fv_ecf, fv_affo_dcf, fv_unbundled, fv_apv, fv_eva, fv_ddm, iv_buffett_dcf, iv_paper, iv_epv, iv_graham, iv_rule40, iv_acquirer, iv_owners_earnings)
array<float> omni_bl = array.from(compositeLo, M_PE.lo, M_PS.lo, M_PFCF.lo, M_PB.lo, M_PTBV.lo, M_EV.lo, M_PCF.lo, M_PAFFO.lo, fv_rnpv_lo, fv_ecf_lo, fv_affo_lo, fv_unb_lo, fv_apv_lo, fv_eva_lo, fv_ddm_lo, iv_dcf_lo, iv_paper_lo, iv_epv_lo, iv_graham_lo, iv_r40_lo, iv_acq_lo, iv_oe_lo)
array<float> omni_bh = array.from(compositeHi, M_PE.hi, M_PS.hi, M_PFCF.hi, M_PB.hi, M_PTBV.hi, M_EV.hi, M_PCF.hi, M_PAFFO.hi, fv_rnpv_hi, fv_ecf_hi, fv_affo_hi, fv_unb_hi, fv_apv_hi, fv_eva_hi, fv_ddm_hi, iv_dcf_hi, iv_paper_hi, iv_epv_hi, iv_graham_hi, iv_r40_hi, iv_acq_hi, iv_oe_hi)
array<bool> omni_fw = array.from(true, M_PE.on, M_PS.on, M_PFCF.on, M_PB.on, M_PTBV.on, M_EV.on, M_PCF.on, M_PAFFO.on, use_rnpv, use_ecf, use_affo_dcf, use_unbundled, use_apv, use_eva, use_ddm, use_dcf, use_paper_ivm, use_epv, use_graham, use_rule40, use_acquirer, use_oe)
// Auto: indices 1-15 are already inside the Composite at index 0.
array<bool> omni_auto = array.from(true, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, use_dcf, use_paper_ivm, use_epv, use_graham, use_rule40, use_acquirer, use_oe)
array<bool> omni_mn = array.from(i_om_comp, i_om_pe, i_om_ps, i_om_pfcf, i_om_pb, i_om_ptbv, i_om_ev, i_om_pcf, i_om_paffo, i_om_rnpv, i_om_ecf, i_om_affo, i_om_unb, i_om_apv, i_om_eva, i_om_ddm, i_om_dcf, i_om_rim, i_om_epv, i_om_graham, i_om_r40, i_om_acq, i_om_oe)
// Provenance factor per member (same weighting rule as the Standard blend).
array<float> omni_tq = array.from(1.0)
for k = 0 to 14
    array.push(omni_tq, array.get(blend_tq, k))
for t in array.from(t_ocf, t_ni, t_ebit, t_eps, t_rev, t_ebit, t_ocf)
    array.push(omni_tq, f_tier_q(t))
bool omni_manual = i_omni_mode == 'Manual (Tick Models Below)'
bool omni_sane_on = i_omni_sanity_x >= 1.5 and close > 0
float omni_v_sum = 0.0, float omni_lo_sum = 0.0, float omni_hi_sum = 0.0, float omni_w_sum = 0.0
float omni_eq_v = 0.0, float omni_eq_lo = 0.0, float omni_eq_hi = 0.0
int omni_n = 0, int omni_sub = 0
bool omni_comp_on = false
array<float> omni_vals = array.new_float(0)
for k = 0 to 22
    Omni o = array.get(OMNI, k)
    float v = array.get(omni_bv, k)
    bool ok = omni_manual ? array.get(omni_mn, k) and (not i_omni_strict or array.get(omni_fw, k)) : array.get(omni_auto, k)
    bool sane = not omni_sane_on or k == 0 or (not na(v) and v <= close * i_omni_sanity_x and v * i_omni_sanity_x >= close)
    o.on := ok and not na(v) and v > 0 and sane
    o.fv := o.on ? v : na
    o.lo := o.on ? nz(array.get(omni_bl, k), v) : na
    o.hi := o.on ? nz(array.get(omni_bh, k), v) : na
    float wk = o.on ? f_model_weight(o.hist, hist_px_tracker, i_weighting_algo, i_w_horizon) * array.get(omni_tq, k) : 0.0
    o.w := wk
    if o.on
        omni_n += 1
        if k == 0
            omni_comp_on := true
        else if k <= 15
            omni_sub += 1
        omni_eq_v += o.fv, omni_eq_lo += o.lo, omni_eq_hi += o.hi
        array.push(omni_vals, o.fv)
        omni_v_sum += o.fv * o.w, omni_lo_sum += o.lo * o.w, omni_hi_sum += o.hi * o.w, omni_w_sum += o.w
bool omni_dupe = omni_comp_on and omni_sub > 0
float raw_omnibus_fv = na, float raw_omnibus_lo = na, float raw_omnibus_hi = na
if omni_w_sum > 0
    raw_omnibus_fv := omni_v_sum / omni_w_sum
    raw_omnibus_lo := omni_lo_sum / omni_w_sum
    raw_omnibus_hi := omni_hi_sum / omni_w_sum
else if omni_n > 0
    raw_omnibus_fv := omni_eq_v / omni_n
    raw_omnibus_lo := omni_eq_lo / omni_n
    raw_omnibus_hi := omni_eq_hi / omni_n
float omni_stddev = array.size(omni_vals) > 1 ? array.stdev(omni_vals) : na
bool omni_active = is_omnibus and not na(raw_omnibus_fv) and raw_omnibus_fv > 0
if omni_active
    finalFairValue := raw_omnibus_fv
    compositeLo := raw_omnibus_lo
    compositeHi := raw_omnibus_hi
    fv_stddev := nz(omni_stddev, raw_omnibus_fv * 0.15)
// ==============================================================
// === RESOLVE: BANDS + VERDICT (after the blend is final) ======
// ==============================================================
upperBound := na(finalFairValue) ? na : finalFairValue + nz(fv_stddev, finalFairValue * 0.15)
lowerBound := na(finalFairValue) ? na : finalFairValue - nz(fv_stddev, finalFairValue * 0.15)
upperBound := upperBound > 0 ? upperBound : na
lowerBound := lowerBound > 0 ? lowerBound : na
float fv_band = math.max(nz(finalFairValue, 0) * 0.03, 0.0)
if close > upperBound and not na(upperBound)
    valuation_status := 'Very Overvalued'
else if close > finalFairValue + fv_band
    valuation_status := 'Overvalued'
else if close < lowerBound and not na(lowerBound)
    valuation_status := 'Very Undervalued'
else if close < finalFairValue - fv_band
    valuation_status := 'Undervalued'
else
    valuation_status := 'Fairly Valued'
// ==============================================================
// ⚙️ QUANTITATIVE QUALITY & MANAGEMENT RATIOS
// ==============================================================
float raw_shares_prev = ta.valuewhen(is_new_quarter, calc_shares, 4)
float raw_debt_prev = ta.valuewhen(is_new_quarter, calc_debt, 4)
float raw_assets_prev = ta.valuewhen(is_new_quarter, calc_assets, 4)
float safe_shares_prev = not na(raw_shares_prev) ? raw_shares_prev : calc_shares
float safe_debt_prev = not na(raw_debt_prev) ? raw_debt_prev : nz(calc_debt, 0)
float safe_assets_prev = not na(raw_assets_prev) and raw_assets_prev > 0 ? raw_assets_prev : calc_assets
float gpa_ratio = not na(calc_assets) and calc_assets > 0 ? nz(calc_gp, 0) / calc_assets : na
float roic_wacc_spread = not na(roic_adj) and not na(final_discount_rate) ? roic_adj - final_discount_rate : na
float croic_val = not na(invested_capital_adj) and invested_capital_adj > 0 ? nz(true_fcf, 0) / invested_capital_adj : na
float sloan_ratio = not na(calc_assets) and calc_assets > 0 ? (nz(calc_ni, 0) - nz(calc_ocf, 0)) / calc_assets : na
float buyback_yield = safe_shares_prev > 0 ? (safe_shares_prev - calc_shares) / safe_shares_prev : 0.0
float debt_paydown_yield = not na(current_mc) and current_mc > 0 ? (safe_debt_prev - nz(calc_debt, 0)) / current_mc : 0.0
float shareholder_yield = nz(div_yield, 0.0) + math.max(buyback_yield, 0.0) + math.max(debt_paydown_yield, 0.0)
float safe_asset_growth = safe_assets_prev > 0 ? (calc_assets - safe_assets_prev) / safe_assets_prev : 0.0
bool show_croic = false
bool show_asset_growth = false
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
f_scen_txt(float v) =>
    na(v) or v <= 0 ? '-' : str.tostring(math.round(v))
// GREEN price below this case | AMBER within the band | RED price above it.
f_scen_col(float v, float px, bool is_base) =>
    color out = color_bg
    if not na(v) and v > 0
        float dev = px / v - 1
        if math.abs(dev) <= i_scen_fair_band
            out := is_base ? color.new(color.orange, 15) : color.new(color.orange, 40)
        else if dev > 0
            out := is_base ? color.new(color.red, 15) : color_over
        else
            out := is_base ? color.new(color.green, 15) : color_under
    out
// Bear | Base | Bull | vs Price, in one call.
f_model_row(tbl, int row, string label, float lo, float base, float hi, string tt) =>
    float v = na(base) or base <= 0 ? na : (close / base - 1) * 100
    string vtxt = na(v) ? '' : '\n\nPrice vs Base: ' + (v > 0 ? '+' : '') + str.tostring(math.round(v)) + '%'
    table.cell(tbl, 0, row, label, text_color = color_text, bgcolor = color_bg, text_size = i_textSize, tooltip = tt + vtxt)
    f_cell(tbl, 1, row, f_scen_txt(lo), color_text, f_scen_col(lo, close, false), i_textSize)
    f_cell(tbl, 2, row, na(base) ? 'N/A' : str.tostring(math.round(base)), color.white, f_scen_col(base, close, true), i_textSize)
    f_cell(tbl, 3, row, f_scen_txt(hi), color_text, f_scen_col(hi, close, false), i_textSize)
f_mult_tt(float avgr, float curr, float plo, float phi) =>
    'Avg ratio (base): ' + str.tostring(avgr, '#.##') + 'x\nCurrent: ' + (na(curr) ? 'N/A' : str.tostring(curr, '#.##') + 'x') +
         '\n\nBear multiple: ' + (na(plo) ? 'n/a' : str.tostring(plo, '#.##') + 'x') +
         '\nBull multiple: ' + (na(phi) ? 'n/a' : str.tostring(phi, '#.##') + 'x') +
         "\n\nBear/Bull are percentiles of this ticker's own stored ratio history applied to the same per-share base. Blank = too few observations.\n[xx%] = weight in the Standard blend."
if barstate.islast
    var table T = table.new(position.top_right, 4, 60, border_width = 1)
    table.set_position(T, i_tablePos == 'top_right' ? position.top_right : i_tablePos == 'middle_right' ? position.middle_right : position.bottom_right)
    table.clear(T, start_column = 0, start_row = 0, end_column = 3, end_row = 59)
    table.cell(table_id = T, column = 0, row = 0, text = active_model_desc + ' [REAL-TIME]', text_color = color.white, bgcolor = color.new(color.purple, 20), text_size = i_textSize)
    table.cell(table_id = T, column = 1, row = 0, text = '', text_color = color.white, bgcolor = color.new(color.purple, 20), text_size = i_textSize)
    table.cell(table_id = T, column = 2, row = 0, text = '', text_color = color.white, bgcolor = color.new(color.purple, 20), text_size = i_textSize)
    table.cell(table_id = T, column = 3, row = 0, text = '', text_color = color.white, bgcolor = color.new(color.purple, 20), text_size = i_textSize)
    array<float> cur_mult = array.new_float(0)
    for k = 0 to 7
        Mult m = array.get(MULTS, k)
        array.push(cur_mult, m.drv > 0 ? (m.is_ev ? ev_latest : close) / m.drv : na)
    int row_idx = 1
    if i_tableMode == 'Full'
        table.cell(T, 0, row_idx, 'Relative Valuation', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        table.cell(T, 1, row_idx, 'Bear', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        table.cell(T, 2, row_idx, 'Base', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        table.cell(T, 3, row_idx, 'Bull', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        row_idx := row_idx + 1
        for k = 0 to 7
            Mult m = array.get(MULTS, k)
            if m.on and not na(m.fv) and m.fv > 0
                f_model_row(T, row_idx, m.name + (m.syn ? ' *' : '') + f_wt_lbl(array.get(blend_w, k)), m.lo, m.fv, m.hi, (m.syn ? 'SYNTHETIC: fewer than 4 quarters of history, so the base multiple is a default, not observed.\n\n' : '') + f_mult_tt(m.avg, array.get(cur_mult, k), m.plo, m.phi))
                row_idx := row_idx + 1
    table.cell(table_id = T, column = 0, row = row_idx, text = 'Intrinsic Models', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 1, row = row_idx, text = 'Bear', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 2, row = row_idx, text = 'Base', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 3, row = row_idx, text = 'Bull', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    row_idx := row_idx + 1
    if use_paper_ivm
        f_model_row(T, row_idx, 'Intrinsic Value (RIM)', iv_paper_lo, iv_paper, iv_paper_hi, '')
        row_idx := row_idx + 1
    if use_rule40
        float r40_score = not na(rev_growth) and not na(true_fcf_margin_ttm) ? (rev_growth + true_fcf_margin_ttm) * 100 : 0.0
        float rule_x_display_score = not na(rev_growth) and not na(true_fcf_margin_ttm) ? ((rev_growth * 2.0) + true_fcf_margin_ttm) * 100 : 0.0
        bool is_super_stock = rule_x_display_score >= 65
        string label_text = is_super_stock ? '🌟 Rule of 65 (Super Stock)' : 'Rule of 40 Value'
        string label_tooltip = is_super_stock ? 'Rule of 65 Score: ' + str.tostring(rule_x_display_score, '#.#') + '%\n(Hyper-Growth Premium Unlocked!)' : 'Rule of 40 Score: ' + str.tostring(r40_score, '#.#') + '%'
        f_model_row(T, row_idx, label_text, iv_r40_lo, iv_rule40, iv_r40_hi, label_tooltip)
        row_idx := row_idx + 1
    if use_graham
        f_model_row(T, row_idx, 'Graham', iv_graham_lo, iv_graham, iv_graham_hi, 'Needs positive EPS. Growth capped at 15%; the 4.4/Y bond-yield factor is capped at 1.0.')
        row_idx := row_idx + 1
    if use_acquirer and not na(iv_acquirer)
        f_model_row(T, row_idx, "Acquirer's Mult (" + str.tostring(i_acquirer_mult) + "x EBIT)", iv_acq_lo, iv_acquirer, iv_acq_hi, 'Bear/Bull shift the EBIT multiple by +/-' + str.tostring(i_scen_acq_delta) + 'x.')
        row_idx := row_idx + 1
    if use_dcf
        f_model_row(T, row_idx, 'DCF (McKinsey/ROIC)', iv_dcf_lo, iv_buffett_dcf, iv_dcf_hi, 'Bear/Bull move the discount rate, terminal growth AND stage-1 growth.')
        row_idx := row_idx + 1
    if use_epv
        f_model_row(T, row_idx, 'EPV (Greenwald)', iv_epv_lo, iv_epv, iv_epv_hi, '')
        row_idx := row_idx + 1
    if use_rnpv and not na(fv_rnpv)
        f_model_row(T, row_idx, 'rNPV (Risk-Adj)' + f_wt_lbl(array.get(blend_w, 8)), fv_rnpv_lo, fv_rnpv, fv_rnpv_hi, '')
        row_idx := row_idx + 1
    if use_ecf and not na(fv_ecf)
        f_model_row(T, row_idx, 'Equity Cash Flow' + f_wt_lbl(array.get(blend_w, 9)), fv_ecf_lo, fv_ecf, fv_ecf_hi, 'Two-stage FCFE: NI + D&A - CapEx + net borrowing.')
        row_idx := row_idx + 1
    if use_affo_dcf and not na(fv_affo_dcf)
        f_model_row(T, row_idx, 'AFFO DCF' + f_wt_lbl(array.get(blend_w, 10)), fv_affo_lo, fv_affo_dcf, fv_affo_hi, '')
        row_idx := row_idx + 1
    if use_unbundled and not na(fv_unbundled)
        f_model_row(T, row_idx, 'Unbundled (SOTP)' + f_wt_lbl(array.get(blend_w, 11)), fv_unb_lo, fv_unbundled, fv_unb_hi, '')
        row_idx := row_idx + 1
    if use_apv and not na(fv_apv)
        f_model_row(T, row_idx, 'Adjusted PV (APV)' + f_wt_lbl(array.get(blend_w, 12)), fv_apv_lo, fv_apv, fv_apv_hi, 'Steady-state APV at terminal growth, plus tax shield, less debt, plus cash.')
        row_idx := row_idx + 1
    if use_eva and not na(fv_eva)
        f_model_row(T, row_idx, 'Economic Value Added' + f_wt_lbl(array.get(blend_w, 13)), fv_eva_lo, fv_eva, fv_eva_hi, 'Invested capital + PV(EVA) - net debt.')
        row_idx := row_idx + 1
    if use_ddm and not na(fv_ddm)
        float ddm_yield = close > 0 and not na(div_per_share_ttm) ? div_per_share_ttm / close * 100 : na
        string ddm_tt = 'Gordon growth on the trailing dividend.\nDPS: ' + str.tostring(div_per_share_ttm, '#.##') + '\nYield: ' + (na(ddm_yield) ? 'N/A' : str.tostring(ddm_yield, '#.##') + '%') + '\nCost of equity: ' + str.tostring(cost_of_equity * 100, '#.#') + '%\nTerminal growth: ' + str.tostring(final_terminal_growth * 100, '#.#') + '%'
        f_model_row(T, row_idx, 'Dividend Discount (DDM)' + f_wt_lbl(array.get(blend_w, 14)), fv_ddm_lo, fv_ddm, fv_ddm_hi, ddm_tt)
        row_idx := row_idx + 1
    table.cell(table_id = T, column = 0, row = row_idx, text = 'Composite', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 1, row = row_idx, text = 'Bear', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 2, row = row_idx, text = 'Base', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 3, row = row_idx, text = 'Bull', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    row_idx := row_idx + 1
    string composite_label = omni_active ? 'Omnibus FV (' + str.tostring(omni_n) + '/23 models)' : is_omnibus ? 'Standard FV (Omnibus unavailable)' : (selected_industry == 'General/Diversified' ? 'Overall Relative Value' : 'Industry Relative Value')
    color valuation_color = valuation_status == 'Overvalued' or valuation_status == 'Very Overvalued' ? color_over : valuation_status == 'Undervalued' or valuation_status == 'Very Undervalued' ? color_under : color_bg
    float variance_pct = na(finalFairValue) ? na : (close / finalFairValue - 1) * 100
    string comp_tt = (blend_eq ? 'No model has a predictive track record yet, so the blend is EQUAL-WEIGHTED (x data-quality tier).\n\n' : 'Weights = inverse error of each model\'s fair value against the price ' + str.tostring(i_w_horizon) + ' quarters later, x data-quality tier.\n\n') + 'Bear/Bull are the same weights applied to each model\'s own bear and bull case.' + (na(variance_pct) ? '' : '\n\nPrice vs Base: ' + (variance_pct > 0 ? '+' : '') + str.tostring(math.round(variance_pct)) + '%')
    f_model_row(T, row_idx, composite_label, compositeLo, finalFairValue, compositeHi, comp_tt)
    row_idx := row_idx + 1
    float band_w = not na(compositeLo) and not na(compositeHi) and not na(finalFairValue) and finalFairValue > 0 ? (compositeHi - compositeLo) / finalFairValue * 100 : na
    f_cell(T, 0, row_idx, 'Price vs Fair Value', color_text, color_header, i_textSize)
    f_cell(T, 1, row_idx, na(variance_pct) ? 'N/A' : (variance_pct > 0 ? '+' : '') + str.tostring(math.round(variance_pct)) + '%', na(variance_pct) ? color_text : variance_pct > 0 ? color.red : color.green, color_bg, i_textSize)
    f_cell(T, 2, row_idx, valuation_status, color_text, valuation_color, i_textSize)
    f_cell(T, 3, row_idx, na(band_w) ? 'N/A' : 'Width ' + str.tostring(math.round(band_w)) + '%', na(band_w) ? color_text : band_w < 30 ? color.green : band_w < 60 ? color.orange : color.red, color_bg, i_textSize)
    row_idx := row_idx + 1
    if is_omnibus
        string omni_tt = omni_n == 0 ? 'No member survived gating, so the row above is the Standard composite, not an Omnibus value.' : (omni_w_sum > 0 ? 'Share of the blend. Weight = inverse prediction error against price ' + str.tostring(i_w_horizon) + ' quarters later, x data-quality tier.\n\n' : 'No member has 4+ paired quarters yet, so this is a plain equal-weight mean.\n\n')
        if omni_dupe
            omni_tt += 'WARNING: the Standard Composite is in the blend alongside ' + str.tostring(omni_sub) + ' of the models it already contains. Those are counted twice.\n\n'
        for k = 0 to 22
            Omni o = array.get(OMNI, k)
            if o.on
                omni_tt += o.name + '  ' + str.tostring(omni_w_sum > 0 ? o.w / omni_w_sum * 100 : 100.0 / omni_n, '#.#') + '%\n'
        f_cell(T, 0, row_idx, 'Omnibus Members', color_text, color_header, i_textSize)
        table.cell(T, 1, row_idx, str.tostring(omni_n) + ' / 23', text_color = omni_dupe ? color.orange : omni_n >= 3 ? color.green : omni_n > 0 ? color.orange : color.red, bgcolor = color_bg, text_size = i_textSize, tooltip = omni_tt)
        f_cell(T, 2, row_idx, omni_manual ? (i_omni_strict ? 'Manual (strict)' : 'Manual') : 'Auto', color_text, color_bg, i_textSize)
        f_cell(T, 3, row_idx, omni_n == 0 ? 'INACTIVE' : omni_dupe ? 'DOUBLE-COUNT' : omni_w_sum > 0 ? 'Weighted' : 'Equal wt', omni_n == 0 ? color.red : omni_dupe ? color.orange : color_text, color_bg, i_textSize)
        row_idx := row_idx + 1
    // ================= DIAGNOSTICS ==================
    table.cell(table_id = T, column = 0, row = row_idx, text = 'Diagnostics', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 1, row = row_idx, text = 'Value', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 2, row = row_idx, text = 'Detail', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    table.cell(table_id = T, column = 3, row = row_idx, text = 'Status', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
    row_idx := row_idx + 1
    float nd_ebitda = not na(ebitda_ttm) and ebitda_ttm > 0 ? nz(net_debt_robust, 0) / ebitda_ttm : na
    string nd_txt = 'N/A'
    color nd_col = color_bg
    if not na(nd_ebitda)
        if nd_ebitda < 0
            nd_txt := 'Net Cash'
            nd_col := color_under
        else if nd_ebitda <= 1.5
            nd_txt := 'Conservative'
            nd_col := color_under
        else if nd_ebitda <= 3.0
            nd_txt := 'Moderate'
            nd_col := color_bg
        else if nd_ebitda <= 4.5
            nd_txt := 'Elevated'
            nd_col := color.new(color.orange, 40)
        else
            nd_txt := 'High'
            nd_col := color_over
    string nd_tt = 'Net debt as a multiple of TTM EBITDA.\n\n<0 net cash | <1.5 conservative | 1.5-3 moderate | 3-4.5 elevated | >4.5 high.\n\nCapital-intensive sectors run structurally higher.'
    table.cell(table_id = T, column = 0, row = row_idx, text = 'Net Debt / EBITDA', text_color = color_text, bgcolor = color_bg, text_size = i_textSize, tooltip = nd_tt)
    f_cell(T, 1, row_idx, na(nd_ebitda) ? 'N/A' : str.tostring(nd_ebitda, '#.#') + 'x', not na(nd_ebitda) and nd_ebitda > 3.0 ? color.red : color_text, color_bg, i_textSize)
    f_cell(T, 2, row_idx, 'Leverage', color_text, color_bg, i_textSize)
    f_cell(T, 3, row_idx, nd_txt, color_text, nd_col, i_textSize)
    row_idx := row_idx + 1
    string piotroski_status_text = na
    color piotroski_status_color = color_bg
    if not na(piotroski_f_score)
        if piotroski_f_score >= 7
            piotroski_status_text := 'Strong'
            piotroski_status_color := color_under
        else if piotroski_f_score <= 3
            piotroski_status_text := 'Weak'
            piotroski_status_color := color_over
        else
            piotroski_status_text := 'Neutral'
            piotroski_status_color := color_bg
    f_cell(T, 0, row_idx, 'Piotroski F-Score', color_text, color_bg, i_textSize)
    f_cell(T, 1, row_idx, piotroski_f_score, color_text, color_bg, i_textSize)
    f_cell(T, 2, row_idx, 'Financial Strength', color_text, color_bg, i_textSize)
    f_cell(T, 3, row_idx, piotroski_status_text, color_text, piotroski_status_color, i_textSize)
    row_idx := row_idx + 1
    // --- 4-QUADRANT RISK MATRIX (Z-Score + M-Score) ---
    if i_useBeneishCheck and not na(altman_z) and not na(m_score)
        string risk_matrix_txt = 'N/A'
        color risk_matrix_color = color_bg
        string risk_matrix_tooltip = ''
        bool is_z_safe = altman_z >= z_safe_cut
        bool is_z_golden = altman_z >= z_gold_cut
        bool is_m_safe = not is_manipulator
        if is_z_safe and is_m_safe
            risk_matrix_txt := is_z_golden ? 'Golden Standard' : 'Safe & Honest'
            risk_matrix_color := color_under
            risk_matrix_tooltip := 'Quadrant 1: Safe & Honest\nSafe from bankruptcy & honest accounting.'
        else if not is_z_safe and is_m_safe
            risk_matrix_txt := 'Failing / Honest'
            risk_matrix_color := color.new(color.orange, 40)
            risk_matrix_tooltip := 'Quadrant 4: Failing but Honest\nHigh distress risk, but financials are truthful. (Value Trap or Turnaround)'
        else if is_z_safe and not is_m_safe
            risk_matrix_txt := 'Fake Safe (Enron)'
            risk_matrix_color := color_over
            risk_matrix_tooltip := 'Quadrant 3: Fake Safe\nLooks financially healthy, but earnings are likely manipulated. DO NOT TRUST.'
        else
            risk_matrix_txt := 'Desperation Spiral'
            risk_matrix_color := color.new(color.red, 0)
            risk_matrix_tooltip := 'Quadrant 2: Desperation Spiral\nHigh distress AND accounting manipulation. Extreme Danger.'
        risk_matrix_tooltip += (z_is_em ? "\n\nScore is Z''-EM: safe > 5.85, distress < 4.35." : '\n\nScore is Altman Z: safe > 3.0, distress < 1.8.') + '\nM-Score cutoff: -1.78.'
        f_cell(T, 0, row_idx, 'Z+M Risk Matrix', color_text, color_bg, i_textSize)
        f_cell(T, 1, row_idx, 'Z: ' + str.tostring(altman_z, '#.#') + ' | M: ' + str.tostring(m_score, '#.#'), color_text, color_bg, i_textSize)
        f_cell(T, 2, row_idx, 'Risk Profile', color_text, color_bg, i_textSize)
        table.cell(table_id = T, column = 3, row = row_idx, text = risk_matrix_txt, text_color = color.white, bgcolor = risk_matrix_color, text_size = i_textSize, tooltip = risk_matrix_tooltip)
        row_idx := row_idx + 1
    string inv_status = 'Efficient'
    color inv_color = color_under
    if investment_dummy
        inv_status := 'Empire Builder'
        inv_color := color_over
    else if is_deteriorating
        inv_status := 'Deteriorating'
        inv_color := color_over
    string growth_text = str.tostring(math.round(nz(asset_growth, 0) * 100)) + '% / ' + str.tostring(math.round(nz(ebitda_growth, 0) * 100)) + '%'
    string inv_tooltip = investment_dummy ? "DANGER: YoY Asset Growth strictly exceeds YoY EBITDA Growth." : "Safe: Core cash generation (EBITDA) is keeping pace with or exceeding Asset Expansion."
    f_cell(T, 0, row_idx, 'Asset Growth YoY / EBITDA Growth YoY', color_text, color_bg, i_textSize)
    f_cell(T, 1, row_idx, growth_text, investment_dummy ? color.red : color_text, color_bg, i_textSize)
    f_cell(T, 2, row_idx, 'Capital Allocation', color_text, color_bg, i_textSize)
    table.cell(table_id = T, column = 3, row = row_idx, text = inv_status, text_color = color_text, bgcolor = inv_color, text_size = i_textSize, tooltip = inv_tooltip)
    row_idx := row_idx + 1
    if i_use_rkv
        string rkv_status_txt = is_rkv_value_trap ? 'Value Trap' : is_rkv_deep_value ? 'True Deep Value' : 'Neutral'
        color rkv_status_col = is_rkv_value_trap ? color_over : is_rkv_deep_value ? color_under : color_bg
        string rkv_tt = "Rhodes-Kropf M/B decomposition:\n\nGrowth options (V/B): " + str.tostring(rkv_growth_vb, '#.##') + "x -- fair value vs book. Below 1.0x the business is worth less than its balance sheet.\n\nMispricing (P/V): " + str.tostring(rkv_mispricing_mv, '#.##') + "x -- price vs fair value."
        f_cell(T, 0, row_idx, 'Rhodes-Kropf V/B (Growth)', color_text, color_bg, i_textSize)
        f_cell(T, 1, row_idx, str.tostring(rkv_growth_vb, '#.##') + 'x', is_rkv_deep_value ? color.green : (is_rkv_value_trap ? color.red : color_text), color_bg, i_textSize)
        f_cell(T, 2, row_idx, 'RKV Diagnosis', color_text, color_bg, i_textSize)
        table.cell(table_id = T, column = 3, row = row_idx, text = rkv_status_txt, text_color = color_text, bgcolor = rkv_status_col, text_size = i_textSize, tooltip = rkv_tt)
        row_idx := row_idx + 1
    string wacc_tt = 'CAPM Beta: ' + str.tostring(beta_mkt, '#.##') +
         '\nDownside Beta: ' + (na(downside_beta) ? 'N/A' : str.tostring(downside_beta, '#.##')) +
         '\nRisk-free base: ' + i_rf_base + ' = ' + str.tostring(base_rf_for_calc * 100, '#.##') + '%' +
         '\nERP: ' + str.tostring(calc_erp * 100, '#.#') + '%' +
         '\nCRP: ' + str.tostring(calc_crp * 100, '#.#') + '% (local-US spread: ' + str.tostring(auto_crp_raw * 100, '#.#') + '%)' +
         '\nCost of Debt (synthetic): ' + str.tostring(cost_of_debt_synthetic * 100, '#.#') + '%' +
         '\nEffective tax: ' + str.tostring(effective_tax_rate * 100, '#.#') + '%'
    table.cell(table_id = T, column = 0, row = row_idx, text = 'Discount Rate (WACC)', text_color = color_text, bgcolor = color_header, text_size = i_textSize, tooltip = wacc_tt)
    f_cell(T, 1, row_idx, str.tostring(math.round(final_discount_rate * 100)) + '%', color_text, color_value, i_textSize)
    f_cell(T, 2, row_idx, 'CoE ' + str.tostring(math.round(cost_of_equity * 100)) + '%', color_text, color_bg, i_textSize)
    string wacc_flag = final_discount_rate < 0.05 ? 'Too Low' : final_discount_rate > 0.20 ? 'Extreme' : 'Normal'
    color wacc_flag_col = wacc_flag == 'Normal' ? color_under : color_over
    f_cell(T, 3, row_idx, wacc_flag, color.white, wacc_flag_col, i_textSize)
    row_idx := row_idx + 1
    // [MACRO] The CPI/GDP feeds are gone; say what replaced them.
    string macro_src = (i_lr_infl > 0 ? 'input' : 'auto') + ' / ' + (i_lr_rgdp > 0 ? 'input' : 'auto')
    table.cell(table_id = T, column = 0, row = row_idx, text = 'Macro (manual)', text_color = color_text, bgcolor = color_header, text_size = i_textSize, tooltip = 'Long-run inflation and real GDP growth are assumptions, not feeds. Set them in Industry-Specific Valuation. auto = per-currency default.')
    f_cell(T, 1, row_idx, 'Infl ' + str.tostring(lr_infl * 100, '#.##') + '% | GDP ' + str.tostring(lr_rgdp * 100, '#.##') + '%', color_text, color_value, i_textSize)
    f_cell(T, 2, row_idx, macro_src, color_text, color_bg, i_textSize)
    f_cell(T, 3, row_idx, 'Terminal g ' + str.tostring(final_terminal_growth * 100, '#.##') + '%', color_text, color_bg, i_textSize)
    row_idx := row_idx + 1
    if use_oe
        float oe_yield_pct = close > 0 ? nz(oe_per_share) / close * 100 : 0.0
        float yield_spread = oe_yield_pct - us10y_yield
        string coupon_status = 'PASS'
        color coupon_color = color_over
        if yield_spread >= 3.0
            coupon_status := 'SCREAMING BUY'
            coupon_color := color.new(color.green, 0)
        else if yield_spread > 0
            coupon_status := 'BUY (Positive Carry)'
            coupon_color := color_under
        else
            coupon_status := 'PASS (Yield < Bond)'
            coupon_color := color_over
        string coupon_tt = 'Owner Earnings yield: ' + str.tostring(oe_yield_pct, '#.##') + '%' +
             '\n10Y hurdle: ' + str.tostring(us10y_yield, '#.##') + '%' +
             '\nSpread: ' + (yield_spread > 0 ? '+' : '') + str.tostring(yield_spread, '#.##') + '%'
        table.cell(table_id = T, column = 0, row = row_idx, text = 'Buffett Coupon vs 10Y', text_color = color_text, bgcolor = color_header, text_size = i_textSize, tooltip = coupon_tt)
        f_cell(T, 1, row_idx, str.tostring(oe_yield_pct, '#.##') + '%', color_text, color_value, i_textSize)
        f_cell(T, 2, row_idx, (yield_spread > 0 ? '+' : '') + str.tostring(yield_spread, '#.##') + '%', yield_spread > 0 ? color.green : color.red, color_bg, i_textSize)
        f_cell(T, 3, row_idx, coupon_status, color.white, coupon_color, i_textSize)
        row_idx := row_idx + 1
    f_cell(T, 0, row_idx, 'Implied Exit P/E (Yr' + str.tostring(i_dcf_stage1_yrs) + ')', color_text, color_header, i_textSize)
    f_cell(T, 1, row_idx, str.tostring(math.round(implied_exit_multiple, 1)) + 'x', color_text, color_value, i_textSize)
    f_cell(T, 2, row_idx, 'Sanity Check', color_text, color_header, i_textSize)
    bool is_crazy_exit = implied_exit_multiple > 30.0
    f_cell(T, 3, row_idx, is_crazy_exit ? 'High' : 'Safe', is_crazy_exit ? color.red : color.green, color_bg, i_textSize)
    row_idx := row_idx + 1
    float growth_benchmark = nz(fwd_eps_growth, i_analyst_growth)
    string growth_src = na(fwd_eps_growth) ? 'Manual Est.' : 'Consensus Est.'
    bool expensive_growth = implied_market_growth > growth_benchmark
    f_cell(T, 0, row_idx, 'Market Implied Growth', color_text, color_header, i_textSize)
    f_cell(T, 1, row_idx, str.tostring(math.round(implied_market_growth * 100, 1)) + '%', color_text, color_value, i_textSize)
    f_cell(T, 2, row_idx, growth_src + ' ' + str.tostring(math.round(growth_benchmark * 100, 1)) + '%', color_text, color_bg, i_textSize)
    f_cell(T, 3, row_idx, expensive_growth ? 'Demanding' : 'Achievable', color.white, expensive_growth ? color_over : color_under, i_textSize)
    row_idx := row_idx + 1
    // --- QUALITY & MANAGEMENT RATIOS ---
    bool has_quality_metrics = show_gpa or show_roic_wacc or show_croic or show_sloan or show_shareholder or show_asset_growth
    if has_quality_metrics
        table.cell(table_id = T, column = 0, row = row_idx, text = 'Quant Quality Filters', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        table.cell(table_id = T, column = 1, row = row_idx, text = 'Value', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        table.cell(table_id = T, column = 2, row = row_idx, text = 'Target', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        table.cell(table_id = T, column = 3, row = row_idx, text = 'Status', text_color = color_text, bgcolor = color_header, text_size = i_textSize)
        row_idx := row_idx + 1
        if show_gpa
            bool pass_gpa = gpa_ratio > 0.33
            f_cell(T, 0, row_idx, 'Gross Profit / Assets (GPA)', color_text, color_bg, i_textSize)
            f_cell(T, 1, row_idx, str.tostring(gpa_ratio * 100, '#.##') + '%', pass_gpa ? color.green : color.red, color_bg, i_textSize)
            f_cell(T, 2, row_idx, '> 33%', color_text, color_bg, i_textSize)
            f_cell(T, 3, row_idx, pass_gpa ? 'PASS' : 'FAIL', color.white, pass_gpa ? color_under : color_over, i_textSize)
            row_idx := row_idx + 1
        if show_roic_wacc
            bool pass_spread = roic_wacc_spread > 0.05
            f_cell(T, 0, row_idx, 'ROIC vs WACC Spread', color_text, color_bg, i_textSize)
            f_cell(T, 1, row_idx, (roic_wacc_spread > 0 ? '+' : '') + str.tostring(roic_wacc_spread * 100, '#.##') + '%', pass_spread ? color.green : color.red, color_bg, i_textSize)
            f_cell(T, 2, row_idx, '> +5%', color_text, color_bg, i_textSize)
            f_cell(T, 3, row_idx, pass_spread ? 'PASS' : 'FAIL', color.white, pass_spread ? color_under : color_over, i_textSize)
            row_idx := row_idx + 1
        if show_croic
            bool pass_croic = croic_val > 0.15
            f_cell(T, 0, row_idx, 'Cash ROIC (CROIC)', color_text, color_bg, i_textSize)
            f_cell(T, 1, row_idx, str.tostring(croic_val * 100, '#.##') + '%', pass_croic ? color.green : color.red, color_bg, i_textSize)
            f_cell(T, 2, row_idx, '> 15%', color_text, color_bg, i_textSize)
            f_cell(T, 3, row_idx, pass_croic ? 'PASS' : 'FAIL', color.white, pass_croic ? color_under : color_over, i_textSize)
            row_idx := row_idx + 1
        if show_sloan
            bool pass_sloan = sloan_ratio < 0
            table.cell(table_id = T, column = 0, row = row_idx, text = 'Sloan Accrual Ratio', text_color = color_text, bgcolor = color_bg, text_size = i_textSize, tooltip = '(Net Income - Operating Cash Flow) / Total Assets.\n\nSloan (1996) is a RETURNS anomaly, not a fraud test. Beneish M-Score in the Z+M row is the manipulation model.')
            f_cell(T, 1, row_idx, str.tostring(sloan_ratio * 100, '#.##') + '%', pass_sloan ? color.green : color.red, color_bg, i_textSize)
            f_cell(T, 2, row_idx, '< 0%', color_text, color_bg, i_textSize)
            f_cell(T, 3, row_idx, pass_sloan ? 'SAFE' : 'HIGH ACCRUALS', color.white, pass_sloan ? color_under : color_over, i_textSize)
            row_idx := row_idx + 1
        if show_shareholder
            bool pass_shy = shareholder_yield > 0.05
            f_cell(T, 0, row_idx, 'True Shareholder Yield', color_text, color_bg, i_textSize)
            f_cell(T, 1, row_idx, str.tostring(shareholder_yield * 100, '#.##') + '%', pass_shy ? color.green : color_text, color_bg, i_textSize)
            f_cell(T, 2, row_idx, '> 5%', color_text, color_bg, i_textSize)
            f_cell(T, 3, row_idx, pass_shy ? 'PASS' : 'FAIL', color.white, pass_shy ? color_under : color_over, i_textSize)
            row_idx := row_idx + 1
        if show_asset_growth
            bool pass_ag = safe_asset_growth < 0.05
            f_cell(T, 0, row_idx, 'Asset Growth YoY', color_text, color_bg, i_textSize)
            f_cell(T, 1, row_idx, str.tostring(safe_asset_growth * 100, '#.##') + '%', pass_ag ? color.green : color.red, color_bg, i_textSize)
            f_cell(T, 2, row_idx, '< 5%', color_text, color_bg, i_textSize)
            f_cell(T, 3, row_idx, pass_ag ? 'PASS' : 'EMPIRE BLDR', color.white, pass_ag ? color_under : color_over, i_textSize)
            row_idx := row_idx + 1
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
// ==========================================
// 8. TRUE ROLLING BACKTESTER
// ==========================================
// [FIX BPY] Holding period in bars from bars-per-year, not calendar days / bar length.
float hold_years = i_bt_unit == 'Days' ? i_bt_val / 365.25 : i_bt_unit == 'Weeks' ? i_bt_val * 7 / 365.25 : i_bt_unit == 'Months' ? i_bt_val / 12.0 : i_bt_val * 1.0
int bars_to_hold = math.max(math.min(int(math.round(hold_years * bpy)), 4800), 1)
// --- HELPER: ARRAY CORRELATION (FOR TIME-SERIES IC) ---
f_array_correl(arr_x, arr_y) =>
    int n = array.size(arr_x)
    float res = na
    if n > 1
        float sum_x = 0.0, float sum_y = 0.0
        for i = 0 to n - 1
            sum_x += array.get(arr_x, i)
            sum_y += array.get(arr_y, i)
        float mean_x = sum_x / n
        float mean_y = sum_y / n
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
// --- MODEL STATS TYPES (NESTED) ---
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
    int straddled = 0
    int last_entry = -999
f_new_model() =>
    ModelStats.new(
         PeriodStats.new(0, 0, 0.0, 0.0, array.new_float(), array.new_float(), array.new_float(), array.new_float(), array.new_float()),
         PeriodStats.new(0, 0, 0.0, 0.0, array.new_float(), array.new_float(), array.new_float(), array.new_float(), array.new_float()),
         PeriodStats.new(0, 0, 0.0, 0.0, array.new_float(), array.new_float(), array.new_float(), array.new_float(), array.new_float()),
         array.new_float(), array.new_float(), array.new_int(), array.new_float(), array.new_int(), 0, -999)
var dcf_stats = f_new_model(), var graham_stats = f_new_model(), var epv_stats = f_new_model(), var paper_stats = f_new_model()
var rule40_stats = f_new_model(), var pe_stats = f_new_model(), var comp_stats = f_new_model(), var rnpv_stats = f_new_model()
var ecf_stats = f_new_model(), var apv_stats = f_new_model(), var eva_stats = f_new_model(), var psstats = f_new_model()
var pfcfstats = f_new_model(), var pbstats = f_new_model(), var ptbvstats = f_new_model(), var evebitdastats = f_new_model()
var pcfstats = f_new_model(), var paffostats = f_new_model(), var acquirer_stats = f_new_model()
var affo_stats = f_new_model(), var unbundled_stats = f_new_model(), var ddm_stats = f_new_model()
var base_stats = f_new_model()
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
float bt_dyn_margin = entry_margin
int bt_cooldown = math.max(1, int(bpy / 12))
f_rolling_update(stats_obj, current_fv, current_close, current_low, exit_prem, max_hold, max_open, int current_period) =>
    int open_trades = array.size(stats_obj.entry_prices)
    bool target_hit = not na(current_fv) and current_fv > 0 and current_close >= current_fv * (1.0 + exit_prem)
    float div_y = nz(div_yield, 0.0)
    if open_trades > 0
        for i = open_trades - 1 to 0
            float e_price = array.get(stats_obj.entry_prices, i)
            int e_bar = array.get(stats_obj.entry_bars, i)
            int e_period = array.get(stats_obj.entry_periods, i)
            float current_min = array.get(stats_obj.floating_min_prices, i)
            float new_min = math.min(current_min, current_low)
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
                float collected_dividends = e_price * (div_y * years_held)
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
                array.pop(stats_obj.entry_prices)
                array.pop(stats_obj.floating_min_prices)
                array.pop(stats_obj.entry_bars)
                array.pop(stats_obj.entry_discounts)
                array.pop(stats_obj.entry_periods)
    // Entry Logic (max_open 0 = unlimited)
    int n_open = array.size(stats_obj.entry_prices)
    if current_period > 0 and not na(current_fv) and current_fv > 0 and (max_open <= 0 or n_open < max_open)
        float buy_limit = current_fv * (1.0 - bt_dyn_margin)
        if current_close <= buy_limit and (n_open == 0 or (bar_index - stats_obj.last_entry) >= bt_cooldown)
            array.push(stats_obj.entry_prices, current_close)
            array.push(stats_obj.floating_min_prices, current_close)
            array.push(stats_obj.entry_bars, bar_index)
            array.push(stats_obj.entry_discounts, (current_fv - current_close) / current_close)
            array.push(stats_obj.entry_periods, current_period)
            stats_obj.last_entry := bar_index
// The backtest deliberately IGNORES the allocation matrix: it is the evidence
// you use to DECIDE an allocation. Order must match bt_vals / bt_labels.
var array<ModelStats> bt_models = array.from(comp_stats, dcf_stats, graham_stats, epv_stats, paper_stats, rule40_stats, pe_stats, psstats, pfcfstats, pbstats, ptbvstats, evebitdastats, pcfstats, paffostats, acquirer_stats, rnpv_stats, ecf_stats, affo_stats, unbundled_stats, apv_stats, eva_stats, ddm_stats, base_stats)
if i_show_bt
    array<float> bt_vals = array.from(finalFairValue, iv_buffett_dcf, iv_graham, iv_epv, iv_paper, iv_rule40)
    for k = 0 to 7
        array.push(bt_vals, array.get(MULTS, k).fv)
    for v in array.from(iv_acquirer, fv_rnpv, fv_ecf, fv_affo_dcf, fv_unbundled, fv_apv, fv_eva, fv_ddm)
        array.push(bt_vals, v)
    // [BASELINE] fv = 10x price: always "cheap", never hits target, so it
    // buys on every cooldown and exits at max hold -- a buy-and-hold proxy.
    array.push(bt_vals, close * 10)
    for i = 0 to array.size(bt_models) - 1
        f_rolling_update(array.get(bt_models, i), array.get(bt_vals, i), close, low, i_bt_exit_premium, bars_to_hold, i_bt_max_open, bt_period)
f_calc_vacagr(PeriodStats stats) =>
    float geo_cagr = na
    int n_ann = array.size(stats.closed_ann_returns)
    if n_ann > 0
        float comp_mult = 1.0
        for i = 0 to n_ann - 1
            float r_dec = array.get(stats.closed_ann_returns, i) / 100.0
            comp_mult *= math.max(1.0 + r_dec, 0.001)
        geo_cagr := (math.pow(comp_mult, 1.0 / n_ann) - 1.0) * 100.0
    geo_cagr
// =====================================================================
// BACKTEST RENDERER -- 3 VIEWS
// =====================================================================
f_arr_median(array<float> a) =>
    float r = na
    int n = array.size(a)
    if n > 0
        array<float> s = array.copy(a)
        array.sort(s)
        r := n % 2 == 1 ? array.get(s, int(n / 2)) : (array.get(s, int(n / 2) - 1) + array.get(s, int(n / 2))) / 2.0
    r
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
    float med_ret = f_arr_median(stats.closed_returns)
    float avg_hold = array.size(stats.closed_holds) > 0 ? array.avg(stats.closed_holds) : na
    float vacagr = f_calc_vacagr(stats)
    PMetrics.new(n, wr, expectancy, mae, ic, med_ret, avg_hold, vacagr)
f_conf_col(int n) =>
    color out = color(na)
    if n == 0
        out := color.new(color.gray, 85)
    else if n < i_bt_min_n
        out := color.new(color.gray, 75)
    out
f_format_period(PeriodStats stats) =>
    PMetrics p = f_period_metrics(stats)
    int n = p.n
    float wr = p.wr
    float expectancy = p.expectancy
    float mae = p.mae
    float ic = p.ic
    float med_ret = p.med_ret
    float avg_hold = p.avg_hold
    float vacagr = p.vacagr
    if n == 0
        ["N/A", "No trades in this period.", color.new(color.gray, 80), color.gray]
    else
        string main_txt = (not na(vacagr) ? str.tostring(vacagr, "#.0") + "%" : "0.0%") + " (" + str.tostring(wr, "#.0") + "%) n=" + str.tostring(n)
        string tt = "Trades: " + str.tostring(n) +
             "\nIC (Alpha): " + (not na(ic) ? str.tostring(ic, "#.00") : "N/A") +
             "\nExpectancy: " + (not na(expectancy) ? str.tostring(expectancy * 100, "#.0") + "%" : "N/A") +
             "\nMedian trade: " + (not na(med_ret) ? str.tostring(med_ret * 100, "#.0") + "%" : "N/A") +
             "\nAvg hold: " + (not na(avg_hold) ? str.tostring(avg_hold, "#.0") + "y" : "N/A") +
             "\nMAE (per-trade): " + (not na(mae) ? str.tostring(mae, "#.0") + "%" : "N/A") +
             "\n\nVACAGR annualizes each trade with a 1-month floor, so short holds dominate. Read median trade + avg hold alongside it."
        color dim_col = f_conf_col(n)
        color bg_col = not na(dim_col) ? dim_col : (not na(vacagr) and vacagr >= 15.0 ? color.new(color.yellow, 0) : (vacagr > 0 ? color.new(color.green, 70) : color.new(color.red, 70)))
        color txt_col = not na(dim_col) ? color.silver : (not na(vacagr) and vacagr >= 15.0 ? color.black : color.white)
        [main_txt, tt, bg_col, txt_col]
// --- VIEW 1: MATRIX (all three periods) ---
f_fill_matrix_row(tbl, row, name, ModelStats m) =>
    table.cell(tbl, 0, row, name, bgcolor = color.new(color.black, 50), text_color = color.white, text_size = size.small, text_halign = text.align_left)
    [txt_is, tt_is, bg_is, tcol_is] = f_format_period(m.is_stats)
    table.cell(tbl, 1, row, txt_is, bgcolor = bg_is, text_color = tcol_is, text_size = size.small, tooltip = tt_is)
    [txt_oos, tt_oos, bg_oos, tcol_oos] = f_format_period(m.oos_stats)
    table.cell(tbl, 2, row, txt_oos, bgcolor = bg_oos, text_color = tcol_oos, text_size = size.small, tooltip = tt_oos)
    [txt_fwd, tt_fwd, bg_fwd, tcol_fwd] = f_format_period(m.fwd_stats)
    table.cell(tbl, 3, row, txt_fwd, bgcolor = bg_fwd, text_color = tcol_fwd, text_size = size.small, tooltip = tt_fwd)
// --- VIEW 2: FOCUS (one period, metrics as columns) ---
f_fill_focus_row(tbl, row, name, ModelStats m, int which) =>
    PeriodStats ps = which == 1 ? m.is_stats : which == 2 ? m.oos_stats : m.fwd_stats
    PMetrics p = f_period_metrics(ps)
    int n = p.n
    float wr = p.wr
    float expectancy = p.expectancy
    float mae = p.mae
    float ic = p.ic
    float med_ret = p.med_ret
    float avg_hold = p.avg_hold
    float vacagr = p.vacagr
    color grey = f_conf_col(n)
    color base = not na(grey) ? grey : color.new(color.black, 70)
    color txt = not na(grey) ? color.silver : color.white
    table.cell(tbl, 0, row, name, bgcolor = color.new(color.black, 50), text_color = color.white, text_size = size.small, text_halign = text.align_left)
    table.cell(tbl, 1, row, n == 0 ? "-" : str.tostring(n), bgcolor = base, text_color = txt, text_size = size.small, tooltip = m.straddled > 0 ? "straddling trades excluded: " + str.tostring(m.straddled) : "")
    color ic_bg = not na(grey) ? grey : (na(ic) ? color.new(color.gray, 80) : ic > 0.3 ? color.new(color.green, 30) : ic > 0 ? color.new(color.green, 70) : color.new(color.red, 60))
    table.cell(tbl, 2, row, na(ic) ? "-" : str.tostring(ic, "#.00"), bgcolor = ic_bg, text_color = txt, text_size = size.small, tooltip = "Correlation between entry discount and realised return. Near zero = the fair value carries no predictive information.")
    color ex_bg = not na(grey) ? grey : (na(expectancy) ? color.new(color.gray, 80) : expectancy > 0 ? color.new(color.green, 60) : color.new(color.red, 60))
    table.cell(tbl, 3, row, na(expectancy) ? "-" : str.tostring(expectancy * 100, "#.0") + "%", bgcolor = ex_bg, text_color = txt, text_size = size.small)
    table.cell(tbl, 4, row, na(med_ret) ? "-" : str.tostring(med_ret * 100, "#.0") + "%", bgcolor = base, text_color = txt, text_size = size.small)
    table.cell(tbl, 5, row, na(wr) ? "-" : str.tostring(wr, "#.0") + "%", bgcolor = base, text_color = txt, text_size = size.small)
    table.cell(tbl, 6, row, na(avg_hold) ? "-" : str.tostring(avg_hold, "#.1") + "y", bgcolor = base, text_color = txt, text_size = size.small)
    table.cell(tbl, 7, row, na(mae) ? "-" : str.tostring(mae, "#.0") + "%", bgcolor = base, text_color = txt, text_size = size.small)
    table.cell(tbl, 8, row, na(vacagr) ? "-" : str.tostring(vacagr, "#.0") + "%", bgcolor = base, text_color = txt, text_size = size.small, tooltip = "VACAGR floors holding period at 1 month. Read with Median and Hold.")
// --- VIEW 3: ROBUSTNESS VERDICT (vs the always-in baseline) ---
f_fill_robust_row(tbl, row, name, ModelStats m, ModelStats b) =>
    PMetrics p1 = f_period_metrics(m.is_stats)
    PMetrics p2 = f_period_metrics(m.oos_stats)
    PMetrics p3 = f_period_metrics(m.fwd_stats)
    int n1 = p1.n
    int n2 = p2.n
    int n3 = p3.n
    float v1 = p1.vacagr
    float v2 = p2.vacagr
    float v3 = p3.vacagr
    // [FIX BASELINE] "Stable" also requires beating simply being invested.
    PMetrics q1 = f_period_metrics(b.is_stats)
    PMetrics q2 = f_period_metrics(b.oos_stats)
    PMetrics q3 = f_period_metrics(b.fwd_stats)
    float edge = ((nz(v1) - nz(q1.vacagr)) + (nz(v2) - nz(q2.vacagr)) + (nz(v3) - nz(q3.vacagr))) / 3.0
    bool beats_all = nz(v1) > nz(q1.vacagr) and nz(v2) > nz(q2.vacagr) and nz(v3) > nz(q3.vacagr)
    bool enough = n1 >= i_bt_min_n and n2 >= i_bt_min_n and n3 >= i_bt_min_n
    float lo = math.min(nz(v1, 0), nz(v2, 0), nz(v3, 0))
    float hi = math.max(nz(v1, 0), nz(v2, 0), nz(v3, 0))
    float spread = hi - lo
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
    table.cell(tbl, 0, row, name, bgcolor = color.new(color.black, 50), text_color = color.white, text_size = size.small, text_halign = text.align_left)
    table.cell(tbl, 1, row, na(v1) ? "-" : str.tostring(v1, "#.0"), bgcolor = color.new(color.black, 70), text_color = n1 < i_bt_min_n ? color.silver : color.white, text_size = size.small, tooltip = "n=" + str.tostring(n1))
    table.cell(tbl, 2, row, na(v2) ? "-" : str.tostring(v2, "#.0"), bgcolor = color.new(color.black, 70), text_color = n2 < i_bt_min_n ? color.silver : color.white, text_size = size.small, tooltip = "n=" + str.tostring(n2))
    table.cell(tbl, 3, row, na(v3) ? "-" : str.tostring(v3, "#.0"), bgcolor = color.new(color.black, 70), text_color = n3 < i_bt_min_n ? color.silver : color.white, text_size = size.small, tooltip = "n=" + str.tostring(n3))
    table.cell(tbl, 4, row, enough ? str.tostring(spread, "#.0") : "-", bgcolor = color.new(color.black, 70), text_color = color.white, text_size = size.small)
    table.cell(tbl, 5, row, verdict, bgcolor = vcol, text_color = color.white, text_size = size.small, tooltip = vtip)
    table.cell(tbl, 6, row, enough ? (edge > 0 ? "+" : "") + str.tostring(edge, "#.0") : "-", bgcolor = enough ? (edge > 0 ? color.new(color.green, 60) : color.new(color.red, 60)) : color.new(color.black, 70), text_color = color.white, text_size = size.small)
    table.cell(tbl, 7, row, "", bgcolor = color.new(color.black, 100), text_size = size.small)
    table.cell(tbl, 8, row, "", bgcolor = color.new(color.black, 100), text_size = size.small)
// --- DISPATCHER ---
f_bt_row(tbl, row, name, ModelStats m, ModelStats b) =>
    if i_bt_view == 'Matrix (all periods)'
        f_fill_matrix_row(tbl, row, name, m)
    else if i_bt_view == 'Robustness verdict'
        f_fill_robust_row(tbl, row, name, m, b)
    else
        int which = i_bt_view == 'Focus: Period 1' ? 1 : i_bt_view == 'Focus: Period 2' ? 2 : 3
        f_fill_focus_row(tbl, row, name, m, which)
// --- DASHBOARD RENDERER ---
var table bt_tbl = table.new(position.bottom_left, 9, 32, border_width = 1)
if barstate.islast and i_show_bt
    color th_bg = color.new(color.blue, 20)
    color th_txt = color.white
    table.clear(bt_tbl, 0, 0, 8, 31)
    string mode_tag = i_period_mode == 'Auto-Split' ? " [auto-split]" : i_period_mode == 'Full Period' ? " [pooled]" : ""
    if i_bt_view == 'Matrix (all periods)'
        table.cell(bt_tbl, 0, 0, "Valuation Model Matrix" + mode_tag, bgcolor = color.new(color.purple, 30), text_color = color.yellow, text_size = size.small)
        table.cell(bt_tbl, 1, 0, "Period 1\n(In-Sample)", bgcolor = th_bg, text_color = th_txt, text_size = size.small, tooltip = "VACAGR% (Win%) n=trades")
        table.cell(bt_tbl, 2, 0, "Period 2\n(Out-of-Sample)", bgcolor = th_bg, text_color = th_txt, text_size = size.small, tooltip = "VACAGR% (Win%) n=trades")
        table.cell(bt_tbl, 3, 0, "Period 3\n(Forward)", bgcolor = th_bg, text_color = th_txt, text_size = size.small, tooltip = "VACAGR% (Win%) n=trades")
    else if i_bt_view == 'Robustness verdict'
        table.cell(bt_tbl, 0, 0, "Robustness" + mode_tag, bgcolor = color.new(color.purple, 30), text_color = color.yellow, text_size = size.small)
        table.cell(bt_tbl, 1, 0, "P1", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 2, 0, "P2", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 3, 0, "P3", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 4, 0, "Spread", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 5, 0, "Verdict", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 6, 0, "vs Base", bgcolor = th_bg, text_color = th_txt, text_size = size.small, tooltip = "Average VACAGR edge over the always-in baseline across the three periods.")
    else
        table.cell(bt_tbl, 0, 0, i_bt_view + mode_tag, bgcolor = color.new(color.purple, 30), text_color = color.yellow, text_size = size.small)
        table.cell(bt_tbl, 1, 0, "n", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 2, 0, "IC", bgcolor = th_bg, text_color = th_txt, text_size = size.small, tooltip = "Discount-to-return correlation: does a bigger discount predict a bigger return?")
        table.cell(bt_tbl, 3, 0, "Expect", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 4, 0, "Median", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 5, 0, "Win%", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 6, 0, "Hold", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
        table.cell(bt_tbl, 7, 0, "MAE", bgcolor = th_bg, text_color = th_txt, text_size = size.small, tooltip = "Per-trade maximum adverse excursion, NOT portfolio drawdown.")
        table.cell(bt_tbl, 8, 0, "VACAGR", bgcolor = th_bg, text_color = th_txt, text_size = size.small)
    // A dot marks a model the current framework does NOT allocate.
    array<string> bt_labels = array.from('Composite (Final Blend)', 'DCF (McKinsey)', 'Graham Number', 'EPV (Greenwald)', 'Residual Income', 'Rule of 40', 'Blended PE', 'Price / Sales', 'Price / FCF', 'Price / Book', 'Price / TBV', 'EV / EBITDA', 'Price / OCF', 'Price / AFFO', "Acquirer's Mult", 'Risk-Adj NPV', 'Equity Cash Flow', 'AFFO DCF', 'Unbundled SOTP', 'Adjusted PV', 'Econ Value Added', 'Dividend Discount', 'Baseline (always in)')
    array<bool> bt_alloc = array.from(true, use_dcf, use_graham, use_epv, use_paper_ivm, use_rule40, use_pe, use_ps, use_pfcf, use_pb, use_ptbv, use_ev_ebitda, use_pcf, use_paffo, use_acquirer, use_rnpv, use_ecf, use_affo_dcf, use_unbundled, use_apv, use_eva, use_ddm, true)
    int btrowidx = 1
    for i = 0 to array.size(bt_models) - 1
        ModelStats m = array.get(bt_models, i)
        bool allocated = array.get(bt_alloc, i)
        // Sector models (index 15-21) are hidden until they have produced data.
        bool visible = i < 15 or allocated or m.is_stats.total > 0 or m.oos_stats.total > 0
        if visible
            f_bt_row(bt_tbl, btrowidx, (allocated ? '' : '· ') + array.get(bt_labels, i), m, base_stats)
            btrowidx += 1
    // Blank padding to fix rendering glitches in TV
    table.cell(bt_tbl, 0, btrowidx, " ", bgcolor = color.new(color.black, 100), text_color = color.new(color.white, 100))
    table.cell(bt_tbl, 1, btrowidx, " ", bgcolor = color.new(color.black, 100), text_color = color.new(color.white, 100))
    table.cell(bt_tbl, 2, btrowidx, " ", bgcolor = color.new(color.black, 100), text_color = color.new(color.white, 100))
    table.cell(bt_tbl, 3, btrowidx, " ", bgcolor = color.new(color.black, 100), text_color = color.new(color.white, 100))
```
