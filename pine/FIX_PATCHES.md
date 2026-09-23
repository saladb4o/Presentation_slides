# Fundamental Fair Value Pro: fix patches, phases 0–6

Apply the phases in order, then save and check the chart before moving on to the next one.

**How to read each patch**
- **Where** gives the first words of the original line so you can find it with Ctrl+F. Line numbers `L123` refer to the copy you pasted and may be off by a few lines in your editor.
- **One-line edits:** keep the existing indentation of the line you are replacing.
- **Multi-line blocks** are shown at their real indentation: 0 spaces means top level, and 4 spaces means inside an `if` or a function.
- No patch in phases 0–5 depends on a later phase.

---

## Phase 0: Compile errors

Pine ends a single-quoted string at the first `'`. The fix is to escape each apostrophe as `\'`, which the script already does elsewhere.

| Where | Change |
|---|---|
| L577 `i_om_acq = input.bool(true, 'Acquirer's Multiple'` | `'Acquirer\'s Multiple'` |
| L578 `i_om_oe = input.bool(true, 'Owners' Earnings'` | `'Owners\' Earnings'` |
| L618 tooltip of `i_period_mode`: `symbol's available` | `symbol\'s available` |
| L552 tooltip of `i_omni_strict`: `that bank's fair value` | `that bank\'s fair value` |
| L592 tooltip of `i_strict_cap`: `Acquirer's Multiple and every` | `Acquirer\'s Multiple and every` |
| L2549 in `f_mult_tt`: `this ticker's own stored ratio` | `this ticker\'s own stored ratio` |

**Check:** the script compiles and the output is identical to before.

---

## Phase 1: Replace macro data, clean up request slots, visible assumptions

### 1.1a Inputs: delete two, add two
**Delete** L509 `i_cpi_index_ticker = ...` and L510 `i_gdp_index_ticker = ...`.
**Add** in their place:
```pine
i_lr_infl = input.float(0.0, 'Long-run inflation % (0 = auto by currency)', minval = 0, maxval = 15, step = 0.25, group = group_industry, tooltip = 'Replaces the CPI feed. Drives terminal growth and the CAPE inflation adjustment. 0 uses the per-currency default in the code.') / 100
i_lr_rgdp = input.float(0.0, 'Long-run real GDP growth % (0 = auto by currency)', minval = 0, maxval = 10, step = 0.25, group = group_industry, tooltip = 'Replaces the GDP feed. Only used in the nominal-growth ceiling on terminal growth.') / 100
```

### 1.1b Section 3.1 ticker routing (L676–L718)
Replace everything from `string curr = syminfo.currency` through `string final_gdp_ticker = ...` with:
```pine
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
```
Leave the `int current_tf_sec = ...` line that follows as it is.

### 1.1c Replace the CPI and GDP requests
Delete everything from `// >>> SECURITY SLOT 3/6 : CPI` (L746) down to and including `float hist_gdp_10y = ...` (L793), and paste this in its place:
```pine
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
// cpi_series[offset]) keeps working unchanged. Constant-inflation adjustment.
float cpi_raw = math.pow(1 + lr_infl, (time - timestamp(2000, 1, 1)) / (365.25 * 86400000.0))
```

### 1.2 Remove the macro growth adjustment
Replace L1789–L1795 (from `float macro_baseline_historic` through `float final_explicit_growth = ...`) with:
```pine
float base_triangulated_growth = (effective_sgr * 0.15) + (roic_sgr * 0.40) + (i_analyst_growth * 0.15) + (nz(sales_cagr_3y, 0.05) * 0.30)
float final_explicit_growth = base_triangulated_growth
```

### 1.3 Remove the two dead requests
**Delete** these five lines:
- L827 `float payables_fq = f_fin('ACCOUNTS_PAYABLE', 'FQ')`
- L839 `float rev_est_fq = f_fin('SALES_ESTIMATES', 'FQ')`
- L892 `float rev_est_ttm = f_ttm_vault(rev_est_fq, is_new_quarter)`
- L1321 `float fwd_rev_growth = ...`
- L1323 `fwd_rev_growth := ...`

### 1.4 Table row showing the macro assumptions
Paste this directly **after** the WACC row, i.e. after the `row_idx := row_idx + 1` that follows `f_cell(T, 3, row_idx, wacc_flag, ...)` at about L2858. It sits inside `if barstate.islast`, so it is indented 4 spaces:
```pine
    // [MACRO] The CPI/GDP feeds are gone; say what replaced them.
    string macro_src = (i_lr_infl > 0 ? 'input' : 'auto') + ' / ' + (i_lr_rgdp > 0 ? 'input' : 'auto')
    table.cell(table_id = T, column = 0, row = row_idx, text = 'Macro (manual)', text_color = color_text, bgcolor = color_header, text_size = i_textSize, tooltip = 'Long-run inflation and real GDP growth are assumptions, not feeds. Set them in Industry-Specific Valuation. auto = per-currency default.')
    f_cell(T, 1, row_idx, 'Infl ' + str.tostring(lr_infl * 100, '#.##') + '% | GDP ' + str.tostring(lr_rgdp * 100, '#.##') + '%', color_text, color_value, i_textSize)
    f_cell(T, 2, row_idx, macro_src, color_text, color_bg, i_textSize)
    f_cell(T, 3, row_idx, 'Terminal g ' + str.tostring(final_terminal_growth * 100, '#.##') + '%', color_text, color_bg, i_textSize)
    row_idx := row_idx + 1
```

### 1.5 Live FX rate instead of the hardcoded one
Replace L1707 `float fx_rate = (curr == 'VND') ? 25000.0 : ...` with:
```pine
// [FIX FX] Live rate (1 request slot) instead of a hardcoded 25000 / 0.93 / 0.79.
// fx_rate keeps its old meaning: local currency units per 1 USD.
float fx_to_usd = request.currency_rate(curr, 'USD', ignore_invalid_currency = true)
float fx_rate = not na(fx_to_usd) and fx_to_usd > 0 ? 1.0 / fx_to_usd : ((curr == 'VND') ? 25000.0 : (curr == 'EUR' ? 0.93 : (curr == 'GBP' ? 0.79 : 1.0)))
```

**Check:** request count drops from 39 to 36. Terminal growth is 3.0% for USD and 3.5% for VND, and the table shows a "Macro (manual)" row.

---

## Phase 2: Valuation math

### 2.0 New input
Add this in the Scenario Analysis group, directly after `i_scen_g_bps = ...` (L518):
```pine
i_scen_growth_bps = input.float(200, 'DCF scenario: explicit growth shift (bps)', group = group_scen, minval = 0, maxval = 1000, step = 50, tooltip = 'Bear lowers the stage-1 growth rate by this much, Bull raises it. Before, Bear/Bull only moved the discount rate and terminal growth.') / 10000
```
Change the default of L588 `i_dcf_stage1_yrs` from `5` to `10`, so the main DCF keeps its current 10-year fade once it switches to this input (see 2.8).

### 2.1 Equity Cash Flow: add D&A, discount year by year
Replace `f_calculate_ecf` (L287–L291) with:
```pine
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
```

### 2.2 APV: perpetuity at terminal growth, add back cash
Replace `f_calculate_apv` (L323–L326) with:
```pine
// [FIX APV] Perpetuity at TERMINAL growth (was the 15-40% explicit rate over
// a floored 1% spread), and cash added back.
f_calculate_apv(fcf, total_debt, cash, tax_rate, unlevered_coe, g_term, shares) =>
    float ku = math.max(unlevered_coe, g_term + 0.01)
    float unlev_firm_val = fcf * (1 + g_term) / (ku - g_term)
    float pv_tax_shield = total_debt * tax_rate
    shares > 0 and fcf > 0 ? (unlev_firm_val + pv_tax_shield - total_debt + nz(cash)) / shares : na
```

### 2.3 EVA: subtract net debt, use terminal growth
Replace `f_calculate_eva` (L327–L330) with:
```pine
// [FIX EVA] Invested capital + PV(EVA) is FIRM value; subtract net debt to get
// equity. Growth is the terminal rate: the perpetuity must not outgrow the economy.
f_calculate_eva(nopat, invested_capital, wacc, g_term, net_debt, shares) =>
    float current_eva = nopat - (invested_capital * wacc)
    float pv_eva = (current_eva * (1 + g_term)) / math.max(wacc - g_term, 0.01)
    shares > 0 ? (invested_capital + pv_eva - nz(net_debt)) / shares : na
```

### 2.4 Scenario growth legs, and clamped growth for the sector DCFs
Directly **after** L1894 `float tg_bull = final_terminal_growth + i_scen_g_bps`, add:
```pine
float g_bear = math.max(final_growth_rate - i_scen_growth_bps, -0.05)
float g_bull = math.min(final_growth_rate + i_scen_growth_bps, dynamic_growth_cap)
```
Then replace the sector-model block from `if use_rnpv` (L1904) through the end of `if use_eva` (L1951) with the block below. `if use_ddm` stays unchanged.
```pine
if use_rnpv
    float nopat_ps_r = nopat_adjusted/math.max(shares_out_latest, 1)
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
    float sc_ps = serveco_fcf/math.max(shares_out_latest, 1)
    float np_ps = nopat_adjusted/math.max(shares_out_latest, 1)
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
```

### 2.5 Keep negative and na values out of the Standard blend
Replace L2096–L2112, from `if total_score > 0` through `compositeHi := total_weighted_hi`, with the block below. Phase 5 replaces this block again, so it is fine to treat it as temporary.
```pine
// [FIX NEG] A negative or na model value used to enter the blend as nz(b) = 0
// with full weight, because the zero-floor clamps run AFTER the blend.
float blend_w_sum = 0.0
for i = 0 to 14
    float b_i = array.get(blend_bv, i)
    if array.get(blend_sc, i) > 0 and not na(b_i) and b_i > 0
        blend_w_sum += array.get(blend_sc, i)
if blend_w_sum > 0
    for i = 0 to 14
        float sc_i = array.get(blend_sc, i)
        float b = array.get(blend_bv, i)
        if sc_i > 0 and not na(b) and b > 0
            float w = sc_i / blend_w_sum
            total_weighted_value += b * w
            total_weighted_lo += math.max(nz(array.get(blend_lo, i), b), 0.0) * w
            total_weighted_hi += nz(array.get(blend_hi, i), b) * w
            array.push(valid_fvs_for_stddev, b)
    compositeFairValue := total_weighted_value
    compositeLo := total_weighted_lo
    compositeHi := total_weighted_hi
```

### 2.6 Graham: no invented EPS, cap the yield multiplier
Replace L2234–L2239, from `float base_eps = ...` through `float iv_graham_hi = ...`, with:
```pine
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
```

### 2.7 and 2.8 Main DCF: growth shift in Bear/Bull, use the stage-1 input
Replace L2216–L2220, from `[dcf_val, exit_mult] = ...` through `[dcf_hi_v, dcf_hi_m] = ...`, with:
```pine
[dcf_val, exit_mult] = f_calculate_dcf_value_driver_extended(true_fcf_ps, nopat_ps, roic_adj, math.max(final_discount_rate, 0.01), final_growth_rate, final_terminal_growth, i_dcf_stage1_yrs)
iv_buffett_dcf := dcf_val
implied_exit_multiple := exit_mult
[dcf_lo_v, dcf_lo_m] = f_calculate_dcf_value_driver_extended(true_fcf_ps, nopat_ps, roic_adj, math.max(final_discount_rate + i_scen_wacc_bps, 0.01), g_bear, math.max(final_terminal_growth - i_scen_g_bps, 0.0), i_dcf_stage1_yrs)
[dcf_hi_v, dcf_hi_m] = f_calculate_dcf_value_driver_extended(true_fcf_ps, nopat_ps, roic_adj, math.max(final_discount_rate - i_scen_wacc_bps, 0.02), g_bull, final_terminal_growth + i_scen_g_bps, i_dcf_stage1_yrs)
```

### 2.9 Sustainable growth from ROE, not EBIT/equity
Replace L1783 `float base_profitability = ...` with:
```pine
// [FIX SGR] Sustainable growth = ROE x retention. EBIT/equity is pre-interest and pre-tax.
float base_profitability = not na(median_roe) and median_roe > 0 ? median_roe : (not na(median_op) and median_op > 0 ? median_op * (1 - effective_tax) : 0.05)
```

### 2.10 Allow negative growth
Replace L1803 `final_growth_rate := math.max(final_growth_rate, 0.0)` with:
```pine
final_growth_rate := math.max(final_growth_rate, -0.05) // [FIX G-FLOOR] shrinking firms may shrink
```

### 2.11 EPS estimate: fiscal-year consensus, not a sum of quarters
- L838 becomes `float eps_est_fq = f_fin('EARNINGS_ESTIMATE', 'FY') // 31 [FY consensus]`
- L891 becomes `float eps_est_ttm = f_locf(eps_est_fq)`

**Check:** record each model's Base value on three tickers (a bank, a REIT and a growth stock) before and after this phase. ECF, APV and EVA should move toward the DCF. Graham should show N/A when EPS ≤ 0, and every DCF-type row should show Bear < Base < Bull.

---

## Phase 3: Cost of equity and risk

### 3.0 New inputs
Add these to the `group_risk` block, after `i_crp_manual`:
```pine
i_rf_base = input.string('Local 10Y', 'Risk-free base', options = ['Local 10Y', 'US 10Y + CRP'], group = group_risk, tooltip = 'Local 10Y: discount local-currency cash flows at the local sovereign yield. Country risk is already inside that yield, so auto-CRP is 0 (manual CRP is still added when Auto is off).\n\nUS 10Y + CRP: a USD build -- US yield plus the local-minus-US spread (or the manual CRP). Use it when the local curve is thin or administered.')
```
Add this to `group_calc`:
```pine
i_sbc_proxy = input.bool(false, 'Subtract Non-cash items as SBC proxy', group = group_calc, tooltip = 'Pine has no stock-based-compensation field. NON_CASH_ITEMS also holds impairments, deferred tax, FX and fair-value moves, so subtracting it from FCF is a guess. Off by default.')
```
Replace the `i_financial_model_type` line (L511) with:
```pine
i_financial_model_type = input.string('Auto (by industry)', 'Financials Valuation Model', options = ['Auto (by industry)', 'Equity Model (Bank/Insurer)', 'Entity Model (Brokerage/FinTech)'], group = group_industry, tooltip = 'Auto: banks and insurers use the Equity model (Net Income / Book), brokers, asset managers and lenders use the Entity model (NOPAT / Invested Capital).')
```

### 3.1 Beta alignment
Replace L1357–L1384, from `// [FIX 2.2] R3 IN ACTION` through `downside_beta := cov_down / var_down`, with:
```pine
// [FIX BETA-ALIGN] Both legs are now sampled on the SAME bar: the first chart
// bar of each new beta-timeframe period, holding the PREVIOUS period's close.
// Before, the stock leg updated on the first bar of the week and the
// benchmark (lookahead_off) on the last bar, so the two return series never
// moved on the same bar: beta -> ~0 (0.33 after Blume), downside beta -> 0.
string beta_tf = timeframe.in_seconds(i_beta_tf) <= timeframe.in_seconds(timeframe.period) ? timeframe.period : i_beta_tf
bool beta_sample = ta.change(time(beta_tf)) != 0
float asset_p = f_locf(close[1])
// >>> SECURITY SLOT : benchmark, non-repainting (close[1] + lookahead_on)
[bench_c] = request.security(final_mkt_bench, beta_tf, [close[1]], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
float mkt_bench_p = f_locf(bench_c)
max_bars_back(asset_p, 500)
max_bars_back(mkt_bench_p, 500)
// One return pair per beta-timeframe period. i_beta_lookback now counts
// PERIODS (104 = two years of weeks), not chart bars.
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
    float sa = 0.0, float sb = 0.0
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
```
Then replace the rolling beta engine, L1500–L1519, from `// --- ROLLING BETA ENGINE ---` through `beta_mkt := not na(beta_rolling) ? beta_rolling : 1.0`, with:
```pine
// --- ROLLING BETA ENGINE --- (sampled pairs, see FIX BETA-ALIGN) + Blume adjustment
float beta_rolling = not na(raw_beta_s) ? (0.67 * raw_beta_s) + 0.33 : 1.0
var float beta_mkt = na
beta_mkt := beta_rolling
```
Leave `float finalFairValue = na` and the three lines after it (L1496–L1499) where they are.

### 3.2 Bars per year
Add this directly **after** L719 `int current_tf_sec = ...`:
```pine
// [FIX BPY] Bars per year from the trading calendar, not 365 calendar days.
// A daily stock chart has ~252 bars a year, so "5 years" of 365-bar years
// was ~7.2 years (inflating the ERP CAGR window) and a "1 year" hold ~1.45.
int trading_days = syminfo.type == 'crypto' ? 365 : 252
int bpy = current_tf_sec < 86400 ? math.max(1, int(math.round(trading_days * 23400.0 / current_tf_sec))) : current_tf_sec < 604800 ? math.max(1, int(math.round(trading_days * 86400.0 / current_tf_sec))) : math.max(1, int(math.round(365.25 * 86400.0 / current_tf_sec)))
```
Then make these one-line edits:

| Where | New line |
|---|---|
| L847 `int min_gap_bars = ...` | `int min_gap_bars = math.max(1, int(bpy * 45 / 365.25))` |
| L1129 `int bars_per_qtr = ...` | `int bars_per_qtr = math.max(1, int(bpy / 4))` |
| L1396 `int bars_in_5y = ...` | `int bars_in_5y = 5 * bpy` |
| L1719 `float px_1m_ago = close[21]` | `float px_1m_ago = close[math.max(1, int(bpy / 12))]` |
| L1720 `float px_12m_ago = close[252]` | `float px_12m_ago = close[bpy]` |
| L1819 `int bars_per_year = timeframe.isdaily ? ...` (inside the CAPE block) | **delete** it, and on the next lines change `i * bars_per_year` to `i * bpy` |
| L3091 `int bt_cooldown = timeframe.isdaily ? 21 : ...` | `int bt_cooldown = math.max(1, int(bpy / 12))` |
| L3123 `float years_held = math.max(bars_held / 252.0, 0.083)` | `float years_held = math.max(bars_held / float(bpy), 0.083)` |

Replace L2995–L3010, from `f_get_lookback_bars(days) =>` through `int bars_to_hold = f_get_lookback_bars(total_days_calc)`, with:
```pine
// [FIX BPY] Holding period in bars from bars-per-year, not calendar days / bar length.
float hold_years = i_bt_unit == 'Days' ? i_bt_val / 365.25 : i_bt_unit == 'Weeks' ? i_bt_val * 7 / 365.25 : i_bt_unit == 'Months' ? i_bt_val / 12.0 : i_bt_val * 1.0
int bars_to_hold = math.max(math.min(int(math.round(hold_years * bpy)), 4800), 1)
```

### 3.3 and 3.4 One risk-free base, and CRP charged once
Replace L1415–L1420, from `yield_local_daily = local_rf_raw` through `float calc_crp = ...`, with:
```pine
yield_local_daily = local_rf_raw
yield_us_daily = us10y_true_raw
float auto_crp_raw = (yield_local_daily > yield_us_daily) ? (yield_local_daily - yield_us_daily) / 100 : 0.0
bool rf_local = i_rf_base == 'Local 10Y'
// [FIX CRP-1] In the local build the spread is already inside the base rate.
float auto_crp = (curr == 'USD' or rf_local) ? 0.0 : auto_crp_raw
float calc_erp = i_auto_calc_erp_crp ? auto_erp : i_erp_manual
float calc_crp = i_auto_calc_erp_crp ? auto_crp : i_crp_manual
```
- Change L1705 to `float base_rf_for_calc = rf_local ? us10y_yield / 100 : us10y_true_raw / 100`. The name `us10y_yield` is misleading: it holds the 90-day average of the **local** yield.
- Change L1771 to:
```pine
// [FIX CRP-2] CRP is charged once, in the cost of equity. Debt = same base + synthetic spread.
float cost_of_debt_synthetic = base_rf_for_calc + auto_credit_spread + (rf_local ? 0.0 : calc_crp)
```

### 3.5 RMW sign (Fama-French 5-factor)
Replace the two premium lines inside `if i_use_factors` (L1760–L1763) with:
```pine
if i_use_factors
    // [FIX RMW] In FF5 robust profitability earns a POSITIVE premium: a
    // robust firm loads positively on RMW, so its required return goes up.
    if current_op > 0.20
        rmw_premium := 0.015
    else if current_op < 0.05
        rmw_premium := -0.015
```

### 3.6 Clamp the tax rate in WACC
Change L1767 to `float effective_tax_rate = effective_tax // [FIX TAX] same 0-35% clamp as NOPAT`.

### 3.7 Z''-EM cutoffs
Replace L1292–L1294, from `if _is_bank_like and not na(altman_z_dd)` through `altman_z := f_locf(altman_z)`, with:
```pine
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
```
In the table (L2780–L2781), replace `bool is_z_safe = altman_z >= 1.8` and `bool is_z_golden = altman_z >= 3.0` with the lines below, at their existing indentation:
```pine
        bool is_z_safe = altman_z >= z_safe_cut
        bool is_z_golden = altman_z >= z_gold_cut
```
Directly **before** `f_cell(T, 0, row_idx, 'Z+M Risk Matrix', ...)` (L2801), add at the same indentation:
```pine
        risk_matrix_tooltip += z_is_em ? "\n\nScore is Z''-EM: safe > 5.85, distress < 4.35." : '\n\nScore is Altman Z: safe > 3.0, distress < 1.8.'
```

### 3.8 SBC proxy off by default
Change L911 to `float sbc_ttm = i_sbc_proxy ? math.max(nz(noncash_ttm, 0), 0) : 0.0`.

### 3.9 Finance sector routing
Replace L1565–L1569, from `else if sec == 'Finance'` through the `selected_industry := 'Financials (Bank/Insurance)'` under its `else`, with the block below. It sits inside `if i_industry == 'Auto-Detect'`, so it starts at 4 spaces.
```pine
    else if sec == 'Finance'
        string fin_ind = syminfo.industry
        if str.contains(fin_ind, 'Real Estate Investment Trust') or str.contains(syminfo.description, 'REIT')
            selected_industry := 'REITs'
        else if str.contains(fin_ind, 'Bank') or str.contains(fin_ind, 'Insurance') or str.contains(fin_ind, 'Brokers') or str.contains(fin_ind, 'Investment Managers') or str.contains(fin_ind, 'Finance/Rental') or str.contains(fin_ind, 'Financial Conglomerates')
            selected_industry := 'Financials (Bank/Insurance)'
        else
            // [FIX FIN-ROUTE] Property developers and other Finance-sector
            // operating companies: the bank model (NI / book, no EV) does not fit.
            selected_industry := 'General/Diversified'
```
Replace L2197 `bool use_bank_model = ...` with:
```pine
string _fin_ind = syminfo.industry
bool fin_bank_like = (str.contains(_fin_ind, 'Banks') and not str.contains(_fin_ind, 'Brokers')) or str.contains(_fin_ind, 'Insurance')
bool use_bank_model = is_financial_sector and (i_financial_model_type == 'Equity Model (Bank/Insurer)' or (i_financial_model_type == 'Auto (by industry)' and fin_bank_like))
```

### 3.10 RKV: drop value-trap observations instead of flooring them
Inside the ratio-push loop (L1479–L1480), replace
`if m.rkv and rkv_trip and not na(r) and r < 1.2` / `r := math.max(r, 1.0)` with the lines below, at their existing indentation:
```pine
        // [FIX RKV-FLOOR] A low P/B earned by sub-CoE returns is a deserved
        // discount. Flooring it at 1.0 pushed the average P/B UP and made value
        // traps look cheap. Drop the observation instead.
        if m.rkv and rkv_trip and not na(r) and r < 1.2
            r := na
```

### 3.11 r² with negative correlation
There is nothing to patch here: Phase 5 removes r² from the weights entirely.

**Check:** the WACC tooltip shows a beta roughly equal to the one you get on a weekly chart (within about 0.1). Downside beta should be above 0, not N/A, once there are about 12 down weeks of data. The green buy line should no longer sit at the 5% floor.

---

## Phase 4: Remove backtest look-ahead

### 4.1 New inputs
Add these inside the backtester inputs, after `i_bt_win_threshold` (L606):
```pine
i_report_lag = input.int(45, 'Report lag (days)', minval = 0, maxval = 120, group = group_bt, tooltip = 'request.financial returns a quarter\'s numbers from the START of the next period -- weeks before they were published. Each new value is held back this many days before the script may use it. 45 matches the usual filing deadline; 0 restores the old (look-ahead) behaviour. The latest value is always released on the last bar.')
i_flow_ttm = input.bool(true, 'Request flows as TTM', group = group_calc, tooltip = 'Income and cash-flow items are requested as TTM directly instead of summing four FQ values, so a missing quarter no longer gets padded. If a financial ID errors on TTM for your market, switch this off.')
```

### 4.2 Gated `f_fin`
Replace `f_fin` (L652–L653) with:
```pine
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
```

### 4.3 TTM requests for the flows
Directly **before** `float rev_fq = ...` (L798), add:
```pine
string flow_per = i_flow_ttm ? 'TTM' : 'FQ'
```
In these 12 lines, change `'FQ'` to `flow_per`. Keep the variable names; `_fq` now means "as requested".
`rev_fq, cogs_fq, ebit_fq, pretax_fq, inc_tax_fq, eps_fq, interest_fq, rnd_fq, ocf_fq, capex_fq, da_fq, noncash_fq`
Leave these on `'FQ'`: `pref_div_fq`, `div_ps_fq` and `minority_fq`, plus every balance-sheet line.

Then add this helper **after** `f_ttm_vault` (after L876):
```pine
f_flow(float x, bool trig) =>
    float vault = f_ttm_vault(x, trig)
    float held = f_locf(x)
    i_flow_ttm ? held : vault
```
In the TTM vault list (L877–L890), change `f_ttm_vault(` to `f_flow(` for the same 12 series. Leave `pref_div_ttm` and `div_per_share_ttm` on `f_ttm_vault`.

The optional `request.earnings()` upgrade (actual report dates instead of a fixed lag) is **not** included. It would work, but the fixed lag is simpler and leaves room in the request budget.

**Check:** the backtest's VACAGR and IC will probably **fall**. That is expected: the old numbers traded on reports before they existed. The table on the last bar should be unchanged.

---

## Phase 5: Weighting and an honest backtest

### 5.1 One weighting function
**Delete** these four functions: `f_get_error_metric` (L335–L367), `f_master_score`, `f_master_price_score` and `f_omni_weight` (L416–L498, including their comment blocks). **Keep** `f_get_price_error_metric`.
Paste this directly **after** `f_get_price_error_metric`, because it calls that function:
```pine
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
            [err, k] = f_get_price_error_metric(fv_s, px_s, base_algo)
            if not na(err) and k >= 4
                weight := 1.0 / math.max(err, 0.02)
                weight *= math.min(k / 12.0, 1.0)
    weight
// [FIX TIERS] Down-weight models built on carried or guessed inputs, using
// the provenance tiers (3 reported, 2 exact identity, 1 carried, 0 guess).
f_tier_q(int t) =>
    t >= 3 ? 1.0 : t == 2 ? 0.85 : t == 1 ? 0.6 : 0.3
f_wt_lbl(float w) =>
    w > 0 ? '  [' + str.tostring(w * 100, '#') + '%]' : ''
```
Add this input to `group_calc`:
```pine
i_w_horizon = input.int(4, 'Weighting: forecast horizon (quarters)', minval = 0, maxval = 8, group = group_calc, tooltip = 'Each model is scored on how well its fair value at quarter t predicted the price at t + N. 0 = same-quarter fit (closer to the old behaviour).')
```

### 5.2 Scores
Replace L2033–L2076, from `int corr_len = ...` through `total_score += array.get(MULTS, k).score`, with:
```pine
// ==============================================================
// === UNIFIED WEIGHTING ENGINE =================================
// ==============================================================
// Provenance of each model's main input. Same order as MULTS.
array<int> mult_tier = array.from(t_eps, t_rev, t_ocf, t_equity, t_equity, t_ebitda, t_ocf, t_ocf)
for k = 0 to 7
    Mult m = array.get(MULTS, k)
    m.score := m.on and not na(m.fv) and m.fv > 0 ? f_model_weight(m.fvhist, hist_px_tracker, i_weighting_algo, i_w_horizon) * f_tier_q(array.get(mult_tier, k)) : 0.0
f_sector_w(float fv, array<float> h, int tier) =>
    not na(fv) and fv > 0 ? f_model_weight(h, hist_px_tracker, i_weighting_algo, i_w_horizon) * f_tier_q(tier) : 0.0
float s_rnpv = f_sector_w(fv_rnpv, hist_fv_rnpv, t_ocf)
float s_ecf = f_sector_w(fv_ecf, hist_fv_ecf, t_ni)
float s_affo_dcf = f_sector_w(fv_affo_dcf, hist_fv_affo_dcf, t_ocf)
float s_unbundled = f_sector_w(fv_unbundled, hist_fv_unbundled, t_ocf)
float s_apv = f_sector_w(fv_apv, hist_fv_apv, t_ocf)
float s_eva = f_sector_w(fv_eva, hist_fv_eva, t_ebit)
float s_ddm = f_sector_w(fv_ddm, hist_fv_ddm, 3)
```
`hist_px_tracker` is a `var` at global scope, so `f_sector_w` can read it. If Pine complains about a function declared after a `var` it uses, move `f_sector_w` directly below `var array<float> hist_px_tracker` (L1979).

### 5.3 Blend with equal-weight fallback and visible weights
Replace the Phase 2.5 block (from `float blend_w_sum = 0.0` through `compositeHi := total_weighted_hi`) with:
```pine
// Tier factor + framework flag per blend slot (8 multiples, then 7 sector models).
array<float> blend_tq = array.from(f_tier_q(t_ocf), f_tier_q(t_ni), f_tier_q(t_ocf), f_tier_q(t_ocf), f_tier_q(t_ocf), f_tier_q(t_ebit), 1.0)
array<bool> blend_on = array.from(use_rnpv, use_ecf, use_affo_dcf, use_unbundled, use_apv, use_eva, use_ddm)
for k = 7 to 0
    array.unshift(blend_tq, f_tier_q(array.get(mult_tier, k)))
    array.unshift(blend_on, array.get(MULTS, k).on)
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
```

### 5.4 Omnibus uses the same weight
Directly **before** `for k = 0 to 22` in the Omnibus (L2357), add:
```pine
array<float> omni_tq = array.from(1.0)
for k = 0 to 14
    array.push(omni_tq, array.get(blend_tq, k))
for t in array.from(t_ocf, t_ni, t_ebit, t_eps, t_rev, t_ebit, t_ocf)
    array.push(omni_tq, f_tier_q(t))
```
Replace L2373 `float wk = nz(f_omni_weight(...), 0.0)` with the line below, at its existing indentation (4 spaces, inside the loop):
```pine
    float wk = o.on ? f_model_weight(o.hist, hist_px_tracker, i_weighting_algo, i_w_horizon) * array.get(omni_tq, k) : 0.0
```

### 5.5 Table: show every blended model with its weight
In the relative-multiple loop of the table (L2581–L2582), replace the `if m.on and m.score > 0` line and the `f_model_row(...)` line below it with:
```pine
            if m.on and not na(m.fv) and m.fv > 0
                f_model_row(T, row_idx, m.name + (m.syn ? ' *' : '') + f_wt_lbl(array.get(blend_w, k)), m.lo, m.fv, m.hi, (m.syn ? 'SYNTHETIC: fewer than 4 quarters of history, so the base multiple is a default, not observed.\n\n' : '') + f_mult_tt(m.avg, array.get(cur_mult, k), m.plo, m.phi))
```
For the sector rows, add the weight to each label:

| Row | New label |
|---|---|
| rNPV | `'rNPV (Risk-Adj)' + f_wt_lbl(array.get(blend_w, 8))` |
| Equity Cash Flow | `'Equity Cash Flow' + f_wt_lbl(array.get(blend_w, 9))` |
| AFFO DCF | `'AFFO DCF' + f_wt_lbl(array.get(blend_w, 10))` |
| Unbundled | `'Unbundled (SOTP)' + f_wt_lbl(array.get(blend_w, 11))` |
| APV | `'Adjusted PV (APV)' + f_wt_lbl(array.get(blend_w, 12))` |
| EVA | `'Economic Value Added' + f_wt_lbl(array.get(blend_w, 13))` |
| DDM | `'Dividend Discount (DDM)' + f_wt_lbl(array.get(blend_w, 14))` |

### 5.6 One entry margin for the chart and the backtest
Replace L2973–L2977, from `// 1. Recreate the Backtester's` through `visual_dynamic_margin := math.min(...)`, with:
```pine
// [FIX ZONE] ONE entry margin, used by both the chart and the backtester.
// The chart used downside beta (5%..50%), the backtest plain beta (>= 0.5x):
// the green line and the simulated entries disagreed.
float entry_margin = math.min(math.max(i_bt_margin * math.max(nz(downside_beta, beta_mkt), 0.5), 0.05), 0.50)
float visual_dynamic_margin = entry_margin
```
Change L3090 to `float bt_dyn_margin = entry_margin`.

### 5.7 Baseline row in the backtester
- After the `var affo_stats = ...` line (L3071), add `var base_stats = f_new_model()`.
- In `bt_models` (L3193), add `, base_stats` as the **last** element.
- After the `for v in array.from(iv_acquirer, ...)` loop (after L3200), add this, indented 4 spaces inside `if i_show_bt`:
```pine
    // [BASELINE] fv = 10x price: always "cheap", never hits target, so it
    // buys on every cooldown and exits at max hold -- a buy-and-hold proxy.
    array.push(bt_vals, close * 10)
```
- In `bt_labels` (L3436), add `, 'Baseline (always in)'` at the end. In `bt_alloc` (L3437), add `, true` at the end.
- Replace `f_bt_row` (L3390–L3397) with:
```pine
f_bt_row(tbl, row, name, ModelStats m, ModelStats b) =>
    if i_bt_view == 'Matrix (all periods)'
        f_fill_matrix_row(tbl, row, name, m)
    else if i_bt_view == 'Robustness verdict'
        f_fill_robust_row(tbl, row, name, m, b)
    else
        int which = i_bt_view == 'Focus: Period 1' ? 1 : i_bt_view == 'Focus: Period 2' ? 2 : 3
        f_fill_focus_row(tbl, row, name, m, which)
```
- In the row loop (L3446), change the call to `f_bt_row(bt_tbl, btrowidx, (allocated ? '' : '· ') + array.get(bt_labels, i), m, base_stats)`.
- In the Robustness header block (after the `"Verdict"` cell, about L3419), add this at the same indentation:
```pine
        table.cell(bt_tbl, 6, 0, "vs Base", bgcolor=th_bg, text_color=th_txt, text_size=size.small, tooltip="Average VACAGR edge over the always-in baseline across the three periods.")
```
- Replace the whole `f_fill_robust_row` function (L3336–L3385) with:
```pine
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
    // [FIX BASELINE] A model only earns "Stable" if it also beats simply
    // being invested, period by period.
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
            vtip := "Stable and positive, but not better than simply being invested. The fair value adds nothing over the market's own drift."
        else
            verdict := "Mixed"
            vcol := color.new(color.gray, 40)
            vtip := "No clean pattern. Treat as unproven rather than broken."
    table.cell(tbl, 0, row, name, bgcolor=color.new(color.black, 50), text_color=color.white, text_size=size.small, text_halign=text.align_left)
    table.cell(tbl, 1, row, na(v1) ? "-" : str.tostring(v1, "#.0"), bgcolor=color.new(color.black, 70), text_color=n1 < i_bt_min_n ? color.silver : color.white, text_size=size.small, tooltip="n=" + str.tostring(n1))
    table.cell(tbl, 2, row, na(v2) ? "-" : str.tostring(v2, "#.0"), bgcolor=color.new(color.black, 70), text_color=n2 < i_bt_min_n ? color.silver : color.white, text_size=size.small, tooltip="n=" + str.tostring(n2))
    table.cell(tbl, 3, row, na(v3) ? "-" : str.tostring(v3, "#.0"), bgcolor=color.new(color.black, 70), text_color=n3 < i_bt_min_n ? color.silver : color.white, text_size=size.small, tooltip="n=" + str.tostring(n3))
    table.cell(tbl, 4, row, enough ? str.tostring(spread, "#.0") : "-", bgcolor=color.new(color.black, 70), text_color=color.white, text_size=size.small)
    table.cell(tbl, 5, row, verdict, bgcolor=vcol, text_color=color.white, text_size=size.small, tooltip=vtip)
    table.cell(tbl, 6, row, enough ? (edge > 0 ? "+" : "") + str.tostring(edge, "#.0") : "-", bgcolor=enough ? (edge > 0 ? color.new(color.green, 60) : color.new(color.red, 60)) : color.new(color.black, 70), text_color=color.white, text_size=size.small)
    table.cell(tbl, 7, row, "", bgcolor=color.new(color.black, 100), text_size=size.small)
    table.cell(tbl, 8, row, "", bgcolor=color.new(color.black, 100), text_size=size.small)
```

**Check:** each blended row shows a `[xx%]` weight label, and the labels sum to about 100%. The Robustness view has a "vs Base" column and a Baseline row, and a model can now be graded "No edge".

---

## Phase 6: Cleanup

1. **Delete** `f_htf_close` (L659–L668). Nothing calls it after Phase 3.
2. Replace the request ledger comment (L627–L629) with:
```pine
// REQUEST LEDGER (hard cap = 40 per script)
// request.security      : 4  (US10Y, local 10Y, benchmark, small-cap ETF)
// request.currency_rate : 1
// request.financial     : 31
// TOTAL                 : 36 -> 4 slots free
// (best use of a free slot: request.earnings() for real report dates)
```
3. In the `// 3.2 MACRO FETCH` header, change `(4 security slots, ~20 series)` to `(2 security slots)`. Also delete the stale `// >>> RESERVE: 2 slots free...` comment (L840–L841).
4. **CAPE consistency:** after Phases 1 and 3, CAPE averages 10 yearly EPS readings spaced `bpy` bars apart, each inflated at `lr_infl`. It is consistent once the Phase 3.2 edit has replaced `bars_per_year` with `bpy`.
5. Optional: a yearly inflation table for backtests. I left it out, because every number in it would need checking against GSO/SBV/FRED first.

---

## Request budget
| | Before | After |
|---|---|---|
| request.security | 6 | 4 |
| request.currency_rate | 0 | 1 |
| request.financial | 33 | 31 |
| **Total** | **39** | **36** |
