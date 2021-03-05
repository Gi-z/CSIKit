import numpy as np

from CSIKit.util.csitools import get_CSI
from CSIKit.reader import get_reader

def generate_npz(path: str, dest: str):
    reader = get_reader(path)
    csi_data = reader.read_file(path)

    if dest[-4:] != ".npz":
        dest += ".npz"

    csi_matrix, _, _ = get_CSI(csi_data)
    np.savez_compressed(dest, csi_matrix)

    print("CSI matrix with shape: {}".format(csi_matrix.shape))
    print("Generating CSI amplitude...")
    print("File written to: {}".format(dest))