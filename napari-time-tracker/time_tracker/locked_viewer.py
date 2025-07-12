import napari
from napari.utils.notifications import show_info
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt

class LockedViewer(napari.Viewer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deactivate the interaction immediately after starting
        self.set_interaction_locked(True) #Start in locked state

    def set_interaction_locked(self, locked: bool):
        if locked:
            self.window._qt_viewer.canvas.setEnabled(False)
            self.window._qt_viewer.setMouseTracking(False)
            # and deactivate the QMainWindow itself to also lock menus
            self.window._qt_viewer.setWindowOpacity(0.5) # Visual signalling
            show_info("Please press “Start” to begin/continue the annotation!")
        else:
            self.window._qt_viewer.canvas.setMouseTracking(True)
            self.window._qt_viewer.canvas.setEnabled(True)
            self.window._qt_viewer.setWindowOpacity(1.0)