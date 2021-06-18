from CSIKit.util.matlab import sqtwolog

import numpy as np
import pywt

def get_var(cD):
    sig = [abs(s) for s in cD[-1]]
    return np.median(sig)/0.6745

def denoise(csi_matrix, level=None):
    denoised_csi = np.zeros(csi_matrix.shape)
    frame_count, subcarrier_count = denoised_csi.shape[:2]

    if level is None:
        level = pywt.dwt_max_level(frame_count, "sym3")

    for subcarrier_index in range(subcarrier_count):
        subcarrier_signal = csi_matrix[:, subcarrier_index]

        coefficients = pywt.wavedec(subcarrier_signal, "sym3", level=level)
        coefficients_sln = [coefficients[0]]

        # Adapted from https://github.com/matthewddavis/lombardi/blob/master/processing/NPS-1.3.2/WDen.py
        # Implementing sln scaling.
        rescaling = get_var(coefficients)

        for l in range(level):
            threshold = sqtwolog(coefficients[l+1]/rescaling)
            threshold *= rescaling

            # Equivalent to wthresh with the "s"=soft setting.
            coefficients_sln.append(pywt.threshold(coefficients[l+1], threshold, mode="soft"))

        reconstructed_signal = pywt.waverec(coefficients_sln, "sym3")
        if len(reconstructed_signal) == frame_count:
            denoised_csi[:, subcarrier_index] = reconstructed_signal
        else:
            denoised_csi[:, subcarrier_index] = reconstructed_signal[:-1]


    return denoised_csi
