import time
import warnings
warnings.filterwarnings(
    "ignore",
    message="Public access to Window.qt_viewer is deprecated"
)

import napari
from napari.layers import Labels
from napari.layers.labels._labels_constants import Mode
from napari.utils.notifications import show_info
from magicgui import magicgui
from .labels_time import LabelMouseTracker

# utility to get the Napari canvas
def _get_canvas(viewer):
     try:
         return viewer.window.qt_viewer.canvas
     except AttributeError:
         return viewer.window._qt_viewer.canvas

# core connector class
class LabelTimeConnector:
    def __init__(self, viewer):
        self.viewer = viewer
        self.tracker = LabelMouseTracker(viewer)
        self._press = None
        self._leave = None

    def start(self):
        """
        Hook up mouse press and leave events on the active Labels layer canvas to track time per label.
        """
        selected = list(self.viewer.layers.selection)
        if len(selected) != 1 or not isinstance(selected[0], Labels):
            show_info("No valid Labels layer selected")
            return
        layer = selected[0]
        mode = Mode(layer.mode)
        # ignore pan/zoom
        if mode == Mode.PAN_ZOOM:
            return
        canvas = _get_canvas(self.viewer)
        # connect press to start tracking
        self._press = canvas.events.mouse_press.connect(self._on_press)
        # connect leave to stop tracking
        self._leave = canvas.events.mouse_leave.connect(self._on_leave)
        show_info("Label time tracking started")

    def _on_press(self, event):
        """Start timing when user presses on the canvas."""
        layer = self.viewer.layers.selection.active
        self.tracker.start(layer.selected_label)

    def _on_leave(self, event):
        """Stop timing when mouse leaves the canvas."""
        self.tracker.stop()
        # disconnect events
        canvas = _get_canvas(self.viewer)
        canvas.events.mouse_press.disconnect(self._press)
        canvas.events.mouse_leave.disconnect(self._leave)
        self._press = None
        self._leave = None

@magicgui(call_button="Start Label Time Tracking")
def start_label_time_tracking():
    viewer = napari.current_viewer()
    connector = LabelTimeConnector(viewer)
    connector.start()

# Napari entrypoint
def napari_experimental_provide_dock_widget():
    return start_label_time_tracking
