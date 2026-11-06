---
name: openpowerlifting
description: Look up powerlifting meet results from OpenPowerlifting. Use when asked about a powerlifter's meets, attempts, totals or progress, how a total ranks against other lifters, or how several lifters compare. Answers come from the actual data, not from memory.
---

# OpenPowerlifting

Run the `opl` script in this skill's directory. Each command prints JSON.

```sh
opl search "ray williams"            # find lifters by name
opl history "John Doe #2"            # every meet for one lifter, with each attempt
opl percentile 600 --sex M --equipment Raw --weight-class 93 --tested
opl compare "Lifter A" "Lifter B" --equipment Raw
```

Run `opl <command> --help` for every option.

## Reading the data

- Weights are in kg. A negative attempt is a miss at that weight. A fourth attempt is a record attempt and does not count toward the total.
- Lifters who share a name are told apart with a suffix such as `John Doe #2`. When a name may be ambiguous, run `search` first and pass the exact name to the other commands. `history` returns `found: false` and a list of candidates when the name has no exact match.
- `percentile` counts each lifter once, with their best total, and ignores disqualified entries. Weight classes differ between federations and eras, so leave `--weight-class` out for a broad comparison.
- `--tested` keeps drug-tested meets only and `--untested` keeps untested meets only.
- Pass `--equipment` to `compare` so that raw lifts are not compared with equipped ones.

## Answering

- Say which filters a percentile uses, and the size of the cohort.
- Give dates with results, since a lifter's best may be years old.
- Credit the data: "Data from OpenPowerlifting (openpowerlifting.org)".

If `opl` reports that the data file is missing, tell the user to run `uv run python scripts/fetch_data.py` in the openpowerlifting-mcp checkout.
