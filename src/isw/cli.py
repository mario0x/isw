"""CLI interface for ISW - preserves original command-line behavior."""

import sys
import os
import time
import subprocess
from argparse import ArgumentParser, Action, RawTextHelpFormatter

from .constants import (
    EC_IO_FILE, Text, FAN_MODE_NAMES,
    BATTERY_OFFSET, BATTERY_MIN, BATTERY_MAX,
    SECTION_ADDRESS_DEFAULT,
    FIRMWARE_CPU_TEMP_ADDRS, FIRMWARE_CPU_FAN_SPEED_ADDRS,
    FIRMWARE_GPU_TEMP_ADDRS, FIRMWARE_GPU_FAN_SPEED_ADDRS,
)
from . import ec
from . import config


# Global state (preserved from original for CLI compatibility)
_dump_pos = ''
_list_s = []


def ec_boost(value):
    """Option -b: enable or disable CoolerBoost."""
    cfg = config.load_config()
    cb = config.get_cooler_boost_config(cfg)
    am = config.get_address_map(cfg, cb.address_profile)

    if value == 'off':
        ec.ec_write_byte(am.cooler_boost, cb.off_value)
        _print_single_write(am.cooler_boost, cb.off_value)
    elif value == 'on':
        ec.ec_write_byte(am.cooler_boost, cb.on_value)
        _print_single_write(am.cooler_boost, cb.on_value)
    else:
        print('Error: Only ' + Text.ULINED + 'off' + Text.CLEAR + ' and '
              + Text.ULINED + 'on' + Text.CLEAR + ' are valid.')


class ECCheck(Action):
    """Option -c: show an EC dump."""
    def __call__(self, parser, namespace, values, option_string=None):
        print('\nEC dump ' + str(_dump_pos))
        print(Text.YELLOW + '       00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F' + Text.CLEAR)
        # EC_IO_FILE is a constant, not user input
        subprocess.run(['od', '-A', 'x', '-t', 'x1z', EC_IO_FILE])


def file_profile(value):
    """Option -f: show profile in EC update file."""
    list_cta = FIRMWARE_CPU_TEMP_ADDRS
    list_ct = []
    list_cfsa = FIRMWARE_CPU_FAN_SPEED_ADDRS
    list_cfs = []
    list_gta = FIRMWARE_GPU_TEMP_ADDRS
    list_gt = []
    list_gfsa = FIRMWARE_GPU_FAN_SPEED_ADDRS
    list_gfs = []

    with open(value, 'r+b') as file:
        j = 0
        for h in range(0, 37, 6):
            j += 1
            print('\nPotential profile ' + str(j) + ' dump')
            print(Text.CPU_GPU)
            print(Text.YELLOW + Text.FOUR_COLUMN % (
                  'Value', 'set @ address', 'Value', 'set @ address') + Text.CLEAR)
            for i in range(6):
                file.seek(list_cta[i + h])
                list_ct.append(int(file.read(1).hex(), 16))
                file.seek(list_gta[i + h])
                list_gt.append(int(file.read(1).hex(), 16))
                print(Text.FOUR_COLUMN % (
                      hex(list_ct[i + h]) + '(' + str(list_ct[i + h]) + '\u00b0C)',
                      hex(list_cta[i + h]) + '(byte' + str(list_cta[i + h]) + ')',
                      hex(list_gt[i + h]) + '(' + str(list_gt[i + h]) + '\u00b0C)',
                      hex(list_gta[i + h]) + '(byte' + str(list_gta[i + h]) + ')'))
            if h != 0:
                h += j - 1
            for i in range(7):
                file.seek(list_cfsa[i + h])
                list_cfs.append(int(file.read(1).hex(), 16))
                file.seek(list_gfsa[i + h])
                list_gfs.append(int(file.read(1).hex(), 16))
                if i == 0:
                    print('\r')
                print(Text.FOUR_COLUMN % (
                      hex(list_cfs[i + h]) + '(' + str(list_cfs[i + h]) + '%)',
                      hex(list_cfsa[i + h]) + '(byte' + str(list_cfsa[i + h]) + ')',
                      hex(list_gfs[i + h]) + '(' + str(list_gfs[i + h]) + '%)',
                      hex(list_gfsa[i + h]) + '(byte' + str(list_gfsa[i + h]) + ')'))


def ec_profile(value):
    """Option -p: show current profile in EC."""
    print('\nProfile dump ' + str(_dump_pos))
    cfg = config.load_config()
    am = config.get_address_map(cfg, value)

    # Read and display fan mode
    fm = ec.ec_read_byte(am.fan_mode)
    sfm = FAN_MODE_NAMES.get(fm, 'Unknown')
    print(Text.YELLOW + Text.THREE_COLUMN % (
          'Value', 'set @ address', 'Fan mode') + Text.CLEAR)
    print(Text.THREE_COLUMN % (
          hex(fm) + '(' + str(fm) + ')',
          hex(am.fan_mode) + '(byte' + str(am.fan_mode) + ')',
          sfm + '\n'))

    # Read and display battery threshold
    bct = ec.ec_read_byte(am.battery_threshold)
    print(Text.YELLOW + Text.THREE_COLUMN % (
          'Value', 'set @ address', 'Charging below - stop @') + Text.CLEAR)
    if bct in range(148, 229):
        print(Text.THREE_COLUMN % (
              hex(bct) + '(' + str(bct) + ')',
              hex(am.battery_threshold) + '(byte' + str(am.battery_threshold) + ')',
              str(bct - 138) + '% - ' + str(bct - 128) + '%\n'))
    else:
        print(Text.THREE_COLUMN % (
              hex(bct) + '(' + str(bct) + ')',
              hex(am.battery_threshold) + '(byte' + str(am.battery_threshold) + ')',
              'Nothing is set\n'))

    # Read and display temperatures
    cpu_temps = [ec.ec_read_byte(a) for a in am.cpu_temp]
    gpu_temps = [ec.ec_read_byte(a) for a in am.gpu_temp]
    print(Text.CPU_GPU)
    print(Text.YELLOW + Text.FOUR_COLUMN % (
          'Value', 'set @ address', 'Value', 'set @ address') + Text.CLEAR)
    for i in range(6):
        print(Text.FOUR_COLUMN % (
              hex(cpu_temps[i]) + '(' + str(cpu_temps[i]) + '\u00b0C)',
              hex(am.cpu_temp[i]) + '(byte' + str(am.cpu_temp[i]) + ')',
              hex(gpu_temps[i]) + '(' + str(gpu_temps[i]) + '\u00b0C)',
              hex(am.gpu_temp[i]) + '(byte' + str(am.gpu_temp[i]) + ')'))

    # Read and display fan speeds
    cpu_speeds = [ec.ec_read_byte(a) for a in am.cpu_fan_speed]
    gpu_speeds = [ec.ec_read_byte(a) for a in am.gpu_fan_speed]
    print('\r')
    for i in range(7):
        print(Text.FOUR_COLUMN % (
              hex(cpu_speeds[i]) + '(' + str(cpu_speeds[i]) + '%)',
              hex(am.cpu_fan_speed[i]) + '(byte' + str(am.cpu_fan_speed[i]) + ')',
              hex(gpu_speeds[i]) + '(' + str(gpu_speeds[i]) + '%)',
              hex(am.gpu_fan_speed[i]) + '(byte' + str(am.gpu_fan_speed[i]) + ')'))


def ec_read(value):
    """Option -r: show realtime CPU+GPU temp and fan speed from EC."""
    cfg = config.load_config()
    am = config.get_address_map(cfg, SECTION_ADDRESS_DEFAULT)

    print(Text.YELLOW + Text.CPU_GPU + Text.CLEAR)
    print(Text.TEMP_FS)
    try:
        if int(value) != 0:
            for i in range(0, int(value)):
                data = ec.ec_read_realtime(am)
                _print_realtime_row(data)
                time.sleep(2)
        else:
            while True:
                data = ec.ec_read_realtime(am)
                _print_realtime_row(data)
                print(Text.TEMP_FS_END + Text.CURSOR_UP + Text.CURSOR_UP)
                time.sleep(2)
        print(Text.TEMP_FS_END)
    except:
        print(Text.CURSOR_DOWN + Text.CURSOR_LEFT + Text.CURSOR_LEFT + Text.TEMP_FS_END)


def ec_set(value):
    """Option -s: set a single value into EC."""
    global _list_s
    _list_s.append(value)
    if len(_list_s) == 2:
        addr = int(_list_s[0], 16)
        val = int(_list_s[1])
        ec.ec_write_byte(addr, val)
        _print_single_write(addr, val)
        _list_s = []


def ec_battery_threshold(value):
    """Option -t: set the battery charging threshold."""
    cfg = config.load_config()
    am = config.get_address_map(cfg, SECTION_ADDRESS_DEFAULT)

    if int(value) in range(BATTERY_MIN, BATTERY_MAX + 1):
        ec_val = int(value) + BATTERY_OFFSET
        ec.ec_write_byte(am.battery_threshold, ec_val)
        _print_single_write(am.battery_threshold, ec_val)
    else:
        print('Error: Only ' + Text.ULINED + 'NUMBER' + Text.CLEAR + ' between '
              + Text.ULINED + '20' + Text.CLEAR + ' and '
              + Text.ULINED + '100' + Text.CLEAR + ' are valid.')


def ec_usb_backlight(value):
    """Option -u: set usb backlight level."""
    cfg = config.load_config()
    ub = config.get_usb_backlight_config(cfg)
    am = config.get_address_map(cfg, ub.address_profile)

    if value == 'off':
        ec.ec_write_byte(am.usb_backlight, ub.off_value)
        _print_single_write(am.usb_backlight, ub.off_value)
    elif value == 'half':
        ec.ec_write_byte(am.usb_backlight, ub.half_value)
        _print_single_write(am.usb_backlight, ub.half_value)
    elif value == 'full':
        ec.ec_write_byte(am.usb_backlight, ub.full_value)
        _print_single_write(am.usb_backlight, ub.full_value)
    else:
        print('Error: Only ' + Text.ULINED + 'off' + Text.CLEAR + ', '
              + Text.ULINED + 'half' + Text.CLEAR + ' and '
              + Text.ULINED + 'full' + Text.CLEAR + ' are valid.')


def ec_write(value):
    """Option -w: write config profile into EC."""
    global _dump_pos
    _dump_pos = 'after modification'
    print('\nWriting config to EC...')

    cfg = config.load_config()
    profile = config.get_profile(cfg, value)
    am = config.get_address_map(cfg, value)

    ec.ec_write_profile(am, profile)

    # Display results (matching original output format)
    sfm = FAN_MODE_NAMES.get(profile.fan_mode, 'Unknown')
    print(Text.YELLOW + Text.THREE_COLUMN % (
          'Value', 'set @ address', 'Fan mode') + Text.CLEAR)
    print(Text.THREE_COLUMN % (
          hex(profile.fan_mode) + '(' + str(profile.fan_mode) + ')',
          hex(am.fan_mode) + '(byte' + str(am.fan_mode) + ')',
          sfm + '\n'))

    if BATTERY_MIN <= profile.battery_threshold <= BATTERY_MAX:
        bct_ec = profile.battery_threshold + BATTERY_OFFSET
        print(Text.YELLOW + Text.THREE_COLUMN % (
              'Value', 'set @ address', 'Charging below - stop @') + Text.CLEAR)
        print(Text.THREE_COLUMN % (
              hex(bct_ec) + '(' + str(bct_ec) + ')',
              hex(am.battery_threshold) + '(byte' + str(am.battery_threshold) + ')',
              str(bct_ec - 138) + '% - ' + str(bct_ec - 128) + '%\n'))

    print(Text.CPU_GPU)
    print(Text.YELLOW + Text.FOUR_COLUMN % (
          'Value', 'set @ address', 'Value', 'set @ address') + Text.CLEAR)
    for i in range(6):
        print(Text.FOUR_COLUMN % (
              hex(profile.cpu_temps[i]) + '(' + str(profile.cpu_temps[i]) + '\u00b0C)',
              hex(am.cpu_temp[i]) + '(byte' + str(am.cpu_temp[i]) + ')',
              hex(profile.gpu_temps[i]) + '(' + str(profile.gpu_temps[i]) + '\u00b0C)',
              hex(am.gpu_temp[i]) + '(byte' + str(am.gpu_temp[i]) + ')'))

    print('\r')
    for i in range(7):
        print(Text.FOUR_COLUMN % (
              hex(profile.cpu_fan_speeds[i]) + '(' + str(profile.cpu_fan_speeds[i]) + '%)',
              hex(am.cpu_fan_speed[i]) + '(byte' + str(am.cpu_fan_speed[i]) + ')',
              hex(profile.gpu_fan_speeds[i]) + '(' + str(profile.gpu_fan_speeds[i]) + '%)',
              hex(am.gpu_fan_speed[i]) + '(byte' + str(am.gpu_fan_speed[i]) + ')'))


# Helper functions for formatted output

def _print_single_write(address, value):
    """Print formatted output for a single EC write."""
    print('\r')
    print(Text.YELLOW + Text.TWO_COLUMN % (
          'Value', 'set @ address') + Text.CLEAR)
    print(Text.TWO_COLUMN % (
          hex(value) + '(' + str(value) + ')',
          hex(address) + '(byte' + str(address) + ')'))


def _print_realtime_row(data):
    """Print a single row of realtime monitoring data."""
    print(Text.HEIGHT_COLUMN % (
          '\u2502 ' + str(data['cpu_temp']) + '\u00b0C',
          '\u2502 ' + str(data['cpu_fan_speed']) + '% ',
          str(data['cpu_fan_rpm']) + 'RPM',
          '\u2502',
          '\u2502 ' + str(data['gpu_temp']) + '\u00b0C',
          '\u2502 ' + str(data['gpu_fan_speed']) + '% ',
          str(data['gpu_fan_rpm']) + 'RPM',
          '\u2502'))


def main():
    """Main CLI entry point."""
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter, epilog=
'''
\u250c\u2500 TIPS \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
\u2502 Set your config in '/etc/isw.conf'.                                     \u2502
\u2502 Arguments order is relevant, -c and -p can be used twice. Example:      \u2502
\u2502 isw -cw ''' + Text.ULINED + '''SECTION_NAME''' + Text.CLEAR + ''' -c will show you EC dump before and after change.  \u2502
\u251c\u2500 SUPPORT \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524
\u2502 Help me support your laptop by providing following command output:      \u2502
\u2502 isw -cp MSI_ADDRESS_DEFAULT                                             \u2502
\u2502 via https://github.com/YoyPa/isw (open an issue).                       \u2502
\u2502 Make sure your dump is made before altering EC with isw, you can reset  \u2502
\u2502 your EC with a reboot or by changing power source.                      \u2502
\u251c\u2500 NAME \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524
\u2502 ISW is MSI at 180\u00b0                                                      \u2502
\u2502 It means Ice-Sealed Wyvern in opposition to MSI's 'unleash the dragon'  \u2502
\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
''')
    parser.add_argument('-b', type=ec_boost,
                        help='\u252c enable or disable CoolerBoost\n'
                             '\u2514 replace ' + Text.ULINED + 'B' + Text.CLEAR + ' with '
                             + Text.ULINED + 'off' + Text.CLEAR + ' OR '
                             + Text.ULINED + 'on' + Text.CLEAR + '\n ')
    parser.add_argument('-c', action=ECCheck, nargs=0,
                        help='\u2500 show an EC dump\n ')
    parser.add_argument('-f', '--file', type=file_profile,
                        help='\u252c show profile in EC update file\n'
                             '\u2514 replace ' + Text.ULINED + 'FILE' + Text.CLEAR + ' with '
                             + Text.ULINED + 'FILE_NAME' + Text.CLEAR + '\n ')
    parser.add_argument('-p', type=ec_profile,
                        help='\u252c show current profile in EC\n'
                             '\u2514 replace ' + Text.ULINED + 'P' + Text.CLEAR + ' with '
                             + Text.ULINED + 'SECTION_NAME' + Text.CLEAR + '\n ')
    parser.add_argument('-r', type=ec_read, nargs='?', const='0',
                        help='\u252c show realtime CPU+GPU temp and fan speed from EC\n'
                             '\u251c replace [R] with any [NUMBER] to perform a [NUMBER] of time(s)\n'
                             '\u2514 Assume [0] if given nothing = infinite loop\n ')
    parser.add_argument('-s', type=ec_set, nargs=2,
                        help='\u252c set a single value into EC\n'
                             '\u251c replace 1st ' + Text.ULINED + 'S' + Text.CLEAR + ' with '
                             + Text.ULINED + 'ADDRESS' + Text.CLEAR + ' in hexadecimal (0x00)\n'
                             '\u2514 replace 2nd ' + Text.ULINED + 'S' + Text.CLEAR + ' with '
                             + Text.ULINED + 'VALUE' + Text.CLEAR + '   in decimal     (00)\n ')
    parser.add_argument('-t', type=ec_battery_threshold,
                        help='\u252c set the battery charging threshold\n'
                             '\u2514 replace ' + Text.ULINED + 'T' + Text.CLEAR + ' with a '
                             + Text.ULINED + 'NUMBER' + Text.CLEAR + ' between '
                             + Text.ULINED + '20' + Text.CLEAR + ' and '
                             + Text.ULINED + '100' + Text.CLEAR + ' (\u066a)\n ')
    parser.add_argument('-u', '--usb', type=ec_usb_backlight,
                        help='\u252c set usb backlight level\n'
                             '\u2514 replace ' + Text.ULINED + 'USB' + Text.CLEAR + ' with '
                             + Text.ULINED + 'off' + Text.CLEAR + ', '
                             + Text.ULINED + 'half' + Text.CLEAR + ' OR '
                             + Text.ULINED + 'full' + Text.CLEAR + '\n ')
    parser.add_argument('-w', type=ec_write,
                        help='\u252c write into EC\n'
                             '\u2514 replace ' + Text.ULINED + 'W' + Text.CLEAR + ' with '
                             + Text.ULINED + 'SECTION_NAME' + Text.CLEAR + '')
    parser.add_argument('--gui', action='store_true',
                        help='launch the graphical interface')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        return

    args = parser.parse_args()

    if args.gui:
        from .gui.app import run_gui
        run_gui()
