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
    # E-government adoption - Eurostat isoc_ciegi_ac
    # The locating indicator: it measures what individuals did, not what the
    # state provided, and Denmark and the EU-27 are published on the same base
    # (all individuals aged 16-74, not internet users), so the two are
    # directly comparable without adjustment.
    # ------------------------------------------------------------------
    ("DK.DGX.EGOV.USE", "Individuals interacting with public authorities online",
     "DK", 2024, 98.5, "%", "individuals aged 16 to 74", "", "ES9",
     "Website or app of a public authority, last 12 months. Highest in EU-27."),
    ("EU.DGX.EGOV.USE", "Individuals interacting with public authorities online",
     "EU27", 2024, 70.0, "%", "individuals aged 16 to 74", "", "ES9",
     "EU-27 aggregate, same base and reference period as the Danish value."),

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
     "%", "% of internet users", "", "ES2",
     "Rounded, from a Eurostat news release. Only the 2024 cross-section is "
     "available here unrounded, so this series mixes precisions across years."),
    ("DK.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DK", 2021, 92.0,
     "%", "% of internet users", "", "ES3",
     "Rounded, from a Eurostat news release. See the 2020 note on mixed precision."),

    # ------------------------------------------------------------------
    # 2024 cross-section, COMPLETE: all 27 member states plus the EU-27
    # aggregate, from the isoc_ec_ib20 databrowser export (ES7). Unrounded,
    # and superseding the ten rounded figures previously taken from the
    # Eurostat press release, which named only the top three, bottom three
    # and two large movers. Each superseded value is recorded in the note
    # field of its row rather than erased.
    # ------------------------------------------------------------------
    ("EU.ECM.IND.BUY", "Individuals who bought online in last 12 months", "EU27", 2024, 76.58,
     "%", "% of internet users", "", "ES7", ""),
    ("AT.ECM.IND.BUY", "Individuals who bought online in last 12 months", "AT", 2024, 74.18,
     "%", "% of internet users", "", "ES7", ""),
    ("BE.ECM.IND.BUY", "Individuals who bought online in last 12 months", "BE", 2024, 78.98,
     "%", "% of internet users", "", "ES7", ""),
    ("BG.ECM.IND.BUY", "Individuals who bought online in last 12 months", "BG", 2024, 57.18,
     "%", "% of internet users", "", "ES7",
     "Lowest of the 27, as the press release reported. Supersedes the "
     "rounded 57%."),
    ("CY.ECM.IND.BUY", "Individuals who bought online in last 12 months", "CY", 2024, 68.16,
     "%", "% of internet users", "", "ES7", ""),
    ("CZ.ECM.IND.BUY", "Individuals who bought online in last 12 months", "CZ", 2024, 86.21,
     "%", "% of internet users", "", "ES7", ""),
    ("DE.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DE", 2024, 82.53,
     "%", "% of internet users", "", "ES7",
     "Supersedes the rounded 83%."),
    ("DK.ECM.IND.BUY", "Individuals who bought online in last 12 months", "DK", 2024, 90.86,
     "%", "% of internet users", "", "ES7",
     "Supersedes the rounded 91% taken from the Eurostat press release."),
    ("EE.ECM.IND.BUY", "Individuals who bought online in last 12 months", "EE", 2024, 78.72,
     "%", "% of internet users", "", "ES7", ""),
    ("EL.ECM.IND.BUY", "Individuals who bought online in last 12 months", "EL", 2024, 74.66,
     "%", "% of internet users", "", "ES7", ""),
    ("ES.ECM.IND.BUY", "Individuals who bought online in last 12 months", "ES", 2024, 71.54,
     "%", "% of internet users", "", "ES7", ""),
    ("FI.ECM.IND.BUY", "Individuals who bought online in last 12 months", "FI", 2024, 80.4,
     "%", "% of internet users", "", "ES7", ""),
    ("FR.ECM.IND.BUY", "Individuals who bought online in last 12 months", "FR", 2024, 84.37,
     "%", "% of internet users", "", "ES7", ""),
    ("HR.ECM.IND.BUY", "Individuals who bought online in last 12 months", "HR", 2024, 70.07,
     "%", "% of internet users", "", "ES7", ""),
    ("HU.ECM.IND.BUY", "Individuals who bought online in last 12 months", "HU", 2024, 78.87,
     "%", "% of internet users", "", "ES7",
     "Supersedes the rounded 79%."),
    ("IE.ECM.IND.BUY", "Individuals who bought online in last 12 months", "IE", 2024, 95.79,
     "%", "% of internet users", "", "ES7",
     "Highest in EU. Supersedes the rounded 96%."),
    ("IT.ECM.IND.BUY", "Individuals who bought online in last 12 months", "IT", 2024, 59.6,
     "%", "% of internet users", "", "ES7",
     "Second lowest of the 27. Supersedes the rounded 60%, which tied Italy "
     "with Romania; unrounded Italy is below Romania, so they are not tied."),
    ("LT.ECM.IND.BUY", "Individuals who bought online in last 12 months", "LT", 2024, 71.96,
     "%", "% of internet users", "", "ES7",
     "Supersedes the rounded 72%."),
    ("LU.ECM.IND.BUY", "Individuals who bought online in last 12 months", "LU", 2024, 81.34,
     "%", "% of internet users", "", "ES7", ""),
    ("LV.ECM.IND.BUY", "Individuals who bought online in last 12 months", "LV", 2024, 69.35,
     "%", "% of internet users", "", "ES7", ""),
    ("MT.ECM.IND.BUY", "Individuals who bought online in last 12 months", "MT", 2024, 73.2,
     "%", "% of internet users", "", "ES7", ""),
    ("NL.ECM.IND.BUY", "Individuals who bought online in last 12 months", "NL", 2024, 94.42,
     "%", "% of internet users", "", "ES7",
     "Supersedes the rounded 94%."),
    ("PL.ECM.IND.BUY", "Individuals who bought online in last 12 months", "PL", 2024, 75.07,
     "%", "% of internet users", "", "ES7", ""),
    ("PT.ECM.IND.BUY", "Individuals who bought online in last 12 months", "PT", 2024, 66.64,
     "%", "% of internet users", "", "ES7", ""),
    ("RO.ECM.IND.BUY", "Individuals who bought online in last 12 months", "RO", 2024, 59.73,
     "%", "% of internet users", "", "ES7",
     "Supersedes the rounded 60%. See the Italy note on the tie."),
    ("SE.ECM.IND.BUY", "Individuals who bought online in last 12 months", "SE", 2024, 89.89,
     "%", "% of internet users", "", "ES7", ""),
    ("SI.ECM.IND.BUY", "Individuals who bought online in last 12 months", "SI", 2024, 72.39,
     "%", "% of internet users", "", "ES7", ""),
    ("SK.ECM.IND.BUY", "Individuals who bought online in last 12 months", "SK", 2024, 85.13,
     "%", "% of internet users", "", "ES7", ""),

    ("EU.ECM.IND.BUY", "Individuals who bought online in last 12 months", "EU27", 2014, 59.0,
     "%", "% of internet users", "", "ES4", ""),


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
     "%", "% of age group", "", "EC1", "EU average carried as EU.SKL.1624."),
    ("DK.SKL.2554", "At least basic digital skills, age 25-54", "DK", 2025, 86.89,
     "%", "% of age group", "", "EC1", "EU average carried as EU.SKL.2554."),
    ("DK.SKL.5574", "At least basic digital skills, age 55-74", "DK", 2025, 67.81,
     "%", "% of age group", "", "EC1", "EU average carried as EU.SKL.5574."),

    # EU-27 comparators for the same three bands, same publication. These were
    # previously held only in the note field of the Danish rows, which made them
    # uncitable: a value in a note is not an observation and cannot be looked up,
    # charted or traced. Promoted to rows so F10 can reference them.
    ("EU.SKL.1624", "At least basic digital skills, age 16-24", "EU27", 2025, 74.55,
     "%", "% of age group", "", "EC1", "Comparator for DK.SKL.1624."),
    ("EU.SKL.2554", "At least basic digital skills, age 25-54", "EU27", 2025, 68.57,
     "%", "% of age group", "", "EC1", "Comparator for DK.SKL.2554."),
    ("EU.SKL.5574", "At least basic digital skills, age 55-74", "EU27", 2025, 42.60,
     "%", "% of age group", "", "EC1", "Comparator for DK.SKL.5574."),

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

    # ------------------------------------------------------------------
    # Magnitudes. Every other observation in this file is a ratio; without a
    # level, a share cannot support a statement about how much of anything
    # there is. These four rows are what let 05_CALC convert shares into
    # headcounts and kroner.
    # ------------------------------------------------------------------
    ("DK.POP.TOT", "Resident population", "DK", 2026, 6025603,
     "count", "persons resident in Denmark", "", "DST2", "As at 1 January 2026."),

    ("DK.DGP.EXMP.N", "Citizens formally exempt from Digital Post", "DK", 2025, 256000,
     "count", "citizens aged 15+ resident in Denmark", "e", "DG1",
     "April 2025; source states approx. 256,000."),
    ("DK.DGP.EXMP.N", "Citizens formally exempt from Digital Post", "DK", 2026, 238479,
     "count", "citizens aged 15+ resident in Denmark", "", "DG1",
     "Q1 2026. Paired with the 4.7% rate, implies a 15+ base of about 5.07m."),

    # ------------------------------------------------------------------
    # The fiscal case for mandatory Digital Post, and how much of it the
    # national audit office could actually verify. This is the only
    # cost-side evidence in the workbook.
    # ------------------------------------------------------------------
    ("DK.GOV.DGP.SAVE.PLAN", "Digital Post: projected annual public saving", "DK",
     2016, 1000.0, "million DKK per year", "projected annual saving, whole public sector",
     "e", "RR1",
     "Ministry of Finance business case; Rigsrevisionen reports it as 'approx. 1bn'."),
    ("DK.GOV.DGP.SAVE.VERIF", "Digital Post: annual saving verifiable by audit", "DK",
     2016, 450.0, "million DKK per year", "verified annual saving, whole public sector",
     "e", "RR1",
     "Postage, paper and envelopes only. The wage and overhead component was "
     "never verified: the cross-government study was abandoned after KL declined "
     "to take part."),

    # ------------------------------------------------------------------
    # Labour productivity - Eurostat tesem160
    # Nominal labour productivity per person, indexed on EU27_2020 = 100,
    # current prices in purchasing power standards. The index base is
    # load-bearing: a rise means Denmark gained on the EU average, NOT that
    # Danish productivity grew. Those are different claims and only the first
    # is supported by this series.
    # ------------------------------------------------------------------
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2005, 109.2,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2006, 109.3,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2007, 107.1,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2008, 108.5,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2009, 109.9,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2010, 115.0,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2011, 113.8,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2012, 113.9,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2013, 115.3,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2014, 115.1,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2015, 113.9,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2016, 114.1,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2017, 116.3,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2018, 115.3,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2019, 113.2,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2020, 119.6,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2021, 121.0,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2022, 120.2,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2023, 113.1,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2024, 116.7,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
    ("DK.PRD.LP.PER", "Nominal labour productivity per person", "DK", 2025, 116.8,
     "index", "EU27_2020 = 100, current prices, PPS", "", "ES8", ""),
]


# ---------------------------------------------------------------------------
# Policy events.
#
# The assessment asks for policy that is specific enough for its impact to be
# visible. Outcomes alone cannot show that: a series needs something to be
# measured against. These rows are the instruments themselves, dated, cited,
# and rendered as event markers on the figures.
#
# `precision` is honest about how firmly the date is established:
#   day   - the commencement or publication date is stated by the source
#   month - the source places it in a month
#   year  - the source places it in a year only
#
# Nothing here is dated more precisely than its source allows.
# ---------------------------------------------------------------------------
POLICY_EVENTS = [
    ("2012-06-11", "day", "Lov om Offentlig Digital Post adopted",
     "LOV nr 528 af 11/06/2012", "RI1",
     "Creates the statutory basis for mandatory public digital post. Section 10 "
     "deems delivery effective on availability, not on the message being read.",
     "DK.DGP.EXMP"),

    ("2013-01-01", "year", "Digital Post becomes mandatory for businesses",
     "Lov om Offentlig Digital Post", "DG4",
     "Businesses are enrolled a year ahead of citizens.",
     "DK.ECM.ENT.TRN"),

    ("2014-11-01", "day", "Digital Post becomes mandatory for citizens aged 15+",
     "Lov om Offentlig Digital Post", "DG4",
     "Citizens are enrolled automatically whether or not they registered "
     "themselves. Exemption is available only against statutory criteria. This is "
     "the single most consequential date in this workbook.",
     "DK.DGP.EXMP"),

    ("2016-01-01", "month", "Rigsrevisionen reports on the Digital Post business case",
     "Beretning, January 2016", "RR1",
     "Of an approx. DKK 1bn projected annual saving, only DKK 450m - postage, "
     "paper and envelopes - could be verified.",
     "DK.GOV.DGP.SAVE.PLAN"),

    ("2018-01-01", "year", "SMV:Digital launched",
     "Danish digital growth plan for SMEs", "DG3",
     "Grant scheme subsidising SME digitalisation projects.",
     "DK.SME.SMVD.PROJ"),

    ("2021-10-01", "month", "MitID rollout begins",
     "National electronic ID replacement programme", "DG5",
     "Begins the migration of the whole population off NemID.",
     "DK.TRU.DPS"),

    ("2022-07-01", "day", "Kontantreglen amended",
     "Lov om betalinger, § 81", "RI2",
     "Businesses may refuse cash from other businesses; temporary events are "
     "exempted; the notification duty for 06:00-20:00 acceptance is removed. The "
     "obligation on shops to accept cash from consumers remains.",
     "DK.PAY.CASH.POS"),

    ("2022-09-22", "day", "MitID required for public digital services",
     "National electronic ID replacement programme", "DG5",
     "From this date citizens need MitID for borger.dk, skat.dk and sundhed.dk.",
     "DK.TRU.DPS"),

    ("2023-10-31", "day", "NemID fully phased out",
     "National electronic ID replacement programme", "DG5",
     "The predecessor credential can no longer be obtained or used.",
     "DK.TRU.DPS"),

    ("2026-01-01", "year", "SMV:Digital grant pools continue",
     "Tilskudspuljer i 2026", "SMV1",
     "The scheme is still operating and still awarding grants in 2026; a further "
     "pool opens on 26 October 2026. Recorded because an earlier draft of this "
     "workbook asserted the scheme was being defunded. It was not verifiable and "
     "the opposite is documented.",
     "DK.SME.SMVD.PROJ"),
]


def policy_events_for(series_code):
    """Events whose `related` field names this series. Used for chart markers."""
    return [e for e in POLICY_EVENTS if e[6] == series_code]


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

    # Policy events must be dated, cited, sourced, and must point at a series
    # that exists. An event marker on a chart is a factual claim about when an
    # instrument took effect; it carries the same evidential burden as a value.
    from datetime import date as _date

    codes = {r[0] for r in OBS}
    seen_events = set()
    for ev in POLICY_EVENTS:
        assert len(ev) == 7, f"wrong column count on policy event: {ev[:2]}"
        when, precision, name, citation, src, desc, related = ev
        assert precision in ("day", "month", "year"), \
            f"bad date precision {precision!r} on {name}"
        _date.fromisoformat(when)  # raises if not a real date
        assert citation, f"policy event {name!r} has no legal citation"
        assert src in SOURCES, f"unknown source_id {src!r} on policy event {name!r}"
        assert desc, f"policy event {name!r} has no description"
        assert related in codes, \
            f"policy event {name!r} points at unknown series {related!r}"
        assert (when, name) not in seen_events, f"duplicate policy event: {name}"
        seen_events.add((when, name))

    return len(OBS)


if __name__ == "__main__":
    print(f"{validate()} observations validated")
