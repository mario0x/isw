"""Constants for ISW - EC addresses, fan modes, and magic numbers."""

import os

# File paths
EC_IO_FILE = '/sys/kernel/debug/ec/ec0/io'
CFG_FILE = '/etc/isw.conf'

# Fan mode values written to EC
FAN_MODE_AUTO = 12
FAN_MODE_BASIC = 76
FAN_MODE_ADVANCED = 140

FAN_MODE_NAMES = {
    FAN_MODE_AUTO: 'Auto',
    FAN_MODE_BASIC: 'Basic',
    FAN_MODE_ADVANCED: 'Advanced',
}

# RPM calculation: RPM = RPM_DIVISOR // raw_ec_value
RPM_DIVISOR = 478000

# Battery threshold is stored in EC as user_percentage + BATTERY_OFFSET
BATTERY_OFFSET = 128
BATTERY_MIN = 20
BATTERY_MAX = 100

# Number of temperature thresholds and fan speed points per component
NUM_TEMP_THRESHOLDS = 6
NUM_FAN_SPEEDS = 7

# Config section names for special features
SECTION_ADDRESS_DEFAULT = 'MSI_ADDRESS_DEFAULT'
SECTION_COOLER_BOOST = 'COOLER_BOOST'
SECTION_USB_BACKLIGHT = 'USB_BACKLIGHT'

# Sections that are not laptop profiles
NON_PROFILE_SECTIONS = {
    SECTION_ADDRESS_DEFAULT,
    SECTION_COOLER_BOOST,
    SECTION_USB_BACKLIGHT,
}

# Firmware file profile addresses (for -f option)
FIRMWARE_CPU_TEMP_ADDRS = [
    0xf801, 0xf802, 0xf803, 0xf804, 0xf805, 0xf806,
    0xf841, 0xf842, 0xf843, 0xf844, 0xf845, 0xf846,
    0xf871, 0xf872, 0xf873, 0xf874, 0xf875, 0xf876,
    0xf881, 0xf882, 0xf883, 0xf884, 0xf885, 0xf886,
    0xf8b1, 0xf8b2, 0xf8b3, 0xf8b4, 0xf8b5, 0xf8b6,
    0xf8c1, 0xf8c2, 0xf8c3, 0xf8c4, 0xf8c5, 0xf8c6,
    0xf8f1, 0xf8f2, 0xf8f3, 0xf8f4, 0xf8f5, 0xf8f6,
]

FIRMWARE_CPU_FAN_SPEED_ADDRS = [
    0xf80b, 0xf80c, 0xf80d, 0xf80e, 0xf80f, 0xf810, 0xf811,
    0xf84b, 0xf84c, 0xf84d, 0xf84e, 0xf84f, 0xf850, 0xf851,
    0xf87b, 0xf87c, 0xf87d, 0xf87e, 0xf87f, 0xf880, 0xf881,
    0xf88b, 0xf88c, 0xf88d, 0xf88e, 0xf88f, 0xf890, 0xf891,
    0xf8bb, 0xf8bc, 0xf8bd, 0xf8be, 0xf8bf, 0xf8c0, 0xf8c1,
    0xf8cb, 0xf8cc, 0xf8cd, 0xf8ce, 0xf8cf, 0xf8d0, 0xf8d1,
    0xf8fb, 0xf8fc, 0xf8fd, 0xf8fe, 0xf8ff, 0xf900, 0xf901,
]

FIRMWARE_GPU_TEMP_ADDRS = [
    0xf821, 0xf822, 0xf823, 0xf824, 0xf825, 0xf826,
    0xf861, 0xf862, 0xf863, 0xf864, 0xf865, 0xf866,
    0xf891, 0xf892, 0xf893, 0xf894, 0xf895, 0xf896,
    0xf8a1, 0xf8a2, 0xf8a3, 0xf8a4, 0xf8a5, 0xf8a6,
    0xf8d1, 0xf8d2, 0xf8d3, 0xf8d4, 0xf8d5, 0xf8d6,
    0xf8e1, 0xf8e2, 0xf8e3, 0xf8e4, 0xf8e5, 0xf8e6,
    0xf911, 0xf912, 0xf913, 0xf914, 0xf915, 0xf916,
]

FIRMWARE_GPU_FAN_SPEED_ADDRS = [
    0xf82b, 0xf82c, 0xf82d, 0xf82e, 0xf82f, 0xf830, 0xf831,
    0xf86b, 0xf86c, 0xf86d, 0xf86e, 0xf86f, 0xf870, 0xf871,
    0xf89b, 0xf89c, 0xf89d, 0xf89e, 0xf89f, 0xf8a0, 0xf8a1,
    0xf8ab, 0xf8ac, 0xf8ad, 0xf8ae, 0xf8af, 0xf8b0, 0xf8b1,
    0xf8db, 0xf8dc, 0xf8dd, 0xf8de, 0xf8df, 0xf8e0, 0xf8e1,
    0xf8eb, 0xf8ec, 0xf8ed, 0xf8ee, 0xf8ef, 0xf8f0, 0xf8f1,
    0xf91b, 0xf91c, 0xf91d, 0xf91e, 0xf91f, 0xf920, 0xf921,
]

# ANSI text formatting (for CLI output)
class Text:
    YELLOW = '\033[32;1m'
    ULINED = '\033[4m'
    CLEAR = '\033[0m'
    CURSOR_UP = '\033[A'
    CURSOR_DOWN = '\033[B'
    CURSOR_LEFT = '\033[D'
    TWO_COLUMN = '%-11s %s'
    THREE_COLUMN = '%-11s %-20s %s'
    FOUR_COLUMN = '%-11s %-20s %-11s %s'
    HEIGHT_COLUMN = '%-5s %-7s %-8s %-8s %-6s %-7s %-8s %s'
    CPU_GPU = '-----------CPU-----------        -----------GPU-----------'
    TEMP_FS = '\u250c\u2500Temp\u2500\u252c\u2500Fan Speed\u2500\u2500\u2500\u2500\u2500\u2500\u2510        \u250c\u2500Temp\u2500\u252c\u2500Fan Speed\u2500\u2500\u2500\u2500\u2500\u2500\u2510'
    TEMP_FS_END = '\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518        \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518'
