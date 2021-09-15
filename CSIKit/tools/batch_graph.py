import matplotlib.pyplot as plt
import numpy as np

from CSIKit.util.csitools import get_CSI
from CSIKit.util.filters import bandpass, hampel, running_mean
from CSIKit.reader import get_reader

DEFAULT_PATH = "./data/intel/misc/log.all_csi.6.7.6.dat"
# DEFAULT_PATH = "./data/pi/walk_1597159475.pcap"

class BatchGraph:

    def __init__(self, path: str=DEFAULT_PATH):
        reader = get_reader(path)
        self.csi_data = reader.read_file(path)

    def prepostfilter(self):

        csi_trace = self.csi_data.frames
        finalEntry, no_frames, _ = get_CSI(self.csi_data)

        finalEntry = finalEntry[15]

        hampelData = hampel(finalEntry, 10)
        smoothedData = running_mean(hampelData.copy(), 10)

        y = finalEntry
        y2 = hampelData
        y3 = smoothedData

        x = list([x.timestamp for x in csi_trace])

        if sum(x) == 0:
            x = np.arange(0, no_frames, 1)

        plt.plot(x, y, label="Raw")
        plt.plot(x, y2, label="Hampel")
        plt.plot(x, y3, "r", label="Hampel + Running Mean")

        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude (dBm)")
        plt.legend(loc="upper right")

        plt.show()

    def plotAllSubcarriers(self):

        finalEntry, no_frames, _ = get_CSI(self.csi_data)

        for x in finalEntry:
            plt.plot(np.arange(no_frames)/20, x)

        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude (dBm)")
        plt.legend(loc="upper right")

        plt.show()

    def heatmap(self):

        finalEntry, no_frames, no_subcarriers = get_CSI(self.csi_data)
        if len(finalEntry.shape) == 4:
            #>1 antenna stream.
            #Loading the first for ease.
            finalEntry = finalEntry[:, :, 0, 0]

        # from CSIKit.filters.wavelets.dwt import denoise
        # finalEntry = denoise(finalEntry)

        #Transpose to get subcarriers * amplitude.
        finalEntry = np.transpose(finalEntry)

        x_label = "Time (s)"
        try:
            x = self.csi_data.timestamps
            x = [timestamp-x[0] for timestamp in x]
        except AttributeError as e:
            #No timestamp in frame. Likely an IWL entry.
            #Will be moving timestamps to CSIData to account for this.
            x = [0]

        if sum(x) == 0:
            #Some files have invalid timestamp_low values which means we can't plot based on timestamps.
            #Instead we'll just plot by frame count.

            xlim = no_frames

            x_label = "Frame No."
        else:
            xlim = max(x)

        limits = [0, xlim, 1, no_subcarriers]
        # limits = [0, xlim, -64, 63]

        #TODO Add options for filtering.
        # for x in range(no_subcarriers):
        #     hampelData = hampel(finalEntry[x], 5, 3)
        #     runningMeanData = running_mean(hampelData, 20)
        #     # smoothedData = dynamic_detrend(runningMeanData, 5, 3, 1.2, 10)
        #     # doubleHampel = hampel(smoothedData, 10, 3)

        #     finalEntry[x] = bandpass(9, 1, 2, Fs, runningMeanData)
        #     # for i in range(0, 140):
        #     #     finalEntry[x][i] = 0
            
        _, ax = plt.subplots()
        im = ax.imshow(finalEntry, cmap="jet", extent=limits, aspect="auto")

        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Amplitude (dBm)")

        plt.xlabel(x_label)
        plt.ylabel("Subcarrier Index")

        plt.title(self.csi_data.filename)

        plt.show()

if __name__ == "__main__":
    bg = BatchGraph()
    bg.heatmap()