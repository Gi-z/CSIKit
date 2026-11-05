from CSIKit.util.errors import NoFramesError
from CSIKit.util.matlab import db, dbinv

from collections import Counter
from typing import Tuple

import warnings

import numpy as np


def _as_subcarriers_rx_tx(matrix) -> np.ndarray:
    """View a frame's CSI matrix as (subcarriers, rx, tx)."""
    matrix = np.asarray(matrix)
    if matrix.ndim == 1:
        return matrix.reshape(-1, 1, 1)
    if matrix.ndim == 2:
        return matrix.reshape(matrix.shape[0], matrix.shape[1], 1)
    if matrix.ndim == 3:
        return matrix
    raise ValueError("Unsupported CSI matrix shape {}.".format(matrix.shape))


def get_CSI(csi_data: 'CSIData', metric: str = "amplitude", extract_as_dBm: bool = True,
            squeeze_output: bool = False, return_indices: bool = False) -> Tuple[np.ndarray, int, int]:
    """Assemble the CSI of every frame into one (frames, subcarriers, rx, tx) array.

    Parameters:
        metric: "amplitude" (default), "phase", or anything else for the complex values.
        extract_as_dBm: with metric="amplitude", return 20*log10(|CSI|) instead of |CSI|.
        squeeze_output: drop singleton dimensions (e.g. single-antenna rx/tx axes).
        return_indices: also return the indices (into csi_data.frames / csi_data.timestamps)
            of the frames included, e.g. to select matching timestamps.

    Returns:
        (csi, no_frames, no_subcarriers), plus the included frame indices if return_indices.

    The array needs every frame to have the same (subcarriers, rx, tx) shape. When frames differ:

    - subcarriers: the most common tone count is used and frames with other counts are left out
      (different tone sets can't be aligned, e.g. 52-tone legacy vs 56-tone HT frames in PicoScenes);
    - rx (the capturing device's antennas): the most common count is used; frames with fewer are
      left out, frames with more keep their first antennas;
    - tx (spatial streams, which depend on how each packet was sent): every frame is reduced to
      the streams all frames have.

    A warning says what was left out or reduced. csi_data itself is not modified.
    """
    frames = csi_data.frames
    if not frames:
        raise NoFramesError("No CSI frames to assemble: the file may be empty or in an unsupported format.")

    matrices = [_as_subcarriers_rx_tx(frame.csi_matrix) for frame in frames]
    shapes = Counter(matrix.shape for matrix in matrices)

    # Ties go to the value seen first.
    n_subcarriers = Counter(m.shape[0] for m in matrices).most_common(1)[0][0]
    same_tones = [i for i, m in enumerate(matrices) if m.shape[0] == n_subcarriers]
    n_rx = Counter(matrices[i].shape[1] for i in same_tones).most_common(1)[0][0]
    kept = [i for i in same_tones if matrices[i].shape[1] >= n_rx]
    n_tx = min(matrices[i].shape[2] for i in kept)
    shape = (n_subcarriers, n_rx, n_tx)

    if len(shapes) > 1:
        warnings.warn(
            "get_CSI: frames have different CSI shapes (shape: count) {}; using {} of {} frames as "
            "{} subcarriers x {} Rx x {} Tx.".format(dict(shapes), len(kept), len(frames), *shape),
            stacklevel=2,
        )

    csi = np.stack([matrices[i][:, :n_rx, :n_tx] for i in kept]).astype(complex)

    if metric == "amplitude":
        csi = abs(csi)
        if extract_as_dBm:
            csi = db(csi)
    elif metric == "phase":
        csi = np.angle(csi)

    if squeeze_output:
        csi = np.squeeze(csi)

    result = (csi, len(kept), n_subcarriers)
    return result + (kept,) if return_indices else result


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
