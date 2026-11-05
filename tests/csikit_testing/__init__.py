"""Shared helpers for the CSIKit test suite.

Importable from any test module because ``tests`` is on ``pythonpath``
(see ``[tool:pytest]`` in setup.cfg).
"""
from __future__ import annotations

import contextlib
import functools
import io
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "CSIKit" / "data"
TESTS_DIR = REPO_ROOT / "tests"
SNAPSHOT_DIR = TESTS_DIR / "snapshots"

NUMPY2 = int(np.__version__.split(".")[0]) >= 2
"""NEP 50 integer promotion: out-of-range Python ints raise OverflowError."""


def _scalar_slot_rejects_arrays() -> bool:
    # Assigning a size-1 array into a scalar slot was deprecated in NumPy 1.25
    # and became a TypeError in 2.4. csitools.get_CSI relies on it.
    import warnings

    target = np.zeros(1, dtype=complex)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            target[0] = np.ones(1)
        except TypeError:
            return True
    return False


NUMPY_STRICT_SCALAR_ASSIGNMENT = _scalar_slot_rejects_arrays()


def repo_path(relative: str) -> Path:
    """Resolve a repo-relative path, failing loudly if the file is missing."""
    path = REPO_ROOT / relative
    if not path.exists():
        raise FileNotFoundError(f"Test data file is missing: {path}")
    return path


def read_quietly(reader, path, **kwargs):
    """Call ``reader.read_file`` while swallowing the library's stdout chatter."""
    with contextlib.redirect_stdout(io.StringIO()):
        return reader.read_file(str(path), **kwargs)


@functools.lru_cache(maxsize=None)
def read_cached(relative: str, scaled: bool = False):
    """Parse a sample once per test session.

    Only use this for read-only assertions: ``csitools.get_CSI`` currently
    mutates ``CSIData.timestamps``, so tests that call it should parse their
    own copy with :func:`read_fresh`.
    """
    return read_fresh(relative, scaled=scaled)


def read_fresh(relative: str, scaled: bool = False):
    from CSIKit.reader import get_reader

    path = repo_path(relative)
    with contextlib.redirect_stdout(io.StringIO()):
        reader = get_reader(str(path))
        return reader.read_file(str(path), scaled=scaled)
