import re
import time
import os
import json
import napari

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from skimage import measure

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from qtpy.QtCore import QTimer
from napari.utils.notifications import show_info
from napari.layers import Shapes, Points, Labels, Image

from .points_time import PointsTimeTracker
from .shapes_time import ShapeTimeTracker
from .trigger_labels import LabelsStart
from .total_time import TotalTimer
from .pause_time import PauseTimeTracker

class TimeTrackerWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = LabelsStart(self.viewer)

        self.global_timer = TotalTimer()
        self.pause_timer = PauseTimeTracker(self.viewer)
        self._export_timer = QTimer(self)
        self._export_timer.setInterval(30_000)
        self._export_timer.timeout.connect(self._export_json)

        # create 'Time_Tracker' directory next to napari installation
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

        self.load_json_btn = QPushButton("Load JSON")
        self.load_json_btn.clicked.connect(self.load_json)
        layout.addWidget(self.load_json_btn)

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
            self.start_stop_btn.setText("Start")
            if self._export_timer.isActive():
                self._export_timer.stop()
            show_info(f"Global timer stopped at {self.global_timer.get_total_time():.2f}s and export paused")
        else:
            self.global_timer.start_total_time()
            self.start_stop_btn.setText("Stop")
            if not self._export_timer.isActive():
                self._export_timer.start()
            show_info("Global timer started and export timer activated")

    def _on_reset_clicked(self):
        self._export_timer.stop()
        for tracker in (self.ptt, self.stt, self.ltt):
            tracker.timeMap.clear()
        self.global_timer.reset()
        self.viewer.layers.clear()
        self.stt.disconnect_all()
        self.ltt._disconnect_handlers()

    def get_all_time_maps(self):
        points_raw = self.ptt.get_time_map()
        shapes_raw = self.stt.get_time_map()
        labels_raw = self.ltt.get_time_map()

        def stringify_simple(layer_map):
            return {layer.name or f"layer_{id(layer)}": {int(obj): float(t) for obj, t in times.items()} for layer, times in layer_map.items()}
        def stringify_triple(layer_map):
            return {layer.name or f"layer_{id(layer)}": {int(obj): [float(v) for v in vals] for obj, vals in times.items()} for layer, times in layer_map.items()}

        return {
            "points": stringify_simple(points_raw),
            "shapes": stringify_triple(shapes_raw),
            "labels": stringify_triple(labels_raw),
        }

    def _export_svgs(self):
        svg_files = []
        export_dir = self._time_tracker_dir
        os.makedirs(export_dir, exist_ok=True)

        for layer in self.viewer.layers:
            name = layer.name or layer.__class__.__name__
            svg_name = f"{name}_{id(layer)}.svg"
            svg_path = os.path.join(export_dir, svg_name)

            fig, ax = plt.subplots()
            if isinstance(layer, Shapes):
                segments = [np.asarray(s) for s in layer.data]
                lc = LineCollection(segments)
                ax.add_collection(lc)
                ax.autoscale()
            elif isinstance(layer, Points):
                pts = np.asarray(layer.data)
                ax.scatter(pts[:, 0], pts[:, 1], s=20)
            elif isinstance(layer, Labels):
                lbl = layer.data
                for val in np.unique(lbl):
                    if val == 0: continue
                    contours = measure.find_contours(lbl == val, 0.5)
                    for c in contours:
                        ax.plot(c[:, 1], c[:, 0], linewidth=1)
                ax.invert_yaxis()
                ax.set_aspect('equal')
            else:
                ax.imshow(layer.data, cmap='gray')

            ax.axis('off')
            fig.savefig(svg_path, format='svg', bbox_inches='tight', pad_inches=0)
            plt.close(fig)
            svg_files.append(svg_name)

        return svg_files

    def _export_json(self):
        self.global_timer.update_total_time_on_fly()
        layer_svgs = self._export_svgs()
        data = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
            "per_layer_data": self.get_all_time_maps(),
            "layer_svgs": layer_svgs,
        }
        if all(not v for v in data["per_layer_data"].values()):
            return
        json_path = os.path.join(self._time_tracker_dir, 'time_tracker_data.json')
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        show_info(f"Exported JSON + SVGs to {json_path}")

    def _export_json(self):
        self.global_timer.update_total_time_on_fly()
        layer_svgs = self._export_svgs()
        data = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
            "per_layer_data": self.get_all_time_maps(),
            "layer_svgs": layer_svgs,
        }
        if all(not v for v in data["per_layer_data"].values()):
            return
        json_path = os.path.join(self._time_tracker_dir, 'time_tracker_data.json')
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        show_info(f"Exported JSON + SVGs to {json_path}")

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(None, "Open time_tracker_data.json", self._time_tracker_dir,
                                              "JSON files (*.json)")
        if not path:
            return
        with open(path, 'r') as f:
            data = json.load(f)
        # First, load any SVG layers
        for svg_name in data.get("layer_svgs", []):
            svg_path = os.path.join(self._time_tracker_dir, svg_name)
            if not os.path.exists(svg_path):
                show_info(f"SVG file not found: {svg_name}")
                continue
            try:
                self.viewer.open(svg_path)  # load SVG layer into viewer
            except Exception as e:
                show_info(f"Failed to load SVG {svg_name}: {e}")
        # restore time maps (unchanged)
        per_layer = data.get("per_layer_data", {})

        def clean_map(raw):
            return {int(k): raw[k] if isinstance(raw[k], (list, tuple)) else float(raw[k]) for k in raw}

        self.ptt.timeMap.clear()
        for idx, times in enumerate(per_layer.get("points", {}).values()):
            pts_layers = [ly for ly in self.viewer.layers if isinstance(ly, Points)]
            if idx < len(pts_layers): self.ptt.timeMap[pts_layers[idx]] = clean_map(times)
        self.stt.timeMap.clear()
        for idx, times in enumerate(per_layer.get("shapes", {}).values()):
            shp_layers = [ly for ly in self.viewer.layers if isinstance(ly, Shapes)]
            if idx < len(shp_layers): self.stt.timeMap[shp_layers[idx]] = clean_map(times)
        self.ltt.timeMap.clear()
        for idx, times in enumerate(per_layer.get("labels", {}).values()):
            lbl_layers = [ly for ly in self.viewer.layers if isinstance(ly, Labels)]
            if idx < len(lbl_layers): self.ltt.timeMap[lbl_layers[idx]] = clean_map(times)
        show_info("Time maps successfully loaded from JSON.")



