"""CSIKit.tools.downsample: plots drawn at screen resolution must look the same as full ones."""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from CSIKit.tools.batch_graph import BatchGraph  # noqa: E402
from CSIKit.tools.downsample import DownsampledImage, DownsampledLines, minmax_indices  # noqa: E402


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def noisy(frames=20_000, columns=3, seed=0):
    rng = np.random.default_rng(seed)
    values = rng.normal(30, 3, (frames, columns))
    values[rng.integers(0, frames, 20), 0] = 90  # spikes must survive
    values[rng.integers(0, frames, 50), 1] = -np.inf  # dB of a zero subcarrier
    return np.arange(frames) * 0.01, values


def test_minmax_indices_keep_every_slice_extreme():
    _, values = noisy()
    values = np.where(np.isfinite(values), values, np.nan)
    idx = minmax_indices(values, 0, len(values), 500)
    assert idx.shape[0] <= 2 * 500 + 2 and np.all(np.diff(idx, axis=0) >= 0)
    assert idx[0, 0] == 0 and idx[-1, 0] == len(values) - 1
    kept = np.take_along_axis(values, idx, axis=0)
    np.testing.assert_array_equal(np.nanmax(kept, axis=0), np.nanmax(values, axis=0))
    np.testing.assert_array_equal(np.nanmin(kept, axis=0), np.nanmin(values, axis=0))


def test_short_series_are_not_downsampled():
    values = np.arange(30.0).reshape(10, 3)
    np.testing.assert_array_equal(minmax_indices(values, 0, 10, 100)[:, 1], np.arange(10))


def test_lines_are_downsampled_and_zoom_shows_every_point():
    x, values = noisy()
    fig, ax = plt.subplots()
    lines = DownsampledLines(ax, x, values).lines
    assert len(lines) == 3
    assert len(lines[0].get_xdata()) < len(x) / 5
    assert np.nanmax(lines[0].get_ydata()) == 90  # spikes kept
    full_ylim = ax.get_ylim()

    ax.set_xlim(10, 11)  # 100 frames: drawn in full
    visible = (lines[2].get_xdata() >= 10) & (lines[2].get_xdata() <= 11)
    np.testing.assert_allclose(lines[2].get_xdata()[visible], x[(x >= 10) & (x <= 11)])
    np.testing.assert_allclose(lines[2].get_ydata()[visible], values[(x >= 10) & (x <= 11), 2])
    assert ax.get_ylim() == full_ylim


def test_heatmap_columns_are_averaged_and_zoom_shows_every_frame():
    _, values = noisy(frames=50_000, columns=30)
    image = values.T  # (subcarriers, frames), as the heatmap draws it
    fig, ax = plt.subplots()
    artist = DownsampledImage(ax, image, 500.0, (-0.5, 29.5), aspect="auto", origin="lower").artist
    shown = artist.get_array()
    assert shown.shape[0] == 30 and shown.shape[1] < 50_000 / 10
    finite = np.isfinite(image)
    # Colours span the full-resolution data, not the averages.
    assert artist.norm.vmin == image[finite].min() and artist.norm.vmax == image[finite].max()
    # The first column averages the finite values of the frames it covers.
    frames_per_column = 50_000 / shown.shape[1]
    first = image[:, :int(round(frames_per_column))]
    np.testing.assert_allclose(shown[:, 0], np.nanmean(np.where(np.isfinite(first), first, np.nan), axis=1))
    assert artist.get_extent()[:2] == pytest.approx([0, 500])

    ax.set_xlim(100, 101)  # 100 frames: drawn in full
    left, right, _, _ = artist.get_extent()
    start, stop = int(round(left / 0.01)), int(round(right / 0.01))
    np.testing.assert_array_equal(artist.get_array(), np.ma.masked_invalid(image[:, start:stop]))
    assert start <= 10_000 and stop >= 10_100
    assert ax.get_xlim() == (100, 101)


def test_plot_heatmap_of_a_long_capture_draws_at_screen_resolution(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    _, values = noisy(frames=30_000, columns=56)
    BatchGraph.plot_heatmap(values, list(np.arange(30_000) * 0.01))
    image = plt.gca().get_images()[0]
    assert image.get_array().shape[0] == 56 and image.get_array().shape[1] < 30_000 / 10
    assert image.get_extent()[1] == pytest.approx(299.99)
