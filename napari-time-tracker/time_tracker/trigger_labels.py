from PyQt5.QtCore import QObject
from napari.layers.labels._labels_constants import Mode
from napari.utils.notifications import show_info
from .labels_time import LabelTimeTracker
from napari.layers.labels import Labels



class LabelsStart(QObject):
    #dock widget to start/stop timing
    #Functions: start_tracking:  Wire up mouse events for the active Labels layer.
    #_on_press: Begin a new stroke timer when pressing down.
    # _on_release: Stop the stroke timer and update display.
    #_update_log: Refresh QTextEdit with per-label totals.
    #_print_report: Show a Napari notification of totals.
    #return_label_times: Expose raw stroke durations to external code.
    #return_annotation_data: return List of layer, label_id, time for external code
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self._tracker = LabelTimeTracker()
        self._press_conn = None
        self._release_conn = None
        self._double_press_conn = None
        self._last_label = None

    def start(self):
        layer = self.viewer.layers.selection.active
        if not isinstance(layer, Labels):
            show_info("Please select a Labels layer to track.")
            return
        if Mode(layer.mode) == Mode.PAN_ZOOM:
            show_info("Cannot track in Pan/Zoom mode.")
            return
        canvas = self.viewer.window.qt_viewer.canvas
        if self._press_conn is None:
            self._press_conn = canvas.events.mouse_press.connect(self._on_press)
            self._release_conn = canvas.events.mouse_release.connect(self._on_release)
            self._double_conn = canvas.events.mouse_double_click.connect(self._on_double_click)
            show_info("Label time tracking started.")
        else:
            show_info("Label tracking already running.")


def _on_press(self, event):
    layer = self.viewer.layers.selection.active
    mode = Mode(layer.mode)
    label = layer.selected_label
    if mode in (Mode.PAINT, Mode.FILL, Mode.ERASE, Mode.POLYGON) and not self._tracker.active:
        self._last_label = label
        self._tracker.start(label)

    def _on_release(self, event):
        layer = self.viewer.layers.selection.active
        mode = Mode(layer.mode)
        if mode in (Mode.PAINT, Mode.FILL, Mode.ERASE) and self._tracker.active:
            elapsed = self._tracker.stop()
            label = self._last_label
            total = self._tracker.report().get(label, 0.0)
            show_info(f"Label {label}: +{elapsed:.2f}s (total {total:.2f}s)")
            self._last_label = None

    def _on_double_click(self, event):
        layer = self.viewer.layers.selection.active
        mode = Mode(layer.mode)
        if mode == Mode.POLYGON and self._tracker.active:
            elapsed = self._tracker.stop()
            label = self._last_label
            total = self._tracker.report().get(label, 0.0)
            show_info(f"Label {label}: +{elapsed:.2f}s (total {total:.2f}s)")
            self._last_label = None

    def get_time_map(self):
        return self._tracker.report()



