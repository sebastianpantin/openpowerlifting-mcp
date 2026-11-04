import datetime

import duckdb
import pytest

from opl_mcp.db import connect
from opl_mcp.ingest import csv_to_parquet


def test_converts_every_row(fixture_csv, tmp_path):
    assert csv_to_parquet(fixture_csv, tmp_path / "out.parquet") == 10


def test_types_numbers_dates_and_tested_flag(con):
    squat3, total, date, tested = con.execute(
        """
        SELECT Squat3Kg, TotalKg, Date, Tested
        FROM entries WHERE Name = 'John Smith #1' ORDER BY Date LIMIT 1
        """
    ).fetchone()
    assert squat3 == -215.0
    assert total == 615.0
    assert date == datetime.date(2022, 3, 12)
    assert tested is True


def test_untested_and_disqualified_rows(con):
    tested, total, place = con.execute(
        "SELECT Tested, TotalKg, Place FROM entries WHERE Name = 'Erik Lund'"
    ).fetchone()
    assert tested is True
    assert total is None
    assert place == "DQ"
    assert con.execute("SELECT Tested FROM entries WHERE Name = 'Mia Wong'").fetchone() == (False,)


def test_weight_class_stays_text(con):
    column_type = con.execute(
        "SELECT data_type FROM information_schema.columns WHERE column_name = 'WeightClassKg'"
    ).fetchone()
    assert column_type == ("VARCHAR",)


def test_connect_reports_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="fetch_data.py"):
        connect(tmp_path / "missing.parquet")


def test_csv_to_parquet_handles_quote_in_path(fixture_csv, tmp_path):
    target = tmp_path / "it's.parquet"
    csv_to_parquet(fixture_csv, target)
    assert duckdb.read_parquet(str(target)).shape == (10, 42)


def test_failed_conversion_keeps_previous_file(fixture_csv, tmp_path):
    target = tmp_path / "out.parquet"
    csv_to_parquet(fixture_csv, target)
    broken = tmp_path / "broken.csv"
    broken.write_text(fixture_csv.read_text().replace("2024-04-13", "not a date"))
    with pytest.raises(duckdb.Error):
        csv_to_parquet(broken, target)
    assert duckdb.read_parquet(str(target)).shape == (10, 42)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["broken.csv", "out.parquet"]
