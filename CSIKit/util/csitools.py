from CSIKit.util.matlab import db

from typing import Tuple

import numpy as np

def get_CSI(csi_data: 'CSIData', metric: str="amplitude", antenna_stream: int=None, extract_as_dBm: bool=True) -> Tuple[np.array, int, int]:
    
    #TODO: Clean this up.

    frames = csi_data.frames

    csi_shape = frames[0].csi_matrix.shape
    print("CSI Shape: " + str(csi_shape))

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
                    if extract_as_dBm:
                        csi[y][x] = db(abs(entry[y][antenna_stream][antenna_stream]))
                    else:
                        csi[y][x] = abs(entry[y][antenna_stream][antenna_stream])
                else:
                    if extract_as_dBm:
                        csi[y][x] = db(abs(entry[y]))
                    else:
                        csi[y][x] = abs(entry[y])
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