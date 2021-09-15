from CSIKit.csi.frames import ATHCSIFrame
from CSIKit.csi.frames import IWLCSIFrame
from CSIKit.csi.frames import USRPCSIFrame


class FrameContainer:
    DEVICE_MAP = {
        0x1234: "USRP SDR",
        0x2000: "Intel WiFi6 AX Series",
        0x5300: "Intel IWL5300",
        0x9300: "Qualcomm Atheros QCA9300"
    }

    TIMESTAMP_SECONDS_MAP = {
        0x1234: 1e+9,
        0x2000: 1e+9,
        0x5300: 1e+6,
        0x9300: 1e+6
    }

    CSIKIT_FRAME_MAP = {
        0x1234: USRPCSIFrame,
        # 0x2000: IWLMVMCSIFrame,
        0x5300: IWLCSIFrame,
        0x9300: ATHCSIFrame
    }

    __slots__ = ["RxSBasic", "ExtraInfo", "CSI"]

    def __init__(self):
        pass

    def get_bandwidth(self):
        return self.RxSBasic.cbw

    def get_device(self):
        return self.DEVICE_MAP[self.RxSBasic.deviceType]

    def get_timestamp_seconds(self):
        return self.RxSBasic.timestamp / self.TIMESTAMP_SECONDS_MAP[self.RxSBasic.deviceType]

    def get_frame(self):
        return self.CSIKIT_FRAME_MAP[self.RxSBasic.deviceType].from_picoscenes(self)
