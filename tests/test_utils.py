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
