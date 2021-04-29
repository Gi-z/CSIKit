from CSIKit.util.matlab import db

from typing import Tuple

import numpy as np
import itertools

# This function takes CSIData and returns the assembled CSI matrix from all frames, 
# as well as the number of frames and subcarrier contained therein.
# 
# 1. The first frame's shape is used to establish parameters for the assembled CSI matrix.
#       ? Some kind of assert test or something to check all frames are uniform would be good!
#       - First we get the number of subcarriers.
#       - Then we check the number of dimensions to count the antennas.
# 2. Assemble the empty matrix to contain our extracted CSI.
# 3. Iterate through each frame and extract CSI for each subcarrier at each antenna stream.
# 4. Return complete CSI matrix, number of frames and number of subcarriers.

def get_CSI(csi_data: 'CSIData', metric: str="amplitude", extract_as_dBm: bool=True, squeeze_output: bool=False) -> Tuple[np.array, int, int]:

    #TODO: Add proper error handling.

    #This looks a little ugly.
    frames = csi_data.frames
    csi_shape = frames[0].csi_matrix.shape
    
    no_frames = len(frames)
    no_subcarriers = csi_shape[0]

    #Matrices should be Frames * Subcarriers * Rx * Tx.
    #Single Rx/Tx streams should be squeezed.
    if len(csi_shape) == 3:
        #Intel data comes as Subcarriers * Rx * Tx.
        no_rx_antennas = csi_shape[1]
        no_tx_antennas = csi_shape[2]
    elif len(csi_shape) == 2 or len(csi_shape) == 1:
        #Single antenna stream.
        no_rx_antennas = 1
        no_tx_antennas = 1
    else:
        #Error. Unknown CSI shape.
        print("Error: Unknown CSI shape.")

    csi = np.zeros((no_frames, no_subcarriers, no_rx_antennas, no_tx_antennas), dtype=np.complex)

    ranges = itertools.product(*[range(n) for n in [no_frames, no_subcarriers, no_rx_antennas, no_tx_antennas]])
    is_single_antenna = no_rx_antennas == 1 and no_tx_antennas == 1

    for frame, subcarrier, rx_antenna_index, tx_antenna_index in ranges:
        frame_data = frames[frame].csi_matrix
        subcarrier_data = frame_data[subcarrier]

        csi[frame][subcarrier][rx_antenna_index][tx_antenna_index] = subcarrier_data if is_single_antenna else subcarrier_data[rx_antenna_index][tx_antenna_index]

    if metric == "amplitude":
        csi = abs(csi)
        if extract_as_dBm:
            csi = db(csi)
    elif metric == "phase":
        csi = np.angle(csi)

    if squeeze_output:
        csi = np.squeeze(csi)

    return (csi, no_frames, no_subcarriers)

# def get_CSI(csi_data: 'CSIData', metric: str="amplitude", antenna_stream: int=None, extract_as_dBm: bool=True) -> Tuple[np.array, int, int]:
    
#     #TODO: Clean this up.

#     frames = csi_data.frames

#     csi_shape = frames[0].csi_matrix.shape
#     print("CSI Shape: " + str(csi_shape))

#     no_frames = len(frames)
#     no_subcarriers = csi_shape[0]

#     if len(csi_shape) == 3:
#         if antenna_stream == None:
#             antenna_stream = 0

#     csi = np.zeros((no_subcarriers, no_frames))

#     for x in range(no_frames):
#         entry = frames[x].csi_matrix
#         for y in range(no_subcarriers):
#             if metric == "amplitude":
#                 if antenna_stream is not None:
#                     if extract_as_dBm:
#                         csi[y][x] = db(abs(entry[y][antenna_stream][antenna_stream]))
#                     else:
#                         csi[y][x] = abs(entry[y][antenna_stream][antenna_stream])
#                 else:
#                     if extract_as_dBm:
#                         csi[y][x] = db(abs(entry[y]))
#                     else:
#                         csi[y][x] = abs(entry[y])
#             elif metric == "phasediff":
#                 if entry.shape[1] >= 2:
#                     #Not 100% sure this generates correct Phase Difference.
#                     csi[y][x] = np.angle(entry[y][1][0])-np.angle(entry[y][0][0])
#                 else:
#                     print("Unable to calculate phase difference on single antenna configurations.")
#                     return False
#             elif metric == "phase":
#                 if antenna_stream is not None:
#                     csi[y][x] = np.angle(entry[y][antenna_stream][antenna_stream])
#                 else:
#                     csi[y][x] = np.angle(entry[y])

#     return (csi, no_frames, no_subcarriers)