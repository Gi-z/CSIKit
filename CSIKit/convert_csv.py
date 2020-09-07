import csv

from .csitools import get_CSI, get_timestamps
from .reader import get_reader

def generate_csv(path, dest):
    reader = get_reader(path)

    # unmodified_csi_matrix = reader.csi_trace[0]["csi"]
    csi_matrix, no_frames, no_subcarriers = get_CSI(reader.csi_trace)
    print(csi_matrix.shape)
    print(no_frames)

    with open(dest, "w", newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter="\t")
        
        for x in range(no_subcarriers):
            subcarrier = csi_matrix[x]
            row = [i for i in subcarrier]

            writer.writerow(row)