# time_tracker_widget.py

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image
from .shapes_time import ShapeTimeTracker


# Hier bitte eure classes importieren


class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = None  # Bitte None mit Points Class ersetzen
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
        if isinstance(layer, Shapes):
            self.stt.shape_connect()
            print(layer.data)
        elif isinstance(layer, Points):
            show_info(
                "Point layer selected – logic not yet implemented")  # Hier die class von oben verwenden für Points
        elif isinstance(layer, Labels):
            self.ltt.start() # Hier die class von oben verwenden für Labels
        elif isinstance(layer, Image):
            show_info("Image layers are not supported")
        else:
            show_info("Unknown layer type")
