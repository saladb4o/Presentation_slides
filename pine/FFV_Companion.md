# FFV Companion Feed

Add this to the same chart as Fundamental Fair Value Pro, then link its 14 plots in the main script's Companion Feed settings. Copy everything inside the code block into a new Pine Editor tab.

```pine
//@version=6
// FFV Companion Feed: fetches the line items Fundamental Fair Value Pro has no request slot
// for and hands them over as Data Window plots, which the main script links as sources.
// It only FETCHES and picks: every value enters the main script's data engine (or the
// owner-earnings formula there) as an input, where the exact identities, quality tiers,
// staleness cap and sanity checks apply. Nothing here is a finished valuation figure.
// Release timing is the main script's own (FFVLib.release), and the report lag is sealed
// into the check value so the two scripts cannot run on different lags.
indicator('FFV Companion Feed', overlay = true)
import YOUR_TV_USERNAME/FFVLib/2 as FL

i_lag = input.int(45, 'Report lag (days)', minval = 0, maxval = 120, tooltip = 'Must equal the main script setting: the check value carries it, and the main script ignores the feed on a mismatch.')
i_nc = input.bool(false, 'Owner earnings: add back other non-cash items', tooltip = 'Other non-cash items include stock-based compensation, which Buffett counts as a real cost. Off by default.')
i_acq = input.bool(false, 'Owner earnings: treat acquisitions as capital spending', tooltip = 'For companies that grow by buying businesses rather than building them.')
i_tbl = input.bool(true, 'Show table')

f(string id, string per) =>
    request.financial(syminfo.tickerid, id, per, ignore_invalid_symbol = true, currency = syminfo.currency)
float earn_raw = request.earnings(syminfo.tickerid, earnings.actual, ignore_invalid_symbol = true)
bool report_bar = not na(earn_raw) and (na(earn_raw[1]) or earn_raw != earn_raw[1])

// 31 requests (30 here + report dates). Index: 0-2 equity | 3-5 gross profit | 6-9 EBITDA |
// 10-12 capex | 13-14 cash-flow D&A (8 doubles as its backup) | 15-22 owner-earnings parts |
// 23 shares | 24 cash | 25-27 debt | 28-29 current liabilities.
array<float> raw = array.from(
     f('TOTAL_EQUITY', 'FQ'), f('SHRHLDRS_EQUITY', 'FQ'), f('BOOK_VALUE_PER_SHARE', 'FQ'),
     f('GROSS_PROFIT', 'TTM'), f('GROSS_MARGIN', 'TTM'), f('COGS_TO_REVENUE', 'FQ'),
     f('EBITDA', 'TTM'), f('OPER_INCOME', 'TTM'), f('DEPRECIATION_DEPLETION', 'FQ'), f('EBITDA_MARGIN', 'TTM'),
     f('CAPITAL_EXPENDITURES', 'FQ'), f('CAPITAL_EXPENDITURES_FIXED_ASSETS', 'FQ'), f('CAPITAL_EXPENDITURES_OTHER_ASSETS', 'FQ'),
     f('CASH_FLOW_DEPRECATION_N_AMORTIZATION', 'FQ'), f('AMORTIZATION', 'FQ'),
     f('IMPAIRMENTS', 'FY'), f('TOTAL_REVENUE', 'TTM'), f('PURCHASE_OF_BUSINESS', 'FQ'), f('CHANGES_IN_WORKING_CAPITAL', 'FQ'),
     f('CHANGE_IN_INVENTORIES', 'FQ'), f('CHANGE_IN_ACCOUNTS_RECEIVABLE', 'FQ'), f('CHANGE_IN_ACCOUNTS_PAYABLE', 'FQ'), f('NON_CASH_ITEMS', 'FQ'),
     f('BASIC_SHARES_OUTSTANDING', 'FQ'), f('CASH_N_EQUIVALENTS', 'FQ'),
     f('LONG_TERM_DEBT', 'FQ'), f('SHORT_TERM_DEBT_EXCL_CURRENT_PORT', 'FQ'), f('DEBT_TO_EQUITY', 'FQ'),
     f('CURRENT_RATIO', 'FQ'), f('TOTAL_CURRENT_ASSETS', 'FQ'))
int NR = 30
var array<float> pend = array.new_float(NR, na)
var array<float> known = array.new_float(NR, na)
var array<int> seen = array.new_int(NR, 0)
bool changed = FL.release(raw, pend, known, seen, i_lag, report_bar)
K(int i) =>
    known.get(i)
// TradingView margins may come as percent: a margin above 3 is read as percent.
pct(float x) =>
    na(x) ? na : math.abs(x) > 3 ? x / 100 : x

// ---------- QUARTER STORE ----------
// One row per quarter, newest first: the quarterly flows as released (a value repeating the
// previous quarter's exactly counts as missing: a frozen field), then the TTM
// working-capital change (for its 3-year average).
var array<int> FLOW = array.from(8, 10, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22)
int C_WC = 12
var matrix<float> Q = matrix.new<float>(0, 13, na)
f_fresh(float v) =>
    not na(v) and (na(v[1]) or v != v[1])
bool fr1 = f_fresh(K(16)), bool fr2 = f_fresh(K(0)), bool fr3 = f_fresh(K(10)), bool fr4 = f_fresh(K(13))
// Bars per year as the main script counts them; a new quarter needs 45 days since the last.
int tf_sec = math.max(timeframe.in_seconds(timeframe.period), 1)
float bpy = tf_sec < 86400 ? 252 * 23400.0 / tf_sec : tf_sec < 604800 ? 252 * 86400.0 / tf_sec : 365.25 * 86400.0 / tf_sec
int min_gap = math.max(1, int(bpy * 45 / 365.25))
var int last_q = -100000
if (fr1 or fr2 or fr3 or fr4) and bar_index - last_q >= min_gap
    last_q := bar_index
    Q.add_row(0, array.new_float(13, na))
    if Q.rows() > 16
        Q.remove_row(16)
// Column j from row r: na outside the store.
q(int r, int j) =>
    r < Q.rows() ? Q.get(r, j) : na
// TTM of flow column j starting at row r: the sum of 4 quarters; fewer are annualised from
// their mean (as the main script does); none -> na.
ttm(int r, int j) =>
    float s = 0.0
    int n = 0
    for k = r to r + 3
        float x = q(k, j)
        if not na(x)
            s += x
            n += 1
    n == 0 ? na : n == 4 ? s : s / n * 4.0
// The first available of up to three candidates, with its code: 1 reported, 2 built from
// reported parts, 3 from a ratio (the main script rates 3 one tier lower), 0 none.
pick(float a, int ca, float b, int cb, float c, int cc) =>
    float v = na
    int cd = 0
    if not na(a)
        v := a
        cd := ca
    else if not na(b)
        v := b
        cd := cb
    else if not na(c)
        v := c
        cd := cc
    [v, cd]

// ---------- OUTPUTS ----------
// 0 equity | 1 gross profit | 2 EBITDA | 3 capex (negative) | 4 cash-flow D&A |
// 5 impairments (last FY) | 6 working-capital change, 3-year average of TTM | 7 opt-in
// owner-earnings adjustment (non-cash items - acquisitions) | 8 shares | 9 cash |
// 10 total debt | 11 current liabilities.
var array<float> V = array.new_float(12, na)
var array<int> C = array.new_int(12, 0)
put(int i, float v, int c) =>
    V.set(i, v)
    C.set(i, na(v) ? 0 : c)
if Q.rows() > 0 and (changed or last_q == bar_index)
    // Rewrite the open quarter (late fields and restatements land here).
    for [k, i] in FLOW
        float x = K(i)
        float prev = q(1, k)
        Q.set(0, k, not na(prev) and x == prev ? na : x)
    float rev = K(16)
    float sh = K(23)
    [e, ce] = pick(K(0), 1, K(1), 2, K(2) * sh > 0 ? K(2) * sh : na, 3)
    put(0, e, ce)
    float gm = pct(K(4)), float cr = pct(K(5))
    [g, cg] = pick(K(3), 1, rev > 0 ? gm * rev : na, 3, rev > 0 ? rev * (1 - cr) : na, 3)
    put(1, g, cg)
    float da1 = ttm(0, 4), float dd = ttm(0, 0), float am = ttm(0, 5)
    float em = pct(K(9))
    [ed, ced] = pick(K(6), 1, K(7) + dd, 2, rev > 0 ? em * rev : na, 3)
    put(2, ed, ced)
    float cx1 = ttm(0, 1), float cxf = ttm(0, 2), float cxo = ttm(0, 3)
    [cx, ccx] = pick(-math.abs(cx1), 1, -(math.abs(cxf) + math.abs(nz(cxo))), 2, na, 0)
    put(3, cx, ccx)
    [d, cd] = pick(da1, 1, dd + nz(am), 2, na, 0)
    put(4, d, cd)
    // Owner-earnings parts (the main script adds net income, D&A and maintenance capex
    // from its own engine). Working capital: the cash-flow change (negative = build-up),
    // else inventories + receivables + payables changes; averaged over 3 years.
    put(5, math.abs(K(15)), 1)
    float wc_p = ttm(0, 8) + ttm(0, 9) + ttm(0, 10)
    Q.set(0, C_WC, nz(ttm(0, 7), wc_p))
    float ws = 0.0
    int wn = 0
    for y = 0 to 2
        float x = q(4 * y, C_WC)
        if not na(x)
            ws += x
            wn += 1
    put(6, wn > 0 ? ws / wn : na, na(ttm(0, 7)) ? 2 : 1)
    put(7, (i_nc ? nz(ttm(0, 11)) : 0.0) - (i_acq ? math.abs(nz(ttm(0, 6))) : 0.0), 1)
    put(8, sh > 0 ? sh : na, 2)
    put(9, K(24), 2)
    // Debt: long-term + short-term excluding the current portion of long-term debt, so it can
    // run short (rated as a ratio); else debt/equity x equity.
    float de = K(27)
    [db, cdb] = pick(not na(K(25)) ? K(25) + nz(K(26)) : na, 3, de >= 0 and e > 0 ? de * e : na, 3, na, 0)
    put(10, db, cdb)
    put(11, K(28) > 0 ? K(29) / K(28) : na, 3)

// ---------- HAND-OVER ----------
// Codes: report lag + 1000 x sum(code_i x 4^i), an exact integer. Check: weighted
// mantissas (FL.mant) of everything sent, so a link left on its default (the close) or
// swapped with another fails the main script's recomputation at any scale.
float csum = 0.0
float check = 0.0
for i = 0 to 11
    csum += C.get(i) * math.pow(4, i)
    check += (i + 2) * FL.mant(V.get(i))
float codes = i_lag + 1000.0 * csum
check += 14 * FL.mant(codes)
plot(V.get(0), 'FFV Equity', display = display.data_window)
plot(V.get(1), 'FFV Gross profit', display = display.data_window)
plot(V.get(2), 'FFV EBITDA', display = display.data_window)
plot(V.get(3), 'FFV Capex', display = display.data_window)
plot(V.get(4), 'FFV D&A', display = display.data_window)
plot(V.get(5), 'FFV Impairments', display = display.data_window)
plot(V.get(6), 'FFV Working capital', display = display.data_window)
plot(V.get(7), 'FFV OE adjustment', display = display.data_window)
plot(V.get(8), 'FFV Shares', display = display.data_window)
plot(V.get(9), 'FFV Cash', display = display.data_window)
plot(V.get(10), 'FFV Debt', display = display.data_window)
plot(V.get(11), 'FFV Current liabilities', display = display.data_window)
plot(codes, 'FFV Codes', display = display.data_window)
plot(check, 'FFV Check', display = display.data_window)

// ---------- TABLE ----------
var table tb = table.new(position.bottom_right, 3, 14, bgcolor = color.new(color.black, 10), border_width = 1)
var array<string> NM = array.from('Equity', 'Gross profit (TTM)', 'EBITDA (TTM)', 'Capex (TTM)', 'D&A, cash flow (TTM)', 'Impairments (last FY)', 'Working-capital change (3y avg)', 'OE adjustment (opt-in)', 'Shares (basic)', 'Cash & equivalents', 'Total debt', 'Current liabilities')
src(int c) =>
    c == 1 ? 'reported' : c == 2 ? 'parts / substitute' : c == 3 ? 'estimate / ratio' : 'missing'
if barstate.islast and i_tbl
    table.cell(tb, 0, 0, 'FFV Companion Feed', text_color = color.white, text_size = size.small)
    table.cell(tb, 1, 0, 'Value', text_color = color.white, text_size = size.small)
    table.cell(tb, 2, 0, 'Source', text_color = color.white, text_size = size.small)
    for i = 0 to 11
        float v = V.get(i)
        table.cell(tb, 0, i + 1, NM.get(i), text_color = color.white, text_size = size.small, text_halign = text.align_left)
        table.cell(tb, 1, i + 1, na(v) ? 'N/A' : str.tostring(v, format.volume), text_color = color.white, text_size = size.small)
        table.cell(tb, 2, i + 1, src(C.get(i)), text_color = color.gray, text_size = size.small)
    table.cell(tb, 0, 13, 'Report lag ' + str.tostring(i_lag) + ' days (must match main)', text_color = color.gray, text_size = size.small, text_halign = text.align_left)

```
