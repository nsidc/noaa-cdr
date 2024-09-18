#!/usr/bin/env python3
import shutil

from pathlib import Path

from pystac import Collection, Item

import stactools.noaa_cdr.stac
from stactools.noaa_cdr import stac 


def get_url(*, year: str, hemisphere: str, frequency: str) -> str:
    if frequency == "daily":
        if hemisphere == "north":
            url = (
                "https://noaadata.apps.nsidc.org/NOAA/G02202_V4/"
                f"{hemisphere}/aggregate/seaice_conc_daily_nh_{year}_v04r00.nc"
            )
        else:
            url = (
                "https://noaadata.apps.nsidc.org/NOAA/G02202_V4/"
                f"{hemisphere}/aggregate/seaice_conc_daily_sh_{year}_v04r00.nc"
            )
    else:
        if hemisphere == "north":
            url = (
                "https://noaadata.apps.nsidc.org/NOAA/G02202_V4/"
                f"{hemisphere}/aggregate/seaice_conc_monthly_nh_{year}_v04r00.nc"
            )
        else:
            url = (
                "https://noaadata.apps.nsidc.org/NOAA/G02202_V4/"
                f"{hemisphere}/aggregate/seaice_conc_monthly_sh_{year}_v04r00.nc"
            )
    return url


def create_item(url: str) -> None:
    sea_ice_concentration_item = stac.create_item(url)

    return sea_ice_concentration_item


def add_item_to_collection(item: str) -> None:
    collection_path = 'examples/noaa-cdr-sea-ice-concentration/collection.json'
    collection = Collection.from_file(collection_path)
    collection.add_item(sea_ice_concentration_item)


def main(*, year: str, hemisphere: str, frequency: str) -> None:
    url = get_url(year=year, hemisphere=hemisphere, frequency=frequency)
    create_item(url)
    add_item_to_collection(sea_ice_concentration_item)
