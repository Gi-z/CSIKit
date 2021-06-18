from scipy import signal

import numpy as np

def lowpass(csi_vec: np.array, cutoff: float, fs: float, order: int) -> np.array:
    nyq = 0.5*fs
    normal_cutoff = cutoff/nyq
    b, a = signal.butter(order, normal_cutoff, btype="low", analog=False)
    return signal.filtfilt(b, a, csi_vec)

def highpass(csi_vec: np.array, cutoff: float, fs: float, order: int) -> np.array:
    nyq = 0.5*fs
    normal_cutoff = cutoff/nyq
    b, a = signal.butter(order, normal_cutoff, btype="high", analog=False)
    return signal.filtfilt(b, a, csi_vec)

def bandpass(csi_vec: np.array, low_cut: float, high_cut: float, fs: float, order: int) -> np.array:
    nyq = 0.5*fs
    b, a = signal.butter(order, [low_cut/nyq, high_cut/nyq], btype="band", analog=False)
    return signal.filtfilt(b, a, csi_vec)