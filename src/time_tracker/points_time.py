import time
import napari
import napari.viewer
from napari.layers import Image
from napari.utils.notifications import show_info

class PointsTimeTracker:
    """A class to track timing of point annotations in Napari."""

    def __init__(self, v):
        self.viewer = v
        self.points_layer = None
        self.start_time = None
        self.points_array_before = 0
        self.timeMap = {}

    def get_current_points_layer(self, viewer):

        # Get currently selected layers
        selected_layers = list(viewer.layers.selection)

        # Find the first selected points layer
        for layer in selected_layers:
            if isinstance(layer, napari.layers.Points):
                return layer

        return None  # No points layer is selected

    def onClick_detector(self, viewer, event):
        if event.button == 1:
            self.start_time = time.time()
        yield

    def on_points_change(self, event):
        """Callback for when points data changes."""
        points_array_after = len(self.points_layer.data)

        if points_array_after > self.points_array_before and self.start_time is not None:
            duration = time.time() - self.start_time
            self.points_layer.selected_data = {points_array_after - 1}
            self.map_time(duration)
            self.points_array_before = points_array_after
            self.start_time = None

    def start(self):
        """Initialize and start the point annotation timer."""
        show_info("You started annotating with points")

        self.points_layer = self.get_current_points_layer(self.viewer)

        if self.points_layer is None:
            show_info("No points layer selected!")
            return

        self.points_array_before = len(self.points_layer.data)

        # Connect the callbacks
        self.viewer.mouse_drag_callbacks.append(self.onClick_detector)
        self.points_layer.events.data.connect(self.on_points_change)

    def map_time(self, t):
        current_layer = list(self.viewer.layers.selection)[0]
        selected = current_layer.selected_data

        if len(selected) != 1: return

        object_id = next(iter(selected))  # int, geeignet als Dictionary-Key

        if current_layer not in self.timeMap:
            self.timeMap[current_layer] = {}

        self.timeMap[current_layer][object_id] = t
        print(self.timeMap)
    def get_time_map(self):
        return self.timeMap