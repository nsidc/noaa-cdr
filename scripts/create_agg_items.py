from pathlib import Path

from pystac import Item

from .. import run_command


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
    # extract hemisphere from URL
    if "north" in url:
        hemi = "north"
    else:
        hemi = "south"

    # extract filename from URL
    f = url.split("/")
    file = f[(len(f) - 1)]
    filename = file.split(".")[0]
    sea_ice_path = Path(
        f"examples/noaa-cdr-sea-ice-concentration/{hemi}/{filename}.json"
    )
    run_command(f"noaa-cdr sea-ice-concentration create-item {url} {sea_ice_path}")
    Item.from_file(f"{sea_ice_path}")

    # return sea_ice_path


# def add_item_to_collection(item_path: str) -> None:
#     collection_path = 'examples/noaa-cdr-sea-ice-concentration/collection.json'
#     run_command(f'add {item_path} {collection_path}')


def main(*, year: str, hemisphere: str, frequency: str) -> None:
    url = get_url(year=year, hemisphere=hemisphere, frequency=frequency)
    create_item(url)
