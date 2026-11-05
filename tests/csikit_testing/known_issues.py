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

ESP32_IMAG_REAL_ORDER = Issue(
    70, "ESP32: subcarrier values are read as (real, imag) but ESP-IDF stores (imag, real)")
ESP32_TIMESTAMPS = Issue(
    63, "ESP32: timestamps are 1000x too small (seconds divided by 1000)")
ESP32_ODD_LENGTH_ROW = Issue(
    71, "ESP32: a CSV row with an odd number of CSI values aborts the whole read")
CSV_DROPS_ANTENNA_1 = Issue(
    72, "CSV reader drops every row with ant == 1, for all CSV formats")
NEXMON_OVERSIZED_FRAMES_DROPPED = Issue(
    73, "Nexmon: frames with trailing padding are silently dropped")
NEXMON_SKIPPED_FRAMES_APPENDED = Issue(
    74, "Nexmon: skipped frames are appended as zero-CSI frames at the end with timestamp 0")
FILTER_MAC_BROKEN = Issue(
    75, "filter_mac is ignored by the Nexmon reader and crashes the FeitCSI reader")
ATHEROS_DROPS_TRAILING_FRAMES = Issue(
    None, "Atheros: the last frames of a file are dropped when records are small")
IWL_TIMESTAMP_WRAP = Issue(
    77, "IWL5300: 32-bit timestamp_low wraparound produces negative timestamps")
PICOSCENES_LOG_EXCEPTION = Issue(
    54, "PicoScenes: invalid frame header raises AttributeError (log_exception)")
FEITCSI_MULTI_TX_INTERPOLATION = Issue(
    64, "FeitCSI: pilot interpolation only covers the first Tx stream", kind="pull")

# --- Processing / API -----------------------------------------------------------

GET_CSI_DROPPED_FRAMES = Issue(
    78, "get_CSI returns a stale frame count when it drops frames, and mutates CSIData.timestamps")
NUMPY_GLOBAL_ERRSTATE = Issue(
    79, "Importing CSIKit changes NumPy's global floating-point error settings")
UNRECOGNISED_FILES = Issue(
    80, "Unrecognised files fall back to the Intel reader and crash later with IndexError")

# --- CLI -------------------------------------------------------------------------

INFO_INTEL_RSSI_NOT_DBM = Issue(
    81, "csikit info reports raw Intel RSSI as dBm")
CLI_GRAPH_TYPES_CRASH = Issue(
    82, "csikit --graph_type all_subcarriers and subcarrier_filter crash")

# --- Not bugs we can assert on yet ---------------------------------------------

NEEDS_GROUND_TRUTH = Issue(
    None, "Unverified conventions: Atheros element order/offset, PicoScenes IWL5300 antenna "
       "permutation, Nexmon core/spatial-stream axes")
