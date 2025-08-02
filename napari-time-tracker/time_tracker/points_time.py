import time
import napari
import napari.viewer
from napari.layers import Image
from napari.utils.notifications import show_info


class PointsTimeTracker:
    """
    A class to track timing of point annotations in Napari.

    This tracker measures the time taken to create individual point annotations,
    from the moment a mouse drag begins until a new point is added to the layer.
    The timing data is stored in a nested dictionary structure mapping layers
    to point indices and their corresponding creation times.

    Workflow:
    1. User selects a points layer and calls start()
    2. Mouse drag events trigger timing start
    3. When new points are added, timing stops and duration is recorded
    4. Times are mapped to specific point indices for later retrieval
    """

    def __init__(self, v):
        """
        Initialize the PointsTimeTracker.

        Args:
            v (napari.Viewer): The napari viewer instance to track
        """
        # Core viewer reference
        self.viewer = v

        # Layer tracking
        self.points_layer = None  # Currently tracked points layer

        # Timing variables
        self.start_time = None  # Timestamp when mouse drag begins
        self.points_array_before = 0  # Number of points before current annotation

        # Data storage: {layer: {point_index: creation_time}}
        self.timeMap = {}

    def get_current_points_layer(self, viewer):
        """
        Find the first selected points layer in the viewer.

        Searches through currently selected layers to find a points layer
        that can be used for annotation timing.

        Args:
            viewer (napari.Viewer): The napari viewer to search

        Returns:
            napari.layers.Points or None: The first selected points layer,
                                         or None if no points layer is selected
        """
        # Get currently selected layers
        selected_layers = list(viewer.layers.selection)

        # Find the first selected points layer
        for layer in selected_layers:
            if isinstance(layer, napari.layers.Points):
                return layer

        return None  # No points layer is selected

    def onClick_detector(self, viewer, event):
        """
        Mouse drag callback to detect the start of point annotation.

        This generator function is called when mouse drag events occur.
        It records the start time when the left mouse button (button 1)
        is pressed, indicating the beginning of a point annotation action.

        Args:
            viewer (napari.Viewer): The napari viewer instance
            event: Mouse drag event containing button information and position

        Yields:
            None: Required for napari callback generator protocol
        """
        # Check if left mouse button is pressed (button 1)
        if event.button == 1:
            # Record the timestamp when annotation begins
            self.start_time = time.time()
        yield  # Required for napari callback generators

    def on_points_change(self, event):
        """
        Callback for when points data changes in the tracked layer.

        This method is triggered whenever the points array is modified.
        If a new point was added and timing was active, it calculates
        the duration, selects the new point, and stores the timing data.

        Args:
            event: Napari event object containing information about the data change
        """
        # Get current number of points in the layer
        points_array_after = len(self.points_layer.data)

        # Check if a new point was added and timing is active
        if points_array_after > self.points_array_before and self.start_time is not None:
            # Calculate how long it took to create this point
            duration = time.time() - self.start_time

            # Select the newly created point (last in array)
            self.points_layer.selected_data = {points_array_after - 1}

            # Store the timing data for this point
            self.map_time(duration)

            # Update state for next annotation
            self.points_array_before = points_array_after
            self.start_time = None  # Reset timing

    def start(self):
        """
        Initialize and start the point annotation timer.

        This method:
        1. Finds the currently selected points layer
        2. Records the initial number of points
        3. Connects the necessary event callbacks
        4. Shows user feedback about the tracking state

        Returns:
            None: Exits early if no points layer is selected
        """
        # Notify user that tracking has started
        show_info("You started annotating with points")

        # Find the currently selected points layer
        self.points_layer = self.get_current_points_layer(self.viewer)

        # Validate that a points layer is available
        if self.points_layer is None:
            show_info("No points layer selected!")
            return

        # Record initial state (number of existing points)
        self.points_array_before = len(self.points_layer.data)

        # Connect event callbacks for tracking
        # Mouse drag callback to detect annotation start
        self.viewer.mouse_drag_callbacks.append(self.onClick_detector)
        # Points data change callback to detect annotation completion
        self.points_layer.events.data.connect(self.on_points_change)

    def map_time(self, t):
        """
        Store the annotation time for a specific point in the current layer.

        This method creates a nested dictionary structure that maps:
        - Layer -> Point Index -> Creation Time

        The timing is only stored if exactly one point is selected,
        ensuring accurate mapping to the correct point.

        Args:
            t (float): The time duration (in seconds) taken to create the point
        """
        current_layer = list(self.viewer.layers.selection)[0]
        selected = current_layer.selected_data

        if len(selected) != 1:
            return

        point_index = next(iter(selected))
        point_obj = current_layer.data[point_index]
        point_id = id(point_obj)

        if current_layer not in self.timeMap:
            self.timeMap[current_layer] = {}

        self.timeMap[current_layer][point_id] = t
        print(self.timeMap)

    def get_time_map(self):
        """
        Retrieve the complete timing data for all tracked points.

        Returns:
            dict: Nested dictionary with structure:
                  {layer: {point_index: creation_time}}
                  where:
                  - layer: napari.layers.Points instance
                  - point_index: int (index of the point in the layer)
                  - creation_time: float (seconds taken to create the point)
        """
        return self.timeMap