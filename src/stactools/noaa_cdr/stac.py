import logging

# from typing import Any, Dict, List, Optional, Union
#
# import numpy as np
# import rasterio
# from dateutil.parser import isoparse
from datetime import datetime, timezone

import stactools.core.create
from pystac import (
    # Asset,
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

# from .fileinfo import FileInfo

logger = logging.getLogger(__name__)


def create_collection(
    # region: str,
) -> Collection:
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
    return collection


def create_item(asset_href: str) -> Item:
    """Creates a STAC item from a raster asset.

    This example function uses :py:func:`stactools.core.utils.create_item` to
    generate an example item.  Datasets should customize the item with
    dataset-specific information, e.g.  extracted from metadata files.

    See `the STAC specification
    <https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md>`_
    for information about an item's fields, and
    `Item<https://pystac.readthedocs.io/en/latest/api/pystac.html#pystac.Item>`_ for
    information on the PySTAC class.

    This function should be updated to take all hrefs needed to build the item.
    It is an anti-pattern to assume that related files (e.g. metadata) are in
    the same directory as the primary file.

    Args:
        asset_href (str): The HREF pointing to an asset associated with the item

    Returns:
        Item: STAC Item object
    """
    item = stactools.core.create.item(asset_href)
    item.id = "example-item"
    item.properties["custom_attribute"] = "foo"
    return item
