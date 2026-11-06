"""Command-line access to the same queries as the MCP server, printing JSON."""

import argparse
import json
import sys
from typing import get_args

from opl_mcp import queries
from opl_mcp.db import connect, parquet_path


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="opl",
        description="Query OpenPowerlifting meet results. Weights are in kg; "
        "a negative attempt is a missed lift at that weight.",
    )
    commands = root.add_subparsers(dest="command", required=True)

    search = commands.add_parser("search", help="find lifters by name")
    search.add_argument("query", help="part of a name, e.g. 'ray williams' or 'doe #2'")
    search.add_argument("--limit", type=int, default=20)

    history = commands.add_parser("history", help="every meet for one lifter")
    history.add_argument("name", help="exact lifter name including any '#N' suffix")

    percentile = commands.add_parser("percentile", help="rank a total in a cohort")
    percentile.add_argument("total_kg", type=float)
    percentile.add_argument("--sex", required=True, choices=get_args(queries.Sex))
    percentile.add_argument("--equipment", choices=get_args(queries.Equipment))
    percentile.add_argument("--weight-class", help="class label, e.g. '93' or '120+'")
    tested = percentile.add_mutually_exclusive_group()
    tested.add_argument("--tested", action="store_true", default=None)
    tested.add_argument("--untested", dest="tested", action="store_false")
    percentile.add_argument("--event", default="SBD", choices=get_args(queries.Event))

    compare = commands.add_parser("compare", help="career bests side by side")
    compare.add_argument("names", nargs="+", metavar="name")
    compare.add_argument("--equipment", choices=get_args(queries.Equipment))
    return root


def run(con, args: argparse.Namespace):
    match args.command:
        case "search":
            return queries.search_lifters(con, args.query, args.limit)
        case "history":
            return queries.lifter_history(con, args.name)
        case "percentile":
            return queries.percentile_for_total(
                con,
                args.total_kg,
                args.sex,
                args.equipment,
                args.weight_class,
                args.tested,
                args.event,
            )
        case "compare":
            return queries.compare_lifters(con, args.names, args.equipment)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        con = connect(parquet_path())
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 1
    with con:
        print(json.dumps(run(con, args), indent=2))
    return 0
