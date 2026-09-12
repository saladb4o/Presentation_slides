"""Verified observations for the ECON1596 Assessment 2 data workbook.

Each row is one observation:

    (series_code, indicator, geo, year, value, unit, denominator, flag,
     source_id, note)

Flags follow Eurostat conventions:
    b  break in series (definition or denominator changed)
    e  estimate
    p  provisional
    d  definition differs
    u  low reliability

RULE OF THIS FILE: a value is present only if it was verified against the issuing
authority named in its source_id. Nothing here is interpolated, smoothed, or
inferred from a neighbouring year. Gaps are real gaps and are left as gaps.
"""

OBS = [
    # ------------------------------------------------------------------
    # Payments - Danmarks Nationalbank, Danskernes betalingsvaner
    # Denominator for the three share-of-payments series is uniform, which is
    # what makes them safe to plot on one axis (see F2).
    # ------------------------------------------------------------------
    ("DK.PAY.CASH.POS", "Cash share of payments, physical retail", "DK", 2017, 23.0,
     "%", "share of number of payments in physical retail", "", "NB1", ""),
    ("DK.PAY.CASH.POS", "Cash share of payments, physical retail", "DK", 2023, 11.0,
     "%", "share of number of payments in physical retail", "", "NB1", ""),
    ("DK.PAY.CASH.POS", "Cash share of payments, physical retail", "DK", 2025, 9.0,
     "%", "share of number of payments in physical retail", "", "NB1", ""),

    ("DK.PAY.CRD.PHYS", "Physical payment card share of payments", "DK", 2017, 73.0,
     "%", "share of number of payments in physical retail", "", "NB1", ""),
    ("DK.PAY.CRD.PHYS", "Physical payment card share of payments", "DK", 2025, 54.0,
     "%", "share of number of payments in physical retail", "", "NB1", ""),

    ("DK.PAY.WLT.SHR", "Mobile wallet share of payments", "DK", 2025, 32.0,
     "%", "share of number of payments in physical retail", "", "NB1",
     "Card-based wallets on mobile phones (e.g. Apple Pay, Google Pay)."),

    ("DK.PAY.DIG.POS.NUM", "Digital share of payments, by number", "DK", 2025, 91.0,
     "%", "share of number of payments in physical retail", "", "NB1", ""),
    ("DK.PAY.DIG.POS.VAL", "Digital share of payments, by value", "DK", 2025, 93.0,
     "%", "share of value of payments in physical retail", "", "NB1",
     "Different denominator from the by-number series - do not plot together."),

    # Memo series: different denominator (% of citizens, not % of payments).
    # Deliberately excluded from the F2 chart for that reason.
    ("DK.PAY.WLT.OWN", "Citizens holding a mobile wallet solution", "DK", 2019, 12.0,
     "%", "% of citizens", "", "NB1", "Memo only - denominator differs from F2 series."),
    ("DK.PAY.WLT.OWN", "Citizens holding a mobile wallet solution", "DK", 2023, 41.0,
     "%", "% of citizens", "", "NB1", "Memo only - denominator differs from F2 series."),
    ("DK.PAY.WLT.OWN", "Citizens holding a mobile wallet solution", "DK", 2025, 51.0,
     "%", "% of citizens", "", "NB1", "Memo only - denominator differs from F2 series."),

    # ------------------------------------------------------------------
    # Banking structure - Finans Danmark
    # ------------------------------------------------------------------
    ("DK.FIN.BRCH", "Bank branches", "DK", 2004, 2025, "count", "branches", "", "FD1", ""),
    ("DK.FIN.BRCH", "Bank branches", "DK", 2006, 1975, "count", "branches", "", "FD1", ""),
    ("DK.FIN.BRCH", "Bank branches", "DK", 2010, 1598, "count", "branches", "", "FD1", ""),
    ("DK.FIN.BRCH", "Bank branches", "DK", 2016, 948, "count", "branches", "", "FD1", ""),
    ("DK.FIN.BRCH", "Bank branches", "DK", 2021, 701, "count", "branches", "", "FD1", ""),
    ("DK.FIN.BRCH", "Bank branches", "DK", 2024, 665, "count", "branches", "", "FD1", ""),

    ("DK.FIN.INST", "Financial institutions", "DK", 1991, 219, "count", "institutions", "", "FD1", ""),
    ("DK.FIN.INST", "Financial institutions", "DK", 2024, 51, "count", "institutions", "", "FD1", ""),

    ("DK.FIN.EMP", "Bank employees", "DK", 1991, 51000, "count", "persons employed", "e", "FD1",
     "Source states 'around 51,000'."),
    ("DK.FIN.EMP", "Bank employees", "DK", 2024, 36000, "count", "persons employed", "e", "FD1",
     "Source states 'just under 36,000'."),

    # ------------------------------------------------------------------
    # E-commerce, individuals - Eurostat
    # DENOMINATOR BREAK: 2019 is % of individuals; 2020 onward is % of internet
    # users. These must not be plotted as one continuous series.
    # ------------------------------------------------------------------
    ("DK.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DK", 2019, 84.0,
     "%", "% of individuals", "b", "ES1",
     "BREAK: denominator is % of individuals. Highest in EU that year."),
    ("DK.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DK", 2020, 90.0,
     "%", "% of internet users", "", "ES2", ""),
    ("DK.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DK", 2021, 92.0,
     "%", "% of internet users", "", "ES3", ""),
    ("DK.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DK", 2024, 91.0,
     "%", "% of internet users", "", "ES4", ""),

    ("EU.ECM.IND.BUY", "Individuals who bought online in last 12 months", "EU27", 2014, 59.0,
     "%", "% of internet users", "", "ES4", ""),
    ("EU.ECM.IND.BUY", "Individuals who bought online in last 12 months", "EU27", 2024, 77.0,
     "%", "% of internet users", "", "ES4", ""),

    # 2024 cross-section, verified countries only (8 of 27).
    ("IE.ECM.IND.BUY", "Individuals who bought online in last 12 months", "IE", 2024, 96.0,
     "%", "% of internet users", "", "ES4", "Highest in EU."),
    ("NL.ECM.IND.BUY", "Individuals who bought online in last 12 months", "NL", 2024, 94.0,
     "%", "% of internet users", "", "ES4", ""),
    ("DE.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DE", 2024, 83.0,
     "%", "% of internet users", "", "ES4", "Ranked 8th in EU."),
    ("IT.ECM.IND.BUY", "Individuals who bought online in last 12 months", "IT", 2024, 60.0,
     "%", "% of internet users", "", "ES4", ""),
    ("RO.ECM.IND.BUY", "Individuals who bought online in last 12 months", "RO", 2024, 60.0,
     "%", "% of internet users", "", "ES4", ""),
    ("BG.ECM.IND.BUY", "Individuals who bought online in last 12 months", "BG", 2024, 57.0,
     "%", "% of internet users", "", "ES4", "Lowest in EU."),

    # ------------------------------------------------------------------
    # E-commerce, enterprises - Eurostat
    # ------------------------------------------------------------------
    ("DK.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "DK", 2014, 17.05,
     "%", "% of total enterprise turnover", "", "ES5", ""),
    ("DK.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "DK", 2024, 33.31,
     "%", "% of total enterprise turnover", "", "ES5", "2nd in EU after Ireland."),
    ("EU.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "EU27", 2014, 16.43,
     "%", "% of total enterprise turnover", "", "ES5", ""),
    ("EU.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "EU27", 2024, 19.49,
     "%", "% of total enterprise turnover", "", "ES5", ""),
    ("IE.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "IE", 2024, 38.25,
     "%", "% of total enterprise turnover", "", "ES5", "Highest in EU."),

    # Additional 2024 adoption values named in the Eurostat press release.
    ("HU.ECM.IND.BUY", "Individuals who bought online in last 12 months", "HU", 2024, 79.0,
     "%", "% of internet users", "", "ES4", "Rose 37pp from 42% in 2014."),
    ("LT.ECM.IND.BUY", "Individuals who bought online in last 12 months", "LT", 2024, 72.0,
     "%", "% of internet users", "", "ES4", "Rose 36pp from 36% in 2014."),

    # ------------------------------------------------------------------
    # E-sales share of enterprise turnover, EU cross-section 2024.
    # Flagged 'u': these country-level values were retrieved via search of
    # Eurostat tin00110 rather than from the databrowser directly. Two of them
    # (EU27 19.49 and IE 38.25) are independently corroborated by source ES5,
    # which raises confidence in the column, but every value should be
    # spot-checked against the databrowser before final submission.
    # ------------------------------------------------------------------
    ("BE.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "BE", 2024, 29.51,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("SE.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "SE", 2024, 26.32,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("CZ.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "CZ", 2024, 25.65,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("LU.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "LU", 2024, 23.86,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("HU.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "HU", 2024, 21.35,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("DE.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "DE", 2024, 19.05,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("AT.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "AT", 2024, 18.96,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("HR.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "HR", 2024, 18.48,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("ES.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "ES", 2024, 18.27,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("PL.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "PL", 2024, 17.66,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("SI.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "SI", 2024, 16.78,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("IT.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "IT", 2024, 15.66,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("MT.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "MT", 2024, 15.46,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("FR.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "FR", 2024, 14.25,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("CY.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "CY", 2024, 13.36,
     "%", "% of total enterprise turnover", "u", "ES6", ""),
    ("BG.ECM.ENT.TRN", "E-sales as share of enterprise turnover", "BG", 2024, 7.63,
     "%", "% of total enterprise turnover", "u", "ES6", ""),

    ("DK.ECM.ENT.SHR", "Enterprises making e-sales", "DK", 2024, 38.78,
     "%", "% of enterprises", "", "ES5", "2nd in EU after Lithuania."),
    ("LT.ECM.ENT.SHR", "Enterprises making e-sales", "LT", 2024, 43.03,
     "%", "% of enterprises", "", "ES5", "Highest in EU."),

    # ------------------------------------------------------------------
    # Digital Post and digital exclusion
    # Five measures of the same underlying phenomenon on five definitions.
    # The spread between them is the analytical point, not a data problem.
    # ------------------------------------------------------------------
    ("DK.DGP.EXMP", "Citizens formally exempt from Digital Post", "DK", 2025, 5.0,
     "%", "% of citizens aged 15+ resident in Denmark", "", "DG1",
     "April 2025; approx. 256,000 citizens."),
    ("DK.DGP.EXMP", "Citizens formally exempt from Digital Post", "DK", 2026, 4.7,
     "%", "% of citizens aged 15+ resident in Denmark", "", "DG1",
     "Q1 2026; 238,479 citizens. 95.2% enrolled."),

    ("DK.DGP.EXMP.7584", "Exemption rate, age 75-84", "DK", 2022, 20.0,
     "%", "% of age group", "e", "DG1", "Source states 'nearly one in five'."),
    ("DK.DGP.EXMP.85P", "Exemption rate, age 85+", "DK", 2022, 33.0,
     "%", "% of age group", "e", "DG1", "Source states 'roughly one in three'."),

    ("DK.DGX.NOUSE", "Do not use digital public services at all", "DK", 2026, 6.5,
     "%", "% of population", "", "EC1", "Agency for Digital Government estimate."),
    ("DK.DGX.DIFF", "Face difficulties using digital public services", "DK", 2026, 16.5,
     "%", "% of population", "", "EC1", "Agency for Digital Government estimate."),
    ("DK.DGX.DISADV.LO", "'Digitally disadvantaged' - lower bound", "DK", 2025, 17.0,
     "%", "% of adult population", "e", "DG2", "Published as a 17-22% range."),
    ("DK.DGX.DISADV.HI", "'Digitally disadvantaged' - upper bound", "DK", 2025, 22.0,
     "%", "% of adult population", "e", "DG2", "Published as a 17-22% range."),
    ("DK.DGX.JUST", "'Digitally disadvantaged' - Justitia estimate", "DK", 2022, 25.0,
     "%", "% of adult population", "e", "JU1",
     "Report states 'up to a quarter of the adult population'."),

    # ------------------------------------------------------------------
    # Trust - European Commission Digital Decade country report
    # ------------------------------------------------------------------
    ("DK.TRU.DPS", "Trust in digital public solutions", "DK", 2024, 82.0,
     "%", "% of population", "", "EC1", ""),
    ("DK.TRU.DPS", "Trust in digital public solutions", "DK", 2025, 84.0,
     "%", "% of population", "", "EC1", "Record high."),
    ("DK.TRU.DGP.SEC", "Perceived security of Digital Post", "DK", 2017, 77.0,
     "%", "% of population", "", "EC1", ""),
    ("DK.TRU.DGP.SEC", "Perceived security of Digital Post", "DK", 2025, 89.0,
     "%", "% of population", "", "EC1", ""),

    # ------------------------------------------------------------------
    # Digital skills by age - European Commission Digital Decade report
    # ------------------------------------------------------------------
    ("DK.SKL.1624", "At least basic digital skills, age 16-24", "DK", 2025, 92.06,
     "%", "% of age group", "", "EC1", "EU average 74.55%."),
    ("DK.SKL.2554", "At least basic digital skills, age 25-54", "DK", 2025, 86.89,
     "%", "% of age group", "", "EC1", "EU average 68.57%."),
    ("DK.SKL.5574", "At least basic digital skills, age 55-74", "DK", 2025, 67.81,
     "%", "% of age group", "", "EC1", "EU average 42.60%."),

    # ------------------------------------------------------------------
    # Enterprise digitalisation and public services - European Commission
    # ------------------------------------------------------------------
    ("DK.ENT.DII", "SMEs with at least basic digital intensity", "DK", 2025, 92.45,
     "%", "% of SMEs", "", "EC1", "EU average 71.39%."),
    ("EU.ENT.DII", "SMEs with at least basic digital intensity", "EU27", 2025, 71.39,
     "%", "% of SMEs", "", "EC1", ""),
    ("DK.ENT.AI", "Enterprises adopting AI", "DK", 2025, 42.03,
     "%", "% of enterprises", "", "EC1", "EU average 19.95%."),
    ("DK.ENT.AI.LRG", "Large enterprises adopting AI", "DK", 2025, 74.52,
     "%", "% of large enterprises (250+)", "", "EC1", ""),
    ("DK.ENT.AI.SME", "SMEs adopting AI", "DK", 2025, 40.99,
     "%", "% of SMEs (10-249)", "", "EC1", ""),

    ("DK.GOV.DPS.CIT", "Digital public services for citizens (score)", "DK", 2025, 82.2,
     "score 0-100", "eGovernment Benchmark score", "", "EC1",
     "BELOW the EU average of 84.64."),
    ("EU.GOV.DPS.CIT", "Digital public services for citizens (score)", "EU27", 2025, 84.64,
     "score 0-100", "eGovernment Benchmark score", "", "EC1", ""),
    ("DK.GOV.DPS.XB", "Cross-border digital public services, citizens (score)", "DK", 2025, 64.4,
     "score 0-100", "eGovernment Benchmark score", "", "EC1", "EU average 75.28."),

    # ------------------------------------------------------------------
    # Environment - European Commission (candidate SDG evidence)
    # ------------------------------------------------------------------
    ("DK.ENV.WEEE", "ICT waste recycled or prepared for reuse", "DK", 2023, 15.37,
     "%", "% of ICT-related WEEE collected", "", "EC1",
     "Among the lowest in the EU; EU average 80.23%."),
    ("EU.ENV.WEEE", "ICT waste recycled or prepared for reuse", "EU27", 2023, 80.23,
     "%", "% of ICT-related WEEE collected", "", "EC1", ""),

    # ------------------------------------------------------------------
    # SME policy
    # ------------------------------------------------------------------
    ("DK.SME.SMVD.PROJ", "SMV:Digital projects supported since 2018", "DK", 2025, 7000,
     "count", "digitalisation projects", "e", "DG3",
     "Source states 'knap 7.000' (just under 7,000)."),
    ("DK.SME.SMVD.INV", "Participants who invested further during the project", "DK", 2025, 65.0,
     "%", "% of participating enterprises", "", "DG3", ""),
    ("DK.SME.SMVD.NOINV", "Participants with no further investment plans", "DK", 2025, 2.0,
     "%", "% of participating enterprises", "", "DG3", ""),
]


COUNTRIES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus",
    "CZ": "Czechia", "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "EL": "Greece", "ES": "Spain", "FI": "Finland", "FR": "France",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta",
    "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia",
}


def cross_section(year=2024):
    """Split EU countries into complete (X and Y) and incomplete pairs.

    X = XX.ECM.IND.BUY (adoption), Y = XX.ECM.ENT.TRN (economic outcome).
    The EU27 aggregate is excluded - it is not an observation.

    Returns (paired, awaiting_x, awaiting_y), each a list of ISO codes. The
    split is recomputed at build time, so adding observations to OBS moves a
    country into the plotted table automatically on the next rebuild.
    """
    have = {}
    for code, _ind, geo, yr, *_ in OBS:
        if yr != year or geo not in COUNTRIES:
            continue
        if code.endswith(".ECM.IND.BUY"):
            have.setdefault(geo, {})["x"] = True
        elif code.endswith(".ECM.ENT.TRN"):
            have.setdefault(geo, {})["y"] = True

    paired = sorted(c for c, d in have.items() if d.get("x") and d.get("y"))
    awaiting_x = sorted(c for c, d in have.items() if d.get("y") and not d.get("x"))
    awaiting_y = sorted(c for c, d in have.items() if d.get("x") and not d.get("y"))
    return paired, awaiting_x, awaiting_y


def validate():
    """Structural checks on the dataset. Raises AssertionError on failure."""
    from sources import SOURCES

    seen = set()
    for row in OBS:
        assert len(row) == 10, f"wrong column count: {row[:3]}"
        code, ind, geo, year, val, unit, denom, flag, src, note = row
        key = (code, geo, year)
        assert key not in seen, f"duplicate observation: {key}"
        seen.add(key)
        assert src in SOURCES, f"unknown source_id {src!r} on {code} {year}"
        assert unit, f"missing unit on {code} {year}"
        assert denom, f"missing denominator on {code} {year}"
        assert isinstance(val, (int, float)), f"non-numeric value on {code} {year}"
        assert flag in ("", "b", "e", "p", "d", "u"), f"bad flag {flag!r} on {code}"

    # The denominator break on the Danish online-purchasing series must be flagged.
    row_2019 = [r for r in OBS if r[0] == "DK.ECM.IND.BUY" and r[3] == 2019][0]
    assert row_2019[7] == "b", "2019 online-purchasing row must carry flag 'b'"
    assert row_2019[6] != [r for r in OBS
                           if r[0] == "DK.ECM.IND.BUY" and r[3] == 2020][0][6], \
        "2019 and 2020 denominators must differ"

    return len(OBS)


if __name__ == "__main__":
    print(f"{validate()} observations validated")
