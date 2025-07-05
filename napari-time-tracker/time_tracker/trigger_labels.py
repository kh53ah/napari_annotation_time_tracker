from qtpy.QtCore import QObject
from napari.utils.notifications import show_info
from napari.layers.labels._labels_constants import Mode

from .labels_time import LabelTimeTracker


class LabelsStart(QObject):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self._tracker = LabelTimeTracker()
        self._press_conn = None
        self._release_conn = None
        self._double_conn = None

        self._last_label = None

        # attributs needed for mode changes
        self._connected_labels_layer = None

    def start(self):
        self._connected_labels_layer = list(self.viewer.layers.selection)[0]
        self._connected_labels_layer.events.mode.connect(self._on_mode_change)
        self._attach_handlers()

        show_info("Label time tracking started. Switch to an annotation tool to begin timing.")

    def _attach_handlers(self):
        canvas = self.viewer.window.qt_viewer.canvas
        if self._press_conn is None:
            self._press_conn = canvas.events.mouse_press.connect(self._on_press)
        if self._release_conn is None:
            self._release_conn = canvas.events.mouse_release.connect(self._on_release)
        if self._double_conn is None:
            self._double_conn = canvas.events.mouse_double_click.connect(self._on_double_click)

    def _disconnect_handlers(self):
        canvas = self.viewer.window.qt_viewer.canvas
        try:
            if self._press_conn:
                canvas.events.mouse_press.disconnect(self._press_conn)
                self._press_conn = None
            if self._release_conn:
                canvas.events.mouse_release.disconnect(self._release_conn)
                self._release_conn = None
            if self._double_conn:
                canvas.events.mouse_double_click.disconnect(self._double_conn)
                self._double_conn = None
            if self._connected_labels_layer is not None:
                self._connected_labels_layer.events.mode.disconnect(self._on_mode_change)
                self._connected_labels_layer = None

        except Exception as e:
            show_info(f"Error disconnecting handlers: {e}")

    def _on_mode_change(self, event):
        if self._tracker.active:
            self._tracker.stop()
        self._disconnect_handlers()
        self.start()

    def _on_press(self, event):
        mode = Mode(self._connected_labels_layer.mode)
        if mode not in (Mode.PAINT, Mode.FILL, Mode.ERASE, Mode.POLYGON):
            return
        label = self._connected_labels_layer.selected_label
        if not self._tracker.active and label is not None:
            self._last_label = label
            self._tracker.start(label)

    def _on_release(self, event):
        if not self._tracker.active:
            return
        mode = Mode(self._connected_labels_layer.mode)
        if mode in (Mode.PAINT, Mode.FILL, Mode.ERASE):
            self._stop_and_print()

    def _on_double_click(self, event):
        if not self._tracker.active:
            return
        mode = Mode(self._connected_labels_layer.mode)
        if mode == Mode.POLYGON:
            self._stop_and_print()

    def _stop_and_print(self):
        elapsed = self._tracker.stop()
        label = self._last_label
        total = self._tracker.report().get(label, 0.0)
        self._last_label = None

    def get_time_map(self):
        return self._tracker.report()
