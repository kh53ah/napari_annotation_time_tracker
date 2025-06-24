import napari
from napari.layers import Shapes
from napari.utils.notifications import show_info
from napari.layers.shapes._shapes_constants import Mode
import time
from .shapes_time import MouseTracker
from magicgui import magicgui


class ShapeTimeTracker:
    def __init__(self,v):
        self.viewer = v
        self.tracker = MouseTracker(self.viewer)

        self._mouse_press_connection_drag = None
        self._mouse_release_connection_drag = None

        self._mouse_press_connection_click = None
        self._key_press_connection_click = None

        self._dual_mouse_press_connection = None
        self._dual_mouse_release_connection = None
        self._dual_key_press_connection = None
        self.tracker_running = False
        self.click_count = 0

    def is_valid_shape_layer_selected(self):
        selected = list(self.viewer.layers.selection)
        return len(selected) == 1 and isinstance(selected[0], Shapes)

    def check_tool_type_and_connect(self):
        if not self.is_valid_shape_layer_selected():
            show_info("No valid shape layer selected")
            return

        shape_layer = list(self.viewer.layers.selection)[0]
        shape_layer_mode = Mode(shape_layer.mode)
        shape_layer.events.mode.connect(self._on_mode_change)

        match shape_layer_mode:     #Only track if we use a annotation tool
            case Mode.ADD_ELLIPSE| Mode.ADD_RECTANGLE | Mode.ADD_LINE:
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
            self._key_press_connection_click= canvas.events.key_press.connect(self._on_key_press)


    def _connect_dual_with_extension(self): #We need this, because lasso and path implements both of the functions above with modifications
        canvas = self.viewer.window.qt_viewer.canvas

        if self._dual_mouse_press_connection is None:
            self._dual_mouse_press_connection = canvas.events.mouse_press.connect(self._on_dual_press)

        if self._dual_mouse_release_connection is None:
            self._dual_mouse_release_connection = canvas.events.mouse_release.connect(self._on_dual_release)

        if self._dual_key_press_connection is None:
            self._dual_key_press_connection = canvas.events.key_press.connect(self._on_dual_key)


    def _on_mouse_press(self, event):
        print("Mouse pressed – start timetracker")
        self.tracker.start()

    def _on_mouse_release(self, event):
        print("Mouse released – stop timetracker")
        self.tracker.stop()
        self.tracker_running = False
        self.disconnect_all()

    def _on_click(self, event):
        if not self.tracker_running:
            self.tracker.start()
            self.tracker_running = True

    def _on_key_press(self, event):
        if event.key == 'Escape':
            print("ESC – stop Timer")
            self.tracker.stop()
            self.tracker_running = False
            self.disconnect_all()

    def _on_dual_press(self, event):
        if not self.tracker_running and self.click_count == 0: #first left click starts timer
            self._press_time = time.time()
            print("Start Timer")
            self.tracker.start()
            self.tracker_running = True
        elif self.tracker_running and self.click_count == 1: #second left click of click-based tracking shall not start timer again
            pass

    def _on_dual_release(self, event):
        if self.tracker_running and self.click_count == 0: #only check this, if its a first click and the timer is running, otherwise
            release_time = time.time()
            press_duration = release_time - self._press_time
            if press_duration >= 0.3:  # z. B. 300 ms
                print(f"Drag detected (Duration: {press_duration:.3f}s)")
                self.tracker.stop()
                self.tracker_running = False
            else:
                self.click_count = 1
                print(f"Click detected (Duration: {press_duration:.3f}s)")
        elif self.tracker_running and self.click_count == 1:
            print("Stop Timer")
            self.tracker.stop()
            self.tracker_running = False
            self.click_count = 0
            self.disconnect_all()

    def _on_dual_key(self, event):
        if event.key == 'Escape' and self.tracker_running:
            print("Escape – stop Timer")
            self.tracker.stop()
            self.tracker_running = False
            self.click_count = 0
            self.disconnect_all()

    def _on_dual_right_click(self, event):
        if event.button == 2 and self.tracker_running:
            print("Right click – stop Timer")
            self.tracker.stop()
            self.tracker_running = False
            self.click_count = 0
            self.disconnect_all()

    def _on_mode_change(self, event):
        show_info(f"Tool changed: {list(self.viewer.layers.selection)[0].mode}")
        self.disconnect_all()
        self.check_tool_type_and_connect()

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
            print(f"Fehler beim Trennen von Event-Handlern: {e}")


t = None

@magicgui(call_button="Start Tracking")
def run():
    viewer = napari.current_viewer()
    global t
    t = ShapeTimeTracker(viewer)
    t.check_tool_type_and_connect()

def napari_experimental_provide_dock_widget():
    return run
