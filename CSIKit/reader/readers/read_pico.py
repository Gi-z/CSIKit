from typing import Tuple

from CSIKit.csi import CSIData
from CSIKit.reader import Reader

from CSIKit.reader.readers.pico.AbstractPicoScenesFrameSegment import AbstractPicoScenesFrameSegment
from CSIKit.reader.readers.pico.CSISegment import CSISegment
from CSIKit.reader.readers.pico.ExtraInfoSegment import ExtraInfoSegment
from CSIKit.reader.readers.pico.FrameContainer import FrameContainer
from CSIKit.reader.readers.pico.ModularPicoScenesFrame import ModularPicoScenesFrame
from CSIKit.reader.readers.pico.RxSBasicSegment import RxSBasicSegment
from CSIKit.reader.readers.pico.MVMExtraSegment import MVMExtraSegment

import os
import struct

from CSIKit.util import stringops


class PicoScenesBeamformReader(Reader):

    SEGMENT_MAPPING = {
        "RxSBasic": RxSBasicSegment,
        # "ExtraInfo": ExtraInfoSegment,
        "MVMExtra": MVMExtraSegment,
        "CSI": CSISegment
    }

    def __init__(self):
        pass

    @staticmethod
    def can_read(path: str) -> bool:
        if os.path.exists(path):
            _, extension = os.path.splitext(path)
            if extension == ".csi":
                with open(path, "rb") as file:
                    # Checking bytes 4-8 match magic.
                    first_bytes = file.read(8)
                    return first_bytes[4:8] == b'\x15\x03\x15 '

        return False

    @staticmethod
    def get_block(data: bytes, offset: int) -> Tuple[int, bytes]:
        # When retrieving block bytes, adding the length indicator to total size reduces boilerplate.
        length = struct.unpack("I", data[offset:offset+4])[0] + 4
        return (length, data[offset:offset + length])

    def read_file(self, filename: str, scaled: bool = False, filter_mac: str = None) -> CSIData:
        file_bytes = open(filename, "rb").read()
        pos = 0

        self.filename = filename

        ret_data = CSIData(self.filename, "PicoScenes", filter_mac=filter_mac)
        ret_data.bandwidth = 0

        self.frames = []
        initial_timestamp = None

        while pos < len(file_bytes):
            frame_length, frame_bytes = self.get_block(file_bytes, pos)
            if len(frame_bytes) != frame_length:
                #print("Reached end of file.")
                break

            frame = ModularPicoScenesFrame(frame_bytes[:ModularPicoScenesFrame.SIZE])
            frame_pos = ModularPicoScenesFrame.SIZE

            frame_container = FrameContainer()

            for i in range(frame.numRxSegments):
                seg_length, seg_bytes = self.get_block(frame_bytes, frame_pos)
                segment = AbstractPicoScenesFrameSegment(seg_bytes)

                subseg_start = frame_pos + segment.pos
                subseg_bytes = frame_bytes[subseg_start:subseg_start+seg_length]

                if segment.subsegmentName in self.SEGMENT_MAPPING:
                    setattr(frame_container, segment.subsegmentName, self.SEGMENT_MAPPING[segment.subsegmentName](subseg_bytes, segment.subsegmentVersion))

                frame_pos += seg_length

            source_mac = stringops.hexToMACString(frame_bytes[frame_pos+4:frame_pos+10].hex())
            frame_container.set_source_mac(source_mac)

            # print(frame_container.RxSBasic.timestamp)

            pos += frame_length

            if ret_data.bandwidth == 0:
                ret_data.bandwidth = frame_container.get_bandwidth()

            if ret_data.chipset == "":
                ret_data.set_chipset(frame_container.get_device())

            if initial_timestamp is None:
                initial_timestamp = frame_container.get_timestamp_seconds()

            new_timestamp = frame_container.get_timestamp_seconds()
            given_timestamp = new_timestamp - initial_timestamp

            # if hasattr(frame_container, "RxSBasic"):
            #     if frame_container.RxSBasic.deviceType == 0x2000:
            #         # initial_timestamp = 0
            #         if frame_container.RxSBasic.mcs == 4 and frame_container.CSI.packetFormat == 1:
            #             # given_timestamp = frame_container.get_timestamp_seconds()
            #             # given_timestamp = len(ret_data.frames) * 0.01
            #             # frame_container.CSI.parsed_csi = frame_container.CSI.parsed_csi[[x for x in range(frame_container.CSI.parsed_csi.shape[1]) if x not in [8, 22, 35, 48]]]
            #             pass
            #         else:
            #             continue
            #     elif frame_container.RxSBasic.deviceType == 0x1234:
            #         # initial_timestamp = 0
            #         # if frame_container.RxSBasic.mcs == 4 and frame_container.CSI.packetFormat == 1:
            #         #     pass
            #         if frame_container.CSI.packetFormat == 0:
            #             pass
            #         else:
            #             continue

            ret_data.push_frame(frame_container.get_frame(), given_timestamp)

        return ret_data