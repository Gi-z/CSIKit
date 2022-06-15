from CSIKit.csi.frames import ATHCSIFrame
from CSIKit.csi.frames import IWLCSIFrame
from CSIKit.csi.frames import USRPCSIFrame
from CSIKit.csi.frames.mvm import IWLMVMCSIFrame


class FrameContainer:
    DEVICE_MAP = {
        0x1234: "USRP SDR",
        0x2000: "Intel WiFi6 AX200",
        0x2100: "Intel WiFi6E AX210",
        0x5300: "Intel IWL5300",
        0x9300: "Qualcomm Atheros QCA9300"
    }

    TIMESTAMP_SECONDS_MAP = {
        0x1234: 1e+9,
        0x2000: 1e+6,
        0x2100: 1e+6,
        0x5300: 1e+6,
        0x9300: 1e+6
    }

    CSIKIT_FRAME_MAP = {
        0x1234: USRPCSIFrame,
        0x2000: IWLMVMCSIFrame,
        0x2100: IWLMVMCSIFrame,
        0x5300: IWLCSIFrame,
        0x9300: ATHCSIFrame,
    }

    __slots__ = ["RxSBasic", "ExtraInfo", "MVMExtra", "CSI"]

    def __init__(self):
        pass

    def get_bandwidth(self):
        return self.RxSBasic.cbw

    def get_device(self):
        return self.DEVICE_MAP[self.RxSBasic.deviceType]

    def get_timestamp_seconds(self):
        if self.RxSBasic.deviceType == 0x2000:
            return self.MVMExtra.muClock / self.TIMESTAMP_SECONDS_MAP[self.RxSBasic.deviceType]
        else:
            return self.RxSBasic.timestamp / self.TIMESTAMP_SECONDS_MAP[self.RxSBasic.deviceType]

    def get_frame(self):
        return self.CSIKIT_FRAME_MAP[self.RxSBasic.deviceType].from_picoscenes(self)

    def set_source_mac(self, mac):
        self.RxSBasic.source_mac = mac
