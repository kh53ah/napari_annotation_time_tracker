import time
import napari
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication


class PauseTimeTracker:

    def __init__(self, viewer=None):
        self.viewer = viewer or napari.current_viewer()
        self.current_state = None
        self.state_start_time = None
        self.last_mouse_event = None

        # Store durations
        self.durations_on_image = 0
        self.durations_off_image = 0

        # Timer for periodic checks to catch missed events
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.periodic_check)
        self.check_timer.start(50)  # every 50 ms

        # Connect mouse move callback
        self.viewer.mouse_move_callbacks.append(self.on_mouse_move)

    def update_onImage_time_on_fly(self):
        current_time = time.time()

        # Calculate current accumulated time including ongoing state
        total_on_image = self.durations_on_image

        # Add time from current state if active
        if self.current_state is not None and self.state_start_time is not None:
            duration = current_time - self.state_start_time
            total_on_image += duration

        # Reset accumulated durations and restart timing for current state
        self.state_start_time = current_time

        return total_on_image

    def update_offImage_time_on_fly(self):
        current_time = time.time()

        # Calculate current accumulated time including ongoing state
        total_off_image = self.durations_off_image

        # Add time from current state if active
        if self.current_state is not None and self.state_start_time is not None:
            duration = current_time - self.state_start_time
            total_off_image += duration

        # Reset accumulated durations and restart timing for current state
        self.state_start_time = current_time

        return total_off_image

    def record_state_change(self, new_state):
        current_time = time.time()

        if self.current_state != new_state:
            # Record duration of previous state
            if self.current_state is not None and self.state_start_time is not None:
                duration = current_time - self.state_start_time
                if self.current_state == 'on_image':
                    self.durations_on_image += duration
                else:
                    self.durations_off_image += duration

            self.current_state = new_state
            self.state_start_time = current_time

    def is_mouse_on_image(self):
        try:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)

                    # Get Qt components (suppressing all warnings)
                    qt_window = self.viewer.window._qt_window
                    canvas_widget = self.viewer.window._qt_viewer.canvas.native
                    canvas = self.viewer.window._qt_viewer.canvas

                    # Method 1: Check if mouse inside canvas bounds
                    global_pos = qt_window.cursor().pos()
                    canvas_pos = canvas_widget.mapFromGlobal(global_pos)
                    canvas_rect = canvas_widget.rect()

                    if not canvas_rect.contains(canvas_pos):
                        return False

                    # Method 2: Check widget under mouse is canvas or child
                    app = QApplication.instance()
                    widget_under_mouse = app.widgetAt(global_pos)

                    if widget_under_mouse is None:
                        return False

                    current_widget = widget_under_mouse
                    for _ in range(10):
                        if current_widget is None or current_widget == canvas_widget:
                            break
                        current_widget = current_widget.parent()
                    else:
                        # Did not find canvas in parents
                        return False

                    # Method 3: Check if mouse is actually over image data
                    try:
                        world_coords = canvas.map_to_world([canvas_pos.x(), canvas_pos.y()])

                        for layer in self.viewer.layers:
                            if isinstance(layer, napari.layers.Image) and layer.visible:
                                try:
                                    data_coords = layer.world_to_data(world_coords)
                                    if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                        return True
                                except Exception:
                                    continue

                    except Exception:
                        # Fallback using last mouse event position if available
                        if self.last_mouse_event is not None and hasattr(self.last_mouse_event, 'position'):
                            for layer in self.viewer.layers:
                                if isinstance(layer, napari.layers.Image) and layer.visible:
                                    try:
                                        data_coords = layer.world_to_data(self.last_mouse_event.position)
                                        if all(0 <= coord < dim for coord, dim in zip(data_coords, layer.data.shape)):
                                            return True
                                    except Exception:
                                        continue

                    return False

            except Exception as e:
                print(f"Qt-based detection failed: {e}")

                # Fallback method: Use napari's public API only when Qt method fails
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

                return False

        except Exception as e:
            print(f"Error in is_mouse_on_image: {e}")
            return False

    def periodic_check(self):
        try:
            on_image = self.is_mouse_on_image()
            new_state = 'on_image' if on_image else 'off_image'

            if self.current_state is None or self.current_state != new_state:
                self.record_state_change(new_state)
        except Exception as e:
            print(f"Error in periodic_check: {e}")

    def on_mouse_move(self, viewer, event):
        try:
            self.last_mouse_event = event
            on_image = self.is_mouse_on_image()
            new_state = 'on_image' if on_image else 'off_image'
            self.record_state_change(new_state)
        except Exception as e:
            print(f"Error in on_mouse_move: {e}")

    def get_onImage(self):
        return self.update_onImage_time_on_fly()

    def get_offImage(self):
        return self.update_offImage_time_on_fly()