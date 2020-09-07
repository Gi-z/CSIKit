import numpy as np
import pandas as pd
from scipy import signal


def bandpass(order, low, high, fs, data):
    fshalf = 0.5*fs
    b, a = signal.butter(order, [low/fshalf, high/fshalf], "bandpass")
    return signal.filtfilt(b, a, data)

#Original implementation.
#Runs slightly slower than Pandas implementation.
def hampel(csi, k=3, nsigma=3):
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

# def running_mean(x, N):
#     #This example was taken from stackoverflow, mostly to avoid additional imports.
#     #The previous implementation I was using (via pandas) is commented out below.
#     #https://stackoverflow.com/questions/13728392/moving-average-or-running-mean

#     cumsum = np.cumsum(np.insert(x, 0, 0))
#     return (cumsum[N:] - cumsum[:-N]) / float(N)

def running_mean(x, N):
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).mean().to_numpy()

# def running_stdev(x, N):
#     return pd.Series(x).rolling(window=N, min_periods=1, center=True).std().to_numpy()

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