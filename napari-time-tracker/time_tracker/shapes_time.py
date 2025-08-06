import napari
import numpy as np
from PyQt5.QtCore import QTimer
from napari.layers import Shapes
from napari.utils.notifications import show_info
from napari.layers.shapes._shapes_constants import Mode
import time
from .mmt import MouseTracker


class ShapeTimeTracker:
    """
    Tracks the time spent interacting with shape annotations in a Napari viewer.

    Depending on the annotation tool (rectangle, polygon, lasso, etc.), it hooks into
    the appropriate mouse and keyboard events and uses MouseTracker to measure interaction duration.
    """

    def __init__(self, v):
        """
        Initialize the tracker with a given Napari viewer instance.

        Parameters:
        v: The Napari viewer instance.
        """

        self.viewer = v
        self.tracker = MouseTracker(self.viewer)

        # Drag-and-drop implementation
        self._mouse_press_connection_drag = None
        self._mouse_release_connection_drag = None

        # Click-based implementation
        self._mouse_press_connection_click = None
        self._key_press_connection_click = None
        self._last_click_time = 0

        # Combined/dual interaction (e.g., polygon lasso, path)
        self._dual_mouse_press_connection = None
        self._dual_mouse_release_connection = None
        self._dual_key_press_connection = None
        self._dual_press_time = None
        self._dual_click_count = 0

        self.tracker_running = False
        self.click_count = 0
        self.timeMap = {}
        self._connected_shape_layer = None

    def shape_connect(self):
        """
        Connects event handlers based on the current shape layer and its active drawing mode.
        """
        sel = list(self.viewer.layers.selection)
        if not sel or not isinstance(sel[0], Shapes):
            return

        self._connected_shape_layer = sel[0]
        shape_layer_mode = Mode(self._connected_shape_layer.mode)
        self._connected_shape_layer.events.mode.connect(self._on_mode_change)

        match shape_layer_mode:
            case Mode.ADD_ELLIPSE | Mode.ADD_RECTANGLE | Mode.ADD_LINE:
                self._connect_drag_and_drop()
            case Mode.ADD_POLYGON | Mode.ADD_POLYLINE:
                self._connect_click_based()
            case Mode.ADD_POLYGON_LASSO | Mode.ADD_PATH:
                self._connect_dual_with_extension()
            case Mode.SELECT:
                pass
            case _:
                show_info(f"Tool '{shape_layer_mode}' unsupported")

        if self._connected_shape_layer is not None:
            self._connected_shape_layer.events.data.connect(self._on_shapes_removed)

    def _connect_drag_and_drop(self):
        """
        Sets up mouse press/release events for drag-and-drop based shape tools.
        """
        canvas = self.viewer.window.qt_viewer.canvas

        if self._mouse_press_connection_drag is None:
            self._mouse_press_connection_drag = canvas.events.mouse_press.connect(self._on_mouse_press)

        if self._mouse_release_connection_drag is None:
            self._mouse_release_connection_drag = canvas.events.mouse_release.connect(self._on_mouse_release)

    def _connect_click_based(self):
        """
        Sets up mouse and key events for click-based shape tools.
        """
        canvas = self.viewer.window.qt_viewer.canvas

        if self._mouse_press_connection_click is None:
            self._mouse_press_connection_click = canvas.events.mouse_press.connect(self._on_click)

        if self._key_press_connection_click is None:
            self._key_press_connection_click = canvas.events.key_press.connect(self._on_key_press)

        if self._connected_shape_layer is not None:
            self._connected_shape_layer.events.data.connect(self._on_shape_inserted)
            self._previous_shape_count = len(self._connected_shape_layer.data)

    def _connect_dual_with_extension(self):
        """
        Sets up combined mouse/keyboard events for tools like polygon lasso or path
        that use a hybrid interaction model.
        """
        canvas = self.viewer.window.qt_viewer.canvas

        if self._dual_mouse_press_connection is None:
            self._dual_mouse_press_connection = canvas.events.mouse_press.connect(self._on_dual_press)

        if self._dual_mouse_release_connection is None:
            self._dual_mouse_release_connection = canvas.events.mouse_release.connect(self._on_dual_release)

        if self._dual_key_press_connection is None:
            self._dual_key_press_connection = canvas.events.key_press.connect(self._on_dual_key)

    def _on_mouse_press(self, event):
        """
        Starts the time tracker on mouse press (drag-and-drop tools).
        """
        if not self.tracker_running:
            self.tracker.start()
            self.tracker_running = True

    def _on_mouse_release(self, event):
        """
        Stops the tracker on mouse release and reconnects events (drag-and-drop tools).
        """
        if self.tracker_running:
            self.end_and_reconnect()

    def _on_click(self, event):
        """
        Starts tracking on mouse click for click-based shape tools.
        """
        if not self.tracker_running:
            self.tracker.start()
            self.tracker_running = True

    def _on_shape_inserted(self, event):
        """
        Called when a new shape is inserted (Polygon, Polyline, etc.).
        Stops tracking and saves time.
        """
        new_count = len(self._connected_shape_layer.data)
        if self.tracker_running and new_count > self._previous_shape_count:
            self.end_and_reconnect()
        self._previous_shape_count = new_count

    def _on_key_press(self, event):
        """
        Stops the tracker if 'Escape' is pressed (click-based tools).
        """
        if event.key == 'Escape':
            self.end_and_reconnect()

    def _on_dual_press(self, event):
        """
        Starts tracking on the first click (dual-mode tools).
        """
        if not self.tracker_running and self._dual_click_count == 0:
            self._dual_press_time = time.time()
            self.tracker.start()
            self.tracker_running = True

    def _on_dual_release(self, event):
        """
        Handles both drag and click sequences for dual-mode tools.
        Detects whether the action was a click or a drag based on press duration.
        """
        if self.tracker_running and self._dual_click_count == 0:
            release_time = time.time()
            press_duration = release_time - self._dual_press_time
            if press_duration >= 0.3:
                self.end_and_reconnect()  # drag detected
            else:
                self._dual_click_count = 1  # wait for second click
        elif self.tracker_running and self._dual_click_count == 1:
            self._dual_click_count = 0
            self.end_and_reconnect()

    def _on_dual_key(self, event):
        """
        Cancels the tracking on 'Escape' key for dual-mode tools.
        """
        if event.key == 'Escape' and self.tracker_running:
            self._dual_click_count = 0
            self.end_and_reconnect()

    def _on_dual_right_click(self, event):
        """
        Cancels tracking on right mouse button click (if supported).
        """
        if event.button == 2 and self.tracker_running:
            self.click_count = 0
            self.end_and_reconnect()

    def _on_mode_change(self, event):
        """
        Handles tool/mode changes in the shape layer by reconnecting appropriate handlers.
        """
        print(self.timeMap)
        self.disconnect_all()
        self.shape_connect()

    def end_and_reconnect(self, force=False):
        """
        Stops the tracker, saves timing data, resets state, and reconnects event handlers.
        """
        movement_time = self.tracker.stop()
        self.map_time(self.tracker.remember_start, self.tracker.remember_stop, movement_time)
        self.tracker.reset_timestamps()
        self.tracker_running = False
        self.disconnect_all()
        self.shape_connect()
        print(self.timeMap)

    def disconnect_all(self):
        """
        Disconnects all previously connected event handlers to ensure no duplicates remain.
        """
        canvas = self.viewer.window.qt_viewer.canvas

        try:
            if self._mouse_press_connection_drag is not None:
                canvas.events.mouse_press.disconnect(self._mouse_press_connection_drag)
                self._mouse_press_connection_drag = None

            if self._mouse_release_connection_drag is not None:
                canvas.events.mouse_release.disconnect(self._mouse_release_connection_drag)
                self._mouse_release_connection_drag = None

            if self._mouse_press_connection_click is not None:
                canvas.events.mouse_press.disconnect(self._mouse_press_connection_click)
                self._mouse_press_connection_click = None

            if self._connected_shape_layer is not None:
                self._connected_shape_layer.events.data.disconnect(self._on_shape_inserted)
                self._connected_shape_layer = None

            if self._key_press_connection_click is not None:
                canvas.events.key_press.disconnect(self._key_press_connection_click)
                self._key_press_connection_click = None

            if self._dual_mouse_press_connection is not None:
                canvas.events.mouse_press.disconnect(self._dual_mouse_press_connection)
                self._dual_mouse_press_connection = None

            if self._dual_mouse_release_connection is not None:
                canvas.events.mouse_release.disconnect(self._dual_mouse_release_connection)
                self._dual_mouse_release_connection = None

            if self._dual_key_press_connection is not None:
                canvas.events.key_press.disconnect(self._dual_key_press_connection)
                self._dual_key_press_connection = None

            if self._connected_shape_layer is not None:
                self._connected_shape_layer.events.mode.disconnect(self._connected_shape_layer)
                self._connected_shape_layer.events.data.disconnect(self._on_shape_data_changed)
                self._connected_shape_layer = None

        except Exception as e:
            show_info(f"event-handler-error: {e}")

    def map_time(self, start_timestamp, stop_timestamp, object_time):
        """
        Saves the measured time data for the currently selected shape object.

        Parameters:
        start_timestamp (float): Start time of the interaction.
        stop_timestamp (float): End time of the interaction.
        object_time (float): Duration of the interaction.
        """
        current_layer = list(self.viewer.layers.selection)[0]
        selected = current_layer.selected_data

        if len(selected) != 1:
            return

        shape_index = next(iter(selected))
        shape_obj = current_layer.data[shape_index]
        shape_id = id(shape_obj)

        if current_layer not in self.timeMap:
            self.timeMap[current_layer] = {}

        list_times = [start_timestamp, stop_timestamp, object_time]
        self.timeMap[current_layer][shape_id] = list_times

    def get_time_map(self):
        """
        Returns the current map of interaction times.

        Returns:
        dict: A dictionary mapping shape layers and object IDs to timing data.
        """
        return self.timeMap

    def _on_shapes_removed(self, event):
        pass




