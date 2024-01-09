from CSIKit.csi.csiframe import CSIFrame
from CSIKit.csi.csimetadata import CSIMetadata
from CSIKit.util.csitools import get_CSI

import numpy as np

class CSIData:

    def __init__(self, filename: str="", backend: str="", chipset: str="", filter_mac: str=None):
        
        self.frames = []
        self.timestamps = []

        self.expected_frames = 0
        self.skipped_frames = 0

        self.bandwidth = 0

        self.filename = filename
        self.backend = backend
        self.chipset = chipset
        self.filter_mac = filter_mac

    def set_chipset(self, chipset: str):
        self.chipset = chipset

    def set_backend(self, backend: str):
        self.backend = backend

    def push_frame(self, frame: CSIFrame, timestamp: float):
        if self.filter_mac is not None:
            if hasattr(frame, "source_mac"):
                if self.filter_mac.casefold() == frame.source_mac.casefold():
                    self.frames.append(frame)
                    self.timestamps.append(timestamp)
            elif hasattr(frame, "mac"):
                if self.filter_mac.casefold() == frame.mac.casefold():
                    self.frames.append(frame)
                    self.timestamps.append(timestamp)
        else:
            self.frames.append(frame)
            self.timestamps.append(timestamp)

    def get_metadata(self) -> CSIMetadata:
        chipset = self.chipset
        backend = self.backend

        bandwidth = self.bandwidth

        unmodified_csi_matrix = self.frames[0].csi_matrix
        _, no_frames, no_subcarriers = get_CSI(self)

        rx_count = (0, 0)
        tx_count = (0, 0)

        if len(unmodified_csi_matrix.shape) <= 2:
            rx_count, tx_count = (1, 1)
        elif len(unmodified_csi_matrix.shape) == 3:
            rx_count, tx_count = unmodified_csi_matrix.shape[1:]

        antenna_config_string = "{} Rx, {} Tx".format(rx_count, tx_count)

        timestamps = self.timestamps
        final_timestamp = timestamps[-1]

        #Check if timestamp is relative or epoch.

        time_length = 0
        if len(str(final_timestamp)) > 9:
            #Likely an epoch timestamp.
            #Get diff between first and last.
            time_length = final_timestamp - timestamps[0]
        else:
            time_length = round(float(final_timestamp), 1)

        average_sample_rate = 0
        if time_length > 0 and final_timestamp != 0:
                average_sample_rate = round(no_frames/time_length, 1)

        rss_total = []
        if hasattr(self.frames[0], "rssi"):
            rss_total = [x.rssi for x in self.frames]
        elif self.backend == "FeitCSI":
            rss_total = [max(frame.rssi_1, frame.rssi_2) for frame in self.frames]
        else:
            rss_total = [max(frame.rssi_a, frame.rssi_b, frame.rssi_c) for frame in self.frames]
            # Must sum a/b/c.
            # for frame in self.frames:
            #     total_rss_for_frame = 0
            #     divisor = 0
            #     if frame.rssi_a != 0:
            #         total_rss_for_frame += frame.rssi_a
            #         divisor += 1
            #     if frame.rssi_b != 0:
            #         total_rss_for_frame += frame.rssi_b
            #         divisor += 1
            #     if frame.rssi_c != 0:
            #         total_rss_for_frame += frame.rssi_c
            #         divisor += 1
            #     total_rss_for_frame /= divisor
            #     rss_total.append(total_rss_for_frame)

        average_rssi = round(np.mean(rss_total), 1)

        data = {
            "chipset": chipset,
            "backend": backend,
            "bandwidth": bandwidth,
            "antenna_config": antenna_config_string,
            "frames": no_frames,
            "subcarriers": no_subcarriers,
            "time_length": time_length,
            "average_sample_rate": average_sample_rate,
            "average_rssi": average_rssi,
            "csi_shape": unmodified_csi_matrix.shape
        }    

        return CSIMetadata(data)