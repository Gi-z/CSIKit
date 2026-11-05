"""CSIKit.util: byte operations, MATLAB-equivalent helpers and string helpers."""
import subprocess
import sys

import numpy as np
import pytest

from CSIKit.util import byteops, matlab, stringops
from csikit_testing import REPO_ROOT


@pytest.mark.parametrize(
    "value, bits, expected",
    [(0, 10, 0), (0x1FF, 10, 511), (0x200, 10, -512), (0x3FF, 10, -1), (0x7F, 8, 127), (0x80, 8, -128)],
)
def test_signbit_convert(value, bits, expected):
    assert byteops.signbit_convert(value, bits) == expected


def test_get_next_bits_appends_a_little_endian_word():
    data, idx, bits_left = byteops.get_next_bits(b"\x34\x12\xff", 0b101, 0, 3)
    assert (data, idx, bits_left) == (0b101 | (0x1234 << 3), 2, 19)


def test_db_of_zero_is_minus_infinity_without_a_warning(recwarn):
    assert matlab.db(0.0) == -np.inf and matlab.db(np.zeros(3), "pow").tolist() == [-np.inf] * 3
    assert not [w for w in recwarn if issubclass(w.category, RuntimeWarning)]


@pytest.mark.parametrize("x", [1e-3, 0.5, 1.0, 42.0])
def test_db_and_dbinv_are_inverse(x):
    assert matlab.dbinv(matlab.db(x, "pow")) == pytest.approx(x)
    assert matlab.db(x) == pytest.approx(2 * matlab.db(x, "pow"))  # voltage = 20 log10


def test_hex_to_mac_string():
    assert stringops.hexToMACString("a1b2c3d4e5f6") == "A1:B2:C3:D4:E5:F6"


def test_import_does_not_change_numpy_error_state():
    code = (
        "import numpy as np; before = np.geterr(); "
        "import CSIKit.reader, CSIKit.util.csitools; "
        "assert np.geterr() == before, (before, np.geterr())"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("fmt, nman, nexp", [(0, 9, 5), (1, 12, 6)], ids=["bcm4358", "bcm4366c0"])
@pytest.mark.parametrize("seed", range(5))
def test_unpack_float_acphy_matches_reference_loop(fmt, nman, nexp, seed):
    # The vectorised unpacker must equal the direct port of nexmon's unpack_float.c on any input.
    rng = np.random.default_rng(seed)
    words = rng.integers(0, 2**32, size=256, dtype=np.uint64).astype(np.uint32)
    words[rng.integers(0, 256, 20)] = 0  # zero words exercise the no-autoscale path
    args = (10, 1, 0, 1, nman, nexp, 256, words)
    np.testing.assert_array_equal(byteops.unpack_float_acphy(*args), byteops._unpack_float_acphy_loop(*args))


@pytest.mark.parametrize("n_rx, n_tx", [(1, 1), (2, 1), (3, 1), (3, 2), (3, 3)])
@pytest.mark.parametrize("seed", range(3))
def test_unpack_iwl5300_csi_matches_reference_loop(n_rx, n_tx, seed):
    rng = np.random.default_rng(seed)
    payload = rng.integers(0, 256, size=(30 * (n_rx * n_tx * 16 + 3) + 7) // 8 + 1, dtype=np.uint8).tobytes()
    for perm in ([0, 1, 2], [2, 0, 1], [1, 2, 0]):
        if n_rx < 3 and perm != [0, 1, 2]:
            continue
        np.testing.assert_array_equal(byteops.unpack_iwl5300_csi(payload, n_rx, n_tx, perm),
                                      byteops._unpack_iwl5300_csi_loop(payload, n_rx, n_tx, perm))
    # A truncated payload falls back to the loop's partial decode.
    short = payload[:len(payload) // 2]
    np.testing.assert_array_equal(byteops.unpack_iwl5300_csi(short, n_rx, n_tx, [0, 1, 2]),
                                  byteops._unpack_iwl5300_csi_loop(short, n_rx, n_tx, [0, 1, 2]))


def test_unpack_float_acphy_batches_records_independently():
    # Each record is autoscaled on its own, so a batch must equal record-by-record decoding.
    rng = np.random.default_rng(42)
    words = rng.integers(0, 2**32, size=(6, 256), dtype=np.uint64).astype(np.uint32)
    words[2] = 0  # an all-zero record
    words[4, :200] = 0
    batch = byteops.unpack_float_acphy(10, 1, 0, 1, 12, 6, 256, words)
    assert batch.shape == (6, 512)
    for row, record in zip(batch, words):
        np.testing.assert_array_equal(row, byteops._unpack_float_acphy_loop(10, 1, 0, 1, 12, 6, 256, record))
