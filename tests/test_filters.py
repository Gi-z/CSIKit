"""CSIKit.filters (and the duplicate implementations in CSIKit.util.filters)."""
import numpy as np
import pytest

from CSIKit.filters import passband, statistical
from CSIKit.filters.wavelets import dwt
from CSIKit.util import filters as util_filters

FS = 100.0
T = np.arange(0, 10, 1 / FS)
LOW = np.sin(2 * np.pi * 2 * T)    # 2 Hz
HIGH = np.sin(2 * np.pi * 30 * T)  # 30 Hz
INTERIOR = slice(100, -100)        # ignore filtfilt edge effects


def test_lowpass_keeps_low_band():
    out = passband.lowpass(LOW + HIGH, 10, FS, 5)
    np.testing.assert_allclose(out[INTERIOR], LOW[INTERIOR], atol=0.02)


def test_highpass_keeps_high_band():
    out = passband.highpass(LOW + HIGH, 10, FS, 5)
    np.testing.assert_allclose(out[INTERIOR], HIGH[INTERIOR], atol=0.02)


def test_bandpass_isolates_band():
    out = passband.bandpass(LOW + HIGH, 20, 40, FS, 4)
    np.testing.assert_allclose(out[INTERIOR], HIGH[INTERIOR], atol=0.05)


def test_running_statistics():
    x = np.array([1.0, 2, 3, 4, 5])
    np.testing.assert_allclose(statistical.running_mean(x, 3), [1.5, 2, 3, 4, 4.5])
    np.testing.assert_allclose(statistical.running_variance(x, 3)[1:-1], [1, 1, 1])
    np.testing.assert_allclose(statistical.running_stdev(x, 3) ** 2, statistical.running_variance(x, 3))


def test_hampel_replaces_isolated_outlier():
    x = np.ones(100)
    x[50] = 10
    out = util_filters.hampel(x, 5, 3)
    assert out[50] == 1
    np.testing.assert_array_equal(np.delete(out, 50), np.ones(99))
    assert x[50] == 10, "input must not be modified"


@pytest.mark.parametrize("seed", range(6))
def test_hampel_matches_original_loop(seed):
    # hampel() screens long series with array operations; its output must equal the original
    # per-sample loop's exactly, including how replacements feed into later windows.
    rng = np.random.default_rng(seed)
    for _ in range(40):
        n = int(rng.integers(4, 300))
        k = int(rng.integers(1, max(2, n // 4 + 1)))
        if seed % 3 == 0:
            x = rng.integers(-5, 5, n)  # integers, with ties
        else:
            x = rng.normal(0, 1, n)
            if seed % 3 == 2:
                x = np.round(2 * x)
                x[rng.random(n) < 0.02] = -np.inf  # dB of a zero subcarrier
        x[rng.random(n) < 0.05] += 40
        for nsigma in (1, 3):
            expected = util_filters._hampel_loop(x, k, nsigma)
            actual = util_filters.hampel(x, k, nsigma)
            assert actual.dtype == expected.dtype
            np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize(
    "name, args",
    [
        ("lowpass", (LOW + HIGH, 10, FS, 5)),
        ("bandpass", (LOW + HIGH, 20, 40, FS, 4)),
        ("running_mean", (LOW, 7)),
        ("running_stdev", (LOW, 7)),
        ("running_variance", (LOW, 7)),
    ],
)
def test_util_filters_duplicates_match(name, args):
    canonical = getattr(passband, name, None) or getattr(statistical, name)
    np.testing.assert_allclose(getattr(util_filters, name)(*args), canonical(*args))


def test_wavelet_denoise_reduces_noise():
    rng = np.random.default_rng(0)
    clean = np.stack([np.sin(2 * np.pi * 0.5 * T + k) for k in range(8)], axis=1)  # (frames, subcarriers)
    noisy = clean + rng.normal(scale=0.3, size=clean.shape)
    out = dwt.denoise(noisy)
    assert out.shape == noisy.shape
    assert np.mean((out - clean) ** 2) < 0.5 * np.mean((noisy - clean) ** 2)
