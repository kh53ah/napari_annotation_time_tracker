import time
from napari.viewer import Viewer
from qtpy.QtCore import QTimer


class MouseTracker:
    """
    A class to track mouse movement within a Napari viewer.

    This tracker monitors mouse motion events and calculates the total duration
    of active movement. Movement is considered active as long as the mouse is moving
    without long pauses.
    """

    def __init__(self, viewer: Viewer):
        """
        Initialize the MouseTracker with a given Napari viewer.

        Parameters:
        viewer (Viewer): An instance of the Napari viewer.
        """
        self.viewer = viewer
        self._event_connection = None
        self.last_move_time = None
        self.movement_active = False
        self.total_movement_time = 0.0
        self.remember_start = None
        self.remember_stop = None

    def _on_mouse_move(self, event):
        """
        Internal callback triggered on every mouse move event.

        Starts a timer to detect when movement stops, and tracks the movement start time.
        """
        start_time = time.time()
        if self.remember_start is None:
            self.remember_start = start_time

        # Begin a new movement phase
        if not self.movement_active:
            self.movement_active = True
            self.last_move_time = start_time

        # Reset any previous inactivity timer
        if hasattr(self, "_stop_timer"):
            self._stop_timer.stop()

        # Start a new inactivity timer
        self._stop_timer = QTimer()
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self._on_mouse_stop)
        self._stop_timer.start(200)

    def _on_mouse_stop(self):
        """
        Internal callback triggered when mouse inactivity is detected.

        Calculates and accumulates the time elapsed since the last detected movement.

        Returns:
        float: The timestamp at which movement was considered stopped.
        """
        stop_time = time.time()
        if self.last_move_time is not None:
            delta = stop_time - self.last_move_time
            self.total_movement_time += delta
        self.movement_active = False
        self.remember_stop = stop_time

    def start(self):
        """
        Start tracking mouse movement in the Napari viewer.
        """
        if self._event_connection is None:
            self._event_connection = self.viewer.window.qt_viewer.canvas.events.mouse_move.connect(self._on_mouse_move)

    def stop(self):
        """
        Stop tracking mouse movement and return the total movement duration.

        Returns:
        float: The total amount of time (in seconds) the mouse was actively moving.
        """
        self._on_mouse_stop()
        if self._event_connection is not None:
            self.viewer.window.qt_viewer.canvas.events.mouse_move.disconnect(self._event_connection)
            self._event_connection = None
        result = self.total_movement_time
        self.total_movement_time = 0.0
        return result

    def reset_timestamps(self):
        """
        Reset the stored start and stop timestamps.
        """
        self.remember_start = None
        self.remember_stop = None
