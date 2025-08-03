import time
import napari
import napari.viewer
from napari.layers import Image
from napari.utils.notifications import show_info
import numpy as np


class PointsTimeTracker:
    """
    A class to track timing of point annotations in Napari.

    This tracker measures the time taken to create individual point annotations,
    from the moment a mouse drag begins until a new point is added to the layer.
    The timing data is stored in a nested dictionary structure mapping layers
    to point object IDs and their corresponding creation times.

    Handles point deletions by using coordinate-based fallback to preserve timing data.

    Workflow:
    1. User selects a points layer and calls start()
    2. Mouse drag events trigger timing start
    3. When new points are added, timing stops and duration is recorded
    4. When points are deleted, coordinates are compared to identify deleted points
    5. Timing data for deleted points is removed from the map
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
        self.previous_points_data = None  # Store previous point coordinates

        # Data storage: {layer: {point_object_id: creation_time}}
        # Note: Using object IDs has limitations due to memory address instability
        self.timeMap = {}

        # Additional storage to help with object ID instability
        self.coordinate_to_timing = {}  # Fallback mapping: {layer: {coordinate_tuple: timing}}

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

    def find_deleted_points(self, old_points, new_points):
        """
        Compare old and new point arrays to find which points were deleted.

        Args:
            old_points (np.ndarray): Previous point coordinates (self.previous_points_data)
            new_points (np.ndarray): Current point coordinates

        Returns:
            list: Indices of points that were deleted from old_points
        """
        if len(old_points) == 0:
            return []

        if len(new_points) == 0:
            # All points were deleted
            return list(range(len(old_points)))

        deleted_indices = []

        # For each old point, check if it still exists in new points
        for old_idx, old_point in enumerate(old_points):
            point_still_exists = False

            # Compare with all new points (allowing for small floating point differences)
            for new_point in new_points:
                if np.allclose(old_point, new_point, rtol=1e-9, atol=1e-9):
                    point_still_exists = True
                    break

            if not point_still_exists:
                deleted_indices.append(old_idx)

        return deleted_indices

    def handle_deletion_with_object_ids(self, deleted_indices):
        """
        Handle point deletion when using object IDs as keys.
        Since object IDs change after array modifications, we use coordinate-based fallback.

        Args:
            deleted_indices (list): Indices of points that were deleted
        """
        if self.points_layer not in self.coordinate_to_timing:
            return

        # Remove timing data for deleted coordinates
        deleted_coordinates = set()
        if self.previous_points_data is not None:
            for idx in deleted_indices:
                if idx < len(self.previous_points_data):
                    coord_tuple = tuple(self.previous_points_data[idx])
                    deleted_coordinates.add(coord_tuple)

        # Clean up coordinate-based timing
        current_coord_timing = self.coordinate_to_timing[self.points_layer].copy()
        for coord_tuple in deleted_coordinates:
            if coord_tuple in current_coord_timing:
                del current_coord_timing[coord_tuple]
        self.coordinate_to_timing[self.points_layer] = current_coord_timing

        # Rebuild object ID mapping from coordinate mapping
        new_timing = {}
        if len(self.points_layer.data) > 0:
            for idx, point in enumerate(self.points_layer.data):
                coord_tuple = tuple(point)
                if coord_tuple in current_coord_timing:
                    point_obj = self.points_layer.data[idx]
                    new_object_id = id(point_obj)
                    new_timing[new_object_id] = current_coord_timing[coord_tuple]

        # Update the object ID timing map
        self.timeMap[self.points_layer] = new_timing

    def on_points_change(self, event):
        """
        Callback for when points data changes in the tracked layer.

        This method is triggered whenever the points array is modified.
        It handles both point additions and deletions by comparing
        point coordinates to detect what changed.

        Args:
            event: Napari event object containing information about the data change
        """
        # Get current points data
        current_points = self.points_layer.data.copy() if len(self.points_layer.data) > 0 else np.array([])
        points_array_after = len(current_points)

        # Handle point addition
        if points_array_after > self.points_array_before and self.start_time is not None:
            # Calculate how long it took to create this point
            duration = time.time() - self.start_time

            # Select the newly created point (last in array)
            self.points_layer.selected_data = {points_array_after - 1}

            # Store the timing data for this point
            self.map_time(duration)

            # Update state for next annotation
            self.points_array_before = points_array_after
            self.previous_points_data = current_points.copy()
            self.start_time = None  # Reset timing

        # Handle point deletion
        elif points_array_after < self.points_array_before:
            if self.previous_points_data is not None:
                # Find which points were deleted by comparing coordinates
                deleted_indices = self.find_deleted_points(self.previous_points_data, current_points)

                if deleted_indices:
                    # Update timing map to handle object ID changes after deletion
                    self.handle_deletion_with_object_ids(deleted_indices)

            # Update state
            self.points_array_before = points_array_after
            self.previous_points_data = current_points.copy()

        # Handle case where number of points stayed the same (point moved)
        elif points_array_after == self.points_array_before:
            # Just update the stored points data
            self.previous_points_data = current_points.copy()

    def start(self):
        """
        Initialize and start the point annotation timer.

        This method:
        1. Finds the currently selected points layer
        2. Records the initial number of points
        3. Stores initial point coordinates
        4. Connects the necessary event callbacks
        5. Shows user feedback about the tracking state

        Returns:
            None: Exits early if no points layer is selected
        """
        # Notify user that tracking has started
        show_info("You started annotating with points")

        # Find the currently selected points layer
        self.points_layer = self.get_current_points_layer(self.viewer)

        # Validate that a points layer is available
        if self.points_layer is None:
            return

        # Record initial state (number of existing points and their coordinates)
        self.points_array_before = len(self.points_layer.data)
        self.previous_points_data = self.points_layer.data.copy() if len(self.points_layer.data) > 0 else np.array([])

        # Connect event callbacks for tracking
        # Mouse drag callback to detect annotation start
        self.viewer.mouse_drag_callbacks.append(self.onClick_detector)
        # Points data change callback to detect annotation completion
        self.points_layer.events.data.connect(self.on_points_change)

    def map_time(self, t):
        """
        Store the annotation time for a specific point in the current layer.

        This method creates a nested dictionary structure that maps:
        - Layer -> Point Object ID -> Creation Time

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

        # Store timing with object ID
        self.timeMap[current_layer][point_id] = t

        # Also store coordinate-based mapping as backup
        if current_layer not in self.coordinate_to_timing:
            self.coordinate_to_timing[current_layer] = {}
        coordinate_tuple = tuple(point_obj)
        self.coordinate_to_timing[current_layer][coordinate_tuple] = t

        print(self.timeMap)

    def get_time_map(self):
        """
        Retrieve the complete timing data for all tracked points.

        Returns:
            dict: Nested dictionary with structure:
                  {layer: {point_object_id: creation_time}}
                  where:
                  - layer: napari.layers.Points instance
                  - point_object_id: int (memory address/ID of the point object)
                  - creation_time: float (seconds taken to create the point)

        Note: Object IDs may not be stable across array operations.
              Use get_coordinate_timing_map() for more reliable coordinate-based mapping.
        """
        return self.timeMap

    def get_coordinate_timing_map(self):
        """
        Retrieve timing data mapped by coordinates instead of object IDs.
        This provides a more stable mapping that survives array operations.

        Returns:
            dict: Nested dictionary with structure:
                  {layer: {coordinate_tuple: creation_time}}
                  where:
                  - layer: napari.layers.Points instance
                  - coordinate_tuple: tuple of point coordinates
                  - creation_time: float (seconds taken to create the point)
        """
        return self.coordinate_to_timing