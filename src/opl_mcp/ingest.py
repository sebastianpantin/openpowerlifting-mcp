from pathlib import Path

import duckdb

LIFTS = ("Squat", "Bench", "Deadlift")

NUMERIC_COLUMNS = (
    "Age",
    "BodyweightKg",
    *(f"{lift}{attempt}Kg" for lift in LIFTS for attempt in (1, 2, 3, 4)),
    *(f"Best3{lift}Kg" for lift in LIFTS),
    "TotalKg",
    "Dots",
    "Wilks",
    "Glossbrenner",
    "Goodlift",
)


def csv_to_parquet(csv_path: str | Path, parquet_path: str | Path) -> int:
    """Convert an OpenPowerlifting CSV to typed Parquet and return the row count.

    Numbers become DOUBLE (missed attempts stay negative), Date becomes DATE and
    Tested becomes a boolean. WeightClassKg stays text because of classes like "120+".
    """
    partial = Path(f"{parquet_path}.partial")
    casts = ", ".join(f'TRY_CAST("{c}" AS DOUBLE) AS "{c}"' for c in NUMERIC_COLUMNS)
    try:
        with duckdb.connect() as con:
            con.sql(
                f"""
                SELECT * REPLACE (
                    {casts},
                    coalesce("Tested" = 'Yes', false) AS "Tested",
                    CAST("Date" AS DATE) AS "Date"
                )
                FROM read_csv($csv, header = true, all_varchar = true)
                ORDER BY "Name", "Date"
                """,
                params={"csv": str(csv_path)},
            ).write_parquet(str(partial), compression="zstd")
            rows = con.read_parquet(str(partial)).shape[0]
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(parquet_path)
    return rows
