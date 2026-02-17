"""Real-time temperature and fan speed monitoring widget."""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, GLib, Pango, PangoCairo
import collections

from ..constants import SECTION_ADDRESS_DEFAULT


class MonitorView(Gtk.Box):
    """Real-time monitoring view with current values and rolling graphs."""

    # Graph settings
    MAX_HISTORY = 60  # 2 minutes at 2-second intervals
    MARGIN_LEFT = 50
    MARGIN_RIGHT = 15
    MARGIN_TOP = 15
    MARGIN_BOTTOM = 30

    # Colors
    CPU_TEMP_COLOR = (0.96, 0.36, 0.26)   # Red
    GPU_TEMP_COLOR = (0.96, 0.68, 0.26)   # Orange
    CPU_FAN_COLOR = (0.26, 0.52, 0.96)    # Blue
    GPU_FAN_COLOR = (0.26, 0.80, 0.52)    # Green
    GRID_COLOR = (0.3, 0.3, 0.3)
    BG_COLOR = (0.15, 0.15, 0.15)
    TEXT_COLOR = (0.7, 0.7, 0.7)

    def __init__(self, ec_module, config_module):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)

        self._ec = ec_module
        self._config = config_module
        self._address_map = None
        self._timer_id = None

        # History buffers
        self.history = {
            'cpu_temp': collections.deque(maxlen=self.MAX_HISTORY),
            'gpu_temp': collections.deque(maxlen=self.MAX_HISTORY),
            'cpu_fan_speed': collections.deque(maxlen=self.MAX_HISTORY),
            'gpu_fan_speed': collections.deque(maxlen=self.MAX_HISTORY),
            'cpu_fan_rpm': collections.deque(maxlen=self.MAX_HISTORY),
            'gpu_fan_rpm': collections.deque(maxlen=self.MAX_HISTORY),
        }

        # Current values display
        values_grid = Gtk.Grid()
        values_grid.set_column_spacing(24)
        values_grid.set_row_spacing(8)
        values_grid.set_halign(Gtk.Align.CENTER)

        # Headers
        for col, text in enumerate(['', 'Temperature', 'Fan Speed', 'Fan RPM']):
            label = Gtk.Label(label=text)
            if col > 0:
                label.get_style_context().add_class('dim-label')
            values_grid.attach(label, col, 0, 1, 1)

        # CPU row
        cpu_label = Gtk.Label(label='CPU')
        cpu_label.set_markup('<b>CPU</b>')
        values_grid.attach(cpu_label, 0, 1, 1, 1)

        self.cpu_temp_label = Gtk.Label(label='--\u00b0C')
        values_grid.attach(self.cpu_temp_label, 1, 1, 1, 1)

        self.cpu_fan_label = Gtk.Label(label='--%')
        values_grid.attach(self.cpu_fan_label, 2, 1, 1, 1)

        self.cpu_rpm_label = Gtk.Label(label='-- RPM')
        values_grid.attach(self.cpu_rpm_label, 3, 1, 1, 1)

        # GPU row
        gpu_label = Gtk.Label()
        gpu_label.set_markup('<b>GPU</b>')
        values_grid.attach(gpu_label, 0, 2, 1, 1)

        self.gpu_temp_label = Gtk.Label(label='--\u00b0C')
        values_grid.attach(self.gpu_temp_label, 1, 2, 1, 1)

        self.gpu_fan_label = Gtk.Label(label='--%')
        values_grid.attach(self.gpu_fan_label, 2, 2, 1, 1)

        self.gpu_rpm_label = Gtk.Label(label='-- RPM')
        values_grid.attach(self.gpu_rpm_label, 3, 2, 1, 1)

        self.pack_start(values_grid, False, False, 0)

        # Temperature graph
        temp_frame = Gtk.Frame(label='Temperature (\u00b0C)')
        self.temp_graph = Gtk.DrawingArea()
        self.temp_graph.set_size_request(-1, 180)
        self.temp_graph.set_vexpand(True)
        self.temp_graph.connect('draw', self._draw_temp_graph)
        temp_frame.add(self.temp_graph)
        self.pack_start(temp_frame, True, True, 0)

        # Fan speed graph
        fan_frame = Gtk.Frame(label='Fan Speed (%)')
        self.fan_graph = Gtk.DrawingArea()
        self.fan_graph.set_size_request(-1, 180)
        self.fan_graph.set_vexpand(True)
        self.fan_graph.connect('draw', self._draw_fan_graph)
        fan_frame.add(self.fan_graph)
        self.pack_start(fan_frame, True, True, 0)

    def start_monitoring(self):
        """Start periodic EC reads."""
        if self._timer_id is not None:
            return

        try:
            cfg = self._config.load_config()
            self._address_map = self._config.get_address_map(cfg, SECTION_ADDRESS_DEFAULT)
        except Exception:
            self._address_map = None

        if self._address_map and self._ec.ec_is_available():
            self._read_once()
            self._timer_id = GLib.timeout_add_seconds(2, self._read_once)

    def stop_monitoring(self):
        """Stop periodic EC reads."""
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _read_once(self):
        """Read EC values once and update display."""
        if not self._address_map:
            return False

        try:
            data = self._ec.ec_read_realtime(self._address_map)
        except Exception:
            return True  # Keep timer running, retry next cycle

        # Update history
        for key in self.history:
            self.history[key].append(data[key])

        # Update labels
        self.cpu_temp_label.set_text(f"{data['cpu_temp']}\u00b0C")
        self.cpu_fan_label.set_text(f"{data['cpu_fan_speed']}%")
        self.cpu_rpm_label.set_text(f"{data['cpu_fan_rpm']} RPM")
        self.gpu_temp_label.set_text(f"{data['gpu_temp']}\u00b0C")
        self.gpu_fan_label.set_text(f"{data['gpu_fan_speed']}%")
        self.gpu_rpm_label.set_text(f"{data['gpu_fan_rpm']} RPM")

        # Trigger graph redraws
        self.temp_graph.queue_draw()
        self.fan_graph.queue_draw()

        return True  # Keep timer running

    def _draw_temp_graph(self, area, cr):
        """Draw the temperature history graph."""
        alloc = area.get_allocation()
        self._draw_graph(cr, alloc.width, alloc.height,
                         [('cpu_temp', self.CPU_TEMP_COLOR, 'CPU'),
                          ('gpu_temp', self.GPU_TEMP_COLOR, 'GPU')],
                         y_min=20, y_max=100, y_step=10, unit='\u00b0C')

    def _draw_fan_graph(self, area, cr):
        """Draw the fan speed history graph."""
        alloc = area.get_allocation()
        self._draw_graph(cr, alloc.width, alloc.height,
                         [('cpu_fan_speed', self.CPU_FAN_COLOR, 'CPU'),
                          ('gpu_fan_speed', self.GPU_FAN_COLOR, 'GPU')],
                         y_min=0, y_max=100, y_step=10, unit='%')

    def _draw_graph(self, cr, width, height, series, y_min, y_max, y_step, unit):
        """Generic graph drawing function."""
        px = self.MARGIN_LEFT
        py = self.MARGIN_TOP
        pw = width - self.MARGIN_LEFT - self.MARGIN_RIGHT
        ph = height - self.MARGIN_TOP - self.MARGIN_BOTTOM

        # Background
        cr.set_source_rgb(*self.BG_COLOR)
        cr.rectangle(px, py, pw, ph)
        cr.fill()

        # Grid
        cr.set_source_rgb(*self.GRID_COLOR)
        cr.set_line_width(0.5)

        y_range = y_max - y_min
        for val in range(y_min, y_max + 1, y_step):
            y = py + ph - ((val - y_min) / y_range) * ph
            cr.move_to(px, y)
            cr.line_to(px + pw, y)
            cr.stroke()
            # Label
            cr.set_source_rgb(*self.TEXT_COLOR)
            self._draw_text(cr, f'{val}{unit}', px - 5, y, anchor='right')
            cr.set_source_rgb(*self.GRID_COLOR)

        # Vertical time markers (every 30 seconds = 15 samples)
        for i in range(0, self.MAX_HISTORY + 1, 15):
            x = px + (i / self.MAX_HISTORY) * pw
            cr.move_to(x, py)
            cr.line_to(x, py + ph)
            cr.stroke()

        # Time axis label
        cr.set_source_rgb(*self.TEXT_COLOR)
        self._draw_text(cr, '2 min ago', px, py + ph + 5, anchor='left_top')
        self._draw_text(cr, 'now', px + pw, py + ph + 5, anchor='right_top')

        # Draw series
        for key, color, label in series:
            data = list(self.history[key])
            if not data:
                continue

            cr.set_source_rgba(*color, 0.9)
            cr.set_line_width(2)

            # Pad from the right (newest data on right)
            offset = self.MAX_HISTORY - len(data)
            for j, val in enumerate(data):
                x = px + ((offset + j) / self.MAX_HISTORY) * pw
                y = py + ph - ((val - y_min) / y_range) * ph
                y = max(py, min(py + ph, y))
                if j == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            cr.stroke()

        # Legend
        legend_x = px + pw - 10
        legend_y = py + 8
        for i, (key, color, label) in enumerate(series):
            x = legend_x - (len(series) - 1 - i) * 60
            cr.set_source_rgba(*color, 1.0)
            cr.rectangle(x - 40, legend_y - 4, 12, 12)
            cr.fill()
            cr.set_source_rgb(*self.TEXT_COLOR)
            self._draw_text(cr, label, x - 25, legend_y + 2, anchor='left')

    def _draw_text(self, cr, text, x, y, anchor='left'):
        """Draw text at position."""
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        desc = Pango.FontDescription.from_string('Sans 9')
        layout.set_font_description(desc)
        ink_rect, logical_rect = layout.get_pixel_extents()

        if anchor == 'right':
            x = x - logical_rect.width
            y = y - logical_rect.height / 2
        elif anchor == 'left_top':
            pass
        elif anchor == 'right_top':
            x = x - logical_rect.width
        elif anchor == 'center':
            x = x - logical_rect.width / 2
            y = y - logical_rect.height / 2
        elif anchor == 'left':
            y = y - logical_rect.height / 2

        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)
