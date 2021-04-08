import csv

from CSIKit.util.csitools import get_CSI
from CSIKit.reader import get_reader

def generate_csv(path: str, dest: str, metric: str="amplitude"):
    reader = get_reader(path)
    csi_data = reader.read_file(path)

    csi_matrix, no_frames, no_subcarriers = get_CSI(csi_data, metric)
    no_rx, no_tx = csi_matrix.shape[2:]

    print("CSI Shape: {}".format(csi_matrix.shape))
    print("Number of Frames: {}".format(no_frames))
    print("Generating CSI {}...".format(metric))
    print("CSV dimensions: {} Rows, {} Columns".format(no_frames, no_subcarriers*no_rx*no_tx))

    csv_header = []
    for subcarrier in range(no_subcarriers):
        for rx in range(no_rx):
            for tx in range(no_tx):
                csv_header.append("Sub {} RXTX {}/{}".format(subcarrier, rx, tx))

    with open(dest, "w", newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(csv_header)

        for frame in range(no_frames):
            frame_data = csi_matrix[frame]
            row_data = []

            for subcarrier in range(no_subcarriers):
                subcarrier_data = frame_data[subcarrier]
                for rx in range(no_rx):
                    rx_data = subcarrier_data[rx]
                    for tx in range(no_tx):
                        tx_data = rx_data[tx]
                        row_data.append(tx_data)

            writer.writerow(row_data)

    print("File written to: {}".format(dest))