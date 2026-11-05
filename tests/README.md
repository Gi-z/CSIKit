# CSIKit test suite

```bash
pip install -e ".[test]"          # pytest + scipy
pip install -e ".[crosscheck]"    # optional: csiread, for independent cross-checks
pytest                            # ~45 s
pytest --runslow                  # also parse the two largest captures (~3 min)
```

No environment variables are needed; sample paths are resolved from the repository root.

## Layout

| Path | What it covers |
| --- | --- |
| `readers/test_reader_selection.py` | `get_reader` / `can_read` routing for every bundled capture, foreign files |
| `readers/test_snapshots.py` | Golden-output regression for every bundled capture (see below) |
| `readers/test_<format>.py` | Per-format framing, headers, timestamps, edge cases (Atheros uses synthetic files) |
| `matlab/` | Agreement with the original toolkits' MATLAB parsers (`.mat` references) |
| `test_crosscheck_csiread.py` | Agreement with [csiread](https://github.com/citysu/csiread), an independent parser |
| `test_csitools.py`, `test_csidata.py` | `get_CSI`, scaling, `CSIData` filtering and metadata |
| `test_filters.py`, `test_utils.py` | Signal filters, byte/bit helpers |
| `test_cli.py` | The `csikit` command, run as a subprocess |
| `csikit_testing/` | Shared helpers: sample catalogue, known-issue registry, snapshot tooling, synthetic file builders |

Every capture-driven test is parametrised from `csikit_testing/samples.py`, so a new sample file only needs one entry there.

## Known bugs are strict xfails

Tests assert the *correct* behaviour. Where CSIKit is currently wrong, the test is marked with
`known_bug(<ISSUE>)` from `csikit_testing/known_issues.py`, which is a strict `xfail` linked to the
GitHub issue. When a fix lands the test passes, pytest reports `XPASS(strict)` as a failure, and the
marker must be removed in the same change, so `known_issues.py` stays an accurate list of what is
still broken. Use `pytest --runxfail` to see every known bug fail for real.

CI runs both NumPy 1.x and 2.x, so version-specific breakage shows up too.

Disagreements with csiread that haven't been resolved either way are non-strict xfails pointing at
`NEEDS_GROUND_TRUTH`.

## Snapshots

`snapshots/readers/*.json` fingerprint each capture as CSIKit currently parses it: frame count and
shapes, metadata, timestamp statistics, CSI checksums and the first few values, raw and scaled. They
record current behaviour, *including known bugs*, so any change to reader output is visible.

If a change is meant to alter reader output, regenerate the snapshots and explain the diff in the commit:

```bash
pytest tests/readers/test_snapshots.py --update-snapshots --runslow
```

Generate them on NumPy 1.x, where every format currently parses.
