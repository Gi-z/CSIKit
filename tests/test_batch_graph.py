"""CSIKit.tools.batch_graph: what the csikit --graph plots actually contain.

These check the plotted data, not just that plotting doesn't crash: that each
line is one subcarrier over time, and that the heatmap image is laid out
(subcarriers, frames).
"""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from CSIKit.tools.batch_graph import BatchGraph  # noqa: E402
from CSIKit.util.csitools import get_CSI  # noqa: E402
from csikit_testing import repo_path  # noqa: E402
from csikit_testing.known_issues import HEATMAP_SUBCARRIER_AXIS_FLIPPED, known_bug  # noqa: E402

INTEL = "CSIKit/data/intel/example.dat"  # 26 frames, 30 subcarriers, 3x2, ~2 s
CONSTANT_TIME = "CSIKit/data/intel/log.all_csi.6.7.6.dat"  # every timestamp_low is identical


@pytest.fixture(autouse=True)
def no_show(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    yield
    plt.close("all")


def graph(path=INTEL):
    return BatchGraph(str(repo_path(path)))


def first_pair_amplitude(g):
    csi, _, _, kept = get_CSI(g.csi_data, return_indices=True)
    timestamps = np.array([g.csi_data.timestamps[i] for i in kept])
    return csi[:, :, 0, 0], timestamps - timestamps[0]


def test_all_subcarriers_plots_each_subcarrier_over_time():
    g = graph()
    g.plotAllSubcarriers()
    amplitude, t = first_pair_amplitude(g)
    lines = plt.gca().get_lines()
    assert len(lines) == amplitude.shape[1] == 30
    for subcarrier, line in enumerate(lines):
        np.testing.assert_allclose(line.get_xdata(), t)
        np.testing.assert_allclose(line.get_ydata(), amplitude[:, subcarrier])
    assert plt.gca().get_xlabel() == "Time (s)"


def test_subcarrier_filter_plots_one_subcarrier_over_time():
    g = graph()
    g.prepostfilter()
    amplitude, t = first_pair_amplitude(g)
    raw, hampel_line, smoothed = plt.gca().get_lines()
    np.testing.assert_allclose(raw.get_xdata(), t)
    np.testing.assert_allclose(raw.get_ydata(), amplitude[:, 15])
    assert len(hampel_line.get_ydata()) == len(smoothed.get_ydata()) == len(t) == 26


def test_frame_numbers_are_used_when_timestamps_are_constant():
    g = graph(CONSTANT_TIME)
    g.plotAllSubcarriers()
    line = plt.gca().get_lines()[0]
    np.testing.assert_array_equal(line.get_xdata(), np.arange(len(g.csi_data.frames)))
    assert plt.gca().get_xlabel() == "Frame No."


def test_heatmap_image_is_subcarriers_by_frames():
    g = graph()
    g.heatmap()
    amplitude, t = first_pair_amplitude(g)
    image = plt.gca().get_images()[0]
    np.testing.assert_allclose(image.get_array(), amplitude.T)
    left, right, _, _ = image.get_extent()
    assert (left, right) == pytest.approx((0, t[-1]))


@known_bug(HEATMAP_SUBCARRIER_AXIS_FLIPPED)
def test_heatmap_draws_subcarrier_0_at_the_low_end_of_the_axis():
    amplitude = np.zeros((100, 30))
    amplitude[:, 0] = 10.0  # only subcarrier 0 is bright
    BatchGraph.plot_heatmap(amplitude, list(np.arange(100) * 0.01))
    image = plt.gca().get_images()[0]
    _, _, bottom, top = image.get_extent()
    row_height = (top - bottom) / image.get_array().shape[0]
    y_of_row_0 = top - row_height / 2 if image.origin == "upper" else bottom + row_height / 2
    assert y_of_row_0 < (bottom + top) / 2, f"subcarrier 0 is drawn at y={y_of_row_0:.1f} of {bottom}..{top}"
