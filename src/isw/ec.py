"""Embedded Controller (EC) hardware interface.

Provides low-level read/write access to the MSI EC via
/sys/kernel/debug/ec/ec0/io (the ec_sys kernel module interface).
"""

import os
from .constants import EC_IO_FILE, RPM_DIVISOR


def ec_is_available():
    """Check if the EC interface file exists and is accessible."""
    return os.path.exists(EC_IO_FILE)


def ec_read_byte(address):
    """Read a single byte from the EC at the given address.

    Returns the value as an integer (0-255).
    """
    with open(EC_IO_FILE, 'rb') as f:
        f.seek(address)
        return int(f.read(1).hex(), 16)


def ec_read_word(address):
    """Read two bytes from the EC at the given address.

    Returns the value as an integer (0-65535).
    Used for RPM readings which are 2-byte values.
    """
    with open(EC_IO_FILE, 'rb') as f:
        f.seek(address)
        return int(f.read(2).hex(), 16)


def ec_write_byte(address, value):
    """Write a single byte to the EC at the given address."""
    with open(EC_IO_FILE, 'r+b') as f:
        f.seek(address)
        f.write(bytes((value,)))


def ec_read_realtime(address_map):
    """Read real-time CPU and GPU temperatures, fan speeds, and RPMs.

    Args:
        address_map: An AddressMap with realtime_* address fields.

    Returns:
        dict with keys: cpu_temp, cpu_fan_speed, cpu_fan_rpm,
                        gpu_temp, gpu_fan_speed, gpu_fan_rpm
    """
    with open(EC_IO_FILE, 'rb') as f:
        f.seek(address_map.realtime_cpu_temp)
        cpu_temp = int(f.read(1).hex(), 16)

        f.seek(address_map.realtime_cpu_fan_speed)
        cpu_fan_speed = int(f.read(1).hex(), 16)

        f.seek(address_map.realtime_cpu_fan_rpm)
        cpu_fan_rpm_raw = int(f.read(2).hex(), 16)

        f.seek(address_map.realtime_gpu_temp)
        gpu_temp = int(f.read(1).hex(), 16)

        f.seek(address_map.realtime_gpu_fan_speed)
        gpu_fan_speed = int(f.read(1).hex(), 16)

        f.seek(address_map.realtime_gpu_fan_rpm)
        gpu_fan_rpm_raw = int(f.read(2).hex(), 16)

    cpu_fan_rpm = RPM_DIVISOR // cpu_fan_rpm_raw if cpu_fan_rpm_raw != 0 else 0
    gpu_fan_rpm = RPM_DIVISOR // gpu_fan_rpm_raw if gpu_fan_rpm_raw != 0 else 0

    return {
        'cpu_temp': cpu_temp,
        'cpu_fan_speed': cpu_fan_speed,
        'cpu_fan_rpm': cpu_fan_rpm,
        'gpu_temp': gpu_temp,
        'gpu_fan_speed': gpu_fan_speed,
        'gpu_fan_rpm': gpu_fan_rpm,
    }


def ec_read_profile(address_map):
    """Read the current fan profile values from the EC.

    Returns:
        dict with keys: fan_mode, battery_threshold,
                        cpu_temps (list[6]), cpu_fan_speeds (list[7]),
                        gpu_temps (list[6]), gpu_fan_speeds (list[7])
    """
    fan_mode = ec_read_byte(address_map.fan_mode)
    battery_raw = ec_read_byte(address_map.battery_threshold)

    cpu_temps = [ec_read_byte(a) for a in address_map.cpu_temp]
    cpu_fan_speeds = [ec_read_byte(a) for a in address_map.cpu_fan_speed]
    gpu_temps = [ec_read_byte(a) for a in address_map.gpu_temp]
    gpu_fan_speeds = [ec_read_byte(a) for a in address_map.gpu_fan_speed]

    return {
        'fan_mode': fan_mode,
        'battery_threshold_raw': battery_raw,
        'cpu_temps': cpu_temps,
        'cpu_fan_speeds': cpu_fan_speeds,
        'gpu_temps': gpu_temps,
        'gpu_fan_speeds': gpu_fan_speeds,
    }


def ec_write_profile(address_map, profile):
    """Write a full fan profile to the EC.

    Args:
        address_map: AddressMap with EC register addresses.
        profile: Profile dataclass with fan curve values.
    """
    from .constants import BATTERY_OFFSET, BATTERY_MIN, BATTERY_MAX

    with open(EC_IO_FILE, 'r+b') as f:
        # Fan mode
        f.seek(address_map.fan_mode)
        f.write(bytes((profile.fan_mode,)))

        # Battery threshold (only if in valid range)
        if BATTERY_MIN <= profile.battery_threshold <= BATTERY_MAX:
            f.seek(address_map.battery_threshold)
            f.write(bytes((profile.battery_threshold + BATTERY_OFFSET,)))

        # CPU temperatures
        for addr, val in zip(address_map.cpu_temp, profile.cpu_temps):
            f.seek(addr)
            f.write(bytes((val,)))

        # CPU fan speeds
        for addr, val in zip(address_map.cpu_fan_speed, profile.cpu_fan_speeds):
            f.seek(addr)
            f.write(bytes((val,)))

        # GPU temperatures
        for addr, val in zip(address_map.gpu_temp, profile.gpu_temps):
            f.seek(addr)
            f.write(bytes((val,)))

        # GPU fan speeds
        for addr, val in zip(address_map.gpu_fan_speed, profile.gpu_fan_speeds):
            f.seek(addr)
            f.write(bytes((val,)))


def ec_dump():
    """Read the entire EC memory (256 bytes) and return as bytes."""
    with open(EC_IO_FILE, 'rb') as f:
        return f.read(256)


def ec_read_file_byte(filepath, address):
    """Read a single byte from a firmware file at the given address."""
    with open(filepath, 'rb') as f:
        f.seek(address)
        return int(f.read(1).hex(), 16)
