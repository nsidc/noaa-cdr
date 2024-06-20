from pystac import Link, Provider, ProviderRole

EXTENTS = {
    "NORTH": [31.1, -180, 89.4, 180],
    "SOUTH": [-89.84, -180, -39.36, 180],
}

CITATION = {
    (
        "Meier, W. N., F. Fetterer, A. K. Windnagel, and S. Stewart. 2021."
        "NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice"
        "Concentration, Version 4. Boulder, Colorado, USA."
        "NSIDC: National Snow and Ice Data Center"
        "https://doi.org/10.7265/efmz-2t65."
    )
}

PROVIDERS = [
    Provider(
        name="NOAA at the National Snow and Ice Data Center",
        roles=[
            ProviderRole.PRODUCER,
            ProviderRole.LICENSOR,
            ProviderRole.HOST,
        ],
        url="https://nsidc.org/data",
    ),
]


LINK_USER_GUIDE = Link(
    target=("https://nsidc.org/sites/default/files/g02202-v004-userguide_1_1.pdf"),
    rel="about",
    media_type="application/pdf",
    title="User Guide",
)
LINK_CDR_HOME = Link(
    target=("https://nsidc.org/data/g02202/versions/4#anchor-overview"),
    rel="about",
    media_type="text/html",
    title="CDR Homepage",
)
