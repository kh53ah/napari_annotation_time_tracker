import re
import time
import os
import json
import yaml  # for YAML export
import napari
from PyQt5.QtWidgets import QFileDialog
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from qtpy.QtCore import QTimer
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image
from .points_time import PointsTimeTracker
from .shapes_time import ShapeTimeTracker
from .trigger_labels import LabelsStart
from .total_time import TotalTimer

class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = LabelsStart(self.viewer)

        self.global_timer = TotalTimer()
        self._export_timer = QTimer(self)
        self._export_timer.setInterval(30_000)
        self._export_timer.timeout.connect(self._export_json)

                # create 'Time_Tracker' directory next to napari installation (no spaces for shell compatibility)
        napari_dir = os.path.dirname(napari.__file__)
        self._time_tracker_dir = os.path.join(napari_dir, 'Time_Tracker')
        os.makedirs(self._time_tracker_dir, exist_ok=True)

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
        else:
            show_info("Only Shapes, Points, and Labels layers are supported.")

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
        # export timing JSON
        self._export_json()
        # export full project data to YAML
        self._export_yaml()

    def get_all_time_maps(self):
        def stringify_simple(layer_map):
            out = {}
            for layer_obj, label_times in layer_map.items():
                key = layer_obj.name or f"layer_{id(layer_obj)}"
                out[key] = {int(obj_id): float(t) for obj_id, t in label_times.items()}
            return out

        def stringify_labels(layer_map):
            out = {}
            for layer_obj, label_times in layer_map.items():
                key = layer_obj.name or f"layer_{id(layer_obj)}"
                converted = {int(obj_id): list(map(float, vals)) for obj_id, vals in label_times.items()}
                out[key] = converted
            return out

        return {
            "points": stringify_simple(self.ptt.timeMap),
            "shapes": stringify_simple(self.stt.timeMap),
            "labels": stringify_labels(self.ltt.timeMap),
        }

    def _export_json(self):
        self.global_timer.update_total_time_on_fly()
        data = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
            "per_layer_data": self.get_all_time_maps(),
        }
        if all(not v for v in data["per_layer_data"].values()):
            return
        json_path = os.path.join(self._time_tracker_dir, 'time_tracker_data.json')
        try:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[TimeTrackerWidget] Exported JSON to {json_path}")
        except Exception as e:
            show_info(f"Failed to write JSON: {e}")

    def _export_yaml(self):
        project = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
            "layers": [],
        }
        for layer in self.viewer.layers:
            entry = {
                "type": layer.__class__.__name__,
                "name": layer.name,
                "properties": {},
            }
            # include data for vector layers
            if isinstance(layer, (Shapes, Points)):
                raw = layer.data
                if isinstance(raw, list):
                    entry["data"] = [arr.tolist() if hasattr(arr, 'tolist') else arr for arr in raw]
                else:
                    entry["data"] = raw.tolist()
            elif isinstance(layer, Labels):
                entry["labels"] = layer.data.tolist()
            elif isinstance(layer, Image):
                entry["source"] = getattr(layer, "source", None)
            project["layers"].append(entry)

        yaml_path = os.path.join(self._time_tracker_dir, 'time_tracker_project.yaml')
        try:
            with open(yaml_path, 'w') as f:
                yaml.dump(project, f, sort_keys=False)
            show_info(f"Exported project to YAML at {yaml_path}")
        except Exception as e:
            show_info(f"Failed to write YAML: {e}")

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(None, "Open time_tracker_data.json", self._time_tracker_dir, "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            show_info(f"Failed to load JSON: {e}")
            return

        per_layer = data.get("per_layer_data", {})
        def clean_map(raw):
            return {int(k): raw[k] if isinstance(raw[k], (list, tuple)) else float(raw[k]) for k in raw}

        self.ptt.timeMap.clear()
        for idx, (key, times) in enumerate(per_layer.get("points", {}).items()):
            layers = [ly for ly in self.viewer.layers if isinstance(ly, Points)]
            if idx < len(layers):
                self.ptt.timeMap[layers[idx]] = clean_map(times)

        self.stt.timeMap.clear()
        for idx, (key, times) in enumerate(per_layer.get("shapes", {}).items()):
            layers = [ly for ly in self.viewer.layers if isinstance(ly, Shapes)]
            if idx < len(layers):
                self.stt.timeMap[layers[idx]] = clean_map(times)

        self.ltt.timeMap.clear()
        for idx, (key, times) in enumerate(per_layer.get("labels", {}).items()):
            layers = [ly for ly in self.viewer.layers if isinstance(ly, Labels)]
            if idx < len(layers):
                self.ltt.timeMap[layers[idx]] = clean_map(times)

        show_info("Time maps successfully loaded from JSON.")





