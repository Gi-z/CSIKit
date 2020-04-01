import math
import numpy as np

def phase_calibration(phasedata):
    calibrated_phase = [phasedata[0]]
    difference = 0
    for i in range(1, 29):
        temp = phasedata[i] - phasedata[i-1]
        if abs(temp) > math.pi:
            difference = difference + 1*np.sign(temp)
        calibrated_phase[i] = phasedata[i] - difference * 2 * math.pi

    k = (calibrated_phase[29] - calibrated_phase[0]) / (30 - 1)
    b = np.mean(calibrated_phase)

    calibrated_phase2 = []

    for i in range(0, 29):
        calibrated_phase2[i] = calibrated_phase[i] - k * i - b
    
    return calibrated_phase2