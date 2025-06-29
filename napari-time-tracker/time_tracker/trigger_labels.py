import time
import warnings
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit
import napari
from napari_plugin_engine import napari_hook_implementation
from napari.layers import Labels
from napari.layers.labels._labels_constants import Mode
from napari.utils.notifications import show_info
from .labels_time import LabelTimeTracker



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
        self._annotation_data = []

        # UI setup
        layout = QVBoxLayout()
        self._log = QTextEdit(readOnly=True)
        layout.addWidget(self._log)

        btn_start = QPushButton("Start Tracking")
        btn_start.clicked.connect(self._start_tracking)
        layout.addWidget(btn_start)

        btn_report = QPushButton("Report Times")
        btn_report.clicked.connect(self._print_report)
        layout.addWidget(btn_report)

        self.setLayout(layout)

    def _start_tracking(self):
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
            show_info("Annotation time tracking started.")
        else:
            show_info("Tracking already running.")

    def _on_press(self, event):
        layer = self.viewer.layers.selection.active
        tool = layer.selected_tool
        if tool in ('paintbrush', 'polygon', 'fill', 'eraser'):
            label_id = layer.selected_label if tool != 'eraser' else event.value
            self._tracker.start(label_id)

    def _on_release(self, event):
        elapsed = self._tracker.stop()
        layer = self.viewer.layers.selection.active
        label_id = None
        self.annotation_data.append({
            'layer': layer,
            'label_id': label_id,
            'time': elapsed
        })
        # update live log
        self._update_log()
        # (External code can fetch individual times via return_times)

    def _update_log(self):
        times = self._tracker.report()
        lines = [f"Label {lbl}: {t:.2f} s" for lbl, t in sorted(times.items())]
        self._log.setText("\n".join(lines))

    def _print_report(self):
        times = self._tracker.report()
        show_info("Times per label: " + str(times))

    def return_annotation_data(self):
        return list(self._annotation_data)

    def return_label_times(self):
        """
        Return the list of individual stroke durations (seconds).
        """
        return self._tracker.return_times()


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return AnnotationTimerWidget
