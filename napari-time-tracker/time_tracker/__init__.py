# time_tracker_widget.py

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image
from .shapes_time import ShapeTimeTracker
from .points_time import PointsTimeTracker

# Hier bitte eure classes importieren


class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = None  # Bitte None mit Labels Class ersetzen

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Time tracking plugin active"))
        self.setLayout(layout)

        self.viewer.layers.selection.events.changed.connect(self._on_selection_change)
        self._on_selection_change(None)  # Direkt initialisieren

    def _on_selection_change(self, event):
        selected = list(self.viewer.layers.selection)
        if len(selected) != 1:
            if len(selected) == 0:
                print("No layer selected")
            elif len(selected) > 1:
                print("Multiple layers selected")
            return

        layer = selected[0]
        print(f"Selected layer type: {type(layer)}")  # Debug print
        print(f"Layer name: {layer.name}")  # Debug print

        if isinstance(layer, Shapes):
            print("Connecting shapes tracker")  # Debug print
            self.stt.shape_connect()
            print(layer.data)
        elif isinstance(layer, Points):
            print("Starting points tracker")  # Debug print
            self.ptt.start()
            print(layer.data)
        elif isinstance(layer, Labels):
            print("Labels layer detected")  # Debug print
            show_info("Label layer selected – logic not yet implemented")
        elif isinstance(layer, Image):
            show_info("Image layers are not supported")
        else:
            show_info("Unknown layer type")
