from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit
from napari_plugin_engine import napari_hook_implementation
from napari.layers.labels._labels_constants import Mode
from napari.utils.notifications import show_info
from .labels_time import LabelTimeTracker
from napari.layers.labels import Labels



class AnnotationTimerWidget(QWidget):
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
        self._time_map = {}

    def start(self):
        # find active Labels layer
        layer = self.viewer.layers.selection.active
        if not isinstance(layer, Labels):
            show_info("Please select a Labels layer to track.")
            return
        mode = Mode(layer.mode)
        if mode == Mode.PAN_ZOOM:
            show_info("Cannot track in Pan/Zoom mode.")
            return
        canvas = self.viewer.window.qt_viewer.canvas
        # connect events
        if self._press_conn is None:
            self._press_conn = canvas.events.mouse_press.connect(self._on_press)
            self._release_conn = canvas.events.mouse_release.connect(self._on_release)
            self._double_press_conn = canvas.events.mouse_double_click.connect(self._on_double_click)
            show_info("Annotation time tracking started.")
        else:
            show_info("Tracking already running.")

    def _on_press(self, event):
        layer = self.viewer.layers.selection.active
        tool = layer.selected_tool
        label_id = layer.selected_label
        if not self._tracker.active and tool in ('paintbrush', 'fill', 'eraser', 'polygon'):
            self._tracker.start(label_id)

    def _on_release(self, event):
        layer = self.viewer.layers.selection.active
        tool = layer.selected_tool
        if tool in ('paintbrush', 'fill', 'eraser') and self._tracker.active:
            elapsed = self._tracker.stop()
            show_info(f"Label {layer.selected_label}: +{elapsed:.2f}s (total {self._tracker.report()[layer.selected_label]:.2f}s)")

    def _on_double_click(self, event):
        layer = self.viewer.layers.selection.active
        tool = layer.selected_tool
        if tool == 'polygon' and self._tracker.active:
            elapsed = self._tracker.stop()
            self._record_event(self._last_label, elapsed, layer)
            self._last_label = None
            self._update_log()

    def _update_log(self):
        times = self._tracker.report()
        lines = [f"Label {lbl}: {t:.2f} s" for lbl, t in sorted(times.items())]
        self._log.setText("\n".join(lines))

    def _print_report(self):
        times = self._tracker.report()
        show_info("Times per label: " + str(times))

    def return_annotation_data(self):
        return self._tracker.report()




@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return AnnotationTimerWidget
