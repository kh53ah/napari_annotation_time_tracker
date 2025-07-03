# time_tracker_widget.py

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image
from .points_time import PointsTimeTracker
from .shapes_time import ShapeTimeTracker
from .trigger_labels import LabelsStart


# from .FILENAME import CLASS

class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = LabelsStart(self.viewer)
        self.start_stop_btn = None

        # GUI Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Time tracking plugin active"))

        # Start/Stop Button
        self.start_stop_btn = QPushButton("Start / Stop")
        self.start_stop_btn.clicked.connect(self._on_start_stop_clicked)
        layout.addWidget(self.start_stop_btn)

        # Reset Button
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self.reset_btn)

        self.setLayout(layout)

        # Connect Layer Selection
        self.viewer.layers.selection.events.changed.connect(self._on_selection_change)
        self._on_selection_change(None)

    def _on_selection_change(self, event):
        selected = list(self.viewer.layers.selection)
        if len(selected) != 1:
            if len(selected) == 0:
                show_info("No layer selected")
            elif len(selected) > 1:
                show_info("Multiple layers selected")
            return

        layer = selected[0]
        show_info(f"Selected layer type: {type(layer)}")
        show_info(f"Layer name: {layer.name}")

        if isinstance(layer, Shapes):
            self.stt.shape_connect()
        elif isinstance(layer, Points):
            self.ptt.start()
        elif isinstance(layer, Labels):
            self.ltt.start()
        elif isinstance(layer, Image):
            show_info("Image layers are not supported")
        else:
            show_info("Unknown layer type")

    def _on_start_stop_clicked(self):
        #self.start_stop_btn.start()
        pass

    def _on_reset_clicked(self):  # Insert Reset Methode
        pass
