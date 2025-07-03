import napari
from napari.utils.notifications import show_info
from napari.layers.shapes._shapes_constants import Mode
import time
from .mmt import MouseTracker


class ShapeTimeTracker:
    def __init__(self, v):
        self.viewer = v
        self.tracker = MouseTracker(self.viewer)

        # attributs needed for dragAndDrop implementation
        self._mouse_press_connection_drag = None
        self._mouse_release_connection_drag = None

        # attributs needed for click-based implementation
        self._mouse_press_connection_click = None
        self._key_press_connection_click = None

        # attributs needed for dual implementation
        self._dual_mouse_press_connection = None
        self._dual_mouse_release_connection = None
        self._dual_key_press_connection = None
        self.tracker_running = False
        self.click_count = 0

        # attributs needed for saving time
        self.timeMap = {}

    # main methode for starting the shape layer tracking
    def shape_connect(self):

        shape_layer = list(self.viewer.layers.selection)[0]
        shape_layer_mode = Mode(shape_layer.mode)
        shape_layer.events.mode.connect(self._on_mode_change)

        match shape_layer_mode:  #Only track if we use a annotation tool
            case Mode.ADD_ELLIPSE | Mode.ADD_RECTANGLE | Mode.ADD_LINE:
                self._connect_drag_and_drop()
            case Mode.ADD_POLYGON | Mode.ADD_POLYLINE:
                self._connect_click_based()
            case Mode.ADD_POLYGON_LASSO | Mode.ADD_PATH:
                self._connect_dual_with_extension()
            case _:
                show_info(f"Tool '{shape_layer_mode}' unsupported")

    def _connect_drag_and_drop(self):
        canvas = self.viewer.window.qt_viewer.canvas

        if self._mouse_press_connection_drag is None:
            self._mouse_press_connection_drag = canvas.events.mouse_press.connect(self._on_mouse_press)

        if self._mouse_release_connection_drag is None:
            self._mouse_release_connection_drag = canvas.events.mouse_release.connect(self._on_mouse_release)

    def _connect_click_based(self):
        canvas = self.viewer.window.qt_viewer.canvas

        if self._mouse_press_connection_click is None:
            self._mouse_press_connection_click = canvas.events.mouse_press.connect(self._on_click)

        if self._key_press_connection_click is None:
            self._key_press_connection_click = canvas.events.key_press.connect(self._on_key_press)

    def _connect_dual_with_extension(
            self):  #We need this, because lasso and path implements both of the functions above with modifications
        canvas = self.viewer.window.qt_viewer.canvas

        if self._dual_mouse_press_connection is None:
            self._dual_mouse_press_connection = canvas.events.mouse_press.connect(self._on_dual_press)

        if self._dual_mouse_release_connection is None:
            self._dual_mouse_release_connection = canvas.events.mouse_release.connect(self._on_dual_release)

        if self._dual_key_press_connection is None:
            self._dual_key_press_connection = canvas.events.key_press.connect(self._on_dual_key)

    def _on_mouse_press(self, event):
        if not self.tracker_running:
            self.tracker.start()
            self.tracker_running = True

    def _on_mouse_release(self, event):
        if self.tracker_running:
            movement_time = self.tracker.stop()
            self.map_time(movement_time)
            self.tracker_running = False
            self.disconnect_all()
            self.shape_connect()

    def _on_click(self, event):
        if not self.tracker_running:
            self.tracker.start()
            self.tracker_running = True

    def _on_key_press(self, event):
        if event.key == 'Escape':
            movement_time = self.tracker.stop()
            self.map_time(movement_time)
            self.tracker_running = False
            self.disconnect_all()
            self.shape_connect()

    def _on_dual_press(self, event):
        if not self.tracker_running and self.click_count == 0:  # first left click starts timer
            self._press_time = time.time()
            self.tracker.start()
            self.tracker_running = True

    def _on_dual_release(self, event):
        if self.tracker_running and self.click_count == 0:  # first release determines dragAndDrop or click-based
            release_time = time.time()
            press_duration = release_time - self._press_time
            if press_duration >= 0.3:  # drag detected 300 ms
                movement_time = self.tracker.stop()
                self.map_time(movement_time)
                self.tracker_running = False
                self.disconnect_all()
                self.shape_connect()
            else:  # click detected
                self.click_count = 1
        elif self.tracker_running and self.click_count == 1:  # second release stops time for click-based
            movement_time = self.tracker.stop()
            self.map_time(movement_time)
            self.tracker_running = False
            self.click_count = 0
            self.disconnect_all()
            self.shape_connect()

    def _on_dual_key(self, event):
        if event.key == 'Escape' and self.tracker_running:
            movement_time = self.tracker.stop()
            self.map_time(movement_time)
            self.tracker_running = False
            self.click_count = 0
            self.disconnect_all()
            self.shape_connect()

    def _on_dual_right_click(self, event):
        if event.button == 2 and self.tracker_running:
            movement_time = self.tracker.stop()
            self.map_time(movement_time)
            self.tracker_running = False
            self.click_count = 0
            self.disconnect_all()
            self.shape_connect()

    def _on_mode_change(self, event):
        show_info(f"Tool changed: {list(self.viewer.layers.selection)[0].mode}")
        print(self.timeMap)
        self.disconnect_all()
        self.shape_connect()

    def disconnect_all(self):
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

        except Exception as e:
            show_info(f"event-handler-error: {e}")

    def map_time(self, t):
        current_layer = list(self.viewer.layers.selection)[0]
        current_object = current_layer.selected_data
        tmp = {self.timeMap.get(current_layer): None}
        if tmp is None:
            self.timeMap[current_layer] = {}
        tmp.update({current_object: t})
        self.timeMap.update({current_layer: tmp})
        print(self.timeMap)
