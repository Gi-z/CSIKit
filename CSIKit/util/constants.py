
# These values are based on Table 2-1 on Page 14 of 802.11ac: A Survival Guide.
# https://www.oreilly.com/library/view/80211ac-a-survival/9781449357702/ch02.html
#
# Subcarrier indices are centred. Centre subcarrier is always null.

# 20MHz b/g: Total 52, Pilots 4
# 20MHz HT: Total 64, Data 52, Pilots 4, Guards 8
# 40MHz HT: Total 128, Data , Pilots 6, Guards
# 80MHz VHT: Total 256, Data , Pilots 8, Guards

# Atheros 20MHz: 56 usable subcarriers, no removal needed.

# ESP32 20MHz: 64 subcarriers, 51 usable ones?, 11 null, 2 Pilots?
# ESP32 20MHz null (11): [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37]
# ESP32 20MHz pilot (2): [0, 1]

ESP32_20MHZ_NULL = [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37]
ESP32_20MHZ_PILOT = [0, 1]

ESP32_20MHZ_UNUSABLE = ESP32_20MHZ_NULL + ESP32_20MHZ_PILOT

PI_20MHZ_PILOT = [0, 28, 29]
PI_20MHZ_GUARD = [1, 30, 31, 32, 33, 34, 35, 62, 63]

PI_20MHZ_UNUSABLE = PI_20MHZ_PILOT + PI_20MHZ_GUARD

PI_80MHZ_PILOT = []
PI_80MHZ_GUARD = []

PI_80MHZ_UNUSABLE = PI_80MHZ_PILOT + PI_80MHZ_GUARD

SUBCARRIERS = {
    20: 64,
    40: 128,
    80: 256,
    160: 512
}

GUARD_NULL = {
    20: [],
    40: [],
    80: [],
    160: []
}

BOOK_PILOT = {
    20: [-21, -7, 7, 21],
    40: [-53, -25, -11, 11, 25, 53],
    80: [-103, -75, -39, -11, 11, 39, 75, 103],
    160: [-231, -203, -167, -139, -117, -89, -53, -25, 25, 53, 89, 117, 139, 167, 203, 231]
}

PILOT = {
    20: [10, 24, 38, 52],
    40: [10, 38, 52, 74, 88, 116],
    80: [24, 52, 88, 116, 138, 166, 202, 230],
    160: [24, 52, 88, 116, 138, 166, 202, 230, 280, 308, 344, 372, 394, 422, 458, 486]
}

NON_DATA = {
    20: [],
    40: [],
    80: [],
    160: []
}