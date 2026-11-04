from pathlib import Path

import pytest

from opl_mcp.db import connect
from opl_mcp.ingest import csv_to_parquet


@pytest.fixture(scope="session")
def fixture_csv():
    return Path(__file__).parent / "fixtures" / "opl_sample.csv"


@pytest.fixture(scope="session")
def parquet_path(fixture_csv, tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "openpowerlifting.parquet"
    csv_to_parquet(fixture_csv, path)
    return path


@pytest.fixture
def con(parquet_path):
    connection = connect(parquet_path)
    yield connection
    connection.close()
