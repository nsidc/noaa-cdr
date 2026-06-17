"""Finds new G02202 (NOAA/NSIDC Sea Ice Concentration CDR) V6 daily granules
for both hemispheres, turns each new one into a STAC item using the
sea_ice_concentration stactools module, and appends them to a STAC
GeoParquet file.

Designed to run on a schedule (see
.github/workflows/update-sea-ice-geoparquet.yml) where it's safe to run
repeatedly: granules already present in the GeoParquet (by item id) are
skipped, so a re-run after a no-op day does nothing.

Requires Earthdata Login credentials. In CI, set the EARTHDATA_USERNAME and
EARTHDATA_PASSWORD repository secrets; earthaccess.login(strategy="environment")
will pick those up. Locally, a ~/.netrc entry works too
(strategy="netrc", or just strategy="all").

NOTE ON VERIFICATION: the item-creation logic this script calls into
(stactools.noaa_cdr.sea_ice_concentration.stac.create_item) has been
verified against two real V6 sample files. What hasn't been verified is
the CMR-facing part of this specific script (earthaccess.search_data
against live CMR, and the exact shape of granule.data_links()) -- this
environment didn't have network access to confirm those live, though the
rest of the pipeline (dedup, item building, href-swapping, GeoParquet
append) was tested end to end with earthaccess mocked out. See
README.md for details.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import earthaccess
import pyarrow.parquet as pq
import stac_geoparquet.arrow as stac_geoparquet
from pystac import Item

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from stactools.noaa_cdr.sea_ice_concentration import stac as sic_stac  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("update_geoparquet")

SHORT_NAME = "G02202"
VERSION = "6"
# How many days back to search. V6 has up to a ~7 day processing lag, and
# CMR/processing hiccups can push that further -- a generous lookback keeps
# this idempotent and self-healing without needing a separate state file.
LOOKBACK_DAYS = 21

NORTH_TOKEN = "_psn25_"
SOUTH_TOKEN = "_pss25_"


def hemisphere_of(filename: str) -> str | None:
    if NORTH_TOKEN in filename:
        return "north"
    if SOUTH_TOKEN in filename:
        return "south"
    return None


def existing_item_ids(geoparquet_path: Path) -> set[str]:
    if not geoparquet_path.exists():
        return set()
    table = pq.read_table(geoparquet_path, columns=["id"])
    return set(table.column("id").to_pylist())


def find_new_granules(known_ids: set[str]) -> list[earthaccess.results.DataGranule]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=LOOKBACK_DAYS)
    granules = earthaccess.search_data(
        short_name=SHORT_NAME,
        version=VERSION,
        temporal=(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
    )
    new = []
    for granule in granules:
        links = [link for link in granule.data_links() if link.endswith(".nc")]
        for link in links:
            filename = link.rsplit("/", 1)[-1]
            item_id = filename[: -len(".nc")]
            if item_id in known_ids:
                continue
            if hemisphere_of(filename) is None:
                # Daily files only -- skip monthly/ancillary/aggregate
                # files that don't match the psn25/pss25 naming pattern.
                continue
            new.append(granule)
            break
    return new


def build_items(
    granules: list[earthaccess.results.DataGranule], download_dir: Path
) -> list[Item]:
    if not granules:
        return []
    earthaccess.login(strategy="environment")
    local_paths = earthaccess.download(granules, str(download_dir))
    items = []
    for local_path, granule in zip(local_paths, granules):
        local_path = Path(local_path)
        if local_path.suffix != ".nc":
            continue
        remote_url = next(
            (link for link in granule.data_links() if link.endswith(local_path.name)),
            None,
        )
        item = sic_stac.create_item(str(local_path))
        hemisphere = hemisphere_of(local_path.name)
        if hemisphere:
            item.properties["noaa_cdr:hemisphere"] = hemisphere
        if remote_url:
            # Publish the canonical NSIDC URL, not the CI runner's local
            # download path.
            from stactools.noaa_cdr.constants import NETCDF_ASSET_KEY

            item.assets[NETCDF_ASSET_KEY].href = remote_url
        items.append(item)
        logger.info("Built item %s (%s)", item.id, hemisphere)
    return items


def write_geoparquet(items: Iterable[Item], geoparquet_path: Path) -> int:
    items = list(items)
    if not items:
        return 0
    new_table = stac_geoparquet.parse_stac_items_to_arrow(
        [item.to_dict() for item in items]
    ).read_all()
    if geoparquet_path.exists():
        existing_table = pq.read_table(geoparquet_path)
        # Align schemas in case pyarrow infers slightly different column
        # order/types between the two batches.
        new_table = new_table.cast(existing_table.schema)
        combined = pq.concat_tables([existing_table, new_table])
    else:
        geoparquet_path.parent.mkdir(parents=True, exist_ok=True)
        combined = new_table
    stac_geoparquet.to_parquet(combined, geoparquet_path)
    return len(items)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--geoparquet",
        type=Path,
        default=Path("data/sea-ice-concentration-items.parquet"),
        help="Path to the STAC GeoParquet file to read/append to.",
    )
    args = parser.parse_args()

    known_ids = existing_item_ids(args.geoparquet)
    logger.info("%d items already in %s", len(known_ids), args.geoparquet)

    granules = find_new_granules(known_ids)
    logger.info(
        "%d new granule(s) found in the last %d days", len(granules), LOOKBACK_DAYS
    )

    with tempfile.TemporaryDirectory() as tmp:
        items = build_items(granules, Path(tmp))
        added = write_geoparquet(items, args.geoparquet)

    logger.info("Added %d new item(s) to %s", added, args.geoparquet)
    # Used by the GitHub Actions workflow to decide whether to commit.
    print(f"items_added={added}")


if __name__ == "__main__":
    main()
