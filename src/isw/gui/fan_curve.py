"""Interactive fan curve editor widget using Cairo on Gtk.DrawingArea."""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GObject, Pango, PangoCairo
import math


class FanCurveEditor(Gtk.Box):
    """A widget for visually editing fan temperature/speed curves.

    Displays CPU and GPU fan curves on a temperature (X) vs fan speed (Y) grid.
    Points can be dragged to adjust values. Emits 'curve-changed' when modified.
    """

    __gsignals__ = {
        'curve-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    # Layout constants
    MARGIN_LEFT = 55
    MARGIN_RIGHT = 20
    MARGIN_TOP = 20
    MARGIN_BOTTOM = 40
    POINT_RADIUS = 7
    GRAB_RADIUS = 14

    # Colors
    CPU_COLOR = (0.26, 0.52, 0.96)    # Blue
    GPU_COLOR = (0.96, 0.36, 0.26)    # Red/Orange
    GRID_COLOR = (0.3, 0.3, 0.3)
    BG_COLOR = (0.15, 0.15, 0.15)
    TEXT_COLOR = (0.7, 0.7, 0.7)

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Fan curve data: 6 temp thresholds, 7 fan speeds
        # Speeds: speed[0] is below temp[0], speed[i] is at/above temp[i-1]
        self.cpu_temps = [55, 61, 67, 73, 79, 85]
        self.cpu_speeds = [30, 45, 55, 65, 70, 75, 80]
        self.gpu_temps = [55, 61, 67, 73, 79, 85]
        self.gpu_speeds = [0, 50, 60, 70, 75, 75, 80]

        self.show_cpu = True
        self.show_gpu = True
        self._dragging = None  # ('cpu'/'gpu', index) or None

        # Drawing area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(600, 350)
        self.drawing_area.set_vexpand(True)
        self.drawing_area.set_hexpand(True)
        self.drawing_area.connect('draw', self._draw)

        # Enable events for mouse interaction
        self.drawing_area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.drawing_area.connect('button-press-event', self._on_button_press)
        self.drawing_area.connect('button-release-event', self._on_button_release)
        self.drawing_area.connect('motion-notify-event', self._on_motion)

        self.pack_start(self.drawing_area, True, True, 0)

        # Toggle buttons row
        toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toggle_box.set_halign(Gtk.Align.CENTER)

        self.cpu_toggle = Gtk.ToggleButton(label='CPU')
        self.cpu_toggle.set_active(True)
        self.cpu_toggle.get_style_context().add_class('cpu-toggle')
        self.cpu_toggle.connect('toggled', self._on_cpu_toggled)

        self.gpu_toggle = Gtk.ToggleButton(label='GPU')
        self.gpu_toggle.set_active(True)
        self.gpu_toggle.get_style_context().add_class('gpu-toggle')
        self.gpu_toggle.connect('toggled', self._on_gpu_toggled)

        toggle_box.pack_start(self.cpu_toggle, False, False, 0)
        toggle_box.pack_start(self.gpu_toggle, False, False, 0)
        self.pack_start(toggle_box, False, False, 0)

    def set_profile(self, profile):
        """Load values from a Profile object."""
        self.cpu_temps = list(profile.cpu_temps)
        self.cpu_speeds = list(profile.cpu_fan_speeds)
        self.gpu_temps = list(profile.gpu_temps)
        self.gpu_speeds = list(profile.gpu_fan_speeds)
        self.drawing_area.queue_draw()

    def get_values(self):
        """Return current curve values as (cpu_temps, cpu_speeds, gpu_temps, gpu_speeds)."""
        return (list(self.cpu_temps), list(self.cpu_speeds),
                list(self.gpu_temps), list(self.gpu_speeds))

    def _get_plot_area(self):
        """Return (x, y, width, height) of the plot area."""
        alloc = self.drawing_area.get_allocation()
        w = alloc.width
        h = alloc.height
        return (self.MARGIN_LEFT, self.MARGIN_TOP,
                w - self.MARGIN_LEFT - self.MARGIN_RIGHT,
                h - self.MARGIN_TOP - self.MARGIN_BOTTOM)

    def _temp_to_x(self, temp):
        px, py, pw, ph = self._get_plot_area()
        return px + (temp / 100.0) * pw

    def _speed_to_y(self, speed):
        px, py, pw, ph = self._get_plot_area()
        return py + ph - (speed / 100.0) * ph

    def _x_to_temp(self, x):
        px, py, pw, ph = self._get_plot_area()
        return max(0, min(100, int(round((x - px) / pw * 100))))

    def _y_to_speed(self, y):
        px, py, pw, ph = self._get_plot_area()
        return max(0, min(100, int(round((1 - (y - py) / ph) * 100))))

    def _draw(self, area, cr):
        """Cairo draw function."""
        px, py, pw, ph = self._get_plot_area()

        # Background
        cr.set_source_rgb(*self.BG_COLOR)
        cr.rectangle(px, py, pw, ph)
        cr.fill()

        # Grid lines
        cr.set_source_rgb(*self.GRID_COLOR)
        cr.set_line_width(0.5)

        # Horizontal grid (every 10% fan speed)
        for speed in range(0, 101, 10):
            y = self._speed_to_y(speed)
            cr.move_to(px, y)
            cr.line_to(px + pw, y)
            cr.stroke()
            # Label
            cr.set_source_rgb(*self.TEXT_COLOR)
            self._draw_text(cr, f'{speed}%', px - 8, y, anchor='right')
            cr.set_source_rgb(*self.GRID_COLOR)

        # Vertical grid (every 10C)
        for temp in range(0, 101, 10):
            x = self._temp_to_x(temp)
            cr.move_to(x, py)
            cr.line_to(x, py + ph)
            cr.stroke()
            # Label
            cr.set_source_rgb(*self.TEXT_COLOR)
            self._draw_text(cr, f'{temp}\u00b0C', x, py + ph + 5, anchor='center_top')
            cr.set_source_rgb(*self.GRID_COLOR)

        # Draw curves
        if self.show_cpu:
            self._draw_curve(cr, self.cpu_temps, self.cpu_speeds, self.CPU_COLOR, 'CPU')
        if self.show_gpu:
            self._draw_curve(cr, self.gpu_temps, self.gpu_speeds, self.GPU_COLOR, 'GPU')

    def _draw_curve(self, cr, temps, speeds, color, label):
        """Draw a single fan curve with its points."""
        points = []
        # Start at temp=0 with speed[0]
        points.append((0, speeds[0]))

        for i in range(6):
            # Horizontal line to the threshold at current speed
            points.append((temps[i], speeds[i]))
            # Step up to next speed
            points.append((temps[i], speeds[i + 1]))

        # End at temp=100 with last speed
        points.append((100, speeds[6]))

        # Draw the line
        cr.set_source_rgba(*color, 0.8)
        cr.set_line_width(2.5)
        for i, (t, s) in enumerate(points):
            x, y = self._temp_to_x(t), self._speed_to_y(s)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()

        # Fill area under curve
        cr.set_source_rgba(*color, 0.08)
        px, py, pw, ph = self._get_plot_area()
        for i, (t, s) in enumerate(points):
            x, y = self._temp_to_x(t), self._speed_to_y(s)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.line_to(self._temp_to_x(100), self._speed_to_y(0))
        cr.line_to(self._temp_to_x(0), self._speed_to_y(0))
        cr.close_path()
        cr.fill()

        # Draw draggable points at each threshold
        for i in range(6):
            x = self._temp_to_x(temps[i])
            # Draw point at the "after" speed (speeds[i+1])
            y = self._speed_to_y(speeds[i + 1])
            cr.set_source_rgba(*color, 1.0)
            cr.arc(x, y, self.POINT_RADIUS, 0, 2 * math.pi)
            cr.fill()
            # White border
            cr.set_source_rgba(1, 1, 1, 0.8)
            cr.arc(x, y, self.POINT_RADIUS, 0, 2 * math.pi)
            cr.set_line_width(1.5)
            cr.stroke()

        # Draw the "base speed" point at temp=0
        x = self._temp_to_x(0)
        y = self._speed_to_y(speeds[0])
        cr.set_source_rgba(*color, 0.6)
        cr.arc(x, y, self.POINT_RADIUS - 1, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.5)
        cr.arc(x, y, self.POINT_RADIUS - 1, 0, 2 * math.pi)
        cr.set_line_width(1)
        cr.stroke()

    def _draw_text(self, cr, text, x, y, anchor='left'):
        """Draw text at position with specified anchor."""
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        desc = Pango.FontDescription.from_string('Sans 9')
        layout.set_font_description(desc)
        ink_rect, logical_rect = layout.get_pixel_extents()

        if anchor == 'right':
            x = x - logical_rect.width
            y = y - logical_rect.height / 2
        elif anchor == 'center_top':
            x = x - logical_rect.width / 2
            y = y
        elif anchor == 'center':
            x = x - logical_rect.width / 2
            y = y - logical_rect.height / 2

        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)

    def _find_point_at(self, mx, my):
        """Find which curve point is near (mx, my). Returns ('cpu'/'gpu', index) or None.

        Index 0 = base speed point (at temp=0), index 1-6 = threshold points.
        """
        for curve_name, temps, speeds, visible in [
            ('cpu', self.cpu_temps, self.cpu_speeds, self.show_cpu),
            ('gpu', self.gpu_temps, self.gpu_speeds, self.show_gpu),
        ]:
            if not visible:
                continue
            # Check base speed point (index 0)
            x = self._temp_to_x(0)
            y = self._speed_to_y(speeds[0])
            if (mx - x) ** 2 + (my - y) ** 2 <= self.GRAB_RADIUS ** 2:
                return (curve_name, 0)
            # Check threshold points (index 1-6)
            for i in range(6):
                x = self._temp_to_x(temps[i])
                y = self._speed_to_y(speeds[i + 1])
                if (mx - x) ** 2 + (my - y) ** 2 <= self.GRAB_RADIUS ** 2:
                    return (curve_name, i + 1)
        return None

    def _on_button_press(self, widget, event):
        """Handle mouse button press - start dragging if on a point."""
        if event.button != 1:
            return False
        hit = self._find_point_at(event.x, event.y)
        if hit:
            self._dragging = hit
            return True
        return False

    def _on_button_release(self, widget, event):
        """Handle mouse button release - stop dragging."""
        if event.button != 1:
            return False
        if self._dragging:
            self._dragging = None
            self.emit('curve-changed')
            return True
        return False

    def _on_motion(self, widget, event):
        """Handle mouse motion - drag points or update cursor."""
        if self._dragging:
            curve, idx = self._dragging
            temps = self.cpu_temps if curve == 'cpu' else self.gpu_temps
            speeds = self.cpu_speeds if curve == 'cpu' else self.gpu_speeds

            new_speed = self._y_to_speed(event.y)

            if idx == 0:
                # Base speed point - only vertical movement
                speeds[0] = new_speed
            else:
                # Threshold point - both horizontal and vertical
                new_temp = self._x_to_temp(event.x)

                # Constrain temperature to be between neighbors
                i = idx - 1  # index into temps array
                min_temp = temps[i - 1] + 1 if i > 0 else 1
                max_temp = temps[i + 1] - 1 if i < 5 else 99
                temps[i] = max(min_temp, min(max_temp, new_temp))
                speeds[idx] = new_speed

            self.drawing_area.queue_draw()
            return True

        # Update cursor based on hover state
        hit = self._find_point_at(event.x, event.y)
        display = widget.get_display()
        if hit:
            cursor = Gdk.Cursor.new_from_name(display, 'grab')
        else:
            cursor = None
        widget.get_window().set_cursor(cursor)
        return False

    def _on_cpu_toggled(self, button):
        self.show_cpu = button.get_active()
        self.drawing_area.queue_draw()

    def _on_gpu_toggled(self, button):
        self.show_gpu = button.get_active()
        self.drawing_area.queue_draw()
