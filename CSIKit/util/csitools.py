from CSIKit.util.matlab import db, dbinv

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

def get_CSI(csi_data: 'CSIData', metric: str = "amplitude", extract_as_dBm: bool = True,
            squeeze_output: bool = False) -> Tuple[np.array, int, int]:
    # TODO: Add proper error handling.

    # This looks a little ugly.
    frames = csi_data.frames
    csi_shape = frames[0].csi_matrix.shape

    no_frames = len(frames)
    no_subcarriers = csi_shape[0]

    # Matrices should be Frames * Subcarriers * Rx * Tx.
    # Single Rx/Tx streams should be squeezed.
    if len(csi_shape) == 3:
        # Intel data comes as Subcarriers * Rx * Tx.
        no_rx_antennas = csi_shape[1]
        no_tx_antennas = csi_shape[2]
    elif len(csi_shape) == 2 or len(csi_shape) == 1:
        # Single antenna stream.
        no_rx_antennas = 1
        no_tx_antennas = 1
    else:
        # Error. Unknown CSI shape.
        print("Error: Unknown CSI shape.")

    csi = np.zeros((no_frames, no_subcarriers, no_rx_antennas, no_tx_antennas), dtype=complex)

    ranges = itertools.product(*[range(n) for n in [no_frames, no_subcarriers, no_rx_antennas, no_tx_antennas]])
    is_single_antenna = no_rx_antennas == 1 and no_tx_antennas == 1

    drop_indices = []

    for frame, subcarrier, rx_antenna_index, tx_antenna_index in ranges:
        frame_data = frames[frame].csi_matrix
        if subcarrier >= frame_data.shape[0]:
            # Inhomogenous component
            # Skip frame for now. Need a better method soon.
            continue

        subcarrier_data = frame_data[subcarrier]
        if subcarrier_data.shape != (no_rx_antennas, no_tx_antennas) and not is_single_antenna:
            if rx_antenna_index >= subcarrier_data.shape[0] or tx_antenna_index >= subcarrier_data.shape[1]:
                # Inhomogenous component
                # Skip frame for now. Need a better method soon.
                drop_indices.append(frame)
                continue

        csi[frame][subcarrier][rx_antenna_index][tx_antenna_index] = subcarrier_data if is_single_antenna else \
            subcarrier_data[rx_antenna_index][tx_antenna_index]

    csi = np.delete(csi, drop_indices, 0)
    csi_data.timestamps = [x for i, x in enumerate(csi_data.timestamps) if i not in drop_indices]

    if metric == "amplitude":
        csi = abs(csi)
        if extract_as_dBm:
            csi = db(csi)
    elif metric == "phase":
        csi = np.angle(csi)

    if squeeze_output:
        csi = np.squeeze(csi)

    return (csi, no_frames, no_subcarriers)


def scale_csi_frame(csi: np.array, rss: int, noise_floor: int=0) -> np.array:
    subcarrier_count = csi.shape[0]

    # This is not a true SNR ratio as is the case for the Intel scaling.
    # We do not have agc or noise values so it's just about establishing a scale against RSS.

    # This implementation is based on the equation shown in https://doi.org/10.1109/JIOT.2020.3022573.
    # scaling_coefficient = sqrt(10^(RSS/10) / sum(CSIi^2))

    # CSI is a vector of n subcarriers, represented as complex pairs.
    # The units are "linear voltage space".
    # RSS (for current purposes) is a measure of the received signal strength.
    # The units are dBm.

    # We can observe a linear relationship between CSI magnitude and RSS.
    # Utilising this, we aim to establish a scaling factor between a given
    # RSS/CSI pair.

    rss_pwr = dbinv(rss)

    # Now we'll get CSI magnitude.
    # First, the individual subcarrier magnitudes.
    abs_csi = abs(csi)
    # Then the vector magnitude.
    csi_mag = np.sum(abs_csi ** 2)
    # Then, we'll get the average magnitude per subcarrier.
    norm_csi_mag = csi_mag / subcarrier_count

    # We can then establish a scaling factor
    scale = rss_pwr / norm_csi_mag

    return csi * np.sqrt(scale)
