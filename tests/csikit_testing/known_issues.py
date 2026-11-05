"""Registry of known bugs, each tracked by a GitHub issue.

A test that demonstrates a known bug asserts the *correct* behaviour and is
marked with :func:`known_bug`, which is a strict ``xfail``. When the bug is
fixed the test passes, pytest reports ``XPASS(strict)`` as a failure, and the
fix should remove the marker in the same change. That keeps this file an
accurate list of what is still broken.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

REPO = "Gi-z/CSIKit"


@dataclass(frozen=True)
class Issue:
    number: Optional[int]
    """GitHub issue/PR number, or None while the issue hasn't been filed yet."""
    title: str
    kind: str = "issue"  # or "pull"

    @property
    def ref(self) -> str:
        return f"{REPO}#{self.number}" if self.number else "(issue not yet filed)"

    @property
    def url(self) -> Optional[str]:
        if not self.number:
            return None
        return f"https://github.com/{REPO}/{'pull' if self.kind == 'pull' else 'issues'}/{self.number}"


def known_bug(issue: Issue, *, condition: bool = True, raises=None):
    """Strict xfail tied to a tracked issue."""
    return pytest.mark.xfail(
        condition,
        reason=f"known bug {issue.ref}: {issue.title}",
        strict=True,
        raises=raises,
    )


# --- Parsing ------------------------------------------------------------------

ATHEROS_DROPS_TRAILING_FRAMES = Issue(
    None, "Atheros: the last frames of a file are dropped when records are small")
PICOSCENES_LOG_EXCEPTION = Issue(
    54, "PicoScenes: invalid frame header raises AttributeError (log_exception)")
FEITCSI_MULTI_TX_INTERPOLATION = Issue(
    64, "FeitCSI: pilot interpolation only covers the first Tx stream", kind="pull")

# --- Processing / API -----------------------------------------------------------


# --- CLI -------------------------------------------------------------------------

HEATMAP_SUBCARRIER_AXIS_FLIPPED = Issue(
    None, "Heatmaps draw subcarrier 0 at the top of a subcarrier axis that increases upwards")

# --- Not bugs we can assert on yet ---------------------------------------------

NEEDS_GROUND_TRUTH = Issue(
    None, "Unverified conventions: Atheros element order/offset, PicoScenes IWL5300 antenna "
       "permutation, Nexmon core/spatial-stream axes")
