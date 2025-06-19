from napari import viewer
from .shapes_time import MouseTracker


tracker = MouseTracker(viewer)

_mouse_press_connection = None
_mouse_release_connection = None

def check_layer():
    selection = viewer.layers.selection
    if len(selection) > 1:
        return False
    selected_layer = selection[0]
    if selected_layer.type != 'Shapes':
        return False
    return True

def check_tool_type():
    if check_layer():
        match(viewer.active_tool):
            case 'ellipse' | 'rectangle' | 'line': #Drag and Drop only
                return drag_and_drop()
            case 'polygon' |'polyline':     #Click for start and click for end
                return click()
            case 'polygon_lasso' | 'path': #both of the above
                return
    return None


def drag_and_drop():
    global _mouse_press_connection, _mouse_release_connection
    canvas = viewer.window.qt_viewer.canvas

    if _mouse_press_connection is None:
        _mouse_press_connection = canvas.events.mouse_press.connect(lambda e: on_mouse_press(tracker))

    if _mouse_release_connection is None:
        _mouse_release_connection = canvas.events.mouse_release.connect(lambda e: on_mouse_release(tracker))

def on_mouse_press(tracker):
    print("Mouse pressed - starte Timer")
    tracker.start()  # Timer starten

def on_mouse_release(tracker):
    print("Mouse released - stoppe Timer")
    tracker.stop() # Timer stoppen


def click():
    return
