"""Golden-output snapshots for reader regression tests.

A snapshot is a compact JSON fingerprint of a parsed capture: frame count and
shapes, metadata, timestamp statistics, CSI checksums and the first few CSI
values (raw and scaled). It is deliberately computed straight from
``CSIData.frames`` rather than through ``csitools.get_CSI``, so it stays
stable while ``get_CSI`` is being fixed.

Snapshots record what CSIKit currently outputs, bugs included. A change that
alters a snapshot is a deliberate behaviour change: regenerate with
``pytest --update-snapshots`` and explain the diff in the commit message.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from csikit_testing import SNAPSHOT_DIR

N_FIRST_VALUES = 6


def _f(x) -> float:
    return float(x)


def _complex_list(values) -> list:
    return [[_f(v.real), _f(v.imag)] for v in values]


def _csi_stats(frames) -> dict:
    total = 0j
    abs_total = 0.0
    for frame in frames:
        m = np.asarray(frame.csi_matrix).astype(np.complex128)
        total += complex(m.sum())
        abs_total += float(np.abs(m).sum())
    first = np.asarray(frames[0].csi_matrix).astype(np.complex128).reshape(-1)[:N_FIRST_VALUES]
    return {
        "sum": [_f(total.real), _f(total.imag)],
        "abs_sum": abs_total,
        "first_values": _complex_list(first),
    }


def summarize(raw, scaled) -> dict:
    """Fingerprint a capture parsed with ``scaled=False`` and ``scaled=True``."""
    shapes = Counter(tuple(np.shape(f.csi_matrix)) for f in raw.frames)
    ts = np.asarray(raw.timestamps, dtype=float)
    return {
        "n_frames": len(raw.frames),
        "frame_shapes": {"x".join(map(str, k)): v for k, v in sorted(shapes.items())},
        "frame_class": type(raw.frames[0]).__name__,
        "chipset": raw.chipset,
        "backend": raw.backend,
        "bandwidth": raw.bandwidth if isinstance(raw.bandwidth, (int, str)) else _f(raw.bandwidth),
        "timestamps": {
            "n": int(ts.size),
            "first": _f(ts[0]),
            "last": _f(ts[-1]),
            "sum": _f(ts.sum()),
        },
        "csi": _csi_stats(raw.frames),
        "csi_scaled": _csi_stats(scaled.frames),
    }


def snapshot_path(sample_path: str) -> Path:
    return SNAPSHOT_DIR / "readers" / (sample_path.replace("/", "__") + ".json")


def load(sample_path: str):
    path = snapshot_path(sample_path)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save(sample_path: str, summary: dict) -> None:
    path = snapshot_path(sample_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


def diff(expected, actual, path: str = "", *, rtol: float = 1e-6, scale: float = 0.0) -> list:
    """Return human-readable differences between two snapshot structures.

    Floats compare with relative tolerance ``rtol``; ``scale`` provides an
    absolute floor for sums that can cancel towards zero.
    """
    problems = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            sub = f"{path}.{key}" if path else key
            if key not in actual:
                problems.append(f"{sub}: missing")
            elif key not in expected:
                problems.append(f"{sub}: unexpected (value {actual[key]!r})")
            else:
                sub_scale = scale
                if isinstance(expected[key], dict) and "abs_sum" in expected[key]:
                    sub_scale = expected[key]["abs_sum"]
                problems += diff(expected[key], actual[key], sub, rtol=rtol, scale=sub_scale)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            problems.append(f"{path}: length {len(actual)} != expected {len(expected)}")
        else:
            for i, (e, a) in enumerate(zip(expected, actual)):
                problems += diff(e, a, f"{path}[{i}]", rtol=rtol, scale=scale)
    elif isinstance(expected, float) or isinstance(actual, float):
        e, a = float(expected), float(actual)
        both_nan = math.isnan(e) and math.isnan(a)
        if not both_nan and not math.isclose(e, a, rel_tol=rtol, abs_tol=scale * 1e-9):
            problems.append(f"{path}: {a!r} != expected {e!r}")
    elif expected != actual:
        problems.append(f"{path}: {actual!r} != expected {expected!r}")
    return problems
