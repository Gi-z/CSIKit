import numpy as np

def dbinv(x: float) -> float:
    return np.power(10, x/10)

def db(x: float, metric: str="voltage") -> float:
    # Zero magnitudes (e.g. null subcarriers) give -inf; that's expected, so don't warn,
    # but only here rather than changing NumPy's error state for the whole process.
    with np.errstate(divide="ignore"):
        if metric == "voltage":
            return 20 * np.log10(x)
        elif metric == "pow":
            return 10 * np.log10(x)

def get_total_rss(rssi_a: int, rssi_b: int, rssi_c: int, agc: int) -> float:
    """Received signal strength in dBm from IWL5300 per-antenna RSSI and AGC.

    Port of get_total_rss.m from the Linux 802.11n CSI Tool: the antennas' RSSI values
    are combined as power (zeros meaning "no antenna" are ignored), then -44 dB and the
    AGC gain are subtracted.
    """
    rssi_mag = 0
    for rssi in (rssi_a, rssi_b, rssi_c):
        if rssi != 0:
            rssi_mag = rssi_mag + dbinv(rssi)
    return db(rssi_mag, "pow") - 44 - agc

def sqtwolog(x: float) -> float:
    return np.sqrt(2*np.log(len(x)))