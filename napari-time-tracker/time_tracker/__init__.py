import re
import time
import os
import json
import napari
from PyQt5.QtWidgets import QFileDialog
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from qtpy.QtCore import QTimer
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image
from .points_time import PointsTimeTracker
from .shapes_time import ShapeTimeTracker
from .trigger_labels import LabelsStart
from .export_files import Export_files
from .total_time import TotalTimer

class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = LabelsStart(self.viewer)
        self.global_timer = TotalTimer()

        self.exporter = Export_files(self.viewer)

        # create 'Time Tracker' directory
        napari_dir = os.path.dirname(napari.__file__)
        self._time_tracker_dir = os.path.join(napari_dir, 'Time Tracker')
        os.makedirs(self._time_tracker_dir, exist_ok=True)

        # timer for periodic export
        self._export_timer = QTimer(self)
        self._export_timer.setInterval(30000)
        self._export_timer.timeout.connect(self._export)

        # build UI
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Time tracking plugin active"))

        self.start_stop_btn = QPushButton("Start / Stop")
        self.start_stop_btn.clicked.connect(self._on_start_stop_clicked)
        layout.addWidget(self.start_stop_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self.reset_btn)

        self.load_btn = QPushButton("Load timings")
        self.load_btn.clicked.connect(self.load_json)
        layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)
        self.viewer.layers.selection.events.changed.connect(self._on_selection_change)
        self._on_selection_change(None)

    def _on_selection_change(self, event):
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
        if self.global_timer.is_running:
            self.global_timer.stop_total_time()
            if self._export_timer.isActive():
                self._export_timer.stop()
            show_info(f"Global timer stopped at {self.global_timer.get_total_time():.2f}s and export paused")
        else:
            self.global_timer.start_total_time()
            if not self._export_timer.isActive():
                self._export_timer.start()
            show_info("Global timer started and export timer activated")

    def _on_reset_clicked(self):
        for tracker in (self.ptt, self.stt, self.ltt):
            tracker.timeMap.clear()

    def _on_save_clicked(self):
        if self.global_timer.is_running:
            self.global_timer.stop_total_time()
            show_info(f"Global timer stopped at {self.global_timer.get_total_time():.2f}s")
        # perform export
        self._export()
        show_info("Export complete. Project file ready.")

    def _export(self):
        json_path = self.exporter._export_json()
        if json_path:
            show_info(f"Exported JSON to {json_path}")
        else:
            show_info("No timing data to export.")
        # project layers
        proj_path = self.exporter.export_project(self._time_tracker_dir)
        show_info(f"Exported project file to {proj_path}")

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(None, "Open time_tracker_data.json", "", "JSON files (*.json)")
        if not path:
            return
        try:
            data = json.load(open(path))
        except Exception as e:
            show_info(f"Failed to load JSON: {e}")
            return
        self.ptt.timeMap, self.stt.timeMap, self.ltt.timeMap = (
            data['per_layer_data']['points'],
            data['per_layer_data']['shapes'],
            data['per_layer_data']['labels'],
        )
        show_info("Time maps successfully loaded from JSON.")





