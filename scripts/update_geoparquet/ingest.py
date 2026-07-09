"""Scans the NSIDC HTTPS directory listing for new G02202 V6 daily granules
(both hemispheres), turns each new one into a STAC item using the
sea_ice_concentration stactools module, and appends them to a STAC
GeoParquet file.

Files are publicly accessible at noaadata.apps.nsidc.org with no
authentication required. We parse the directory listing directly rather
than going through CMR/earthaccess, which was returning 0 granules for
this collection even when files are current to within ~7 days.

Designed to run on a schedule (see
.github/workflows/update-sea-ice-geoparquet.yml). Re-runs are safe:
granules already present in the GeoParquet (by item id) are skipped.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests
import stac_geoparquet.arrow as stac_geoparquet
from pystac import Item

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from stactools.noaa_cdr.sea_ice_concentration import stac as sic_stac  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("update_geoparquet")

BASE_URL = "https://noaadata.apps.nsidc.org/NOAA/G02202_V6"
HEMISPHERES = {
    "north": "psn25",
    "south": "pss25",
}
# Filename pattern: sic_psn25_YYYYMMDD_<sensor>_v06r00.nc
FILENAME_RE = re.compile(r"^sic_(psn25|pss25)_(\d{8})_[a-z0-9]+_v06r\d+\.nc$")


def iter_remote_files(
    hemisphere: str, since: datetime | None = None
) -> Iterator[tuple[str, str]]:
    """Yields (filename, url) for daily .nc files for one hemisphere.

    Walks year subdirectories under .../north/daily/ or .../south/daily/,
    skipping any year that's entirely before `since`.
    """
    token = HEMISPHERES[hemisphere]
    base = f"{BASE_URL}/{hemisphere}/daily"

    resp = requests.get(base + "/", timeout=30)
    resp.raise_for_status()
    years = sorted(set(re.findall(r'href="(\d{4})/"', resp.text)))

    since_year = since.year if since is not None else None
    for year in years:
        if since_year is not None and int(year) < since_year:
            continue
        year_url = f"{base}/{year}/"
        resp = requests.get(year_url, timeout=30)
        resp.raise_for_status()
        filenames = re.findall(rf'href="(sic_{token}_\d{{8}}_[^"]+\.nc)"', resp.text)
        for fname in sorted(filenames):
            yield fname, f"{year_url}{fname}"


def existing_item_ids(geoparquet_path: Path) -> set[str]:
    if not geoparquet_path.exists():
        return set()
    table = pq.read_table(geoparquet_path, columns=["id"])
    return set(table.column("id").to_pylist())


def latest_start_datetime(geoparquet_path: Path) -> Any:
    if not geoparquet_path.exists():
        return None
    table = pq.read_table(geoparquet_path, columns=["start_datetime"])
    col = table.column("start_datetime")
    if col.null_count == len(col):
        return None
    return pc.max(col).as_py()


def find_new_urls(
    known_ids: set[str],
    geoparquet_path: Path,
    since: datetime | None = None,
) -> list[tuple[str, str, str]]:
    """Returns list of (filename, url, hemisphere) for files not yet in the GeoParquet."""
    if since is None:
        since = latest_start_datetime(geoparquet_path)
    new = []
    for hemisphere in HEMISPHERES:
        for fname, url in iter_remote_files(hemisphere, since=since):
            item_id = fname[: -len(".nc")]
            if item_id in known_ids:
                continue
            m = FILENAME_RE.match(fname)
            if m and since is not None:
                file_date = datetime.strptime(m.group(2), "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
                if file_date <= since:
                    continue
            new.append((fname, url, hemisphere))
    return new


def build_items(entries: list[tuple[str, str, str]], download_dir: Path) -> list[Item]:
    items = []
    session = requests.Session()
    for fname, url, hemisphere in entries:
        local_path = download_dir / fname
        logger.info("Downloading %s", url)
        with session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        item = sic_stac.create_item(str(local_path))
        item.properties["noaa_cdr:hemisphere"] = hemisphere
        # Publish the canonical NSIDC URL, not the local tmp path
        from stactools.noaa_cdr.constants import NETCDF_ASSET_KEY

        item.assets[NETCDF_ASSET_KEY].href = url
        items.append(item)
        logger.info("Built item %s (%s)", item.id, hemisphere)
        local_path.unlink()  # free space immediately after item is built
    return items


def write_geoparquet(items: list[Item], geoparquet_path: Path) -> int:
    if not items:
        return 0
    new_table = stac_geoparquet.parse_stac_items_to_arrow(
        [item.to_dict() for item in items]
    ).read_all()
    if geoparquet_path.exists():
        existing_table = pq.read_table(geoparquet_path)
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
    )
    parser.add_argument(
        "--since",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc),
        default=None,
        help="Only ingest files after this date (YYYY-MM-DD). "
        "Defaults to the most recent item already in the GeoParquet.",
    )
    args = parser.parse_args()

    known_ids = existing_item_ids(args.geoparquet)
    logger.info("%d items already in %s", len(known_ids), args.geoparquet)

    entries = find_new_urls(known_ids, args.geoparquet, since=args.since)
    logger.info("%d new file(s) found", len(entries))

    with tempfile.TemporaryDirectory() as tmp:
        items = build_items(entries, Path(tmp))
        added = write_geoparquet(items, args.geoparquet)

    logger.info("Added %d new item(s) to %s", added, args.geoparquet)
    print(f"items_added={added}")


if __name__ == "__main__":
    main()
