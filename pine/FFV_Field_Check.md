# FFV Field Check

One-off check: add it to a daily chart with maximum history and send back the table for a few tickers. Copy everything inside the code block into a new Pine Editor tab.

```pine
//@version=6
// FFV Field Check v2 (data overhaul): which fields the overhaul plans to use have data on this
// symbol, how far back they go, and how they are defined. Run it on a daily chart with as much
// history as loads (scroll back to the start) on HPG, FPT, MWG, VPB (HOSE), one US stock (e.g.
// AAPL) and one US REIT (e.g. O), and send back a screenshot of the whole table for each.
// It uses exactly 40 requests. The First column for the two FY rows vs their FQ rows shows
// whether yearly history starts earlier than quarterly.
indicator('FFV Field Check', overlay = true)

f(string id, string per) =>
    request.financial(syminfo.tickerid, id, per, ignore_invalid_symbol = true, currency = syminfo.currency)

var array<string> NAMES = array.from(
     'TOTAL_INVENTORY FQ', 'ACCOUNTS_PAYABLE FQ', 'CURRENT_PORT_DEBT_CAPITAL_LEASES FQ', 'ISSUANCE_OF_STOCK_NET FQ',
     'TOTAL_DEBT FQ', 'SHORT_TERM_DEBT FQ', 'LONG_TERM_DEBT FQ', 'LONG_TERM_DEBT_EXCL_CAPITAL_LEASE FQ',
     'CAPITAL_LEASE_OBLIGATIONS FQ', 'TOTAL_EQUITY FQ', 'SHRHLDRS_EQUITY FQ', 'COMMON_EQUITY_TOTAL FQ',
     'PREFERRED_STOCK_CARRYING_VALUE FQ', 'MINORITY_INTEREST FQ', 'BOOK_VALUE_PER_SHARE FQ', 'BASIC_SHARES_OUTSTANDING FQ',
     'TOTAL_SHARES_OUTSTANDING FQ', 'TOTAL_REVENUE FQ', 'GROSS_PROFIT FQ', 'EBITDA FQ',
     'OPER_INCOME FQ', 'EBIT FQ', 'INTEREST_EXPENSE_ON_DEBT FQ', 'INTERST_COVER FQ',
     'CASH_FLOW_DEPRECATION_N_AMORTIZATION FQ', 'CAPITAL_EXPENDITURES FQ', 'CAPITAL_EXPENDITURES_FIXED_ASSETS FQ', 'NET_INCOME FQ',
     'NET_INCOME_STARTING_LINE FQ', 'FUNDS_F_OPERATIONS FQ', 'CHANGES_IN_WORKING_CAPITAL FQ', 'COMMON_DIVIDENDS_CASH_FLOW FQ',
     'TOTAL_CASH_DIVIDENDS_PAID FQ', 'PREFERRED_DIVIDENDS FQ', 'PIOTROSKI_F_SCORE FQ', 'ALTMAN_Z_SCORE FQ',
     'BENEISH_M_SCORE FQ', 'CASH_CONVERSION_CYCLE FQ', 'TOTAL_REVENUE FY', 'NET_INCOME FY')

array<float> v = array.from(
     f('TOTAL_INVENTORY', 'FQ'), f('ACCOUNTS_PAYABLE', 'FQ'), f('CURRENT_PORT_DEBT_CAPITAL_LEASES', 'FQ'),
     f('ISSUANCE_OF_STOCK_NET', 'FQ'), f('TOTAL_DEBT', 'FQ'), f('SHORT_TERM_DEBT', 'FQ'),
     f('LONG_TERM_DEBT', 'FQ'), f('LONG_TERM_DEBT_EXCL_CAPITAL_LEASE', 'FQ'), f('CAPITAL_LEASE_OBLIGATIONS', 'FQ'),
     f('TOTAL_EQUITY', 'FQ'), f('SHRHLDRS_EQUITY', 'FQ'), f('COMMON_EQUITY_TOTAL', 'FQ'),
     f('PREFERRED_STOCK_CARRYING_VALUE', 'FQ'), f('MINORITY_INTEREST', 'FQ'), f('BOOK_VALUE_PER_SHARE', 'FQ'),
     f('BASIC_SHARES_OUTSTANDING', 'FQ'), f('TOTAL_SHARES_OUTSTANDING', 'FQ'), f('TOTAL_REVENUE', 'FQ'),
     f('GROSS_PROFIT', 'FQ'), f('EBITDA', 'FQ'), f('OPER_INCOME', 'FQ'),
     f('EBIT', 'FQ'), f('INTEREST_EXPENSE_ON_DEBT', 'FQ'), f('INTERST_COVER', 'FQ'),
     f('CASH_FLOW_DEPRECATION_N_AMORTIZATION', 'FQ'), f('CAPITAL_EXPENDITURES', 'FQ'), f('CAPITAL_EXPENDITURES_FIXED_ASSETS', 'FQ'),
     f('NET_INCOME', 'FQ'), f('NET_INCOME_STARTING_LINE', 'FQ'), f('FUNDS_F_OPERATIONS', 'FQ'),
     f('CHANGES_IN_WORKING_CAPITAL', 'FQ'), f('COMMON_DIVIDENDS_CASH_FLOW', 'FQ'), f('TOTAL_CASH_DIVIDENDS_PAID', 'FQ'),
     f('PREFERRED_DIVIDENDS', 'FQ'), f('PIOTROSKI_F_SCORE', 'FQ'), f('ALTMAN_Z_SCORE', 'FQ'),
     f('BENEISH_M_SCORE', 'FQ'), f('CASH_CONVERSION_CYCLE', 'FQ'), f('TOTAL_REVENUE', 'FY'),
     f('NET_INCOME', 'FY'))
int N = 40
int R0 = input.int(0, 'Start the table at field #', minval = 0, maxval = 39, tooltip = 'Set to 30 to see the last fields and the definition tests when the table runs off the screen.')

// Per field: bars with data, bars with exactly 0 (0 can mean "none" or "not reported"),
// negative bars, first bar with data. Coverage = bars with data / bars since any field had data.
var array<int> hits = array.new_int(N, 0)
var array<int> zeros = array.new_int(N, 0)
var array<int> negs = array.new_int(N, 0)
var array<int> first_t = array.new_int(N, 0)
var int any_first = 0
var int bars = 0
bool any_now = false
for i = 0 to N - 1
    float x = v.get(i)
    if not na(x)
        any_now := true
        hits.set(i, hits.get(i) + 1)
        if x == 0
            zeros.set(i, zeros.get(i) + 1)
        if x < 0
            negs.set(i, negs.get(i) + 1)
        if first_t.get(i) == 0
            first_t.set(i, time)
if any_now and any_first == 0
    any_first := time
if any_first > 0
    bars += 1

// Definition tests, counted over bars where every input is present: [bars tested, bars passed].
// Near: within tol of the larger side (or both under 1e-9). Signs are ignored where filers differ.
near(float a, float b, float tol = 0.01) =>
    math.abs(a - b) <= tol * math.max(math.abs(a), math.abs(b)) + 1e-9
float INV = v.get(0), float CP = v.get(2), float ISS = v.get(3)
float TD = v.get(4), float STD = v.get(5), float LTD = v.get(6)
float LTX = v.get(7), float CLO = v.get(8)
float TE = v.get(9), float SE = v.get(10), float CE = v.get(11)
float PS = v.get(12), float MI = v.get(13)
float BV = v.get(14), float BS = v.get(15), float TS = v.get(16)
float EBD = v.get(19), float OI = v.get(20), float EB = v.get(21), float INT = v.get(22)
float COV = v.get(23), float DA = v.get(24)
float CX = v.get(25), float CXF = v.get(26)
float NIS = v.get(28), float NI = v.get(27), float FFO = v.get(29)
float CDV = v.get(31), float TDV = v.get(32), float PDV = v.get(33)

// T12: sign of net stock issuance vs the change in share count, checked once per new share count.
var float last_ts = na
bool iss_have = false
bool iss_ok = false
if not na(TS) and (na(last_ts) or TS != last_ts)
    if not na(last_ts) and not na(ISS) and ISS != 0
        iss_have := true
        iss_ok := math.sign(ISS) == math.sign(TS - last_ts)
    last_ts := TS

var array<string> TN = array.from(
     'T1 TOTAL_DEBT = SHORT_TERM_DEBT + LONG_TERM_DEBT',
     'T2 LONG_TERM_DEBT = EXCL_CAPITAL_LEASE + CAPITAL_LEASE_OBLIG',
     'T3 TOTAL_EQUITY = SHRHLDRS_EQUITY + MINORITY_INTEREST',
     'T4 SHRHLDRS_EQUITY = COMMON_EQUITY_TOTAL + PREFERRED_STOCK',
     'T5 BVPS x BASIC_SHARES = SHRHLDRS_EQUITY (2%)',
     'T6 EBITDA = OPER_INCOME + CF D&A (2%)',
     'T7 EBIT = OPER_INCOME',
     'T8 INTERST_COVER = EBIT / |INTEREST| (5%, same quarter)',
     'T9 FFO = NET_INCOME_STARTING_LINE + CF D&A (5%)',
     'T10 |TOTAL_DIV_PAID| = |COMMON_DIV| + |PREFERRED_DIV| (2%)',
     'T11 CAPEX = CAPEX_FIXED_ASSETS (other parts 0)',
     'T12 ISSUANCE_OF_STOCK_NET sign = share count change',
     'T13 CURRENT_PORT <= SHORT_TERM_DEBT',
     'T14 NET_INCOME_STARTING_LINE = NET_INCOME (includes minority?)')
int NT = 14
var array<int> tn = array.new_int(NT, 0)
var array<int> tp = array.new_int(NT, 0)
f_t(int k, bool have, bool ok) =>
    if have
        tn.set(k, tn.get(k) + 1)
        if ok
            tp.set(k, tp.get(k) + 1)
f_t(0, not na(TD) and not na(STD) and not na(LTD), near(TD, STD + LTD))
f_t(1, not na(LTD) and not na(LTX) and not na(CLO), near(LTD, LTX + CLO))
f_t(2, not na(TE) and not na(SE) and not na(MI), near(TE, SE + MI))
f_t(3, not na(SE) and not na(CE) and not na(PS), near(SE, CE + PS))
f_t(4, not na(BV) and not na(BS) and not na(SE), near(BV * BS, SE, 0.02))
f_t(5, not na(EBD) and not na(OI) and not na(DA), near(EBD, OI + math.abs(DA), 0.02))
f_t(6, not na(EB) and not na(OI), near(EB, OI))
f_t(7, not na(COV) and not na(EB) and not na(INT) and INT != 0, near(COV, EB / math.abs(INT), 0.05))
f_t(8, not na(FFO) and not na(NIS) and not na(DA), near(FFO, NIS + math.abs(DA), 0.05))
f_t(9, not na(TDV) and not na(CDV) and not na(PDV), near(math.abs(TDV), math.abs(CDV) + math.abs(PDV), 0.02))
f_t(10, not na(CX) and not na(CXF), near(CX, CXF))
f_t(11, iss_have, iss_ok)
f_t(12, not na(CP) and not na(STD), CP <= STD * 1.01 + 1e-9)
f_t(13, not na(NIS) and not na(NI), near(NIS, NI))

var table tb = table.new(position.top_right, 6, N + NT + 3, bgcolor = color.new(color.black, 10), border_width = 1)
f_dt(int t) =>
    t == 0 ? '-' : str.format_time(t, 'yyyy-MM', syminfo.timezone)
f_c(int c, int r, string s, color col = color.white, string sz = size.tiny) =>
    table.cell(tb, c, r, s, text_color = col, text_size = sz, text_halign = c == 0 ? text.align_left : text.align_center)
if barstate.islast
    f_c(0, 0, syminfo.ticker + ' ' + syminfo.currency + ' (' + str.tostring(bars) + ' bars)', color.white, size.small)
    f_c(1, 0, 'Coverage', color.white, size.small)
    f_c(2, 0, 'Zero', color.white, size.small)
    f_c(3, 0, 'Negative', color.white, size.small)
    f_c(4, 0, 'First', color.white, size.small)
    f_c(5, 0, 'Latest', color.white, size.small)
    for i = R0 to N - 1
        int h = hits.get(i)
        float c = bars > 0 ? h / float(bars) * 100 : 0.0
        int r = i - R0 + 1
        f_c(0, r, NAMES.get(i))
        f_c(1, r, str.tostring(c, '#') + '%', c >= 90 ? color.green : c >= 50 ? color.orange : color.red)
        f_c(2, r, h == 0 ? '-' : str.tostring(zeros.get(i) / float(h) * 100, '#') + '%')
        f_c(3, r, h == 0 ? '-' : str.tostring(negs.get(i) / float(h) * 100, '#') + '%')
        f_c(4, r, f_dt(first_t.get(i)))
        f_c(5, r, na(v.get(i)) ? 'N/A' : str.tostring(v.get(i), format.volume))
    f_c(0, N - R0 + 1, 'Definition tests', color.yellow, size.small)
    f_c(1, N - R0 + 1, 'Bars tested', color.yellow, size.small)
    f_c(2, N - R0 + 1, 'Passed', color.yellow, size.small)
    for k = 0 to NT - 1
        int n = tn.get(k)
        float p = n > 0 ? tp.get(k) / float(n) * 100 : na
        f_c(0, N - R0 + 2 + k, TN.get(k))
        f_c(1, N - R0 + 2 + k, str.tostring(n))
        f_c(2, N - R0 + 2 + k, n == 0 ? '-' : str.tostring(p, '#') + '%', n == 0 ? color.gray : p >= 90 ? color.green : p >= 50 ? color.orange : color.red)

```
