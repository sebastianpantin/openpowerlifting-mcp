import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from opl_mcp import server


@pytest.fixture
def mcp(parquet_path, monkeypatch):
    monkeypatch.setenv("OPL_PARQUET", str(parquet_path))
    server.database.cache_clear()
    yield server.mcp
    server.database.cache_clear()


def test_lists_tools(mcp):
    tools = anyio.run(mcp.list_tools)
    assert {tool.name for tool in tools} == {
        "search_lifters",
        "lifter_history",
        "percentile_for_total",
        "compare_lifters",
    }
    assert all(tool.description for tool in tools)
    assert all(tool.annotations.read_only_hint for tool in tools)


def test_calls_tool_through_server(mcp):
    result = anyio.run(mcp.call_tool, "lifter_history", {"name": "Jane Doe"})
    assert result.is_error is False
    assert result.structured_content["name"] == "Jane Doe"
    assert len(result.structured_content["meets"]) == 2


def test_rejects_unknown_sex(mcp):
    with pytest.raises(ToolError, match="sex"):
        anyio.run(mcp.call_tool, "percentile_for_total", {"total_kg": 400, "sex": "X"})
