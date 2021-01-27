from .matlab import db, dbinv

import numpy as np

def get_CSI(trace, metric="amplitude", antenna_stream=None, scaled=True):
    
    # csi_key = "scaled_csi" if "scaled_csi" in trace[0] else "csi"
    # csi_key = "csi_matrix"
    csi_shape = trace[0].csi_matrix.shape

    no_frames = len(trace)
    no_subcarriers = csi_shape[0]

    if len(csi_shape) == 3:
        if antenna_stream == None:
            antenna_stream = 0

    csi = np.zeros((no_subcarriers, no_frames))

    for x in range(no_frames):
        entry = trace[x].csi_matrix
        for y in range(no_subcarriers):
            if metric == "amplitude":
                if antenna_stream is not None:
                    csi[y][x] = db(abs(entry[y][antenna_stream][antenna_stream]))
                else:
                    csi[y][x] = db(abs(entry[y]))
            elif metric == "phasediff":
                if entry.shape[1] >= 2:
                    #Not 100% sure this generates correct Phase Difference.
                    csi[y][x] = np.angle(entry[y][1][0])-np.angle(entry[y][0][0])
                else:
                    #Unable to calculate phase difference on single antenna configurations.
                    return False

    return (csi, no_frames, no_subcarriers)

def get_timestamps(trace, relative=True):
    key = "timestamp" if relative else "timestamp_low"
    return list([x[key] for x in trace])