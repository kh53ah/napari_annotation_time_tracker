import napari
from napari.utils.notifications import show_info
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QEvent

class LockedViewer(napari.Viewer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deactivate the interaction immediately after starting
        self.set_interaction_locked(True) #Start in locked state

    def eventFilter(self, obj, event):
        # Blocks mouse events (mouse clicks, movements, double-clicks)
        if event.type() in (QEvent.MouseButtonPress,
                            QEvent.MouseButtonRelease,
                            QEvent.MouseButtonDblClick,
                            QEvent.MouseMove):
            return True

        # Blocks keyboard events
        if event.type() in (QEvent.KeyPress,
                            QEvent.KeyRelease):
            return True

        # For all other events: Allow normal behaviour
        return super().eventFilter(obj, event)

    def set_interaction_locked(self, locked: bool):
        if locked:
            self.window._qt_viewer.canvas.installEventFilter(self)
            # and deactivate the QMainWindow itself to also lock menus
            self.window._qt_viewer.setWindowOpacity(0.5) # Visual signalling
            show_info("Please press “Start” to begin/continue the annotation!")
        else:
            self.window._qt_viewer.canvas.removeEventFilter(self)
            self.window._qt_viewer.setWindowOpacity(1.0)
            self.window._qt_viewer.canvas.setMouseTracking(True)
