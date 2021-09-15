from typing import Tuple

from CSIKit.csi import CSIData
from CSIKit.reader import Reader

from CSIKit.reader.readers.pico.AbstractPicoScenesFrameSegment import AbstractPicoScenesFrameSegment
from CSIKit.reader.readers.pico.CSISegment import CSISegment
from CSIKit.reader.readers.pico.ExtraInfoSegment import ExtraInfoSegment
from CSIKit.reader.readers.pico.FrameContainer import FrameContainer
from CSIKit.reader.readers.pico.ModularPicoScenesFrame import ModularPicoScenesFrame
from CSIKit.reader.readers.pico.RxSBasicSegment import RxSBasicSegment

import os
import struct

class PicoScenesBeamformReader(Reader):

    SEGMENT_MAPPING = {
        "RxSBasic": RxSBasicSegment,
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

    def read_file(self, filename: str, scaled: bool = False) -> CSIData:
        file_bytes = open(filename, "rb").read()
        pos = 0

        self.filename = filename

        ret_data = CSIData(self.filename, "PicoScenes")
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

            pos += frame_length

            if ret_data.bandwidth == 0:
                ret_data.bandwidth = frame_container.get_bandwidth()

            if ret_data.chipset == "":
                ret_data.set_chipset(frame_container.get_device())

            if initial_timestamp is None:
                initial_timestamp = frame_container.get_timestamp_seconds()

            given_timestamp = frame_container.get_timestamp_seconds() - initial_timestamp

            ret_data.push_frame(frame_container.get_frame())
            ret_data.timestamps.append(given_timestamp)

        return ret_data