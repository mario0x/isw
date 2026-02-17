"""Profile selector and management widget."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject


class ProfileSelector(Gtk.Box):
    """Dropdown for selecting laptop profiles from isw.conf."""

    __gsignals__ = {
        'profile-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, config_module):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._config = config_module
        self._loading = False
        self._profile_names = []

        label = Gtk.Label(label='Profile:')
        label.get_style_context().add_class('dim-label')
        self.pack_start(label, False, False, 0)

        self.combo = Gtk.ComboBoxText()
        self.combo.connect('changed', self._on_selected)
        self.pack_start(self.combo, False, False, 0)

        self.refresh()

    def refresh(self):
        """Reload profile list from config."""
        self._loading = True
        try:
            cfg = self._config.load_config()
            self._profile_names = self._config.get_profile_names(cfg)
        except Exception:
            self._profile_names = []

        self.combo.remove_all()
        for name in self._profile_names:
            self.combo.append_text(name)
        self._loading = False

    def get_selected_name(self):
        """Return the currently selected profile name."""
        idx = self.combo.get_active()
        if 0 <= idx < len(self._profile_names):
            return self._profile_names[idx]
        return None

    def set_selected_name(self, name):
        """Select a profile by name."""
        self._loading = True
        try:
            idx = self._profile_names.index(name)
            self.combo.set_active(idx)
        except ValueError:
            pass
        self._loading = False

    def _on_selected(self, combo):
        if self._loading:
            return
        name = self.get_selected_name()
        if name:
            self.emit('profile-selected', name)
