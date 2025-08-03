import time
import napari
from PyQt5.QtCore import QTimer, QRect
from PyQt5.QtWidgets import QApplication


class CanvasTimeTracker:
    """
    Tracks time when the mouse is on or off the canvas widget in a napari viewer.
    """

    def __init__(self, viewer=None):
        self.viewer = viewer or napari.current_viewer()

        self.current_state = None  # 'on_canvas' or 'off_canvas'
        self.state_start_time = None

        self.durations_on_canvas = 0
        self.durations_off_canvas = 0

        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.periodic_check)
        self.check_timer.start(50)

        self.viewer.mouse_move_callbacks.append(self.on_mouse_move)

    def update_onCanvas_time_on_fly(self):
        current_time = time.time()
        total_on_canvas = self.durations_on_canvas

        if self.current_state == 'on_canvas' and self.state_start_time is not None:
            total_on_canvas += current_time - self.state_start_time

        self.state_start_time = current_time
        return total_on_canvas

    def update_offCanvas_time_on_fly(self):
        current_time = time.time()
        total_off_canvas = self.durations_off_canvas

        if self.current_state == 'off_canvas' and self.state_start_time is not None:
            total_off_canvas += current_time - self.state_start_time

        self.state_start_time = current_time
        return total_off_canvas

    def record_state_change(self, new_state):
        current_time = time.time()

        if self.current_state != new_state:
            if self.current_state is not None and self.state_start_time is not None:
                duration = current_time - self.state_start_time

                if self.current_state == 'on_canvas':
                    self.durations_on_canvas += duration
                elif self.current_state == 'off_canvas':
                    self.durations_off_canvas += duration

            self.current_state = new_state
            self.state_start_time = current_time

    def is_mouse_on_canvas(self):
        try:
            app = QApplication.instance()
            canvas_widget = self.viewer.window.qt_viewer.canvas.native.parent()

            # Get global canvas rect
            top_left = canvas_widget.mapToGlobal(canvas_widget.rect().topLeft())
            bottom_right = canvas_widget.mapToGlobal(canvas_widget.rect().bottomRight())
            canvas_global_rect = QRect(top_left, bottom_right)

            # Mouse global position
            mouse_pos = app.desktop().cursor().pos()

            # Check if inside canvas
            if not canvas_global_rect.contains(mouse_pos):
                return False

            # Optional: exclude GUI control panel
            try:
                controls_widget = self.viewer.window.qt_viewer.controls
                controls_top_left = controls_widget.mapToGlobal(controls_widget.rect().topLeft())
                controls_bottom_right = controls_widget.mapToGlobal(controls_widget.rect().bottomRight())
                controls_global_rect = QRect(controls_top_left, controls_bottom_right)

                if controls_global_rect.contains(mouse_pos):
                    return False
            except Exception:
                pass

            return True
        except Exception as e:
            return False

    def periodic_check(self):
        try:
            on_canvas = self.is_mouse_on_canvas()
            new_state = 'on_canvas' if on_canvas else 'off_canvas'

            if self.current_state is None or self.current_state != new_state:
                self.record_state_change(new_state)
        except Exception as e:
            print(f"Error in periodic_check: {e}")

    def on_mouse_move(self, viewer, event):
        try:
            on_canvas = self.is_mouse_on_canvas()
            new_state = 'on_canvas' if on_canvas else 'off_canvas'
            self.record_state_change(new_state)
        except Exception as e:
            print(f"Error in on_mouse_move: {e}")

    def get_onCanvas(self):
        return self.update_onCanvas_time_on_fly()

    def get_offCanvas(self):
        return self.update_offCanvas_time_on_fly()
