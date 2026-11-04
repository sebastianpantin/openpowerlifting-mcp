"""Download the OpenPowerlifting bulk CSV and convert it to Parquet."""

import argparse
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from opl_mcp.db import DEFAULT_PARQUET
from opl_mcp.ingest import csv_to_parquet

URL = "https://openpowerlifting.gitlab.io/opl-csv/files/openpowerlifting-latest.zip"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
ZIP_PATH = RAW / "openpowerlifting-latest.zip"


def download(url: str, target: Path) -> None:
    partial = target.with_suffix(".part")
    with urllib.request.urlopen(url) as response, partial.open("wb") as out:
        size = int(response.headers.get("Content-Length", 0))
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if size:
                print(f"\r{done >> 20} / {size >> 20} MB", end="", flush=True)
    print()
    partial.rename(target)


def extract_csv(zip_path: Path, target_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        [member] = [m for m in archive.namelist() if m.endswith(".csv")]
        target = target_dir / Path(member).name
        with archive.open(member) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="download again even if cached")
    args = parser.parse_args()

    RAW.mkdir(exist_ok=True)
    DEFAULT_PARQUET.parent.mkdir(exist_ok=True)
    if args.force or not ZIP_PATH.exists():
        print(f"Downloading {URL}")
        download(URL, ZIP_PATH)
    elif DEFAULT_PARQUET.exists() and DEFAULT_PARQUET.stat().st_mtime > ZIP_PATH.stat().st_mtime:
        print(f"{DEFAULT_PARQUET.relative_to(ROOT)} is up to date. Use --force to download again.")
        return
    with tempfile.TemporaryDirectory(dir=RAW) as scratch:
        print("Extracting CSV")
        csv_path = extract_csv(ZIP_PATH, Path(scratch))
        print(f"Converting {csv_path.name} to Parquet")
        rows = csv_to_parquet(csv_path, DEFAULT_PARQUET)
    print(f"Wrote {rows:,} rows to {DEFAULT_PARQUET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
