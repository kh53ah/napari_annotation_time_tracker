from qtpy.QtCore import QObject
from napari.utils.notifications import show_info
from napari.layers.labels._labels_constants import Mode
from napari.layers.labels import Labels

from .labels_time import LabelTimeTracker
import time

class LabelsStart(QObject):
    """
        Tracks the time spent annotating labels in a napari Labels layer.

        Connects to mouse and mode events to start and stop timing when the user paints,
        fills, erases, or draws polygons on labels. Maintains a nested map of layer -> label_id ->
        [first_start_timestamp, last_end_timestamp, total_time_seconds].
        """
    def __init__(self, viewer):
        """
        Initialize the LabelsStart tracker.

        Parameters
        ----------
        viewer : napari.Viewer
        The napari viewer instance to attach event handlers to.
        """
        super().__init__()
        self.viewer = viewer
        self._tracker = LabelTimeTracker()
        self._press_conn = None
        self._release_conn = None
        self._double_conn = None
        self._mode_conn = None
        self._last_label = None

        # Nested map[layer][label_id] -> [first_start, last_end, total_time]
        self.timeMap = {}

    def start(self):
        """
        Activate tracking on the currently selected Labels layer.

        If the active layer is not a Labels layer, nothing happens. Otherwise,
        connect to the layer's mode change event and attach mouse event handlers
        to the canvas.
        """
        layer = self.viewer.layers.selection.active
        if not isinstance(layer, Labels):
            return
        if self._mode_conn is None:
            self._mode_conn = layer.events.mode.connect(self._on_mode_change)
        self._attach_handlers()

    def _attach_handlers(self):
        """
        Attach mouse press, release, and double-click event handlers
        to the viewer canvas if not already connected.
        """
        canvas = self.viewer.window.qt_viewer.canvas
        if self._press_conn is None:
            self._press_conn = canvas.events.mouse_press.connect(self._on_press)
        if self._release_conn is None:
            self._release_conn = canvas.events.mouse_release.connect(self._on_release)
        if self._double_conn is None:
            self._double_conn = canvas.events.mouse_double_click.connect(self._on_double_click)

    def _disconnect_handlers(self):
        """
        Disconnect previously attached mouse event handlers from the canvas.
        Any errors during disconnect are caught and shown as notifications.
        """
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
        except Exception as e:
            show_info(f"Error disconnecting handlers: {e}")

    def _on_mode_change(self, event):
        """
        Handle changes in the Labels layer's mode.
        Stops any active timing tracker and re-attaches mouse event handlers
        to ensure timing only occurs for supported modes.

        Parameters
        ----------
        event : napari.utils.notifications.Event
        The mode change event.
        """
        if self._tracker.active:
            self._tracker.stop()
        self._disconnect_handlers()
        self._attach_handlers()

    def _on_press(self, event):
        """
        Handle mouse press events. Start timing if the active mode and layer
        support label editing.

        Parameters
        ----------
        event : napari.utils.notifications.Event
            The mouse press event containing positional and button info.
        """
        layer = self.viewer.layers.selection.active
        if not isinstance(layer, Labels):
            return
        mode = Mode(layer.mode)
        if mode not in (Mode.PAINT, Mode.FILL, Mode.ERASE, Mode.POLYGON):
            return
        label = layer.selected_label
        if not self._tracker.active and label is not None:
            self._last_label = label
            # Record start timestamp
            self._start_time = time.time()
            self._tracker.start(label)

    def _on_release(self, event):
        """
        Handle mouse release events. Stop timing for painting, filling, or erasing.

        Parameters
        ----------
        event : napari.utils.notifications.Event
            The mouse release event.
        """
        if not self._tracker.active:
            return
        layer = self.viewer.layers.selection.active
        mode = Mode(layer.mode)
        if mode in (Mode.PAINT, Mode.FILL, Mode.ERASE):
            self._stop_and_record()

    def _on_double_click(self, event):
        """
        Handle mouse double-click events. Stop timing for polygon tool.

        Parameters
        ----------
        event : napari.utils.notifications.Event
            The double-click event.
        """
        if not self._tracker.active:
            return
        layer = self.viewer.layers.selection.active
        mode = Mode(layer.mode)
        if mode == Mode.POLYGON:
            self._stop_and_record()

    def _stop_and_record(self):
        """
        Stop the LabelTimeTracker, record timing information, and update the timeMap.

        This records first start time if it's the first interaction with the label,
        updates the last end timestamp, and stores the cumulative time spent on the label.
        """
        self._tracker.stop()
        label = self._last_label
        end_time = time.time()
        total = self._tracker.report().get(label, 0.0)
        current_layer = self.viewer.layers.selection.active

        # Initialize structure for layer if missing
        if current_layer not in self.timeMap:
            self.timeMap[current_layer] = {}

        # If first time for this label, record start timestamp
        if label not in self.timeMap[current_layer]:
            first_start = self._start_time
        else:
            first_start = self.timeMap[current_layer][label][0]

        # Update entry: [first_start, last_end, total]
        self.timeMap[current_layer][label] = [first_start, end_time, total]

        print(self.timeMap)
        self._last_label = None

    def get_time_map(self):
        return self.timeMap


