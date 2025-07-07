# time_tracker_widget.py

import time
import os
import json
import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from qtpy.QtCore    import QTimer
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image

from .points_time     import PointsTimeTracker
from .shapes_time     import ShapeTimeTracker
from .trigger_labels  import LabelsStart
# from .total_timer   import TotalTimer  # if you want a global timer

class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = LabelsStart(self.viewer)

        # optional: global total timer
        # self.global_timer = TotalTimer()
        # self.global_timer.start_total_time()
        self._export_timer = QTimer(self) #timer for export
        self._export_timer.setInterval(60_000)
        self._export_timer.timeout.connect(self._export_json)
        self._export_timer.start()

        # build UI
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Time tracking plugin active"))

        self.start_stop_btn = QPushButton("Start / Stop")
        self.start_stop_btn.clicked.connect(self._on_start_stop_clicked)
        layout.addWidget(self.start_stop_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self.reset_btn)

        self.setLayout(layout)

        # watch layer selection
        self.viewer.layers.selection.events.changed.connect(self._on_selection_change)
        self._on_selection_change(None)

    def _on_selection_change(self, event):
        # tear down any previous handlers
        self.stt.disconnect_all()
        self.ltt._disconnect_handlers()

        selected = list(self.viewer.layers.selection)
        if len(selected) != 1:
            show_info("Select exactly one layer.")
            return

        layer = selected[0]
        show_info(f"Selected layer: {layer.name} ({type(layer).__name__})")

        if isinstance(layer, Shapes):
            self.stt.shape_connect()
        elif isinstance(layer, Points):
            self.ptt.start()
        elif isinstance(layer, Labels):
            self.ltt.start()
        elif isinstance(layer, Image):
            show_info("Image layers not supported.")
        else:
            show_info("Unknown layer type.")

    def _on_start_stop_clicked(self):
        pass

    def _on_reset_clicked(self):
        pass

    def get_all_time_maps(self):
        return {
            #"points": self.ptt.get_time_map(),
            "shapes": self.stt.map_time(),
            "labels": self.ltt.get_time_map(),
        }

    def _export_json(self):

        #    self.total_time.update_total_time_on_fly()

        data = {
            "timestamp": time.time(),
            # "global_time_seconds": self.total_timer.get_total_time(),
            "per_layer_data": self.get_all_time_maps(),
        }

        napari_dir = os.path.dirname(napari.__file__)
        out_path   = os.path.join(napari_dir, "time_tracker_data.json")

        try:
            with open(out_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"[TimeTrackerWidget] Exported JSON to {out_path}")
        except Exception as e:
            show_info(f"Failed to write JSON: {e}")

