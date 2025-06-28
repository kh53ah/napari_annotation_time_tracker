# time_tracker_widget.py

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image
from .shapes_time import ShapeTimeTracker


class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.stt = ShapeTimeTracker(self.viewer)
        # hier bitte eure Classes hinterlegen für points und labels

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Time tracking plugin active"))
        self.setLayout(layout)

        self.viewer.layers.selection.events.changed.connect(self._on_selection_change)
        self._on_selection_change(None)  # Direkt initialisieren

    def _on_selection_change(self, event):
        selected = list(self.viewer.layers.selection)
        if len(selected) != 1:
            show_info("Select exactly one layer")
            return

        layer = selected[0]
        if isinstance(layer, Shapes):
            self.stt.shape_connect()
        elif isinstance(layer, Points):
            show_info("Point layer selected – logic not yet implemented")
        elif isinstance(layer, Labels):
            show_info("Label layer selected – logic not yet implemented")
        elif isinstance(layer, Image):
            show_info("Image layers are not supported")
        else:
            show_info("Unknown layer type")


