import logging
from datetime import datetime, timezone
from typing import Any

import fsspec
import xarray as xr
import xstac

# import stactools.core.create
from pystac import (
    Asset,
    Collection,
    Extent,
    Item,
    # MediaType,
    SpatialExtent,
    # Summaries,
    TemporalExtent,
)

#
# from pystac.extensions.item_assets import AssetDefinition, ItemAssetsExtension
# from pystac.extensions.projection import ProjectionExtension
# from pystac.extensions.raster import DataType
#
from . import constants  # , cog

logger = logging.getLogger(__name__)


def create_collection() -> Collection:
    """Creates a STAC Collection for NOAA Climate Data Record.

    Args:
        region (str): The region of the files, North or South.

    Returns:
        Collection: STAC Collection object
    """
    spatial_extents = list(constants.EXTENTS.values())
    extent = Extent(
        SpatialExtent(spatial_extents),
        TemporalExtent([[datetime.now(tz=timezone.utc), None]]),
    )

    keywords = [
        "EARTH SCIENCE",
        "CRYOSPHERE",
        "SEA ICE",
        "SEA ICE CONCENTRATION",
        "Polar",
    ]

    collection = Collection(
        id="seaiceClimateDataRecord-collection",
        title="NOAA Seaice Climate Data Record collection",
        description=(
            "NOAA/NSIDC Climate Data Record of Passive"
            " Microwave Sea Ice Concentration Version 4"
        ),
        extent=extent,
        keywords=keywords,
        license="proprietary",
        providers=constants.PROVIDERS,
    )

    collection.add_link(constants.LINK_CDR_HOME)

    return collection


def create_item(
    ds: xr.Dataset, xarray_to_stac_options: dict[str, Any] | None = None
) -> Any:
    """Creates a STAC item from an xarray dataset.

    Returns:
        Item: STAC Item object
    """
    url = "https://noaadata.apps.nsidc.org/NOAA/G02202_V4/north/aggregate"
    fs = fsspec.filesystem("https")  # , host=host)
    files = [f for f in fs.find(url) if f.endswith(".nc") and "monthly" in f]
    file = files[0]
    ds = xr.open_dataset(ds=xr.open_dataset(file))

    item_id = "seaice-concentration-north-monthly-v4"

    template = Item(
        "item",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [180.0, -90.0],
                    [180.0, 90.0],
                    [-180.0, 90.0],
                    [-180.0, -90.0],
                    [180.0, -90.0],
                ]
            ],
        },
        bbox=[31.1, -180, 89.4, 180],
        datetime=None,
        properties={"start_datetime": None, "end_datetime": None},
        href=file,
    )

    xarray_to_stac_options = xarray_to_stac_options or {}
    xarray_to_stac_options.setdefault("reference_system", 4326)
    xarray_to_stac_options.setdefault("template", template)
    item = xstac.xarray_to_stac(ds, **xarray_to_stac_options)
    item.id = item_id

    # key = asset_key(file)
    asset = Asset(
        file,
        media_type="application/netcdf",
        roles=["data"],
    )

    item.add_asset(asset)

    return item
