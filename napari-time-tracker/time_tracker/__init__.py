# time_tracker_widget.py
import re
import time
import os
import json
import napari
from PyQt5.QtWidgets import QFileDialog
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from qtpy.QtCore    import QTimer
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image
from .points_time     import PointsTimeTracker
from .shapes_time     import ShapeTimeTracker
from .trigger_labels  import LabelsStart
from .total_time   import TotalTimer

class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = LabelsStart(self.viewer)
        self.global_timer = TotalTimer()
        self._export_timer = QTimer(self) #timer for export every 60s
        self._export_timer.setInterval(30_000)
        self._export_timer.timeout.connect(self._export_json)


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
        if self.global_timer.is_running:
            self.global_timer.stop_total_time()
            self.start_stop_btn.setText("stop")
            if self._export_timer.isActive():
                self._export_timer.stop()
            show_info(f"Global timer stopped at {self.global_timer.get_total_time():.2f}s and export paused")
        else:
            self.global_timer.start_total_time()
            self.start_stop_btn.setText("start")
            if not self._export_timer.isActive():
                self._export_timer.start()
            show_info("Global timer started and export timer activated")

    def _on_reset_clicked(self):
        for tracker in (self.ptt, self.stt, self.ltt):
            if hasattr(tracker, 'timeMap'):
                tracker.timeMap.clear()

    def get_all_time_maps(self):
        def stringify_layer_map(layer_map):
            out = {}
            for layer_obj, label_times in layer_map.items():
                key = layer_obj.name or f"layer_{id(layer_obj)}"
                clean_times = {}
                for obj_id, t in label_times.items():
                    clean_times[int(obj_id)] = float(t)
                out[key] = clean_times
            return out

        pts_map = getattr(self.ptt, "timeMap", {})
        shp_map = getattr(self.stt, "timeMap", {})
        lbl_map = getattr(self.ltt, "timeMap", {})

        return {
            "points": stringify_layer_map(pts_map),
            "shapes": stringify_layer_map(shp_map),
            "labels": stringify_layer_map(lbl_map),
        }

    def _export_json(self):

        self.global_timer.update_total_time_on_fly() #update global timer in JSON
        data = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
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

    def _export_json(self):
        # Update and export only if data present
        self.global_timer.update_total_time_on_fly()
        data = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
            "per_layer_data": self.get_all_time_maps(),
        }
        # Skip if no timing recorded
        if all(not v for v in data["per_layer_data"].values()):
            return

        path = os.path.join(os.path.dirname(napari.__file__), "time_tracker_data.json")
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[TimeTrackerWidget] Exported JSON to {path}")
        except Exception as e:
            show_info(f"Failed to write JSON: {e}")

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(None, "Open time_tracker_data.json", "", "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            show_info(f"Failed to load JSON: {e}")
            return

        per_layer = data.get("per_layer_data", {})

        def clean_map(raw):
            return {int(k): float(v) for k, v in raw.items()}

        # Map multiple layer keys by index
        # Points
        self.ptt.timeMap.clear()
        points_layers = [ly for ly in self.viewer.layers if isinstance(ly, Points)]
        for key, times in per_layer.get("points", {}).items():
            m = re.match(r".*\[(\d+)\]$", key)
            idx = int(m.group(1)) if m else 0
            if idx < len(points_layers):
                layer = points_layers[idx]
                self.ptt.timeMap[layer] = clean_map(times)

        # Shapes
        self.stt.timeMap.clear()
        shapes_layers = [ly for ly in self.viewer.layers if isinstance(ly, Shapes)]
        for key, times in per_layer.get("shapes", {}).items():
            m = re.match(r".*\[(\d+)\]$", key)
            idx = int(m.group(1)) if m else 0
            if idx < len(shapes_layers):
                layer = shapes_layers[idx]
                self.stt.timeMap[layer] = clean_map(times)

        # Labels
        self.ltt.timeMap.clear()
        labels_layers = [ly for ly in self.viewer.layers if isinstance(ly, Labels)]
        for key, times in per_layer.get("labels", {}).items():
            m = re.match(r".*\[(\d+)\]$", key)
            idx = int(m.group(1)) if m else 0
            if idx < len(labels_layers):
                layer = labels_layers[idx]
                self.ltt.timeMap[layer] = clean_map(times)

        show_info("Time maps successfully loaded from JSON.")



