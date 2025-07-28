import time
import napari
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication


class PauseTimeTracker:
    """
    A class to track the time spent with the mouse cursor on/off image data in a napari viewer.

    This tracker monitors mouse position relative to visible image layers and accumulates
    time durations for both states: when the cursor is over image data ('on_image') and
    when it's not ('off_image').

    The tracking uses multiple detection methods:
    1. Qt-based canvas boundary checking
    2. Widget hierarchy verification
    3. Image data coordinate mapping
    4. Periodic fallback checks to catch missed events
    """

    def __init__(self, viewer=None):
        """
        Initialize the PauseTimeTracker.

        Args:
            viewer: napari.Viewer instance. If None, uses napari.current_viewer()
        """
        # Get the napari viewer instance
        self.viewer = viewer or napari.current_viewer()

        # State tracking variables
        self.current_state = None  # Current state: 'on_image' or 'off_image'
        self.state_start_time = None  # Timestamp when current state began
        self.last_mouse_event = None  # Store last mouse event for fallback detection

        # Accumulated time durations in seconds
        self.durations_on_image = 0  # Total time spent with cursor on image
        self.durations_off_image = 0  # Total time spent with cursor off image

        # Setup periodic timer to catch missed mouse events
        # This ensures tracking continues even if some events are missed
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.periodic_check)
        self.check_timer.start(50)  # Check every 50 milliseconds

        # Connect to napari's mouse move event system
        self.viewer.mouse_move_callbacks.append(self.on_mouse_move)

    def update_onImage_time_on_fly(self):
        """
        Calculate and return the current total time spent with cursor on image data.

        This method includes time from the current ongoing state if the cursor
        is currently on an image. It also resets the timing for the current state.

        Returns:
            float: Total time in seconds spent with cursor on image data
        """
        current_time = time.time()

        # Start with previously accumulated time
        total_on_image = self.durations_on_image

        # Add duration from current state if cursor is currently on image
        if self.current_state == 'on_image' and self.state_start_time is not None:
            duration = current_time - self.state_start_time
            total_on_image += duration

        # Reset timing for current state to avoid double-counting
        self.state_start_time = current_time

        return total_on_image

    def update_offImage_time_on_fly(self):
        """
        Calculate and return the current total time spent with cursor off image data.

        This method includes time from the current ongoing state if the cursor
        is currently off an image. It also resets the timing for the current state.

        Returns:
            float: Total time in seconds spent with cursor off image data
        """
        current_time = time.time()

        # Start with previously accumulated time
        total_off_image = self.durations_off_image

        # Add duration from current state if cursor is currently off image
        if self.current_state == 'off_image' and self.state_start_time is not None:
            duration = current_time - self.state_start_time
            total_off_image += duration

        # Reset timing for current state to avoid double-counting
        self.state_start_time = current_time

        return total_off_image

    def record_state_change(self, new_state):
        """
        Record a change in mouse cursor state (on_image <-> off_image).

        This method:
        1. Calculates duration of the previous state
        2. Adds that duration to the appropriate accumulator
        3. Updates to the new state and starts timing

        Args:
            new_state (str): The new state ('on_image' or 'off_image')
        """
        current_time = time.time()

        # Only process if state actually changed
        if self.current_state != new_state:
            # Record duration of the previous state
            if self.current_state is not None and self.state_start_time is not None:
                duration = current_time - self.state_start_time

                # Add duration to appropriate accumulator
                if self.current_state == 'on_image':
                    self.durations_on_image += duration
                else:  # self.current_state == 'off_image'
                    self.durations_off_image += duration

            # Update to new state and start timing
            self.current_state = new_state
            self.state_start_time = current_time

    def is_mouse_on_image(self):
        """
        Determine if the mouse cursor is currently positioned over visible image data.

        Uses a multi-layered approach for robust detection:
        1. Qt-based canvas boundary checking
        2. Widget hierarchy verification
        3. World-to-data coordinate mapping for each visible image layer
        4. Fallback using last known mouse event position

        Returns:
            bool: True if cursor is over image data, False otherwise
        """
        try:
            try:
                # Suppress FutureWarnings from napari/Qt interactions
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)

                    # Get Qt window and canvas components
                    qt_window = self.viewer.window._qt_window
                    canvas_widget = self.viewer.window._qt_viewer.canvas.native
                    canvas = self.viewer.window._qt_viewer.canvas

                    # Method 1: Check if mouse is within canvas widget boundaries
                    global_pos = qt_window.cursor().pos()  # Global screen coordinates
                    canvas_pos = canvas_widget.mapFromGlobal(global_pos)  # Canvas-relative coordinates
                    canvas_rect = canvas_widget.rect()  # Canvas boundaries

                    if not canvas_rect.contains(canvas_pos):
                        return False  # Mouse is outside canvas entirely

                    # Method 2: Verify the widget under mouse is the canvas or its child
                    app = QApplication.instance()
                    widget_under_mouse = app.widgetAt(global_pos)

                    if widget_under_mouse is None:
                        return False

                    # Walk up widget hierarchy to find canvas
                    current_widget = widget_under_mouse
                    for _ in range(10):  # Limit search depth to prevent infinite loops
                        if current_widget is None or current_widget == canvas_widget:
                            break
                        current_widget = current_widget.parent()
                    else:
                        # Canvas not found in parent hierarchy
                        return False

                    # Method 3: Check if mouse position maps to actual image data
                    try:
                        # Convert canvas coordinates to world coordinates
                        world_coords = canvas.map_to_world([canvas_pos.x(), canvas_pos.y()])

                        # Check each visible image layer
                        for layer in self.viewer.layers:
                            if isinstance(layer, napari.layers.Image) and layer.visible:
                                try:
                                    # Convert world coordinates to data coordinates for this layer
                                    data_coords = layer.world_to_data(world_coords)
                                    # Check if coordinates are within image bounds
                                    if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                        return True  # Found valid image data under cursor
                                except Exception:
                                    # Continue checking other layers if this one fails
                                    continue

                    except Exception:
                        # Fallback: Use last recorded mouse event position
                        if self.last_mouse_event is not None and hasattr(self.last_mouse_event, 'position'):
                            for layer in self.viewer.layers:
                                if isinstance(layer, napari.layers.Image) and layer.visible:
                                    try:
                                        data_coords = layer.world_to_data(self.last_mouse_event.position)
                                        if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                            return True
                                    except Exception:
                                        continue

                    return False  # No valid image data found under cursor

            except Exception as e:
                print(f"Qt-based detection failed: {e}")

                # Fallback method: Use napari's public API when Qt method fails
                if self.last_mouse_event is not None and hasattr(self.last_mouse_event, 'position'):
                    try:
                        for layer in self.viewer.layers:
                            if isinstance(layer, napari.layers.Image) and layer.visible:
                                try:
                                    data_coords = layer.world_to_data(self.last_mouse_event.position)
                                    if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                        return True
                                except Exception:
                                    continue
                        return False
                    except Exception:
                        pass

                return False  # All methods failed

        except Exception as e:
            print(f"Error in is_mouse_on_image: {e}")
            return False

    def periodic_check(self):
        """
        Periodic timer callback to catch missed mouse events.

        This method runs every 50ms to ensure state tracking continues
        even if some mouse move events are missed or filtered out.
        """
        try:
            # Check current mouse position
            on_image = self.is_mouse_on_image()
            new_state = 'on_image' if on_image else 'off_image'

            # Update state if it has changed or is uninitialized
            if self.current_state is None or self.current_state != new_state:
                self.record_state_change(new_state)
        except Exception as e:
            print(f"Error in periodic_check: {e}")

    def on_mouse_move(self, viewer, event):
        """
        Callback for napari mouse move events.

        This is the primary detection method that responds to actual
        mouse movement within the napari viewer.

        Args:
            viewer: The napari viewer instance
            event: Mouse move event containing position and other data
        """
        try:
            # Store event for potential fallback use
            self.last_mouse_event = event

            # Determine current state based on mouse position
            on_image = self.is_mouse_on_image()
            new_state = 'on_image' if on_image else 'off_image'

            # Record any state changes
            self.record_state_change(new_state)
        except Exception as e:
            print(f"Error in on_mouse_move: {e}")

    def get_onImage(self):
        """
        Get the total time spent with cursor on image data.

        Returns:
            float: Total time in seconds
        """
        return self.update_onImage_time_on_fly()

    def get_offImage(self):
        """
        Get the total time spent with cursor off image data.

        Returns:
            float: Total time in seconds
        """
        return self.update_offImage_time_on_fly()