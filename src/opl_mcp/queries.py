import datetime
import re
from typing import Any, Literal

import duckdb

from opl_mcp.ingest import LIFTS

Sex = Literal["M", "F", "Mx"]
Equipment = Literal["Raw", "Wraps", "Single-ply", "Multi-ply", "Unlimited", "Straps"]
Event = Literal["SBD", "BD", "SD", "SB", "S", "B", "D"]

SUFFIX_TOKEN = re.compile(r"#\d+")
NAME_SUFFIX = r"\s*#\d+$"

CAREER_SUMMARY = """
    Name AS name,
    arg_max(Sex, Date) AS sex,
    count(*) AS meets,
    min(Date) AS first_meet,
    max(Date) AS last_meet,
    max(TotalKg) AS best_total_kg,
    list(DISTINCT Federation ORDER BY Federation) AS federations
"""


def json_value(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime.date) else value


def records(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [d[0] for d in cursor.description]
    return [
        {column: json_value(value) for column, value in zip(columns, row, strict=True)}
        for row in cursor.fetchall()
    ]


def escape_like(token: str) -> str:
    return token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_lifters(
    con: duckdb.DuckDBPyConnection, query: str, limit: int = 20
) -> list[dict[str, Any]]:
    tokens = query.split()
    if not tokens:
        return []
    conditions, params = [], []
    for token in tokens:
        if SUFFIX_TOKEN.fullmatch(token):
            conditions.append("Name LIKE ?")
            params.append(f"% {token}")
        else:
            conditions.append("Name ILIKE ? ESCAPE '\\'")
            params.append(f"%{escape_like(token)}%")
    cursor = con.execute(
        f"""
        SELECT
            {CAREER_SUMMARY},
            regexp_replace(Name, ?, '') AS base_name,
            arg_max(Country, Date) AS country
        FROM entries
        WHERE {" AND ".join(conditions)}
        GROUP BY Name
        ORDER BY meets DESC, name
        LIMIT ?
        """,
        [NAME_SUFFIX, *params, limit],
    )
    return records(cursor)


def resolve_names(con: duckdb.DuckDBPyConnection, names: list[str]) -> dict[str, str]:
    """Map each input to its stored name: exact match first, else a unique case-insensitive one.

    OpenPowerlifting has distinct lifters whose names differ only by case.
    """
    stored = [
        row[0]
        for row in con.execute(
            """
            SELECT DISTINCT Name FROM entries
            WHERE lower(Name) IN (SELECT lower(unnest(?::VARCHAR[])))
            """,
            [names],
        ).fetchall()
    ]
    resolved = {}
    for name in names:
        matches = [s for s in stored if s.lower() == name.lower()]
        if name in matches:
            resolved[name] = name
        elif len(matches) == 1:
            resolved[name] = matches[0]
    return resolved


def lift_struct(lift: str) -> str:
    return (
        f"{{'attempts': [{lift}1Kg, {lift}2Kg, {lift}3Kg], 'best': Best3{lift}Kg,"
        f" 'fourth': {lift}4Kg}}"
        f" AS {lift.lower()}"
    )


def lifter_history(con: duckdb.DuckDBPyConnection, name: str) -> dict[str, Any]:
    stored = resolve_names(con, [name]).get(name)
    if stored is None:
        candidates = search_lifters(con, re.sub(NAME_SUFFIX, "", name), limit=10)
        return {"name": name, "found": False, "candidates": candidates}
    cursor = con.execute(
        f"""
        SELECT
            Date AS date,
            MeetName AS meet_name,
            Federation AS federation,
            MeetCountry AS meet_country,
            Event AS event,
            Equipment AS equipment,
            Division AS division,
            Sex AS sex,
            Age AS age,
            BodyweightKg AS bodyweight_kg,
            WeightClassKg AS weight_class_kg,
            {", ".join(lift_struct(lift) for lift in LIFTS)},
            TotalKg AS total_kg,
            Place AS place,
            Dots AS dots,
            Tested AS tested
        FROM entries
        WHERE Name = ?
        ORDER BY Date, MeetName
        """,
        [stored],
    )
    return {"name": stored, "found": True, "meets": records(cursor)}


def percentile_for_total(
    con: duckdb.DuckDBPyConnection,
    total_kg: float,
    sex: str,
    equipment: str | None = None,
    weight_class: str | None = None,
    tested: bool | None = None,
    event: str = "SBD",
) -> dict[str, Any]:
    filters = [
        ("event", "Event", event),
        ("sex", "Sex", sex),
        ("equipment", "Equipment", equipment),
        ("weight_class", "WeightClassKg", weight_class),
        ("tested", "Tested", tested),
    ]
    active = [f for f in filters if f[2] is not None]
    where = " AND ".join(["TotalKg > 0", *(f"{column} = ?" for _, column, _ in active)])
    lifters, below, equal, p25, median, p75, p90, best = con.execute(
        f"""
        WITH best AS (
            SELECT max(TotalKg) AS total FROM entries WHERE {where} GROUP BY Name
        )
        SELECT
            count(*),
            count(*) FILTER (WHERE total < ?),
            count(*) FILTER (WHERE total = ?),
            quantile_cont(total, 0.25),
            quantile_cont(total, 0.5),
            quantile_cont(total, 0.75),
            quantile_cont(total, 0.9),
            max(total)
        FROM best
        """,
        [*(value for _, _, value in active), total_kg, total_kg],
    ).fetchone()
    return {
        "total_kg": total_kg,
        "filters": {key: value for key, _, value in active},
        "lifters": lifters,
        "percentile": round(100 * (below + equal / 2) / lifters, 1) if lifters else None,
        "cohort_totals_kg": {"p25": p25, "median": median, "p75": p75, "p90": p90, "max": best},
    }


def compare_lifters(
    con: duckdb.DuckDBPyConnection, names: list[str], equipment: str | None = None
) -> dict[str, Any]:
    resolved = resolve_names(con, names)
    equipment_filter, params = "", [list(resolved.values())]
    if equipment:
        equipment_filter = "AND Equipment = ?"
        params.append(equipment)
    best_lifts = ", ".join(f"max(Best3{lift}Kg) AS best_{lift.lower()}_kg" for lift in LIFTS)
    cursor = con.execute(
        f"""
        SELECT
            {CAREER_SUMMARY},
            {best_lifts},
            max(Dots) AS best_dots,
            arg_max(BodyweightKg, Date) AS latest_bodyweight_kg
        FROM entries
        WHERE Name IN (SELECT unnest(?::VARCHAR[])) {equipment_filter}
        GROUP BY Name
        """,
        params,
    )
    by_name = {row["name"]: row for row in records(cursor)}
    return {
        "equipment": equipment,
        "lifters": [by_name[resolved[n]] for n in names if resolved.get(n) in by_name],
        "not_found": [n for n in names if resolved.get(n) not in by_name],
    }
