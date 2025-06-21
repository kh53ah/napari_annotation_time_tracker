import napari
from napari.layers import Shapes
from napari.utils.notifications import show_info
from napari.layers.shapes._shapes_constants import Mode

from .shapes_time import MouseTracker
from magicgui import magicgui


class ShapeTimeTracker:
    def __init__(self,v):
        self.viewer = v
        self.tracker = MouseTracker(self.viewer)
        self._mouse_press_connection = None
        self._mouse_release_connection = None
        self._key_press_connection = None

    def is_valid_shape_layer_selected(self):
        """Überprüft, ob genau ein Shape-Layer ausgewählt ist"""
        selected = list(self.viewer.layers.selection)
        return len(selected) == 1 and isinstance(selected[0], Shapes)

    def check_tool_type_and_connect(self):
        if not self.is_valid_shape_layer_selected():
            show_info("Kein gültiger Shape-Layer ausgewählt.")
            return

        shape_layer = list(self.viewer.layers.selection)[0]
        shape_layer_mode = Mode(shape_layer.mode)
        print("type:", type(shape_layer_mode), "value:", shape_layer_mode)

        match shape_layer_mode:
            case Mode.ADD_ELLIPSE| Mode.ADD_RECTANGLE | Mode.ADD_LINE:
                show_info("not working")
                self._connect_drag_and_drop()
            case Mode.ADD_POLYGON | Mode.ADD_POLYLINE:
                self._connect_click_based()
            case Mode.ADD_POLYGON_LASSO | Mode.ADD_PATH:     #case polygone_lasso und path benötigen beide funktionen
                self._connect_drag_and_drop()
                self._connect_click_based()
            case _:
                show_info(f"Tool '{shape_layer_mode}' wird nicht unterstützt.")


    def _connect_drag_and_drop(self):
        canvas = self.viewer.window.qt_viewer.canvas

        if self._mouse_press_connection is None:
            self._mouse_press_connection = canvas.events.mouse_press.connect(self._on_mouse_press)

        if self._mouse_release_connection is None:
            self._mouse_release_connection = canvas.events.mouse_release.connect(self._on_mouse_release)


    def _connect_click_based(self):
        canvas = self.viewer.window.qt_viewer.canvas

        if self._mouse_press_connection is None:
            self._mouse_press_connection = canvas.events.mouse_press.connect(self._on_click)

        if self._key_press_connection is None:
            self._key_press_connection = canvas.events.key_press.connect(self._on_key_press)

        self.tracker_running = False


    def _on_mouse_press(self, event):
        print("Mouse pressed – starte Timer")
        self.tracker.start()

    def _on_mouse_release(self, event):
        print("Mouse released – stoppe Timer")
        self.tracker.stop()

    def _on_click(self, event):
        if not self.tracker_running:
            print("Erster Klick – starte Timer")
            self.tracker.start()
            self.tracker_running = True

    def _on_key_press(self, event):
        if event.key == 'Escape' and self.tracker_running:
            print("ESC gedrückt – stoppe Timer")
            self.tracker.stop()
            self.tracker_running = False
            self._mouse_press_connection=None


t = None

@magicgui(call_button="Start Tracking")
def run():
    viewer = napari.current_viewer()
    global t
    t = ShapeTimeTracker(viewer)
    t.check_tool_type_and_connect()

def napari_experimental_provide_dock_widget():
    return run
