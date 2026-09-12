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
            "Danmarks Nationalbank 2025, Danskernes betalingsvaner, Danmarks "
            "Nationalbank, Copenhagen, accessed 12 September 2026, "
            "<https://www.nationalbanken.dk/en/what-we-do/safe-and-efficient-payments/"
            "payment-habits-in-denmark>."
        ),
    ),
    "NB2": dict(
        authority="Danmarks Nationalbank",
        title=(
            "Danskerne betaler mere digitalt - det goer offline-betalinger endnu "
            "vigtigere som beredskab (press release, 26 June 2026)"
        ),
        dataset_code="",
        url="https://www.nationalbanken.dk/da/viden-og-nyheder/presse/arkiv/2026/danskerne-betaler-mere-digitalt-det-goer-offline-betalinger-endnu-vigtigere-som-beredskab-26-06-2026",
        accessed=ACCESSED,
        harvard=(
            "Danmarks Nationalbank 2026, Danskerne betaler mere digitalt - det goer "
            "offline-betalinger endnu vigtigere som beredskab, press release, "
            "26 June, Danmarks Nationalbank, Copenhagen, accessed 12 September 2026."
        ),
    ),
    "FD1": dict(
        authority="Finans Danmark",
        title="Institutter, filialer & ansatte",
        dataset_code="",
        url="https://finansdanmark.dk/tal-og-data/institutter-filialer-ansatte/",
        accessed=ACCESSED,
        harvard=(
            "Finans Danmark 2025, Institutter, filialer & ansatte, Finans Danmark, "
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
            "Eurostat 2025, E-commerce statistics for individuals, Statistics "
            "Explained, European Commission, Luxembourg, accessed 12 September 2026."
        ),
    ),
    "ES2": dict(
        authority="Eurostat",
        title="Online shopping ever more popular in 2020 (ddn-20210217-1)",
        dataset_code="isoc_ec_ib20",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/-/ddn-20210217-1",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2021, Online shopping ever more popular in 2020, European "
            "Commission, Luxembourg, accessed 12 September 2026."
        ),
    ),
    "ES3": dict(
        authority="Eurostat",
        title="Online shopping ever more popular (ddn-20220202-1)",
        dataset_code="isoc_ec_ib20",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/-/ddn-20220202-1",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2022, Online shopping ever more popular, European Commission, "
            "Luxembourg, accessed 12 September 2026."
        ),
    ),
    "ES4": dict(
        authority="Eurostat",
        title="E-commerce statistics for individuals, 2024 reference year (ddn-20250220-3)",
        dataset_code="isoc_ec_ib20",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20250220-3",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2025, E-commerce statistics for individuals, European "
            "Commission, Luxembourg, accessed 12 September 2026."
        ),
    ),
    "ES5": dict(
        authority="Eurostat",
        title="EU enterprises' online sales reach new heights in 2023 (ddn-20250227-2)",
        dataset_code="isoc_ec_evaln2 / tin00110",
        url="https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20250227-2",
        accessed=ACCESSED,
        harvard=(
            "Eurostat 2025, EU enterprises' online sales reach new heights, European "
            "Commission, Luxembourg, accessed 12 September 2026."
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
            "Eurostat 2025, Share of enterprises' turnover on e-commerce "
            "(tin00110), European Commission, Luxembourg, accessed "
            "12 September 2026."
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
            "European Commission 2026, Digital Decade 2026 country report: Denmark, "
            "SWD(2026) 155 final, Part 7/27, European Commission, Brussels."
        ),
    ),
    "DG1": dict(
        authority="Digitaliseringsstyrelsen (Danish Agency for Digital Government)",
        title="Statistik om Digital Post",
        dataset_code="",
        url="https://digst.dk/tal-og-statistik/",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2026, Statistik om Digital Post, Agency for "
            "Digital Government, Copenhagen, accessed 12 September 2026."
        ),
    ),
    "DG2": dict(
        authority="Digitaliseringsstyrelsen (Danish Agency for Digital Government)",
        title="Hvem oplever udfordringer ved det digitale?",
        dataset_code="",
        url="https://digst.dk/digital-inklusion/viden-om-digital-inklusion/hvem-oplever-udfordringer-ved-det-digitale/",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2025, Hvem oplever udfordringer ved det "
            "digitale?, Agency for Digital Government, Copenhagen, accessed "
            "12 September 2026."
        ),
    ),
    "DG3": dict(
        authority="Digitaliseringsstyrelsen / Danmarks Statistik",
        title="Effektmaaling af SMV:Digital, June 2025",
        dataset_code="",
        url="https://digst.dk/media/yz2ouzzz/effektmaaling-af-smvdigital-2025.pdf",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2025, Effektmaaling af SMV:Digital, prepared by "
            "Danmarks Statistik, Agency for Digital Government, Copenhagen, accessed "
            "12 September 2026."
        ),
    ),
    "JU1": dict(
        authority="Justitia (independent Danish legal think tank)",
        title="Retssikkerhed for digitalt udsatte borgere, July 2022",
        dataset_code="Folketinget DIU Alm.del bilag 32",
        url="https://justitia-int.org/wp-content/uploads/2022/09/Rapport_Retssikkerhed-for-digitalt-udsatte-borgere-1.pdf",
        accessed=ACCESSED,
        harvard=(
            "Justitia 2022, Retssikkerhed for digitalt udsatte borgere, Justitia, "
            "Copenhagen, accessed 12 September 2026."
        ),
    ),
    "IMR1": dict(
        authority="Institut for Menneskerettigheder (Danish Institute for Human Rights)",
        title="Rettigheder i den digitale velfaerdsstat, December 2023",
        dataset_code="",
        url="https://menneskeret.dk/sites/menneskeret.dk/files/media/document/Rettigheder%20i%20den%20digitale%20velf%C3%A6rdsstat.%20Analyse,%20Institut%20for%20Menneskerettigheder,%20december%202023.PDF",
        accessed=ACCESSED,
        harvard=(
            "Institut for Menneskerettigheder 2023, Rettigheder i den digitale "
            "velfaerdsstat, Danish Institute for Human Rights, Copenhagen, accessed "
            "12 September 2026."
        ),
    ),
    "RI1": dict(
        authority="Retsinformation (Danish official legal information portal)",
        title="Lov om Offentlig Digital Post, LOV nr 528 af 11/06/2012",
        dataset_code="ELI: lta/2012/528",
        url="https://www.retsinformation.dk/eli/lta/2012/528",
        accessed=ACCESSED,
        harvard=(
            "Denmark 2012, Lov om Offentlig Digital Post (LOV nr 528 af 11/06/2012), "
            "Retsinformation, Copenhagen, accessed 12 September 2026."
        ),
    ),
    "RR1": dict(
        authority="Rigsrevisionen (Danish National Audit Office)",
        title=(
            "Beretning om besparelsespotentialet ved obligatorisk Digital Post "
            "paa ca. 1 mia. kr. om aaret, January 2016"
        ),
        dataset_code="",
        url="https://www.rigsrevisionen.dk/revisionssager-arkiv/2016/jan/beretning-om-besparelsespotentialet-ved-obligatorisk-digital-post-paa-ca-1-mia-kr-om-aaret",
        accessed=ACCESSED,
        harvard=(
            "Rigsrevisionen 2016, Beretning om besparelsespotentialet ved "
            "obligatorisk Digital Post paa ca. 1 mia. kr. om aaret, National Audit "
            "Office of Denmark, Copenhagen, accessed 12 September 2026."
        ),
    ),
    "RI2": dict(
        authority="Finanstilsynet (Danish Financial Supervisory Authority)",
        title="Kontantreglen - lov om betalinger section 81",
        dataset_code="Lov om betalinger, ss 81",
        url="https://www.finanstilsynet.dk/finansielle-temaer/betalingstjenester-og-e-penge/kontantreglen",
        accessed=ACCESSED,
        harvard=(
            "Finanstilsynet 2025, Kontantreglen, Danish Financial Supervisory "
            "Authority, Copenhagen, accessed 12 September 2026."
        ),
    ),
    "DG4": dict(
        authority="Digitaliseringsstyrelsen (Danish Agency for Digital Government)",
        title="Digital Post - lovgivning, and the MitID transition news archive",
        dataset_code="",
        url="https://digst.dk/it-loesninger/digital-post/lovgivning/",
        accessed=ACCESSED,
        harvard=(
            "Digitaliseringsstyrelsen 2025, Digital Post - lovgivning, Agency for "
            "Digital Government, Copenhagen, accessed 12 September 2026."
        ),
    ),
    "SMV1": dict(
        authority="SMV:Digital (Danish SME digitalisation grant scheme)",
        title="Tilskudspuljer i 2026",
        dataset_code="",
        url="https://smvdigital.dk/content/ydelser/tilskudspuljer-i-2026/8efa07f4-5032-47f4-b7fa-bab57412b762/",
        accessed=ACCESSED,
        harvard=(
            "SMV:Digital 2026, Tilskudspuljer i 2026, SMV:Digital, Copenhagen, "
            "accessed 12 September 2026."
        ),
    ),
    "DST2": dict(
        authority="Danmarks Statistik",
        title="Befolkningstal (population figures)",
        dataset_code="StatBank FOLK1A",
        url="https://www.dst.dk/da/Statistik/emner/borgere/befolkning/befolkningstal",
        accessed=ACCESSED,
        harvard=(
            "Danmarks Statistik 2026, Befolkningstal, Statistics Denmark, "
            "Copenhagen, accessed 12 September 2026."
        ),
    ),
    "DST1": dict(
        authority="Danmarks Statistik",
        title="Detailomsaetningsindeks (retail trade turnover index)",
        dataset_code="StatBank; base year rebased 2015 -> 2021",
        url="https://www.dst.dk/da/Statistik/dokumentation/statistikdokumentation/detailomsaetningsindeks",
        accessed=ACCESSED,
        harvard=(
            "Danmarks Statistik 2025, Detailomsaetningsindeks, Statistics Denmark, "
            "Copenhagen, accessed 12 September 2026."
        ),
    ),
}
