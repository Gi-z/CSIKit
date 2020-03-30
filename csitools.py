from matlab import db

import numpy as np

def getCSI(trace, metric="amplitude"):
    no_frames = len(trace)
    no_subcarriers = trace[0]["csi"].shape[0]

    csi = np.zeros((no_subcarriers, no_frames))

    for x in range(no_frames):
        scaled_entry = trace[x]["csi"]
        for y in range(no_subcarriers):
            if metric == "amplitude":
                csi[y][x] = db(abs(scaled_entry[y]))
                # csi[y][x] = abs(scaled_entry[y])
            elif metric == "phasediff":
                if scaled_entry.shape[1] >= 2:
                    #Not 100% sure this generates correct Phase Difference.
                    csi[y][x] = np.angle(scaled_entry[y][1][0])-np.angle(scaled_entry[y][0][0])
                else:
                    #In cases where only one antenna is available,
                    #reuse the previous value.
                    csi[y][x] = csi[y][x-1]

    return (csi, no_frames, no_subcarriers)

def getTimestamps(trace, relative=True):
    key = "scaled_timestamp" if relative else "timestamp"
    return list([x[key] for x in trace])