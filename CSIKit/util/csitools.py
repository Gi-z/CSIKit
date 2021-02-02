from CSIKit.util.matlab import db

import numpy as np

def get_CSI(csi_data, metric="amplitude", antenna_stream=None):
    
    frames = csi_data.frames

    csi_shape = frames[0].csi_matrix.shape

    no_frames = len(frames)
    no_subcarriers = csi_shape[0]

    if len(csi_shape) == 3:
        if antenna_stream == None:
            antenna_stream = 0

    csi = np.zeros((no_subcarriers, no_frames))

    for x in range(no_frames):
        entry = frames[x].csi_matrix
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
                    print("Unable to calculate phase difference on single antenna configurations.")
                    return False
            elif metric == "phase":
                if antenna_stream is not None:
                    csi[y][x] = np.angle(entry[y][antenna_stream][antenna_stream])
                else:
                    csi[y][x] = np.angle(entry[y])

    return (csi, no_frames, no_subcarriers)