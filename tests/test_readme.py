"""Run the README's preprocessing example, so it can't silently drift from the library."""
import re

import numpy as np
import pytest

from csikit_testing import REPO_ROOT, repo_path

SAMPLE = "CSIKit/data/pico/picoscenes_ax200_example.csi"  # ~179 Hz; 778 56-tone + 107 52-tone frames


def readme_example():
    readme = (REPO_ROOT / "README.md").read_text()
    section = readme[readme.index("## Using CSI Matrices"):]
    blocks = re.findall(r"```python\n(.*?)```", section, flags=re.S)
    example = next(b for b in blocks if "plot_heatmap" in b)
    return example.replace("/path/to/csi/file", str(repo_path(SAMPLE)))


@pytest.fixture
def namespace(monkeypatch):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    ns = {}
    with pytest.warns(UserWarning, match="different CSI shapes"):  # the mixed 52/56-tone frames
        exec(compile(readme_example(), "README.md", "exec"), ns)
    yield ns
    plt.close("all")


def test_readme_example_filters_each_subcarrier_over_time(namespace):
    from CSIKit.filters.passband import lowpass
    from CSIKit.filters.statistical import running_mean
    from CSIKit.util import csitools
    from CSIKit.util.filters import hampel

    with pytest.warns(UserWarning):
        csi, _, _, kept = csitools.get_CSI(namespace["csi_data"], metric="amplitude", return_indices=True)
    expected = csi[:, :, 0, 0].copy()  # (frames, subcarriers)
    fs = namespace["sample_rate"]
    for s in range(expected.shape[1]):
        expected[:, s] = running_mean(hampel(lowpass(expected[:, s], 10, fs, 5), 10, 3), 10)

    assert namespace["csi_matrix_first"].shape == (778, 56)
    np.testing.assert_allclose(namespace["csi_matrix_first"], expected)
    # Timestamps line up with the frames get_CSI used, not with every frame in the file.
    assert namespace["timestamps"] == [namespace["csi_data"].timestamps[i] for i in kept]
    assert len(namespace["timestamps"]) == 778 < len(namespace["csi_data"].frames)
    assert fs > 20
