"""Source register for the ECON1596 Assessment 2 data workbook.

Every observation in ``dataset.py`` carries a ``source_id`` that must resolve to a
key in ``SOURCES`` below. Each entry records the issuing authority, the publication,
the dataset code where one exists, a retrievable URL, the date the value was accessed,
and a full RMIT Harvard reference string for the report's reference list.

Values were verified individually against the issuing authority. Where a figure could
not be verified it is not present in the dataset at all; see the RETAIL_GAP sheet.
"""

ACCESSED = "2026-09-12"

SOURCES = {
    "NB1": dict(
        authority="Danmarks Nationalbank",
        title="Danskernes betalingsvaner",
        dataset_code="",
        url="https://www.nationalbanken.dk/en/what-we-do/safe-and-efficient-payments/payment-habits-in-denmark",
        accessed=ACCESSED,
        harvard=(
            "Danmarks Nationalbank 2025, *Danskernes betalingsvaner*, Danmarks "
            "Nationalbank, Copenhagen, accessed 12 September 2026, "
            "<https://www.nationalbanken.dk/en/what-we-do/safe-and-efficient-payments/payment-habits-in-denmark>."
        ),
    ),
    "FD1": dict(
        authority="Finans Danmark",
        title="Institutter, filialer & ansatte",
        dataset_code="",
        url="https://finansdanmark.dk/tal-og-data/institutter-filialer-ansatte/",
        accessed=ACCESSED,
        harvard=(
            "Finans Danmark 2025, *Institutter, filialer & ansatte*, Finans Danmark, "
            "Copenhagen, accessed 12 September 2026, "
            "<https://finansdanmark.dk/tal-og-data/institutter-filialer-ansatte/>."
        ),
    ),
    "ES1": dict(
        authority="Eurostat",
        title="E-commerce statistics for individuals (Statistics Explained)",
        dataset_code="isoc_ec_ib20 / isoc_ec_ibuy",
        url="https://ec.europa.eu/eurostat/statistics-explained/index.php?title=E-commerce_statistics_for_individuals",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2025, *E-commerce statistics for individuals*, Statistics "
            "Explained, European Commission, Luxembourg, accessed 12 September 2026, "
            "<https://ec.europa.eu/eurostat/statistics-explained/index.php?title=E-commerce_statistics_for_individuals>."
        ),
    ),
    "ES2": dict(
        authority="Eurostat",
        title="Online shopping ever more popular in 2020 (ddn-20210217-1)",
        dataset_code="isoc_ec_ib20",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/-/ddn-20210217-1",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2021, *Online shopping ever more popular in 2020*, European "
            "Commission, Luxembourg, accessed 12 September 2026, "
            "<https://ec.europa.eu/eurostat/web/products-eurostat-news/-/ddn-20210217-1>."
        ),
    ),
    "ES3": dict(
        authority="Eurostat",
        title="Online shopping ever more popular (ddn-20220202-1)",
        dataset_code="isoc_ec_ib20",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/-/ddn-20220202-1",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2022, *Online shopping ever more popular*, European Commission, "
            "Luxembourg, accessed 12 September 2026, "
            "<https://ec.europa.eu/eurostat/web/products-eurostat-news/-/ddn-20220202-1>."
        ),
    ),
    "ES4": dict(
        authority="Eurostat",
        title="E-commerce statistics for individuals, 2024 reference year (ddn-20250220-3)",
        dataset_code="isoc_ec_ib20",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20250220-3",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2025, *E-commerce statistics for individuals*, European "
            "Commission, Luxembourg, accessed 12 September 2026, "
            "<https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20250220-3>."
        ),
    ),
    "ES5": dict(
        authority="Eurostat",
        title="EU enterprises' online sales reach new heights in 2023 (ddn-20250227-2)",
        dataset_code="isoc_ec_evaln2 / tin00110",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20250227-2",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2025, *EU enterprises' online sales reach new heights*, "
            "European Commission, Luxembourg, accessed 12 September 2026, "
            "<https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20250227-2>."
        ),
    ),
    "ES6": dict(
        authority="Eurostat",
        title=(
            "Share of enterprises' turnover on e-commerce, by country "
            "(country-level values retrieved via search of the Eurostat indicator)"
        ),
        dataset_code="tin00110",
        url="https://ec.europa.eu/eurostat/databrowser/view/tin00110/default/table?lang=en",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2025, *Share of enterprises' turnover on e-commerce "
            "(tin00110)*, European Commission, Luxembourg, accessed 12 September "
            "2026, "
            "<https://ec.europa.eu/eurostat/databrowser/view/tin00110/default/table?lang=en>."
        ),
    ),
    "EC1": dict(
        authority="European Commission",
        title=(
            "Digital Decade 2026 country report: Denmark, "
            "SWD(2026) 155 final, Part 7/27, 17 June 2026"
        ),
        dataset_code="DESI 2026",
        url="https://digital-strategy.ec.europa.eu/en/policies/desi",
        accessed=ACCESSED,
        harvard=(
            "European Commission 2026, *Digital Decade 2026 country report: Denmark*, "
            "SWD(2026) 155 final, Part 7/27, European Commission, Brussels, accessed "
            "12 September 2026, "
            "<https://digital-strategy.ec.europa.eu/en/policies/desi>."
        ),
    ),
    "DG1": dict(
        authority="Digitaliseringsstyrelsen (Danish Agency for Digital Government)",
        title="Statistik om Digital Post",
        dataset_code="",
        url="https://digst.dk/tal-og-statistik/",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2026, *Statistik om Digital Post*, Agency for "
            "Digital Government, Copenhagen, accessed 12 September 2026, "
            "<https://digst.dk/tal-og-statistik/>."
        ),
    ),
    "DG2": dict(
        authority="Digitaliseringsstyrelsen (Danish Agency for Digital Government)",
        title="Hvem oplever udfordringer ved det digitale?",
        dataset_code="",
        url="https://digst.dk/digital-inklusion/viden-om-digital-inklusion/hvem-oplever-udfordringer-ved-det-digitale/",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2025, *Hvem oplever udfordringer ved det "
            "digitale?*, Agency for Digital Government, Copenhagen, accessed 12 "
            "September 2026, "
            "<https://digst.dk/digital-inklusion/viden-om-digital-inklusion/hvem-oplever-udfordringer-ved-det-digitale/>."
        ),
    ),
    "DG3": dict(
        authority="Digitaliseringsstyrelsen / Danmarks Statistik",
        title="Effektmåling af SMV:Digital, June 2025",
        dataset_code="",
        url="https://digst.dk/media/yz2ouzzz/effektmaaling-af-smvdigital-2025.pdf",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2025, *Effektmåling af SMV:Digital*, prepared "
            "by Danmarks Statistik, Agency for Digital Government, Copenhagen, "
            "accessed 12 September 2026, "
            "<https://digst.dk/media/yz2ouzzz/effektmaaling-af-smvdigital-2025.pdf>."
        ),
    ),
    "JU1": dict(
        authority="Justitia (independent Danish legal think tank)",
        title="Retssikkerhed for digitalt udsatte borgere, July 2022",
        dataset_code="Folketinget DIU Alm.del bilag 32",
        url="https://justitia-int.org/wp-content/uploads/2022/09/Rapport_Retssikkerhed-for-digitalt-udsatte-borgere-1.pdf",
        accessed=ACCESSED,
        harvard=(
            "Justitia 2022, *Retssikkerhed for digitalt udsatte borgere*, Justitia, "
            "Copenhagen, accessed 12 September 2026, "
            "<https://justitia-int.org/wp-content/uploads/2022/09/Rapport_Retssikkerhed-for-digitalt-udsatte-borgere-1.pdf>."
        ),
    ),
    "IMR1": dict(
        authority="Institut for Menneskerettigheder (Danish Institute for Human Rights)",
        title="Rettigheder i den digitale velfærdsstat, December 2023",
        dataset_code="",
        url="https://menneskeret.dk/sites/menneskeret.dk/files/media/document/Rettigheder%20i%20den%20digitale%20velf%C3%A6rdsstat.%20Analyse,%20Institut%20for%20Menneskerettigheder,%20december%202023.PDF",
        accessed=ACCESSED,
        harvard=(
            "Institut for Menneskerettigheder 2023, *Rettigheder i den digitale "
            "velfærdsstat*, Danish Institute for Human Rights, Copenhagen, accessed "
            "12 September 2026, "
            "<https://menneskeret.dk/sites/menneskeret.dk/files/media/document/Rettigheder%20i%20den%20digitale%20velf%C3%A6rdsstat.%20Analyse,%20Institut%20for%20Menneskerettigheder,%20december%202023.PDF>."
        ),
    ),
    "RI1": dict(
        authority="Retsinformation (Danish official legal information portal)",
        title="Lov om Offentlig Digital Post, LOV nr 528 af 11/06/2012",
        dataset_code="ELI: lta/2012/528",
        url="https://www.retsinformation.dk/eli/lta/2012/528",
        accessed=ACCESSED,
        harvard=(
            "Folketinget 2012, *Lov om Offentlig Digital Post*, LOV nr 528 af 11. "
            "juni 2012, Retsinformation, Copenhagen, accessed 12 September 2026, "
            "<https://www.retsinformation.dk/eli/lta/2012/528>."
        ),
    ),
    "RR1": dict(
        authority="Rigsrevisionen (Danish National Audit Office)",
        title=(
            "Beretning om besparelsespotentialet ved obligatorisk Digital Post "
            "på ca. 1 mia. kr. om året, January 2016"
        ),
        dataset_code="",
        url="https://www.rigsrevisionen.dk/revisionssager-arkiv/2016/jan/beretning-om-besparelsespotentialet-ved-obligatorisk-digital-post-paa-ca-1-mia-kr-om-aaret",
        accessed=ACCESSED,
        harvard=(
            "Rigsrevisionen 2016, *Beretning om besparelsespotentialet ved "
            "obligatorisk Digital Post på ca. 1 mia. kr. om året*, National Audit "
            "Office of Denmark, Copenhagen, accessed 12 September 2026, "
            "<https://www.rigsrevisionen.dk/revisionssager-arkiv/2016/jan/beretning-om-besparelsespotentialet-ved-obligatorisk-digital-post-paa-ca-1-mia-kr-om-aaret>."
        ),
    ),
    "RI2": dict(
        authority="Finanstilsynet (Danish Financial Supervisory Authority)",
        title="Kontantreglen – lov om betalinger § 81",
        dataset_code="Lov om betalinger, § 81",
        url="https://www.finanstilsynet.dk/finansielle-temaer/betalingstjenester-og-e-penge/kontantreglen",
        accessed=ACCESSED,
        harvard=(
            "Finanstilsynet 2025, *Kontantreglen*, Danish Financial Supervisory "
            "Authority, Copenhagen, accessed 12 September 2026, "
            "<https://www.finanstilsynet.dk/finansielle-temaer/betalingstjenester-og-e-penge/kontantreglen>."
        ),
    ),
    "DG4": dict(
        authority="Digitaliseringsstyrelsen (Danish Agency for Digital Government)",
        title="Digital Post – lovgivning, and the MitID transition news archive",
        dataset_code="",
        url="https://digst.dk/it-loesninger/digital-post/lovgivning/",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2025, *Digital Post – lovgivning*, Agency for "
            "Digital Government, Copenhagen, accessed 12 September 2026, "
            "<https://digst.dk/it-loesninger/digital-post/lovgivning/>."
        ),
    ),
    "SMV1": dict(
        authority="SMV:Digital (Danish SME digitalisation grant scheme)",
        title="Tilskudspuljer i 2026",
        dataset_code="",
        url="https://smvdigital.dk/content/ydelser/tilskudspuljer-i-2026/8efa07f4-5032-47f4-b7fa-bab57412b762/",
        accessed=ACCESSED,
        harvard=(
            "SMV:Digital 2026, *Tilskudspuljer i 2026*, SMV:Digital, Copenhagen, "
            "accessed 12 September 2026, "
            "<https://smvdigital.dk/content/ydelser/tilskudspuljer-i-2026/8efa07f4-5032-47f4-b7fa-bab57412b762/>."
        ),
    ),
    "DST2": dict(
        authority="Danmarks Statistik",
        title="Befolkningstal (population figures)",
        dataset_code="StatBank FOLK1A",
        url="https://www.dst.dk/da/Statistik/emner/borgere/befolkning/befolkningstal",
        accessed=ACCESSED,
        harvard=(
            "Danmarks Statistik 2026, *Befolkningstal*, Statistics Denmark, "
            "Copenhagen, accessed 12 September 2026, "
            "<https://www.dst.dk/da/Statistik/emner/borgere/befolkning/befolkningstal>."
        ),
    ),
    "ES7": dict(
        authority="Eurostat",
        title=(
            "Internet purchases by individuals (2020 onwards) - custom extraction, "
            "all individuals, last online purchase in the 12 months, percentage of "
            "individuals who used internet within the last year, 2024"
        ),
        dataset_code="isoc_ec_ib20",
        url="https://ec.europa.eu/eurostat/databrowser/view/isoc_ec_ib20/default/table?lang=en",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2026, *Internet purchases by individuals (2020 onwards)*, "
            "dataset isoc_ec_ib20, Statistical Office of the European Union, "
            "Luxembourg, data last updated 17 April 2026, accessed 12 September 2026, "
            "<https://ec.europa.eu/eurostat/databrowser/view/isoc_ec_ib20/default/table?lang=en>."
        ),
    ),
    "DST1": dict(
        authority="Danmarks Statistik",
        title="Detailomsætningsindeks (retail trade turnover index)",
        dataset_code="StatBank; base year rebased 2015 -> 2021",
        url="https://www.dst.dk/da/Statistik/dokumentation/statistikdokumentation/detailomsaetningsindeks",
        accessed=ACCESSED,
        harvard=(
            "Danmarks Statistik 2025, *Detailomsætningsindeks*, Statistics Denmark, "
            "Copenhagen, accessed 12 September 2026, "
            "<https://www.dst.dk/da/Statistik/dokumentation/statistikdokumentation/detailomsaetningsindeks>."
        ),
    ),
    "ES8": dict(
        authority="Eurostat",
        title=(
            "Labour productivity per person employed and hour worked "
            "(EU27_2020=100) - custom extraction, nominal labour productivity "
            "per person, Denmark, 2005-2025"
        ),
        dataset_code="tesem160",
        url="https://ec.europa.eu/eurostat/databrowser/view/tesem160/default/table?lang=en",
        accessed="2026-09-13",
        harvard=(
            "Eurostat 2026, *Labour productivity per person employed and hour worked "
            "(EU27_2020=100)*, dataset tesem160, Statistical Office of the European "
            "Union, Luxembourg, data last updated 9 September 2026, accessed 13 "
            "September 2026, "
            "<https://ec.europa.eu/eurostat/databrowser/view/tesem160/default/table?lang=en>."
        ),
    ),
    "ES9": dict(
        authority="Eurostat",
        title=(
            "E-government activities of individuals via websites - individuals "
            "using the internet for interaction with public authorities, "
            "last 12 months"
        ),
        dataset_code="isoc_ciegi_ac",
        url="https://ec.europa.eu/eurostat/databrowser/view/isoc_ciegi_ac/default/table?lang=en",
        accessed="2026-09-14",
        harvard=(
            "Eurostat 2026, *E-government activities of individuals via websites*, "
            "dataset isoc_ciegi_ac, Statistical Office of the European Union, "
            "Luxembourg, accessed 14 September 2026, "
            "<https://ec.europa.eu/eurostat/databrowser/view/isoc_ciegi_ac/default/table?lang=en>."
        ),
    ),
    # D: the eID timeline rows used to cite DG4, a Digital Post LEGISLATION
    # page. Table 1 now prints its sources, so that mismatch became a visible
    # citation. MitID is run by the same agency and is the authority on its
    # own phase-out dates.
    "DG5": dict(
        authority="Digitaliseringsstyrelsen (Danish Agency for Digital Government)",
        title="NemID is about to be closed",
        dataset_code="",
        url="https://www.mitid.dk/en-gb/about-mitid/news/nemid-is-about-to-be-closed/",
        accessed="2026-09-14",
        harvard=(
            "Digitaliseringsstyrelsen 2023, *NemID is about to be closed*, MitID, "
            "Agency for Digital Government, Copenhagen, accessed 14 September 2026, "
            "<https://www.mitid.dk/en-gb/about-mitid/news/nemid-is-about-to-be-closed/>."
        ),
    ),
    "LOV1": dict(
        authority="Folketinget",
        title=(
            "Lov om fravigelse fra obligatorisk digital selvbetjening "
            "(Act on derogation from mandatory digital self-service)"
        ),
        dataset_code="LOV nr 603 af 31/05/2023",
        url="https://www.retsinformation.dk/eli/lta/2023/603",
        accessed="2026-09-13",
        harvard=(
            "Folketinget 2023, *Lov om fravigelse fra obligatorisk digital "
            "selvbetjening*, LOV nr 603 af 31. maj 2023, in force 1 June 2023, "
            "Retsinformation, Copenhagen, accessed 13 September 2026, "
            "<https://www.retsinformation.dk/eli/lta/2023/603>."
        ),
    ),
    "BRH1": dict(
        authority="Bundesrechnungshof",
        title=(
            "Bemerkungen 2022 zur Haushalts- und Wirtschaftsführung des Bundes "
            "- findings on the Digital Jetzt lottery allocation"
        ),
        dataset_code="Bemerkungen 2022",
        url=(
            "https://www.bundesrechnungshof.de/SharedDocs/Pressemitteilungen/"
            "DE/2022/bemerkungen2022-hauptband.html"
        ),
        accessed="2026-09-13",
        harvard=(
            "Bundesrechnungshof 2022, *Bemerkungen 2022 zur Haushalts- und "
            "Wirtschaftsführung des Bundes*, German Federal Court of Auditors, Bonn, "
            "accessed 13 September 2026, "
            "<https://www.bundesrechnungshof.de/SharedDocs/Pressemitteilungen/DE/2022/bemerkungen2022-hauptband.html>."
        ),
    ),
    "CE1": dict(
        authority="Conseil d'État (France)",
        title=(
            "Decision No. 452798 - partial annulment of the ANEF decree "
            "mandating online-only residence permit applications"
        ),
        dataset_code="No. 452798",
        url="https://www.conseil-etat.fr/fr/arianeweb/CE/decision/2022-06-03/452798",
        accessed="2026-09-13",
        harvard=(
            "Conseil d'État 2022, *Decision No. 452798*, 3 June 2022, Conseil d'État, "
            "Paris, accessed 13 September 2026, "
            "<https://www.conseil-etat.fr/fr/arianeweb/CE/decision/2022-06-03/452798>."
        ),
    ),
    "BE1": dict(
        authority="Cour constitutionnelle (Belgium)",
        title=(
            "Arrêt no. 126/2025 - Brussels Digital ordinance; cumulative "
            "non-digital access guarantees"
        ),
        dataset_code="ECLI:BE:GHCC:2025:ARR.126",
        url="https://fr.const-court.be/public/f/2025/2025-126f.pdf",
        accessed="2026-09-13",
        harvard=(
            "Cour constitutionnelle 2025, *Arrêt no. 126/2025*, 25 September 2025, "
            "ECLI:BE:GHCC:2025:ARR.126, Cour constitutionnelle, Brussels, accessed 13 "
            "September 2026, <https://fr.const-court.be/public/f/2025/2025-126f.pdf>."
        ),
    ),
    "NO1": dict(
        authority="Digitaliseringsdirektoratet (Digdir)",
        title=(
            "Kontakt- og reservasjonsregisteret and the statutory right to opt "
            "out of digital communication under eForvaltningsforskriften"
        ),
        dataset_code="KRR",
        url="https://www.digdir.no/digitale-felleslosninger/kontakt-og-reservasjonsregisteret-krr/865",
        accessed="2026-09-13",
        harvard=(
            "Digitaliseringsdirektoratet 2025, *Kontakt- og reservasjonsregisteret*, "
            "Norwegian Digitalisation Agency, Oslo, accessed 13 September 2026, "
            "<https://www.digdir.no/digitale-felleslosninger/kontakt-og-reservasjonsregisteret-krr/865>."
        ),
    ),
    "GS1": dict(
        intext="Tran",
        authority="Tran, T.T.",
        title=("Guest speaker session: corporate sustainability and the "
               "adoption of artificial intelligence"),
        dataset_code="ECON1596/ECON1597 guest lecture",
        # A lecture has no retrievable address. The workbook never reads this
        # source, so the url and accessed fields that the workbook verifier
        # requires of a data source do not apply; it is REFERENCE_ONLY.
        url="",
        accessed="",
        harvard=(
            "Tran, TT 2026, 'Guest speaker session: corporate sustainability and the "
            "adoption of artificial intelligence', guest lecture, *ECON1596 Business "
            "Challenges in the Digital Economy*, RMIT University Vietnam, Ho Chi Minh "
            "City, [LECTURE DATE: to be completed by the author]."
        ),
    ),
    "HOW1": dict(
        intext="Howell",
        authority="Howell, S.T.",
        title="Financing Innovation: Evidence from R&D Grants",
        dataset_code="American Economic Review 107(4)",
        url="https://www.aeaweb.org/articles?id=10.1257%2Faer.20150808",
        accessed="2026-09-13",
        harvard=(
            "Howell, ST 2017, 'Financing innovation: evidence from R&D grants', "
            "*American Economic Review*, vol. 107, no. 4, pp. 1136-1164."
        ),
    ),
    "SAN1": dict(
        intext="Santoleri et al.",
        authority="Santoleri, P., Barrows, G., Caravella, S., Crespi, F. and Pellegrino, G.",
        title=(
            "The Causal Effects of R&D Grants: Evidence from a Regression "
            "Discontinuity - the Horizon 2020 SME Instrument scoring threshold"
        ),
        dataset_code="Working paper",
        url="https://pietrosantoleri.github.io/files/Santoleri_et_al_The_effects_of_R_D_grants.pdf",
        accessed="2026-09-13",
        harvard=(
            "Santoleri, P, Barrows, G, Caravella, S, Crespi, F & Pellegrino, G 2022, "
            "*The causal effects of R&D grants: evidence from a regression "
            "discontinuity*, working paper, accessed 13 September 2026, "
            "<https://pietrosantoleri.github.io/files/Santoleri_et_al_The_effects_of_R_D_grants.pdf>."
        ),
    ),
}

# Sources held for the report's reference list that no workbook observation uses
# and no figure note cites. They are declared here rather than left to look like
# oversights: an audit flagged them as orphans, and the honest answer is that
# they support argument in the written report, not any number in this file.
# A source may sit here ONLY if nothing in the workbook depends on it; anything
# a figure actually draws on must be cited in that figure's source note.
REFERENCE_ONLY = frozenset({
    "GS1",   # The guest lecture. Section 5 engages its claims; it
             # supplies no observation to the workbook.
    "LOV1",  # Act 603/2023 - a legal instrument, not a data source. It settles
             # what Section 6 may recommend; it supplies no observation.
    "CE1",   # Conseil d'État and Cour constitutionnelle: comparative legal
    "BE1",   # authority for Appendix G. Rulings, not observations.
     # The Parliamentary Ombudsman on Digital Post's design and on
     # deadlines; Norway's opt-out register; and the two regression
    "NO1",   # discontinuity papers behind Appendix F's instrument. All are
    "HOW1",  # argument or comparative authority, not Danish observations.
    "SAN1",
    "BRH1",  # German Federal Court of Auditors on lottery allocation - the
             # reason Appendix F rejects that instrument. Argument, not data.
})


def plain(harvard):
    """A Harvard string with its emphasis markers removed.

    The reference strings above italicise the title of each standalone work by
    wrapping it in asterisks, because ``build_docx.para`` renders Markdown
    emphasis as real runs and RMIT Harvard italicises those titles. Anywhere the
    string is written as plain text instead - the workbook's ``03_SOURCES``
    sheet, or a comparison against the text extracted from the .docx - the
    markers have to come off first, or the asterisks show up in the output and
    the comparison silently fails to match.
    """
    return harvard.replace("*", "")
