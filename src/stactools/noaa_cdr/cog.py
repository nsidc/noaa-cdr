import os
from typing import Any, Dict

import fsspec
import rasterio.shutil
import xarray
from numpy.typing import NDArray
from pystac import Asset, MediaType
from rasterio import MemoryFile

from . import dataset
from .profile import BandProfile


def cogify(path: str, directory: str) -> Dict[str, Asset]:
    os.makedirs(directory, exist_ok=True)
    file_name = os.path.splitext(os.path.basename(path))[0]
    assets = dict()
    with fsspec.open(path) as file:
        with xarray.open_dataset(file, mask_and_scale=False) as ds:
            for variable in dataset.data_variable_names(ds):
                # TODO remap > 180 longitudes
                profile = BandProfile.build(ds, variable)
                values = ds[variable].values.squeeze()
                path = os.path.join(directory, f"{file_name}-{variable}.tif")
                asset = write(
                    values,
                    path,
                    profile,
                )
                assets[variable] = asset
    return assets


def write(
    values: NDArray[Any],
    path: str,
    profile: BandProfile,
) -> Asset:
    with MemoryFile() as memory_file:
        with memory_file.open(**profile.gtiff()) as open_memory_file:
            open_memory_file.write(values, 1)
            rasterio.shutil.copy(open_memory_file, path, **profile.cog())
    asset = Asset(href=path, media_type=MediaType.COG, roles=["data"])
    asset.extra_fields["raster:bands"] = [profile.raster_band().to_dict()]
    return asset
