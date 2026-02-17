"""Settings and controls panel - CoolerBoost, battery, USB backlight, fan mode."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

from ..constants import (
    FAN_MODE_AUTO, FAN_MODE_BASIC, FAN_MODE_ADVANCED,
    BATTERY_OFFSET, BATTERY_MIN, BATTERY_MAX,
    SECTION_ADDRESS_DEFAULT,
)


def _make_row(label_text, subtitle_text, widget):
    """Create a horizontal row with label/subtitle on the left and widget on the right."""
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.set_margin_start(12)
    row.set_margin_end(12)
    row.set_margin_top(6)
    row.set_margin_bottom(6)

    label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    label_box.set_valign(Gtk.Align.CENTER)

    title = Gtk.Label(label=label_text)
    title.set_halign(Gtk.Align.START)
    label_box.pack_start(title, False, False, 0)

    if subtitle_text:
        subtitle = Gtk.Label(label=subtitle_text)
        subtitle.set_halign(Gtk.Align.START)
        subtitle.get_style_context().add_class('dim-label')
        attrs = subtitle.get_attributes()
        label_box.pack_start(subtitle, False, False, 0)

    row.pack_start(label_box, True, True, 0)

    widget.set_valign(Gtk.Align.CENTER)
    row.pack_end(widget, False, False, 0)

    return row


class ControlsView(Gtk.Box):
    """Settings page with hardware controls."""

    __gsignals__ = {
        'profile-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, ec_module, config_module):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self._ec = ec_module
        self._config = config_module
        self._address_map = None
        self._loading = False  # Prevent signal loops during load

        # Fan Mode group
        fan_frame = Gtk.Frame()
        fan_frame.set_label_widget(self._make_frame_label('Fan Mode'))
        fan_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.fan_mode_combo = Gtk.ComboBoxText()
        for name in ['Advanced', 'Basic', 'Auto']:
            self.fan_mode_combo.append_text(name)
        self.fan_mode_combo.set_active(0)
        self.fan_mode_combo.connect('changed', self._on_fan_mode_changed)
        fan_box.pack_start(
            _make_row('Fan Mode', 'Controls how the EC manages fan behavior',
                       self.fan_mode_combo),
            False, False, 0)

        fan_frame.add(fan_box)
        self.pack_start(fan_frame, False, False, 0)

        # CoolerBoost group
        boost_frame = Gtk.Frame()
        boost_frame.set_label_widget(self._make_frame_label('CoolerBoost'))
        boost_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.cooler_boost_switch = Gtk.Switch()
        self.cooler_boost_switch.connect('notify::active', self._on_cooler_boost_changed)
        boost_box.pack_start(
            _make_row('CoolerBoost', 'Maximum fan speed override',
                       self.cooler_boost_switch),
            False, False, 0)

        boost_frame.add(boost_box)
        self.pack_start(boost_frame, False, False, 0)

        # Battery group
        battery_frame = Gtk.Frame()
        battery_frame.set_label_widget(self._make_frame_label('Battery'))
        battery_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        adj = Gtk.Adjustment(value=100, lower=BATTERY_MIN, upper=BATTERY_MAX,
                             step_increment=5, page_increment=10)
        self.battery_spin = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
        self.battery_spin.connect('value-changed', self._on_battery_changed)
        battery_box.pack_start(
            _make_row('Charging Threshold', 'Stop charging at this percentage',
                       self.battery_spin),
            False, False, 0)

        battery_frame.add(battery_box)
        self.pack_start(battery_frame, False, False, 0)

        # USB Backlight group
        usb_frame = Gtk.Frame()
        usb_frame.set_label_widget(self._make_frame_label('USB Backlight'))
        usb_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.usb_combo = Gtk.ComboBoxText()
        for name in ['Off', 'Half', 'Full']:
            self.usb_combo.append_text(name)
        self.usb_combo.set_active(0)
        self.usb_combo.connect('changed', self._on_usb_changed)
        usb_box.pack_start(
            _make_row('USB Backlight Level', 'Keyboard backlight brightness',
                       self.usb_combo),
            False, False, 0)

        usb_frame.add(usb_box)
        self.pack_start(usb_frame, False, False, 0)

    def _make_frame_label(self, text):
        """Create a bold label for frame titles."""
        label = Gtk.Label()
        label.set_markup(f'<b>{text}</b>')
        return label

    def load_from_ec(self):
        """Read current values from EC and populate controls."""
        self._loading = True
        try:
            cfg = self._config.load_config()
            self._address_map = self._config.get_address_map(cfg, SECTION_ADDRESS_DEFAULT)

            if not self._ec.ec_is_available():
                return

            # Fan mode
            fm = self._ec.ec_read_byte(self._address_map.fan_mode)
            if fm == FAN_MODE_ADVANCED:
                self.fan_mode_combo.set_active(0)
            elif fm == FAN_MODE_BASIC:
                self.fan_mode_combo.set_active(1)
            elif fm == FAN_MODE_AUTO:
                self.fan_mode_combo.set_active(2)

            # CoolerBoost
            cb = self._ec.ec_read_byte(self._address_map.cooler_boost)
            self.cooler_boost_switch.set_active(cb >= 128)

            # Battery threshold
            bct = self._ec.ec_read_byte(self._address_map.battery_threshold)
            if 148 <= bct <= 228:
                self.battery_spin.set_value(bct - BATTERY_OFFSET)

            # USB backlight
            ub = self._ec.ec_read_byte(self._address_map.usb_backlight)
            cfg_ub = self._config.get_usb_backlight_config(cfg)
            if ub == cfg_ub.off_value:
                self.usb_combo.set_active(0)
            elif ub == cfg_ub.half_value:
                self.usb_combo.set_active(1)
            elif ub == cfg_ub.full_value:
                self.usb_combo.set_active(2)

        except Exception as e:
            print(f'Warning: Could not read EC values: {e}')
        finally:
            self._loading = False

    def load_from_profile(self, profile):
        """Set control values from a profile (without writing to EC)."""
        self._loading = True
        try:
            if profile.fan_mode == FAN_MODE_ADVANCED:
                self.fan_mode_combo.set_active(0)
            elif profile.fan_mode == FAN_MODE_BASIC:
                self.fan_mode_combo.set_active(1)
            elif profile.fan_mode == FAN_MODE_AUTO:
                self.fan_mode_combo.set_active(2)

            self.battery_spin.set_value(profile.battery_threshold)
        finally:
            self._loading = False

    def get_fan_mode(self):
        """Return the currently selected fan mode value."""
        idx = self.fan_mode_combo.get_active()
        return [FAN_MODE_ADVANCED, FAN_MODE_BASIC, FAN_MODE_AUTO][idx]

    def get_battery_threshold(self):
        """Return the current battery threshold value."""
        return int(self.battery_spin.get_value())

    def _on_fan_mode_changed(self, combo):
        if self._loading or not self._address_map:
            return
        mode = self.get_fan_mode()
        try:
            self._ec.ec_write_byte(self._address_map.fan_mode, mode)
        except Exception as e:
            print(f'Error writing fan mode: {e}')
        self.emit('profile-changed')

    def _on_cooler_boost_changed(self, switch, pspec):
        if self._loading or not self._address_map:
            return
        try:
            cfg = self._config.load_config()
            cb = self._config.get_cooler_boost_config(cfg)
            value = cb.on_value if switch.get_active() else cb.off_value
            self._ec.ec_write_byte(self._address_map.cooler_boost, value)
        except Exception as e:
            print(f'Error writing cooler boost: {e}')

    def _on_battery_changed(self, spin):
        if self._loading or not self._address_map:
            return
        value = int(spin.get_value())
        if BATTERY_MIN <= value <= BATTERY_MAX:
            try:
                self._ec.ec_write_byte(self._address_map.battery_threshold,
                                       value + BATTERY_OFFSET)
            except Exception as e:
                print(f'Error writing battery threshold: {e}')
        self.emit('profile-changed')

    def _on_usb_changed(self, combo):
        if self._loading or not self._address_map:
            return
        try:
            cfg = self._config.load_config()
            ub = self._config.get_usb_backlight_config(cfg)
            values = [ub.off_value, ub.half_value, ub.full_value]
            idx = combo.get_active()
            self._ec.ec_write_byte(self._address_map.usb_backlight, values[idx])
        except Exception as e:
            print(f'Error writing USB backlight: {e}')
