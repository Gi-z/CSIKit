"""Golden-output regression tests: every bundled capture parses to its recorded fingerprint.

See tests/csikit_testing/snapshots.py. Regenerate with ``pytest --update-snapshots``.
"""
import pytest

from csikit_testing import read_fresh
from csikit_testing import snapshots
from csikit_testing.samples import params


@pytest.mark.parametrize("sample", params())
def test_reader_output_matches_snapshot(sample, update_snapshots):
    summary = snapshots.summarize(read_fresh(sample.path), read_fresh(sample.path, scaled=True))

    if update_snapshots:
        snapshots.save(sample.path, summary)
        return

    expected = snapshots.load(sample.path)
    if expected is None:
        pytest.fail(f"No snapshot for {sample.path}; run `pytest --update-snapshots` to create one.")

    problems = snapshots.diff(expected, summary)
    assert not problems, "Reader output changed:\n  " + "\n  ".join(problems)
