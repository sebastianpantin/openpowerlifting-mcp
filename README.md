# openpowerlifting-mcp

An MCP server that lets an LLM query [OpenPowerlifting](https://www.openpowerlifting.org) meet results: about four million entries from raw and equipped meets worldwide, with every attempt recorded.

Ask things like "How has Taylor Atwood's raw total changed since 2015?" or "Where would a 600 kg total put a tested 93 kg raw lifter?" and the model answers from the actual data instead of from memory.

## Tools

| Tool | What it does |
| --- | --- |
| `search_lifters` | Find lifters by name. Handles the `#2`-style suffixes OpenPowerlifting uses for lifters who share a name. |
| `lifter_history` | Every meet for one lifter with each attempt. Missed attempts are negative; fourth attempts (records only) are kept apart. |
| `percentile_for_total` | Rank a total against each lifter's best total, filtered by sex, equipment, weight class, event and drug testing. |
| `compare_lifters` | Career bests side by side for 2 to 10 lifters. |

## Setup

Needs [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/sebastianpantin/openpowerlifting-mcp
cd openpowerlifting-mcp
uv sync
uv run python scripts/fetch_data.py
```

`fetch_data.py` downloads the latest bulk CSV (about 170 MB zipped, 830 MB unzipped) into `raw/` and converts it once with DuckDB into `data/openpowerlifting.parquet` (about 150 MB). It takes under a minute on a decent connection. Run it again with `--force` to pick up a newer export.

## Use it with Claude Desktop

```sh
uv run mcp install server.py --name openpowerlifting --with-editable .
```

Restart Claude Desktop and the tools show up. Any other MCP client can start the server over stdio with `uv run --directory /path/to/openpowerlifting-mcp openpowerlifting-mcp`.

The server looks for `data/openpowerlifting.parquet` in the repo. Set `OPL_PARQUET` to use a file somewhere else.

## Use it as a skill

`skills/openpowerlifting/` is an [Agent Skill](https://agentskills.io) for clients that load skills instead of, or as well as, MCP servers. It runs the same queries through the `opl` command, so it needs the setup above. Link it into your skills folder, for example for Claude Code:

```sh
ln -s "$PWD/skills/openpowerlifting" ~/.claude/skills/openpowerlifting
```

The skill's `opl` script finds the checkout through the link. You can also run the command yourself:

```sh
uv run opl search "ray williams"
uv run opl history "John Doe #2"
uv run opl percentile 600 --sex M --equipment Raw --weight-class 93 --tested
uv run opl compare "Lifter A" "Lifter B" --equipment Raw
```

## Development

```sh
uv run mcp dev server.py   # MCP Inspector in the browser
uv run pytest
uv run ruff check . && uv run ruff format .
```

Tests run against a nine-row CSV in `tests/fixtures/` that uses the real column layout, so they don't need the full download.

Queries go straight to the Parquet file through DuckDB. Lookups take well under 100 ms on a laptop, so there is no database to run.

## Data

This project uses data from the OpenPowerlifting project, https://www.openpowerlifting.org.
You may download a copy of the data at https://data.openpowerlifting.org.

The data is in the public domain. This repository does not include it; `fetch_data.py` downloads it from OpenPowerlifting.

## License

MIT for the code. See [LICENSE](LICENSE).
