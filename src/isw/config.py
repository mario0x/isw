"""Configuration file parsing and profile management.

Handles reading/writing /etc/isw.conf and converting between
INI sections and structured Profile/AddressMap objects.
"""

import configparser
from dataclasses import dataclass, field
from typing import List, Optional

from .constants import (
    CFG_FILE, NUM_TEMP_THRESHOLDS, NUM_FAN_SPEEDS,
    NON_PROFILE_SECTIONS, SECTION_ADDRESS_DEFAULT,
    SECTION_COOLER_BOOST, SECTION_USB_BACKLIGHT,
)


@dataclass
class AddressMap:
    """EC register addresses for a given address profile."""
    fan_mode: int = 0
    cooler_boost: int = 0
    usb_backlight: int = 0
    battery_threshold: int = 0
    cpu_temp: List[int] = field(default_factory=list)      # 6 addresses
    cpu_fan_speed: List[int] = field(default_factory=list)  # 7 addresses
    gpu_temp: List[int] = field(default_factory=list)       # 6 addresses
    gpu_fan_speed: List[int] = field(default_factory=list)  # 7 addresses
    # Realtime monitoring addresses
    realtime_cpu_temp: int = 0
    realtime_cpu_fan_speed: int = 0
    realtime_cpu_fan_rpm: int = 0
    realtime_gpu_temp: int = 0
    realtime_gpu_fan_speed: int = 0
    realtime_gpu_fan_rpm: int = 0


@dataclass
class Profile:
    """A laptop fan profile with temperature thresholds and fan speeds."""
    name: str = ''
    comment: str = ''
    address_profile: str = SECTION_ADDRESS_DEFAULT
    fan_mode: int = 140
    battery_threshold: int = 100
    cpu_temps: List[int] = field(default_factory=list)       # 6 values
    cpu_fan_speeds: List[int] = field(default_factory=list)  # 7 values
    gpu_temps: List[int] = field(default_factory=list)       # 6 values
    gpu_fan_speeds: List[int] = field(default_factory=list)  # 7 values


@dataclass
class CoolerBoostConfig:
    """CoolerBoost on/off values."""
    address_profile: str = SECTION_ADDRESS_DEFAULT
    off_value: int = 0
    on_value: int = 128


@dataclass
class UsbBacklightConfig:
    """USB backlight level values."""
    address_profile: str = SECTION_ADDRESS_DEFAULT
    off_value: int = 128
    half_value: int = 193
    full_value: int = 129


def load_config(path=None):
    """Load and parse the ISW configuration file.

    Returns a ConfigParser instance.
    """
    if path is None:
        path = CFG_FILE
    cfgp = configparser.ConfigParser()
    with open(path) as f:
        cfgp.read_file(f)
    return cfgp


def get_profile_names(config):
    """Return a list of laptop profile section names (excluding special sections)."""
    return [s for s in config.sections() if s not in NON_PROFILE_SECTIONS]


def get_address_map(config, profile_name=None):
    """Parse EC addresses from an address profile section.

    If profile_name is given, looks up its address_profile first.
    Otherwise uses MSI_ADDRESS_DEFAULT directly.
    """
    if profile_name and profile_name not in NON_PROFILE_SECTIONS:
        ap_name = config.get(profile_name, 'address_profile')
    else:
        ap_name = profile_name or SECTION_ADDRESS_DEFAULT

    am = AddressMap()
    am.fan_mode = int(config.get(ap_name, 'fan_mode_address'), 16)
    am.cooler_boost = int(config.get(ap_name, 'cooler_boost_address'), 16)
    am.usb_backlight = int(config.get(ap_name, 'usb_backlight_address'), 16)
    am.battery_threshold = int(config.get(ap_name, 'battery_charging_threshold_address'), 16)

    am.cpu_temp = [int(config.get(ap_name, f'cpu_temp_address_{i}'), 16)
                   for i in range(NUM_TEMP_THRESHOLDS)]
    am.cpu_fan_speed = [int(config.get(ap_name, f'cpu_fan_speed_address_{i}'), 16)
                        for i in range(NUM_FAN_SPEEDS)]
    am.gpu_temp = [int(config.get(ap_name, f'gpu_temp_address_{i}'), 16)
                   for i in range(NUM_TEMP_THRESHOLDS)]
    am.gpu_fan_speed = [int(config.get(ap_name, f'gpu_fan_speed_address_{i}'), 16)
                        for i in range(NUM_FAN_SPEEDS)]

    am.realtime_cpu_temp = int(config.get(ap_name, 'realtime_cpu_temp_address'), 16)
    am.realtime_cpu_fan_speed = int(config.get(ap_name, 'realtime_cpu_fan_speed_address'), 16)
    am.realtime_cpu_fan_rpm = int(config.get(ap_name, 'realtime_cpu_fan_rpm_address'), 16)
    am.realtime_gpu_temp = int(config.get(ap_name, 'realtime_gpu_temp_address'), 16)
    am.realtime_gpu_fan_speed = int(config.get(ap_name, 'realtime_gpu_fan_speed_address'), 16)
    am.realtime_gpu_fan_rpm = int(config.get(ap_name, 'realtime_gpu_fan_rpm_address'), 16)

    return am


def get_profile(config, name):
    """Parse a laptop profile section into a Profile object."""
    p = Profile()
    p.name = name
    p.address_profile = config.get(name, 'address_profile')
    p.fan_mode = int(config.get(name, 'fan_mode'))
    p.battery_threshold = int(config.get(name, 'battery_charging_threshold'))
    p.cpu_temps = [int(config.get(name, f'cpu_temp_{i}'))
                   for i in range(NUM_TEMP_THRESHOLDS)]
    p.cpu_fan_speeds = [int(config.get(name, f'cpu_fan_speed_{i}'))
                        for i in range(NUM_FAN_SPEEDS)]
    p.gpu_temps = [int(config.get(name, f'gpu_temp_{i}'))
                   for i in range(NUM_TEMP_THRESHOLDS)]
    p.gpu_fan_speeds = [int(config.get(name, f'gpu_fan_speed_{i}'))
                        for i in range(NUM_FAN_SPEEDS)]
    return p


def get_cooler_boost_config(config):
    """Parse the COOLER_BOOST section."""
    cb = CoolerBoostConfig()
    cb.address_profile = config.get(SECTION_COOLER_BOOST, 'address_profile')
    cb.off_value = int(config.get(SECTION_COOLER_BOOST, 'cooler_boost_off'))
    cb.on_value = int(config.get(SECTION_COOLER_BOOST, 'cooler_boost_on'))
    return cb


def get_usb_backlight_config(config):
    """Parse the USB_BACKLIGHT section."""
    ub = UsbBacklightConfig()
    ub.address_profile = config.get(SECTION_USB_BACKLIGHT, 'address_profile')
    ub.off_value = int(config.get(SECTION_USB_BACKLIGHT, 'usb_backlight_off'))
    ub.half_value = int(config.get(SECTION_USB_BACKLIGHT, 'usb_backlight_half'))
    ub.full_value = int(config.get(SECTION_USB_BACKLIGHT, 'usb_backlight_full'))
    return ub


def save_profile(profile, path=None):
    """Write a modified profile back to the config file.

    Reads the existing config, updates the profile section, and writes back.
    Preserves all other sections and comments structure.
    """
    if path is None:
        path = CFG_FILE

    config = load_config(path)

    name = profile.name
    if not config.has_section(name):
        config.add_section(name)

    config.set(name, 'address_profile', profile.address_profile)
    config.set(name, 'fan_mode', str(profile.fan_mode))
    config.set(name, 'battery_charging_threshold', str(profile.battery_threshold))

    for i in range(NUM_TEMP_THRESHOLDS):
        config.set(name, f'cpu_temp_{i}', str(profile.cpu_temps[i]))
    for i in range(NUM_FAN_SPEEDS):
        config.set(name, f'cpu_fan_speed_{i}', str(profile.cpu_fan_speeds[i]))
    for i in range(NUM_TEMP_THRESHOLDS):
        config.set(name, f'gpu_temp_{i}', str(profile.gpu_temps[i]))
    for i in range(NUM_FAN_SPEEDS):
        config.set(name, f'gpu_fan_speed_{i}', str(profile.gpu_fan_speeds[i]))

    with open(path, 'w') as f:
        config.write(f)
