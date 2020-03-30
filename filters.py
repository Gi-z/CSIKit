from scipy import signal

import pandas as pd
import numpy as np

#Original implementation.
#Novel, by Chris
#Runs slightly slower than Pandas implementation.
def hampel(csi, k=3, nsigma=1):
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

#Adapted from top answer on Stackoverflow.
#Fastest implementation.
# May be slightly incorrect? Answer below had complaints.
# def hampel(csi, k=3, nsigma=1):
#     csi = pd.Series(csi)

#     #Hampel Filter
#     L= 1.4286
#     rolling_median = csi.rolling(k).median()
#     difference = np.abs(rolling_median - csi)
#     median_abs_deviation = difference.rolling(k).median()
#     threshold = nsigma * L * median_abs_deviation
#     outlier_idx = difference > threshold
#     csi[outlier_idx] = rolling_median[outlier_idx]

#     return csi.to_numpy()

def mad(x, axis=None):
    return np.mean(np.absolute(x - np.mean(x, axis)), axis)

# def hampel(csi, T1, nsigma=1):
#     n = len(csi)
#     new_series = csi.copy()

#     for i in range(T1, n-T1):
#         u = np.median(csi[i:i+T1])
#         m = mad(csi[i:i+T1])
#         intervalUpper = u+nsigma*m
#         intervalLower = u-nsigma*m

#         sect = new_series[i:i+T1]

#         for i in range(len(sect)):
#             x = sect[i]
#             if x > intervalUpper or x < intervalLower:
#                 sect[i] = u

#     return new_series

def get_ev(data, position, window_size, c):
    window = data[position:position+window_size]
    subwindows = np.array_split(window, c)
    return (1/c) * sum([np.var(x) for x in subwindows])

def dynamic_detrend(x, c=5, l=3, alpha=1.2, Fs=20):
    series = x.copy()
    max_size = l*Fs

    window_size, position = 5, 0
    initialEv = get_ev(series, position, max_size, c)
    ev = initialEv

    while position < len(series):
        while ev < alpha*initialEv and window_size < max_size:
            window_size += int(Fs*0.1)
            ev = get_ev(series, position, window_size, c)
        series[position:position+window_size] = signal.detrend(series[position:position+window_size], type="constant")
        position += window_size
        window_size = 5

    return series

def running_stdev(x, N):
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).std().to_numpy()

def running_mean(x, N):
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).mean().to_numpy()