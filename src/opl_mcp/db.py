import os
from pathlib import Path

import duckdb

DEFAULT_PARQUET = Path(__file__).resolve().parents[2] / "data" / "openpowerlifting.parquet"


def parquet_path() -> Path:
    return Path(os.environ.get("OPL_PARQUET", DEFAULT_PARQUET))


def connect(path: str | Path) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB with an `entries` view over the Parquet file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Run `uv run python scripts/fetch_data.py` "
            "or set OPL_PARQUET to the converted file."
        )
    con = duckdb.connect()
    con.read_parquet(str(path)).create_view("entries")
    return con
