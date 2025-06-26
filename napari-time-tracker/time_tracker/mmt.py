import time
from magicgui import magicgui
from napari.viewer import Viewer
from qtpy.QtCore import QTimer


class MouseTracker:
    def __init__(self, viewer):
        self.viewer = viewer
        self._event_connection = None
        self.last_move_time = None
        self.movement_active = False
        self.total_movement_time = 0.0

    def _on_mouse_move(self, event):
        start_time = time.time()

        # Start Bewegungsphase
        if not self.movement_active:
            self.movement_active = True
            self.last_move_time = start_time

        # Reset den Inaktivitäts-Timeout von der letzten Bewegung
        if hasattr(self, "_stop_timer"):
            self._stop_timer.stop()

        # Inaktivitätstimer für diese Bewegung
        self._stop_timer = QTimer()
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self._on_mouse_stop)
        self._stop_timer.start(200)

    def _on_mouse_stop(self):
        stop_time = time.time()
        if self.last_move_time is not None:
            delta = stop_time - self.last_move_time
            self.total_movement_time += delta
        self.movement_active = False

    def start(self):
        if self._event_connection is None:
            self._event_connection = self.viewer.window.qt_viewer.canvas.events.mouse_move.connect(self._on_mouse_move)

    def stop(self):
        if self.movement_active:
            self._on_mouse_stop()
        if self._event_connection is not None:
            self.viewer.window.qt_viewer.canvas.events.mouse_move.disconnect(self._event_connection)
            self._event_connection = None
        result = self.total_movement_time
        self.total_movement_time = 0.0
        return result

