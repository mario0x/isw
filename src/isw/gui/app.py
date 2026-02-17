"""Main GTK3 application for ISW fan control."""

import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib

import os

from .. import ec
from .. import config
from .fan_curve import FanCurveEditor
from .monitor import MonitorView
from .controls import ControlsView
from .profiles import ProfileSelector


CSS = b"""
.cpu-toggle {
    color: #4286f4;
}
.gpu-toggle {
    color: #f45c42;
}
.status-ok {
    color: #4caf50;
}
.status-error {
    color: #f44336;
}
.warning-bar {
    background: rgba(255, 200, 50, 0.15);
    padding: 8px 12px;
    border-radius: 6px;
}
.toast-bar {
    background: rgba(50, 50, 50, 0.95);
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    margin: 12px;
}
"""


class ISWWindow(Gtk.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app, title='ISW Fan Control',
                         default_width=920, default_height=680)

        self._current_profile = None
        self._toast_timeout_id = None

        # Main layout
        overlay = Gtk.Overlay()
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title('ISW Fan Control')
        self.set_titlebar(header)

        # Profile selector in header
        self.profile_selector = ProfileSelector(config)
        self.profile_selector.connect('profile-selected', self._on_profile_selected)
        header.pack_start(self.profile_selector)

        # Action buttons
        apply_button = Gtk.Button(label='Apply to EC')
        apply_button.get_style_context().add_class('suggested-action')
        apply_button.connect('clicked', self._on_apply)
        header.pack_end(apply_button)

        save_button = Gtk.Button(label='Save Config')
        save_button.connect('clicked', self._on_save)
        header.pack_end(save_button)

        # EC status bar
        if not ec.ec_is_available():
            status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            status_box.get_style_context().add_class('warning-bar')
            status_box.set_margin_start(12)
            status_box.set_margin_end(12)
            status_box.set_margin_top(6)

            icon = Gtk.Image.new_from_icon_name('dialog-warning', Gtk.IconSize.SMALL_TOOLBAR)
            status_box.pack_start(icon, False, False, 0)

            status_label = Gtk.Label(
                label='EC interface not available. Make sure ec_sys module is loaded '
                      'with write_support=1 and you are running as root.')
            status_label.set_line_wrap(True)
            status_box.pack_start(status_label, True, True, 0)

            main_box.pack_start(status_box, False, False, 0)

        # Stack with pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)

        # Fan Curves page
        curves_page = self._build_curves_page()
        self.stack.add_titled(curves_page, 'curves', 'Fan Curves')

        # Monitor page
        self.monitor_view = MonitorView(ec, config)
        self.stack.add_titled(self.monitor_view, 'monitor', 'Monitor')

        # Settings page
        settings_scroll = Gtk.ScrolledWindow()
        settings_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.controls_view = ControlsView(ec, config)
        self.controls_view.set_margin_start(80)
        self.controls_view.set_margin_end(80)
        self.controls_view.set_margin_top(12)
        self.controls_view.set_margin_bottom(12)
        settings_scroll.add(self.controls_view)
        self.stack.add_titled(settings_scroll, 'settings', 'Settings')

        # Stack switcher at top
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        switcher.set_margin_top(6)
        switcher.set_margin_bottom(6)
        main_box.pack_start(switcher, False, False, 0)

        # Separator
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                            False, False, 0)

        main_box.pack_start(self.stack, True, True, 0)

        overlay.add(main_box)

        # Toast revealer (bottom overlay)
        self._toast_revealer = Gtk.Revealer()
        self._toast_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._toast_revealer.set_transition_duration(200)
        self._toast_revealer.set_valign(Gtk.Align.END)
        self._toast_revealer.set_halign(Gtk.Align.CENTER)

        self._toast_label = Gtk.Label()
        self._toast_label.get_style_context().add_class('toast-bar')
        self._toast_revealer.add(self._toast_label)
        overlay.add_overlay(self._toast_revealer)

        self.add(overlay)

        # Track page switches for monitoring
        self.stack.connect('notify::visible-child', self._on_page_changed)

        self.show_all()

        # Load initial state
        self._load_initial_state()

    def _build_curves_page(self):
        """Build the fan curves editor page."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        # Info bar
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.set_margin_bottom(6)

        info_label = Gtk.Label(
            label='Drag points to adjust fan curves. '
                  'X-axis: temperature (\u00b0C), Y-axis: fan speed (%).')
        info_label.get_style_context().add_class('dim-label')
        info_label.set_halign(Gtk.Align.START)
        info_box.pack_start(info_label, True, True, 0)

        # Reset button
        reset_btn = Gtk.Button(label='Reset from EC')
        reset_btn.connect('clicked', self._on_reset_curves)
        info_box.pack_end(reset_btn, False, False, 0)

        box.pack_start(info_box, False, False, 0)

        # Fan curve editor
        self.fan_curve_editor = FanCurveEditor()
        self.fan_curve_editor.set_vexpand(True)
        self.fan_curve_editor.connect('curve-changed', self._on_curve_changed)
        box.pack_start(self.fan_curve_editor, True, True, 0)

        return box

    def _detect_profile(self, profile_names):
        """Try to auto-detect the correct profile for this machine.

        Reads the motherboard name from DMI (e.g. 'MS-16S3') and matches
        it against profile names (e.g. '16S3EMS1').
        Returns the matching profile name, or None.
        """
        try:
            board_name = open('/sys/class/dmi/id/board_name').read().strip()
        except (OSError, IOError):
            return None

        # Board name is like 'MS-16S3', profile is like '16S3EMS1'
        # Strip the 'MS-' prefix to get the board ID
        board_id = board_name.replace('MS-', '')

        for name in profile_names:
            if name.startswith(board_id):
                return name
        return None

    def _load_initial_state(self):
        """Load the first profile and EC state. Auto-detects the right profile."""
        try:
            cfg = config.load_config()
            names = config.get_profile_names(cfg)
            if names:
                detected = self._detect_profile(names)
                if detected:
                    self._load_profile(detected)
                    self._show_toast(f'Detected laptop profile: {detected}')
                else:
                    self._load_profile(names[0])
        except Exception as e:
            print(f'Warning: Could not load initial state: {e}')

        self.controls_view.load_from_ec()

    def _load_profile(self, name):
        """Load a profile into the UI."""
        try:
            cfg = config.load_config()
            profile = config.get_profile(cfg, name)
            self._current_profile = profile

            self.fan_curve_editor.set_profile(profile)
            self.controls_view.load_from_profile(profile)
            self.profile_selector.set_selected_name(name)
        except Exception as e:
            print(f'Error loading profile {name}: {e}')

    def _on_profile_selected(self, selector, name):
        """Handle profile selection change."""
        self._load_profile(name)

    def _on_apply(self, button):
        """Apply current curve values to EC."""
        if not self._current_profile:
            return

        try:
            cfg = config.load_config()
            am = config.get_address_map(cfg, self._current_profile.name)

            # Update profile with current editor values
            cpu_temps, cpu_speeds, gpu_temps, gpu_speeds = self.fan_curve_editor.get_values()
            self._current_profile.cpu_temps = cpu_temps
            self._current_profile.cpu_fan_speeds = cpu_speeds
            self._current_profile.gpu_temps = gpu_temps
            self._current_profile.gpu_fan_speeds = gpu_speeds
            self._current_profile.fan_mode = self.controls_view.get_fan_mode()
            self._current_profile.battery_threshold = self.controls_view.get_battery_threshold()

            ec.ec_write_profile(am, self._current_profile)
            self._show_toast('Profile applied to EC')

        except Exception as e:
            self._show_toast(f'Error: {e}', timeout=4)

    def _on_save(self, button):
        """Save current curve values to config file."""
        if not self._current_profile:
            return

        try:
            cpu_temps, cpu_speeds, gpu_temps, gpu_speeds = self.fan_curve_editor.get_values()
            self._current_profile.cpu_temps = cpu_temps
            self._current_profile.cpu_fan_speeds = cpu_speeds
            self._current_profile.gpu_temps = gpu_temps
            self._current_profile.gpu_fan_speeds = gpu_speeds
            self._current_profile.fan_mode = self.controls_view.get_fan_mode()
            self._current_profile.battery_threshold = self.controls_view.get_battery_threshold()

            config.save_profile(self._current_profile)
            self._show_toast('Profile saved to /etc/isw.conf')

        except Exception as e:
            self._show_toast(f'Error saving: {e}', timeout=4)

    def _on_reset_curves(self, button):
        """Reset fan curves from current EC values."""
        if not self._current_profile:
            return

        try:
            cfg = config.load_config()
            am = config.get_address_map(cfg, self._current_profile.name)
            ec_data = ec.ec_read_profile(am)

            self.fan_curve_editor.cpu_temps = ec_data['cpu_temps']
            self.fan_curve_editor.cpu_speeds = ec_data['cpu_fan_speeds']
            self.fan_curve_editor.gpu_temps = ec_data['gpu_temps']
            self.fan_curve_editor.gpu_speeds = ec_data['gpu_fan_speeds']
            self.fan_curve_editor.drawing_area.queue_draw()

            self._show_toast('Curves reset from EC')

        except Exception as e:
            self._show_toast(f'Error reading EC: {e}', timeout=4)

    def _on_curve_changed(self, editor):
        """Handle fan curve point drag completion."""
        pass  # Values are live in the editor, applied on "Apply" click

    def _on_page_changed(self, stack, pspec):
        """Handle page switches - start/stop monitoring."""
        visible = stack.get_visible_child()
        if visible == self.monitor_view:
            self.monitor_view.start_monitoring()
        else:
            self.monitor_view.stop_monitoring()

    def _show_toast(self, text, timeout=2):
        """Show a brief toast notification at the bottom of the window."""
        if self._toast_timeout_id:
            GLib.source_remove(self._toast_timeout_id)
            self._toast_timeout_id = None

        self._toast_label.set_text(text)
        self._toast_revealer.set_reveal_child(True)

        def hide_toast():
            self._toast_revealer.set_reveal_child(False)
            self._toast_timeout_id = None
            return False

        self._toast_timeout_id = GLib.timeout_add(timeout * 1000, hide_toast)


class ISWApplication(Gtk.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(application_id='com.github.yoypa.isw',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ISWWindow(self)
        win.present()


def run_gui():
    """Entry point for the GUI."""
    app = ISWApplication()
    app.run(sys.argv)
