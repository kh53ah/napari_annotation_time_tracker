import time
import napari
import napari.viewer
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from qtpy import QtWidgets, QtGui, QtCore
from napari.layers import Image
from napari.utils.notifications import show_info
from qtpy.QtCore import QTimer, QEvent
from qtpy.QtWidgets import QApplication

"""
TO DO:
1. add pauses
2. timing for each different object
3. not automatically start tracing a new added points layer
"""

durations = []
pausen = []
start_time_of_plugin = time.time()
durationsOnImage = []
durationsOutOfImage = []

class PointsTimeTracker:
    """A class to track timing of point annotations in Napari."""

    def __init__(self, v):
        self.viewer = v
        self.points_layer = None
        self.start_time = None
        self.points_array_before = 0
        self.durations = []

    def get_current_points_layer(self, viewer):

        # Get currently selected layers
        selected_layers = list(viewer.layers.selection)

        # Find the first selected points layer
        for layer in selected_layers:
            if isinstance(layer, napari.layers.Points):
                return layer

        return None  # No points layer is selected

    def onClick_detector(self, viewer, event):

        self.start_time = time.time()
        yield

    def on_points_change(self, event):
        """Callback for when points data changes."""
        points_array_after = len(self.points_layer.data)

        if points_array_after > self.points_array_before and self.start_time is not None:
            duration = time.time() - self.start_time
            self.durations.append(duration)
            print(f"Point added! Duration: {duration:.3f} seconds")

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

"""
def pause():
    def trace_annotation_modes(viewer):
        Track when annotation tools are selected

        def setup_layer_mode_tracking(layer):
            the data of the layer (name and type)
            layer_name = layer.name  #the layer's name
            layer_type = type(layer).__name__   #the layer's type (image, point, ...)

            @layer.events.mode.connect
            def on_mode_change(event):
                mode = layer.mode #the interaction mode of this particular layer (what are the thing that can be done on it. Add, delete, zoom in- out, ...)

                print(f"Annotation mode changed in {layer_type} '{layer_name}': {mode}") #prints out, what mode got picked

                if hasattr(layer, 'mode'): #checks if the that layer has this mode (function)
                    if layer_type == 'Points' and mode in ['add', 'select', 'pan_zoom']:
                        print(f"  → Points annotation mode: {mode}")

                    #elif layer_type == 'Shapes' and mode in ['add_rectangle', 'add_ellipse', 'add_polygon', 'add_path',
                     #                                        'select', 'pan_zoom']:
                      #  print(f"  → Shapes annotation mode: {mode}")
                    #elif layer_type == 'Labels' and mode in ['paint', 'erase', 'fill', 'pick', 'pan_zoom']:
                     #   print(f"  → Labels annotation mode: {mode}")


        # Track existing layers
        for layer in viewer.layers:
            if hasattr(layer, 'mode'):  # Only layers with modes
                setup_layer_mode_tracking(layer)

        # Track new layers as they're added
        @viewer.layers.events.inserted.connect
        def on_layer_added(event):
            layer = event.value
            if hasattr(layer, 'mode'):
                setup_layer_mode_tracking(layer)
                print(f"Started tracking annotation modes for new {type(layer).__name__} layer: {layer.name}")

    # Usage
    viewer = napari.Viewer()
    trace_annotation_modes(viewer)

    # Add some layers to test
    points_layer = viewer.add_points(name="test_points")
    shapes_layer = viewer.add_shapes(name="test_shapes")
    labels_layer = viewer.add_labels(name="test_labels")


def end():
    end_time = time.time()
    totalTime = end_time - start_time_of_plugin
    totalDuration = 0.0
    for x in durations:
        totalDuration += x
    print(f"Your Annotation time was {totalDuration:.3f} seconds")
    pausenTime = totalTime - totalDuration
    print(f"Your pauses took {pausenTime:.3f} seconds")
    return durations



def mousePosition():

    show_info("Robust method working!")
    viewer = napari.current_viewer()

    # State tracking
    current_state = None
    state_start_time = None
    last_mouse_event = None  # Store locally instead of on viewer

    # Timer for periodic checks (helps catch missed events)
    check_timer = QTimer()

    def record_state_change(new_state):
        nonlocal current_state, state_start_time

        current_time = time.time()

        if current_state != new_state:
            # Record previous state duration
            if current_state is not None and state_start_time is not None:
                duration = current_time - state_start_time

                if current_state == 'on_image':
                    durationsOnImage.append(duration)
                    print(f"Time on image: {duration:.2f} seconds")
                else:
                    durationsOutOfImage.append(duration)
                    print(f"Time off image: {duration:.2f} seconds")

            # Update to new state
            current_state = new_state
            state_start_time = current_time
            print(f"State changed to: {new_state}")

    def is_mouse_on_image():

        /*
        Multiple methods to determine if mouse is on image
        Returns True if on image, False otherwise
        */

        try:
            qt_window = viewer.window._qt_window
            canvas_widget = viewer.window._qt_viewer.canvas.native

            # Method 1: Check canvas boundaries first
            global_pos = qt_window.cursor().pos()
            canvas_pos = canvas_widget.mapFromGlobal(global_pos)
            canvas_rect = canvas_widget.rect()

            if not canvas_rect.contains(canvas_pos):
                return False

            # Method 2: Check if widget under mouse is canvas-related
            app = QApplication.instance()
            widget_under_mouse = app.widgetAt(global_pos)

            if widget_under_mouse is None:
                return False

            # Check if the widget is the canvas or a child of canvas
            current_widget = widget_under_mouse
            is_canvas_related = False

            # Walk up the widget hierarchy to see if we find the canvas
            for _ in range(10):  # Limit depth to avoid infinite loops
                if current_widget is None:
                    break
                if current_widget == canvas_widget:
                    is_canvas_related = True
                    break
                current_widget = current_widget.parent()

            if not is_canvas_related:
                return False

            # Method 3: Check if over actual image data
            try:
                # Use napari's coordinate system
                world_coords = viewer.window._qt_viewer.canvas.map_to_world([canvas_pos.x(), canvas_pos.y()])

                # Check each visible image layer
                for layer in viewer.layers:
                    if isinstance(layer, napari.layers.Image) and layer.visible:
                        try:
                            data_coords = layer.world_to_data(world_coords)
                            if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                return True
                        except (IndexError, ValueError, AttributeError):
                            continue

            except Exception:
                # Fallback: use last known mouse event if coordinate conversion fails
                if last_mouse_event is not None and hasattr(last_mouse_event, 'position'):
                    if last_mouse_event.position is not None:
                        for layer in viewer.layers:
                            if isinstance(layer, napari.layers.Image) and layer.visible:
                                try:
                                    data_coords = layer.world_to_data(last_mouse_event.position)
                                    if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                        return True
                                except (IndexError, ValueError, AttributeError):
                                    continue

            return False

        except Exception as e:
            print(f"Error in is_mouse_on_image: {e}")
            return False

    def periodic_check():
        /*
        Periodic check to catch missed mouse events
        */
        try:
            on_image = is_mouse_on_image()
            new_state = 'on_image' if on_image else 'off_image'

            # Only record if state actually changed
            if current_state is None or current_state != new_state:
                record_state_change(new_state)

        except Exception as e:
            print(f"Error in periodic_check: {e}")

    # Connect the timer
    check_timer.timeout.connect(periodic_check)
    check_timer.start(50)  # Check every 50ms

    @viewer.mouse_move_callbacks.append
    def on_mouse_move(viewer, event):
        /*
        Main mouse move callback
        */
        nonlocal last_mouse_event

        try:
            # Store the event locally
            last_mouse_event = event

            # Check if on image
            on_image = is_mouse_on_image()
            new_state = 'on_image' if on_image else 'off_image'

            record_state_change(new_state)

        except Exception as e:
            print(f"Error in on_mouse_move: {e}")

    # Store timer reference for cleanup (create a simple namespace)
    if not hasattr(viewer, '_mouse_trackers'):
        viewer._mouse_trackers = {}
    viewer._mouse_trackers['timer'] = check_timer

    print("Robust mouse tracking initialized")

def mousePositionSimple():

    show_info("Simple method working!")
    viewer = napari.current_viewer()

    current_state = None
    state_start_time = None

    def record_state_change(new_state):
        nonlocal current_state, state_start_time

        current_time = time.time()

        if current_state != new_state:
            if current_state is not None and state_start_time is not None:
                duration = current_time - state_start_time

                if current_state == 'on_image':
                    durationsOnImage.append(duration)
                    print(f"Time on image: {duration:.2f} seconds")
                else:
                    durationsOutOfImage.append(duration)
                    print(f"Time off image: {duration:.2f} seconds")

            current_state = new_state
            state_start_time = current_time
            print(f"State changed to: {new_state}")

    @viewer.mouse_move_callbacks.append
    def on_mouse_move(viewer, event):
        try:
            on_image = False

            if hasattr(event, 'position') and event.position is not None:
                # Get Qt components
                qt_window = viewer.window._qt_window
                canvas_widget = viewer.window._qt_viewer.canvas.native

                # Check if mouse is within canvas bounds
                global_pos = qt_window.cursor().pos()
                canvas_pos = canvas_widget.mapFromGlobal(global_pos)

                # Simple boundary check
                if (0 <= canvas_pos.x() <= canvas_widget.width() and
                        0 <= canvas_pos.y() <= canvas_widget.height()):

                    # Check if over image data
                    cursor_position = event.position
                    for layer in viewer.layers:
                        if isinstance(layer, napari.layers.Image) and layer.visible:
                            try:
                                data_coords = layer.world_to_data(cursor_position)
                                if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                    on_image = True
                                    break
                            except (IndexError, ValueError, AttributeError):
                                continue

            new_state = 'on_image' if on_image else 'off_image'
            record_state_change(new_state)

        except Exception as e:
            print(f"Error in simple mouse move: {e}")

    print("Simple mouse tracking initialized")


def mousePositionDebounced():

    show_info("Debounced method working!")
    viewer = napari.current_viewer()

    current_state = None
    state_start_time = None
    pending_state = None
    last_event = None

    # Create timer for debouncing
    debounce_timer = QTimer()
    debounce_timer.setSingleShot(True)
    DEBOUNCE_DELAY = 150  # milliseconds

    def record_state_change(new_state):
        nonlocal current_state, state_start_time

        current_time = time.time()

        if current_state != new_state:
            if current_state is not None and state_start_time is not None:
                duration = current_time - state_start_time

                if current_state == 'on_image':
                    durationsOnImage.append(duration)
                    print(f"Time on image: {duration:.2f} seconds")
                else:
                    durationsOutOfImage.append(duration)
                    print(f"Time off image: {duration:.2f} seconds")

            current_state = new_state
            state_start_time = current_time
            print(f"State changed to: {new_state}")

    def commit_state_change():

        if pending_state is not None:
            record_state_change(pending_state)

    def check_position(event):

        try:
            on_image = False

            if hasattr(event, 'position') and event.position is not None:
                qt_window = viewer.window._qt_window
                canvas_widget = viewer.window._qt_viewer.canvas.native

                # Canvas boundary check
                global_pos = qt_window.cursor().pos()
                canvas_pos = canvas_widget.mapFromGlobal(global_pos)
                canvas_rect = canvas_widget.rect()

                if canvas_rect.contains(canvas_pos):
                    # Image data check
                    for layer in viewer.layers:
                        if isinstance(layer, napari.layers.Image) and layer.visible:
                            try:
                                data_coords = layer.world_to_data(event.position)
                                if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                    on_image = True
                                    break
                            except (IndexError, ValueError, AttributeError):
                                continue

            return on_image

        except Exception as e:
            print(f"Error checking position: {e}")
            return False

    # Connect timer
    debounce_timer.timeout.connect(commit_state_change)

    @viewer.mouse_move_callbacks.append
    def on_mouse_move(viewer, event):
        nonlocal pending_state, last_event

        try:
            last_event = event
            on_image = check_position(event)
            new_state = 'on_image' if on_image else 'off_image'

            if new_state != current_state:
                pending_state = new_state
                debounce_timer.start(DEBOUNCE_DELAY)  # Restart timer

        except Exception as e:
            print(f"Error in debounced mouse move: {e}")

    # Store timer reference
    if not hasattr(viewer, '_mouse_trackers'):
        viewer._mouse_trackers = {}
    viewer._mouse_trackers['debounce_timer'] = debounce_timer

    print("Debounced mouse tracking initialized")


def cleanup_mouse_tracking(viewer):

    if hasattr(viewer, '_mouse_trackers'):
        for name, timer in viewer._mouse_trackers.items():
            if timer is not None:
                timer.stop()
                timer.deleteLater()
        delattr(viewer, '_mouse_trackers')
    print("Mouse tracking cleaned up")
"""