import json

import pytest

from opl_mcp.cli import main


@pytest.fixture
def run(parquet_path, monkeypatch, capsys):
    monkeypatch.setenv("OPL_PARQUET", str(parquet_path))

    def run(*args: str):
        code = main(list(args))
        out = capsys.readouterr()
        return code, json.loads(out.out) if out.out else None, out.err

    return run


def test_searches_lifters(run):
    code, result, _ = run("search", "jane")
    assert code == 0
    assert "Jane Doe" in [lifter["name"] for lifter in result]


def test_prints_a_lifters_history(run):
    code, result, _ = run("history", "Jane Doe")
    assert code == 0
    assert result["name"] == "Jane Doe"
    assert len(result["meets"]) == 2


def test_ranks_a_total_with_filters(run):
    code, result, _ = run("percentile", "400", "--sex", "F", "--equipment", "Raw", "--tested")
    assert code == 0
    assert result["filters"] == {"event": "SBD", "sex": "F", "equipment": "Raw", "tested": True}


def test_compares_lifters(run):
    code, result, _ = run("compare", "Jane Doe", "Anna Berg", "--equipment", "Raw")
    assert code == 0
    assert [lifter["name"] for lifter in result["lifters"]] == ["Jane Doe", "Anna Berg"]


def test_rejects_unknown_sex(run):
    with pytest.raises(SystemExit):
        run("percentile", "400", "--sex", "X")


def test_explains_missing_data(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OPL_PARQUET", str(tmp_path / "missing.parquet"))
    assert main(["history", "Jane Doe"]) == 1
    assert "fetch_data.py" in capsys.readouterr().err
