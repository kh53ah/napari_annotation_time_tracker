import napari
from napari.layers import Shapes
from .shapes_time import MouseTracker, start_tracking
from magicgui import magicgui
from qtpy.QtWidgets import QToolButton


class ShapeTimeTracker:
    def __init__(self,v):
        self.viewer = v
        self.tracker = MouseTracker(self.viewer)
        self._mouse_press_connection = None
        self._mouse_release_connection = None

    def is_valid_shape_layer_selected(self):
        """Überprüft, ob genau ein Shape-Layer ausgewählt ist"""
        selected = list(self.viewer.layers.selection)
        return len(selected) == 1 and isinstance(selected[0], Shapes)

    def check_tool_type_and_connect(self):
        if not self.is_valid_shape_layer_selected():
            print("Kein gültiger Shape-Layer ausgewählt.")
            return

        active_tool = self.viewer.layers.selection.active.shape_type
        # Achtung: _active_tool ist intern! Es gibt noch keine offizielle API für tools

        match active_tool:
            case 'ellipse' | 'rectangle' | 'line':
                self._connect_drag_and_drop()
            case 'polygon' | 'polyline':
                self._connect_click_based()
            case _:     #case polygone_lasso und path sind die restlichen Fälle
                print(f"Tool '{active_tool}' wird nicht unterstützt.")

    def _connect_drag_and_drop(self):
        canvas = self.viewer.window.qt_viewer.canvas

        if self._mouse_press_connection is None:
            self._mouse_press_connection = canvas.events.mouse_press.connect(self._on_mouse_press)

        if self._mouse_release_connection is None:
            self._mouse_release_connection = canvas.events.mouse_release.connect(self._on_mouse_release)

        print("Verbindung für Drag-and-Drop aktiviert.")

    def _connect_click_based(self):
        print("Click-basierte Tools noch nicht implementiert.")

    def _on_mouse_press(self, event):
        print("Mouse pressed – starte Timer")
        self.tracker.start()

    def _on_mouse_release(self, event):
        print("Mouse released – stoppe Timer")
        self.tracker.stop()



t = None

@magicgui(call_button="Start Tracking")
def run():
    viewer = napari.current_viewer()
    global t
    t = ShapeTimeTracker(viewer)
    t.check_tool_type_and_connect()

def napari_experimental_provide_dock_widget():
    return run
