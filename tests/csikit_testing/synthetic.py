"""Builders and independent parsers for CSI file formats.

These are written from the formats' descriptions rather than by calling
CSIKit, so tests can construct inputs with known contents (including edge
cases the bundled samples don't cover) and cross-check CSIKit's output.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Atheros CSI Tool
# ---------------------------------------------------------------------------

ATHEROS_HEADER = struct.Struct("<QHHBBBBBBBBBBBH")


def pack_10bit(values: Sequence[int]) -> bytes:
    """Pack signed 10-bit integers LSB-first into a little-endian byte stream."""
    acc = 0
    nbits = 0
    out = bytearray()
    for value in values:
        acc |= (int(value) & 0x3FF) << nbits
        nbits += 10
        while nbits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nbits -= 8
    if nbits:
        out.append(acc & 0xFF)
    if len(out) % 2:
        out.append(0)
    return bytes(out)


def atheros_record(
    timestamp_us: int,
    csi: np.ndarray,
    *,
    channel: int = 2437,
    rate: int = 0x8C,
    bandwidth: int = 0,
    rssi: tuple = (40, 38, 36, 0),
    noise_floor: int = 0,
    payload_len: int = 0,
) -> bytes:
    """Encode one Atheros CSI Tool log record.

    ``csi`` is an integer-valued complex array shaped ``(tones, nr, nc)``.
    Elements are written tone -> nc -> nr, imaginary part first, which is the
    order CSIKit's decoder reads them in. Whether that order (and CSIKit's
    ``+1`` adjustment on decode) matches the original tool is an open
    question tracked in NEEDS_GROUND_TRUTH.
    """
    tones, nr, nc = csi.shape
    values = []
    for k in range(tones):
        for c in range(nc):
            for r in range(nr):
                values += [int(csi[k, r, c].imag), int(csi[k, r, c].real)]
    csi_bytes = pack_10bit(values)
    header = ATHEROS_HEADER.pack(
        timestamp_us, len(csi_bytes), channel, 0, noise_floor, rate, bandwidth,
        tones, nr, nc, rssi[0], rssi[1], rssi[2], rssi[3], payload_len,
    )
    body = header + csi_bytes + bytes(payload_len)
    return struct.pack("<H", len(body)) + body


# ---------------------------------------------------------------------------
# ESP32 CSI Tool (CSV)
# ---------------------------------------------------------------------------

ESP32_FIELDS = [
    "type", "role", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing",
    "not_sounding", "aggregation", "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt",
    "channel", "secondary_channel", "local_timestamp", "ant", "sig_len", "rx_state",
    "real_time_set", "real_timestamp", "len", "CSI_DATA",
]


def esp32_row(csi_values: Sequence[int], **overrides) -> str:
    """One ESP32-CSI-Tool CSV row. ``csi_values`` is the raw int8 buffer."""
    values = dict(
        type="CSI_DATA", role="PASSIVE", mac="11:22:33:44:55:66", rssi=-52, rate=11,
        sig_mode=1, mcs=0, bandwidth=0, smoothing=1, not_sounding=1, aggregation=0,
        stbc=0, fec_coding=0, sgi=0, noise_floor=-98, ampdu_cnt=0, channel=6,
        secondary_channel=0, local_timestamp=0, ant=0, sig_len=100, rx_state=0,
        real_time_set=0, real_timestamp=0.0, len=len(csi_values),
    )
    values.update(overrides)
    head = ",".join(str(values[name]) for name in ESP32_FIELDS[:-1])
    return f"{head},[{' '.join(str(int(v)) for v in csi_values)}]"


def write_esp32_csv(path: Path, rows: Sequence[str]) -> Path:
    path.write_text("\n".join([",".join(ESP32_FIELDS), *rows]) + "\n")
    return path


# ---------------------------------------------------------------------------
# pcap / Nexmon
# ---------------------------------------------------------------------------

PCAP_GLOBAL_HEADER_SIZE = 24
NEXMON_UDP_OFFSET = 42  # Ethernet (14) + IPv4 (20) + UDP (8)


@dataclass
class PcapRecord:
    offset: int
    ts_sec: int
    ts_usec: int
    incl_len: int
    orig_len: int
    data: bytes

    @property
    def nexmon(self) -> dict:
        p = self.data[NEXMON_UDP_OFFSET:]
        core_ss = int.from_bytes(p[12:14], "little")
        return {
            "source_mac": ":".join(f"{b:02X}" for b in p[4:10]),
            "sequence_no": int.from_bytes(p[10:12], "little"),
            "core": core_ss & 0x7,
            "spatial_stream": (core_ss >> 3) & 0x7,
        }


def pcap_records(path) -> Iterator[PcapRecord]:
    raw = Path(path).read_bytes()
    endian = "<" if raw[:4] in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
    pos = PCAP_GLOBAL_HEADER_SIZE
    while pos + 16 <= len(raw):
        ts_sec, ts_usec, incl, orig = struct.unpack(endian + "IIII", raw[pos:pos + 16])
        yield PcapRecord(pos, ts_sec, ts_usec, incl, orig, raw[pos + 16:pos + 16 + incl])
        pos += 16 + incl


def write_pcap(path: Path, template, records: Sequence[PcapRecord]) -> Path:
    """Write records (little-endian) behind the global header of the ``template`` capture."""
    header = Path(template).read_bytes()[:PCAP_GLOBAL_HEADER_SIZE]
    body = b"".join(
        struct.pack("<IIII", r.ts_sec, r.ts_usec, len(r.data), r.orig_len) + r.data for r in records)
    path.write_bytes(header + body)
    return path


def shorten_nexmon_record(record: PcapRecord, csi_bytes: int) -> PcapRecord:
    """A copy of a Nexmon record carrying only ``csi_bytes`` of CSI (as if sent at another bandwidth)."""
    nexmon_header = 18
    data = bytearray(record.data[:NEXMON_UDP_OFFSET + nexmon_header + csi_bytes])
    udp_len = 8 + nexmon_header + csi_bytes
    struct.pack_into(">H", data, 16, 20 + udp_len)  # IPv4 total length
    struct.pack_into(">H", data, 38, udp_len)       # UDP length
    return PcapRecord(0, record.ts_sec, record.ts_usec, len(data), len(data), bytes(data))


# ---------------------------------------------------------------------------
# Linux 802.11n CSI Tool (IWL5300 .dat)
# ---------------------------------------------------------------------------

IWL_BFEE_CODE = 0xBB


def iwl_records(raw: bytes) -> Iterator[tuple]:
    """Yield ``(offset, size, code)`` for each record in a log_to_file .dat."""
    pos = 0
    while pos + 3 <= len(raw):
        size = struct.unpack(">H", raw[pos:pos + 2])[0]
        code = raw[pos + 2]
        yield pos, size, code
        pos += 2 + size


def set_iwl_timestamps(raw: bytes, timestamps: Sequence[int]) -> bytes:
    """Overwrite timestamp_low (u32 LE, first header field) of each bfee record."""
    out = bytearray(raw)
    offsets = [off for off, _, code in iwl_records(raw) if code == IWL_BFEE_CODE]
    for off, ts in zip(offsets, timestamps):
        struct.pack_into("<I", out, off + 3, ts & 0xFFFFFFFF)
    return bytes(out)
