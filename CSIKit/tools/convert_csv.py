import csv

from CSIKit.util.csitools import get_CSI
from CSIKit.reader import get_reader

def generate_csv(path: str, dest: str):
    reader = get_reader(path)
    csi_data = reader.read_file(path)

    csi_matrix, no_frames, no_subcarriers = get_CSI(csi_data)
    print("CSI Shape: {}".format(csi_matrix.shape))
    print("Number of Frames: {}".format(no_frames))
    print("Generating CSI Amplitude...")
    print("CSV dimensions: {} Rows, {} Columns".format(no_subcarriers, no_frames))

    with open(dest, "w", newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter="\t")
        
        for x in range(no_subcarriers):
            subcarrier = csi_matrix[x]
            row = [i for i in subcarrier]

            writer.writerow(row)

    print("File written to: {}".format(dest))