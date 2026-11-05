import functools
from typing import Tuple

import numpy as np

def signbit_convert(data: int, maxbit: int) -> int:
    if (data & (1 << (maxbit - 1))):
        data -= (1 << maxbit)

    return data

def get_next_bits(buf: bytes, current_data: int, idx: int, bits_left: int) -> Tuple[int, int, int]:
    h_data = buf[idx]
    h_data += (buf[idx+1] << 8)

    current_data += h_data << bits_left

    idx += 2
    bits_left += 16

    return current_data, idx, bits_left

def unpack_float_acphy(nbits: int, autoscale: int, shft: int, fmt: int, nman: int, nexp: int, nfft: int,
                       H: np.array) -> np.array:
    """Unpack Broadcom ACPHY floating-point CSI words (BCM4358, BCM4366c0) into interleaved ints.

    Vectorised port of nexmon_csi's unpack_float.c: each 32-bit word holds a sign bit and
    an `nman`-bit mantissa for the real and the imaginary part plus a shared `nexp`-bit signed
    exponent. Returns int64 [re0, im0, re1, im1, ...] (2 * nfft values), scaled so the largest
    magnitude uses `nbits` bits when `autoscale` is set. `shft` and `fmt` are unused, as in
    the original.

    `H` may also be a 2-D (records, words) array: every record is unpacked (and autoscaled)
    independently in one call, returning (records, 2 * nfft).
    """
    given = np.asarray(H, dtype=np.int64)
    single = given.ndim == 1
    given = np.atleast_2d(given)[:, :nfft]
    words = np.zeros((given.shape[0], nfft), dtype=np.int64)
    words[:, :given.shape[1]] = given

    iq_mask = (1 << (nman - 1)) - 1
    e_mask = (1 << nexp) - 1
    e_p = (1 << (nexp - 1))
    sgnr_mask = (1 << (nexp + 2 * nman - 1))
    sgni_mask = (sgnr_mask >> nman)
    e_zero = -nman

    vi = (words >> (nexp + nman)) & iq_mask
    vq = (words >> nexp) & iq_mask
    e = words & e_mask
    e = np.where(e >= e_p, e - (e_p << 1), e)  # signed exponent

    maxbit = np.full(words.shape[0], -e_p, dtype=np.int64)
    if autoscale:
        x = vi | vq
        # floor(log2(x)) exactly, as the original's binary search for the top set bit
        top_bit = np.frexp(x.astype(np.float64))[1] - 1
        maxbit = np.maximum(maxbit, np.where(x != 0, e + top_bit, -e_p).max(axis=1))

    shift = np.repeat(e, 2, axis=1) + (nbits - maxbit)[:, None]
    magnitude = np.stack([vi, vq], axis=2).reshape(words.shape[0], -1)
    negative = np.stack([(words & sgnr_mask) != 0, (words & sgni_mask) != 0], axis=2).reshape(words.shape[0], -1)

    out = np.where(shift < 0, magnitude >> np.clip(-shift, 0, 63), magnitude << np.clip(shift, 0, 63))
    out = np.where(shift < e_zero, 0, out)
    out = np.where(negative, -out, out).astype(np.int64)
    return out[0] if single else out


def _unpack_float_acphy_loop(nbits: int, autoscale: int, shft: int, fmt: int, nman: int, nexp: int, nfft: int,
                             H: np.array) -> np.array:
    # Element-by-element reference implementation (a direct port of unpack_float.c), kept for tests.
    k_tof_unpack_sgn_mask = (1 << 31)

    He = [0] * nfft
    Hout = [0] * nfft*2

    iq_mask = (1 << (nman - 1)) - 1
    e_mask = (1 << nexp) - 1
    e_p = (1 << (nexp - 1))
    sgnr_mask = (1 << (nexp + 2 * nman - 1))
    sgni_mask = (sgnr_mask >> nman)
    e_zero = -nman

    out = np.zeros((nfft * 2), dtype=np.int64)
    n_out = (nfft << 1)
    e_shift = 1
    maxbit = -e_p

    for i in range(len(H)):
        h = int(H[i])
        vi = ((h >> (nexp + nman)) & iq_mask)
        vq = ((h >> nexp) & iq_mask)
        e = (h & e_mask)

        if e >= e_p:
            e -= (e_p << 1)

        He[i] = e

        x = vi | vq

        if autoscale and x:
            m = 0xffff0000
            b = 0xffff
            s = 16

            while s > 0:
                if x & m:
                    e += s
                    x >>= s

                s >>= 1
                m = (m >> s) & b
                b >>= s

            if e > maxbit:
                maxbit = e

        if h & sgnr_mask:
            vi |= k_tof_unpack_sgn_mask

        if h & sgni_mask:
            vq |= k_tof_unpack_sgn_mask

        Hout[i << 1] = vi
        Hout[(i << 1) + 1] = vq

    shft = nbits - maxbit
    for i in range(n_out):
        e = He[(i >> e_shift)] + shft
        vi = Hout[i]

        sgn = 1

        if vi & k_tof_unpack_sgn_mask:
            sgn = -1

            vi &= ~k_tof_unpack_sgn_mask

        if e < e_zero:
            vi = 0
        elif e < 0:
            e = -e
            vi = (vi >> e)
        else:
            vi = (vi << e)

        out[i] = sgn * vi

    return out


IWL5300_SUBCARRIERS = 30


def unpack_iwl5300_csi(payload, n_rx: int, n_tx: int, perm) -> np.ndarray:
    """Decode an IWL5300 beamforming-feedback payload into a (30, n_rx, n_tx) complex64 matrix.

    As in read_bfee.c from the Linux 802.11n CSI Tool: each of the 30 subcarriers starts with 3
    padding bits, followed by n_rx * n_tx entries of a signed 8-bit real and imaginary part,
    bit-packed LSB-first with no byte alignment. Rx row j is stored at row perm[j].

    Vectorised: every entry's bit offset is computed up front and all entries are decoded with
    array operations. Truncated payloads and repeated permutation entries take the original
    loop, which decodes what it can and leaves the rest zero.
    """
    buf = np.frombuffer(payload if isinstance(payload, (bytes, bytearray)) else bytes(payload), dtype=np.uint8)
    rows = list(perm[:n_rx])
    ind8, rem, needed = _iwl5300_layout(n_rx, n_tx)
    if not needed or needed > len(buf) or len(set(rows)) != n_rx:
        return _unpack_iwl5300_csi_loop(bytes(buf), n_rx, n_tx, perm)

    b = buf.astype(np.uint16)
    real = (((b[ind8] >> rem) | (b[ind8 + 1] << (8 - rem))) & 0xFF).astype(np.uint8).view(np.int8)
    imag = (((b[ind8 + 1] >> rem) | (b[ind8 + 2] << (8 - rem))) & 0xFF).astype(np.uint8).view(np.int8)

    csi = np.zeros((IWL5300_SUBCARRIERS, n_rx, n_tx), dtype=np.complex64)
    csi[:, rows, :] = (real.astype(np.float32) + 1j * imag.astype(np.float32)).reshape(IWL5300_SUBCARRIERS, n_rx, n_tx)
    return csi


@functools.lru_cache(maxsize=None)
def _iwl5300_layout(n_rx: int, n_tx: int):
    """Byte index and bit shift of every entry for an antenna layout, plus the payload bytes it needs."""
    n = n_rx * n_tx
    if n == 0:
        return None, None, 0
    sub = np.arange(IWL5300_SUBCARRIERS)[:, None]
    bit = 3 * (sub + 1) + 16 * (n * sub + np.arange(n)[None, :])  # (30, n) bit offset of each entry
    ind8 = bit >> 3
    return ind8, (bit & 7).astype(np.uint16), int(ind8.max()) + 3


def _unpack_iwl5300_csi_loop(data: bytes, n_rx: int, n_tx: int, perm) -> np.ndarray:
    # Element-by-element reference decoder; stops a row early when the payload runs out.
    csi = np.zeros((IWL5300_SUBCARRIERS, n_rx, n_tx), dtype=np.complex64)
    index = 0
    for i in range(IWL5300_SUBCARRIERS):
        index += 3
        remainder = index % 8
        for j in range(n_rx):
            for k in range(n_tx):
                ind8 = index // 8
                if ind8 + 2 >= len(data):
                    break
                real = ((data[ind8] >> remainder) | (data[1 + ind8] << (8 - remainder))) & 0xFF
                imag = ((data[1 + ind8] >> remainder) | (data[2 + ind8] << (8 - remainder))) & 0xFF
                if real > 127:
                    real -= 256
                if imag > 127:
                    imag -= 256
                csi[i][perm[j]][k] = complex(real, imag)
                index += 16
    return csi


def unpack_int16_csi(data, pos: int, n_tones: int, n_rx: int, n_tx: int) -> np.ndarray:
    """(n_tones, n_rx, n_tx) complex128 CSI from little-endian int16 (real, imag) pairs.

    The layout used by Intel's iwlwifi CSI dumps (PicoScenes AX200/AX210, FeitCSI): Rx outermost,
    then Tx, then tone.
    """
    count = 2 * n_tones * n_rx * n_tx
    pairs = np.frombuffer(data, dtype="<i2", count=count, offset=pos).astype(np.float64).reshape(n_rx, n_tx, n_tones, 2)
    return np.ascontiguousarray((pairs[..., 0] + 1j * pairs[..., 1]).transpose(2, 0, 1))
