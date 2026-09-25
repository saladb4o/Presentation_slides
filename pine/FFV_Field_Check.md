# FFV Field Check

One-off check: add it to a daily chart with maximum history and send back the table for a few tickers. Copy everything inside the code block into a new Pine Editor tab.

```pine
//@version=6
// FFV Field Check: how often each candidate field for the FFV companion has data on this
// symbol. Run it on your usual tickers (daily chart, as much history as loads) and send
// back the table. It also plots one test value to the Data Window only, to check whether
// another script can pick a Data-Window-only plot as its source.
indicator('FFV Field Check', overlay = true)

f(string id, string per) =>
    request.financial(syminfo.tickerid, id, per, ignore_invalid_symbol = true, currency = syminfo.currency)

var array<string> NAMES = array.from(
     'TOTAL_EQUITY FQ', 'SHRHLDRS_EQUITY FQ', 'BOOK_VALUE_PER_SHARE FQ', 'TOTAL_LIABILITIES FQ',
     'GROSS_PROFIT TTM', 'GROSS_MARGIN TTM', 'COGS_TO_REVENUE FQ',
     'EBITDA TTM', 'OPER_INCOME TTM', 'DEPRECIATION_DEPLETION FQ', 'EBITDA_MARGIN TTM',
     'CAPITAL_EXPENDITURES FQ', 'CAPEX_FIXED_ASSETS FQ', 'CAPEX_OTHER_ASSETS FQ',
     'CF_DEPRECIATION_N_AMORT FQ', 'AMORTIZATION FQ',
     'BASIC_SHARES_OUTSTANDING FQ', 'CASH_N_EQUIVALENTS FQ', 'LONG_TERM_DEBT FQ', 'ST_DEBT_EXCL_CURR_PORT FQ',
     'DEBT_TO_EQUITY FQ', 'CURRENT_RATIO FQ', 'TOTAL_CURRENT_ASSETS FQ', 'TOTAL_CURRENT_LIABILITIES FQ',
     'NET_INCOME TTM', 'IMPAIRMENTS FY', 'TOTAL_REVENUE TTM', 'PPE_TOTAL_NET FQ', 'DILUTED_SHARES FQ',
     'PURCHASE_OF_BUSINESS FQ', 'CHANGES_IN_WORKING_CAPITAL FQ', 'CHANGE_IN_INVENTORIES FQ',
     'CHANGE_IN_ACCOUNTS_RECEIVABLE FQ', 'CHANGE_IN_ACCOUNTS_PAYABLE FQ', 'NON_CASH_ITEMS FQ',
     'TOTAL_REVENUE FQ', 'TOTAL_REVENUE FY', 'NET_INCOME FY', 'FREE_CASH_FLOW FY')

array<float> v = array.from(
     f('TOTAL_EQUITY', 'FQ'), f('SHRHLDRS_EQUITY', 'FQ'), f('BOOK_VALUE_PER_SHARE', 'FQ'), f('TOTAL_LIABILITIES', 'FQ'),
     f('GROSS_PROFIT', 'TTM'), f('GROSS_MARGIN', 'TTM'), f('COGS_TO_REVENUE', 'FQ'),
     f('EBITDA', 'TTM'), f('OPER_INCOME', 'TTM'), f('DEPRECIATION_DEPLETION', 'FQ'), f('EBITDA_MARGIN', 'TTM'),
     f('CAPITAL_EXPENDITURES', 'FQ'), f('CAPITAL_EXPENDITURES_FIXED_ASSETS', 'FQ'), f('CAPITAL_EXPENDITURES_OTHER_ASSETS', 'FQ'),
     f('CASH_FLOW_DEPRECATION_N_AMORTIZATION', 'FQ'), f('AMORTIZATION', 'FQ'),
     f('BASIC_SHARES_OUTSTANDING', 'FQ'), f('CASH_N_EQUIVALENTS', 'FQ'), f('LONG_TERM_DEBT', 'FQ'), f('SHORT_TERM_DEBT_EXCL_CURRENT_PORT', 'FQ'),
     f('DEBT_TO_EQUITY', 'FQ'), f('CURRENT_RATIO', 'FQ'), f('TOTAL_CURRENT_ASSETS', 'FQ'), f('TOTAL_CURRENT_LIABILITIES', 'FQ'),
     f('NET_INCOME', 'TTM'), f('IMPAIRMENTS', 'FY'), f('TOTAL_REVENUE', 'TTM'), f('PPE_TOTAL_NET', 'FQ'), f('DILUTED_SHARES_OUTSTANDING', 'FQ'),
     f('PURCHASE_OF_BUSINESS', 'FQ'), f('CHANGES_IN_WORKING_CAPITAL', 'FQ'), f('CHANGE_IN_INVENTORIES', 'FQ'),
     f('CHANGE_IN_ACCOUNTS_RECEIVABLE', 'FQ'), f('CHANGE_IN_ACCOUNTS_PAYABLE', 'FQ'), f('NON_CASH_ITEMS', 'FQ'),
     f('TOTAL_REVENUE', 'FQ'), f('TOTAL_REVENUE', 'FY'), f('NET_INCOME', 'FY'), f('FREE_CASH_FLOW', 'FY'))
int N = 39

// Per field: bars with data, first bar with data. Coverage = bars with data / bars since
// the FIRST field of any kind had data (so a field that starts later scores lower).
var array<int> hits = array.new_int(N, 0)
var array<int> first_t = array.new_int(N, 0)
var int any_first = 0
var int bars = 0
bool any_now = false
for i = 0 to N - 1
    if not na(v.get(i))
        any_now := true
        hits.set(i, hits.get(i) + 1)
        if first_t.get(i) == 0
            first_t.set(i, time)
if any_now and any_first == 0
    any_first := time
if any_first > 0
    bars += 1

// Does a backup survive when its primary is missing? Bars where primary is na but backup
// has data, over bars where the primary is na.
// Pairs (primary index, backup index).
var array<int> PA = array.from(0, 0, 4, 7, 7, 11, 23, 3)
var array<int> PB = array.from(1, 2, 5, 8, 10, 12, 21, 0)
var array<int> p_miss = array.new_int(8, 0)
var array<int> p_fill = array.new_int(8, 0)
if any_first > 0
    for k = 0 to 7
        if na(v.get(PA.get(k)))
            p_miss.set(k, p_miss.get(k) + 1)
            if not na(v.get(PB.get(k)))
                p_fill.set(k, p_fill.get(k) + 1)

// Link test: pick this in another script's Source input. If it is not in the list, a
// Data-Window-only plot cannot be linked.
plot(v.get(26), 'FFV link test (TTM revenue)', display = display.data_window)

var table tb = table.new(position.top_right, 4, N + 11, bgcolor = color.new(color.black, 10), border_width = 1)
f_dt(int t) =>
    t == 0 ? '-' : str.format_time(t, 'yyyy-MM', syminfo.timezone)
if barstate.islast
    table.cell(tb, 0, 0, syminfo.ticker + ' (' + str.tostring(bars) + ' bars)', text_color = color.white, text_size = size.small)
    table.cell(tb, 1, 0, 'Coverage', text_color = color.white, text_size = size.small)
    table.cell(tb, 2, 0, 'First', text_color = color.white, text_size = size.small)
    table.cell(tb, 3, 0, 'Latest', text_color = color.white, text_size = size.small)
    for i = 0 to N - 1
        float c = bars > 0 ? hits.get(i) / float(bars) * 100 : 0.0
        color col = c >= 90 ? color.green : c >= 50 ? color.orange : color.red
        table.cell(tb, 0, i + 1, NAMES.get(i), text_color = color.white, text_size = size.tiny, text_halign = text.align_left)
        table.cell(tb, 1, i + 1, str.tostring(c, '#') + '%', text_color = col, text_size = size.tiny)
        table.cell(tb, 2, i + 1, f_dt(first_t.get(i)), text_color = color.white, text_size = size.tiny)
        table.cell(tb, 3, i + 1, na(v.get(i)) ? 'N/A' : str.tostring(v.get(i), format.volume), text_color = color.white, text_size = size.tiny)
    table.cell(tb, 0, N + 1, 'Backup fills primary gap', text_color = color.yellow, text_size = size.small)
    table.cell(tb, 1, N + 1, 'Gap bars', text_color = color.yellow, text_size = size.small)
    table.cell(tb, 2, N + 1, 'Filled', text_color = color.yellow, text_size = size.small)
    for k = 0 to 7
        int m = p_miss.get(k)
        table.cell(tb, 0, N + 2 + k, NAMES.get(PA.get(k)) + ' <- ' + NAMES.get(PB.get(k)), text_color = color.white, text_size = size.tiny, text_halign = text.align_left)
        table.cell(tb, 1, N + 2 + k, str.tostring(m), text_color = color.white, text_size = size.tiny)
        table.cell(tb, 2, N + 2 + k, m == 0 ? '-' : str.tostring(p_fill.get(k) / float(m) * 100, '#') + '%', text_color = color.white, text_size = size.tiny)

```
