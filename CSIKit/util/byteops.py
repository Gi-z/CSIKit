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
        vi = ((H[i] >> (nexp + nman)) & iq_mask)
        vq = ((H[i] >> nexp) & iq_mask)
        e = (H[i] & e_mask)

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

        if H[i] & sgnr_mask:
            vi |= k_tof_unpack_sgn_mask

        if H[i] & sgni_mask:
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