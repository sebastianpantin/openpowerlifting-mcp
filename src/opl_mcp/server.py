from functools import cache
from typing import Annotated, Any, Literal

import duckdb
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from opl_mcp import queries
from opl_mcp.db import connect, parquet_path

Sex = Literal["M", "F", "Mx"]
Equipment = Literal["Raw", "Wraps", "Single-ply", "Multi-ply", "Unlimited", "Straps"]
Event = Literal["SBD", "BD", "SD", "SB", "S", "B", "D"]

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)

mcp = MCPServer(
    "openpowerlifting",
    instructions=(
        "Query OpenPowerlifting meet results. Lifters who share a name are told apart "
        "with a suffix such as 'John Doe #2', so call search_lifters first when a name "
        "may be ambiguous and pass the exact name to the other tools. Weights are in kg. "
        "A negative attempt is a missed lift at that weight."
    ),
)


@cache
def database() -> duckdb.DuckDBPyConnection:
    return connect(parquet_path())


@mcp.tool(annotations=READ_ONLY)
def search_lifters(
    query: Annotated[str, Field(description="Part of a name, e.g. 'ray williams' or 'doe #2'")],
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
) -> list[dict[str, Any]]:
    """Find lifters by name. Every word must appear in the name, in any order.

    A word like '#2' matches the OpenPowerlifting suffix used to tell apart lifters
    with the same name. Results are sorted by number of meets.
    """
    with database().cursor() as con:
        return queries.search_lifters(con, query, limit)


@mcp.tool(annotations=READ_ONLY)
def lifter_history(
    name: Annotated[str, Field(description="Exact lifter name including any '#N' suffix")],
) -> dict[str, Any]:
    """Every meet for one lifter in date order, with each attempt per lift.

    A fourth attempt is a record attempt and does not count toward the total.

    If the name has no exact match, returns found=false and a list of candidates.
    """
    with database().cursor() as con:
        return queries.lifter_history(con, name)


@mcp.tool(annotations=READ_ONLY)
def percentile_for_total(
    total_kg: Annotated[float, Field(gt=0)],
    sex: Sex,
    equipment: Equipment | None = None,
    weight_class: Annotated[
        str | None, Field(description="OpenPowerlifting class label, e.g. '93' or '120+'")
    ] = None,
    tested: Annotated[
        bool | None, Field(description="true for drug-tested only, false for untested only")
    ] = None,
    event: Event = "SBD",
) -> dict[str, Any]:
    """Where a total ranks among lifters' best totals in a filtered cohort.

    Each lifter counts once, with their best total. Disqualified entries are ignored.
    Weight classes differ between federations and eras, so leave weight_class out for
    a broad comparison.
    """
    with database().cursor() as con:
        return queries.percentile_for_total(
            con, total_kg, sex, equipment, weight_class, tested, event
        )


@mcp.tool(annotations=READ_ONLY)
def compare_lifters(
    names: Annotated[list[str], Field(min_length=2, max_length=10)],
    equipment: Equipment | None = None,
) -> dict[str, Any]:
    """Side-by-side career bests for several lifters, matched by exact name.

    Pass equipment to avoid comparing raw lifts with equipped ones.
    """
    with database().cursor() as con:
        return queries.compare_lifters(con, names, equipment)


def main() -> None:
    mcp.run()
