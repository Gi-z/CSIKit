import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from scipy import signal

def lowpass(csi_vec: np.array, cutoff: float, fs: float, order: int) -> np.array:
    nyq = 0.5*fs
    normal_cutoff = cutoff/nyq
    b, a = signal.butter(order, normal_cutoff, btype="low", analog=False)
    return signal.filtfilt(b, a, csi_vec)

def bandpass(csi_vec: np.array, low_cut: float, high_cut: float, fs: float, order: int) -> np.array:
    nyq = 0.5*fs
    b, a = signal.butter(order, [low_cut/nyq, high_cut/nyq], btype="band", analog=False)
    return signal.filtfilt(b, a, csi_vec)

def hampel(csi: np.array, k: int=3, nsigma: int=3) -> np.array:
    """Replace samples further than nsigma standard deviations from the median of their window.

    Gives exactly the same output as the original implementation (_hampel_loop below,
    from whyrlpool), including its window choice and the way replacements feed into later
    windows, but long 1-D series are handled with array operations. Other input goes
    through the original loop.
    """
    values = np.asarray(csi)
    if (values.ndim != 1 or k < 1 or len(values) < 4 * k
            or not np.issubdtype(values.dtype, np.number) or np.iscomplexobj(values)):
        return _hampel_loop(csi, k, nsigma)
    return _hampel_fast(values, k, nsigma)


def _hampel_fast(values: np.ndarray, k: int, nsigma: float) -> np.ndarray:
    n, width = len(values), 2 * k
    position = np.arange(n)
    # Start of each sample's 2k-sample window, as _hampel_loop chooses it: looking forward
    # for the first k+1 samples, the 2k samples before it near the end, centred otherwise.
    starts = np.where(position <= k, position, np.where(position + k > n, position - width, position - k))
    out = values.copy()

    def possible_outliers(first, last):
        # Vectorised screen of positions first..last against `out` as it is now. The threshold is
        # lowered slightly so rounding can't hide a real outlier; exact() makes the decision.
        window_starts = starts[first:last + 1]
        lo = window_starts.min()
        span = out[lo:window_starts.max() + width].astype(np.float64)
        windows = sliding_window_view(span, width)[window_starts - lo]
        with np.errstate(invalid="ignore"):
            deviation = np.abs(out[first:last + 1].astype(np.float64) - np.median(windows, axis=1))
            return first + np.flatnonzero(deviation > nsigma * np.std(windows, axis=1) * (1 - 1e-7))

    def exact(i):
        # The original loop's test for sample i, on the same window and values.
        window = out[starts[i]:starts[i] + width]
        stdev = np.std(window)
        median = np.median(window)
        if abs(out[i] - median) > nsigma * stdev:
            out[i] = median
            return True
        return False

    candidates = possible_outliers(0, n - 1)
    # Samples up to here may have a replaced sample in their window: a window starts at most 2k
    # samples before its sample, and replacements happen in order.
    recheck_until = -1
    i = 0
    while i < n:
        if i > recheck_until:
            # No replaced samples in any window from here on, so only the screened candidates can change.
            next_candidate = np.searchsorted(candidates, i)
            if next_candidate == len(candidates):
                break
            i = int(candidates[next_candidate])
            if exact(i):
                recheck_until = i + width
            i += 1
        else:
            last = min(recheck_until, n - 1)
            replaced = next((j for j in possible_outliers(i, last) if exact(j)), None)
            if replaced is None:
                i = last + 1
            else:
                recheck_until = int(replaced) + width
                i = int(replaced) + 1

    return out


# Original implementation from whyrlpool. Kept as the reference for hampel() and for input it
# doesn't vectorise.
def _hampel_loop(csi: np.array, k: int=3, nsigma: int=3) -> np.array:
    index = 0
    csi = csi.copy()
    for x in csi:
        y = 0
        if index <= k:
            #Special case, first few samples.
            y = k
        elif index+k > len(csi):
            #Special case, last few samples
            y = -k

        index += y
        stdev = np.std(csi[index-k:index+k])
        median = np.median(csi[index-k:index+k])
        index -= y

        if abs(x-median) > nsigma * stdev:
            csi[index] = median
        index += 1

    return csi

def running_mean(x: np.array, N: int) -> np.array:
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).mean().to_numpy()

def running_stdev(x: np.array, N: int) -> np.array:
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).std().to_numpy()

def running_variance(x: np.array, N: int) -> np.array:
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).var().to_numpy()

# def mad(x, axis=None):
#     return np.mean(np.absolute(x - np.mean(x, axis)), axis)

# def get_ev(data, position, window_size, c):
#     window = data[position:position+window_size]
#     subwindows = np.array_split(window, c)
#     return (1/c) * sum([np.var(x) for x in subwindows])

# def dynamic_detrend(x, c=5, l=3, alpha=1.2, Fs=20):
#     series = x.copy()
#     max_size = l*Fs

#     window_size, position = 5, 0
#     initialEv = get_ev(series, position, max_size, c)
#     ev = initialEv

#     while position < len(series):
#         while ev < alpha*initialEv and window_size < max_size:
#             window_size += int(Fs*0.1)
#             ev = get_ev(series, position, window_size, c)
#         series[position:position+window_size] = signal.detrend(series[position:position+window_size], type="constant")
#         position += window_size
#         window_size = 5

#     return series