import matplotlib.pyplot as plt
import numpy as np
from CSIKit.util import matlab

from CSIKit.util.csitools import get_CSI
from CSIKit.reader import get_reader
from CSIKit.tools.downsample import DownsampledImage, DownsampledLines

DEFAULT_PATH = "./data/intel/misc/log.all_csi.6.7.6.dat"
# DEFAULT_PATH = "./data/pi/walk_1597159475.pcap"

class BatchGraph:

    def __init__(self, path: str=DEFAULT_PATH, scaled: bool=False, filter_mac: str=None):
        reader = get_reader(path)
        self.csi_data = reader.read_file(path, scaled=scaled, filter_mac=filter_mac)

    def _first_pair_amplitude(self, **kwargs):
        """CSI amplitude of the first Rx/Tx pair as (frames, subcarriers), with the frames used."""
        csi, no_frames, no_subcarriers, kept = get_CSI(self.csi_data, return_indices=True, **kwargs)
        return csi[:, :, 0, 0], no_frames, no_subcarriers, kept

    def _time_axis(self, kept):
        """Seconds since the first plotted frame, or frame numbers if the capture has no usable timestamps."""
        timestamps = np.asarray(self.csi_data.timestamps, dtype=float)[np.asarray(kept, dtype=int)]
        x = timestamps - timestamps[0]
        if not np.any(x):
            return np.arange(len(kept)), "Frame No."
        return x, "Time (s)"

    def prepostfilter(self, subcarrier: int = 15):
        """Plot one subcarrier's amplitude over time: raw, Hampel-filtered, and Hampel + running mean."""
        # Imported here: SciPy and pandas take most of a second to load, and only this view needs them.
        from CSIKit.util.filters import hampel, running_mean

        amplitude, no_frames, no_subcarriers, kept = self._first_pair_amplitude()
        subcarrier = min(subcarrier, no_subcarriers - 1)

        raw = amplitude[:, subcarrier]  # one subcarrier, over time
        hampelData = hampel(raw, 10)
        smoothedData = running_mean(hampelData.copy(), 10)

        x, x_label = self._time_axis(kept)

        ax = plt.gca()
        DownsampledLines(ax, x, raw, label="Raw")
        DownsampledLines(ax, x, hampelData, label="Hampel")
        DownsampledLines(ax, x, smoothedData, color="r", label="Hampel + Running Mean")

        plt.xlabel(x_label)
        plt.ylabel("Amplitude (dBm)")
        plt.title("Subcarrier {}".format(subcarrier))
        plt.legend(loc="upper right")

        plt.show()

    def plotAllSubcarriers(self):
        """Plot every subcarrier's amplitude over time (first Rx/Tx pair)."""
        amplitude, no_frames, no_subcarriers, kept = self._first_pair_amplitude()
        x, x_label = self._time_axis(kept)

        # One line per subcarrier.
        DownsampledLines(plt.gca(), x, amplitude)

        plt.xlabel(x_label)
        plt.ylabel("Amplitude (dBm)")

        plt.show()

    def heatmap(self):

        # self.csi_data.frames = self.csi_data.frames[slice(1, len(self.csi_data.frames), 2)]

        finalEntry, no_frames, no_subcarriers, kept = get_CSI(self.csi_data, return_indices=True)
        if len(finalEntry.shape) == 4:
            #>1 antenna stream.
            #Loading the first for ease.
            finalEntry = finalEntry[:, :, 0, 0]

        # from CSIKit.filters.wavelets.dwt import denoise
        # finalEntry = denoise(finalEntry)

        #Transpose to get subcarriers * amplitude.
        finalEntry = np.transpose(finalEntry)

        x, x_label = self._time_axis(kept)
        xlim = no_frames if x_label == "Frame No." else np.max(x)

        # Subcarrier i is centred on y = i, with subcarrier 0 at the bottom.
        _, ax = plt.subplots()
        im = DownsampledImage(ax, finalEntry, xlim, (-0.5, no_subcarriers - 0.5),
                              cmap="jet", aspect="auto", origin="lower").artist

        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Amplitude (dBm)")

        plt.xlabel(x_label)
        plt.ylabel("Subcarrier Index")

        plt.title(self.csi_data.filename)

        plt.show()

    # Simple implementation.
    # Takes a 2D matrix of CSI data and timestamps to visualise amplitude.
    # CSI data should be arranged as (no_frames, no_subcarriers)
    @staticmethod
    def plot_heatmap(csi_matrix, timestamps):

        csi_matrix = np.transpose(csi_matrix)

        x_label = "Time (s)"
        x = np.asarray(timestamps, dtype=float)
        x = x - x[0] if len(x) else x

        if not np.any(x):
            # Some files have invalid timestamp_low values which means we can't plot based on timestamps.
            # Instead we'll just plot by frame count.

            xlim = csi_matrix.shape[1]

            x_label = "Frame No."
        else:
            xlim = np.max(x)

        # Subcarrier i is centred on y = i, with subcarrier 0 at the bottom.
        _, ax = plt.subplots()
        im = DownsampledImage(ax, csi_matrix, xlim, (-0.5, csi_matrix.shape[0] - 0.5),
                              cmap="jet", aspect="auto", origin="lower").artist

        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Amplitude (dBm)")

        plt.xlabel(x_label)
        plt.ylabel("Subcarrier Index")

        plt.title("CSI Amplitude Heatmap Plot")

        plt.show()

    def sumsqrssi(self):
        finalEntry, no_frames, no_subcarriers, kept = get_CSI(self.csi_data, extract_as_dBm=False, return_indices=True)
        if len(finalEntry.shape) == 4:
            # >1 antenna stream.
            # Loading the first for ease.
            finalEntry = finalEntry[:, :, 0, 0]

        rssis = []
        sumsq = []


        csi = finalEntry
        rss = [self.csi_data.frames[i].rssi for i in kept]

        sumsq = np.sum(csi ** 2, axis=1)
        norm_sumsq = np.sqrt(sumsq) / no_subcarriers

        line = []

        for rss_value, sumsq_value in zip(rss, norm_sumsq):
            line.append(matlab.db(sumsq_value) / rss_value)

        # plt.scatter(rssis, sumsq)
        plt.plot([self.csi_data.timestamps[i] for i in kept], line)

        plt.xlabel("Time (s)")
        plt.ylabel("RSSI / sumsq")

        plt.title(self.csi_data.filename)

        plt.show()

if __name__ == "__main__":
    bg = BatchGraph()
    bg.heatmap()