# time_tracker_widget.py
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
from .locked_viewer import set_editable_all_layers
from .display_histogram import start_dash_app


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
        self._export_timer.timeout.connect(self._export_cycle)
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
        self.save_btn.clicked.connect(self.on_save_clicked)
        layout.addWidget(self.save_btn)

        self.show_histogram_btn = QPushButton("Show Result")
        self.show_histogram_btn.clicked.connect(self.show_histogram)
        layout.addWidget(self.show_histogram_btn)

        self.setLayout(layout)

        # watch layer selection
        self.viewer.layers.selection.events.changed.connect(self._on_selection_change)
        self._on_selection_change(None)
        set_editable_all_layers(self.viewer, False)

    def _on_selection_change(self, event):
        if not self.global_timer.is_running:
            show_info("Please press ‘Start’ to begin or continue the Annotation!")
            set_editable_all_layers(self.viewer, False)
            return

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
            show_info("Only Shapes, Points, and Labels layers are supported.")

    def _on_start_stop_clicked(self):
        if self.global_timer.is_running:
            self.global_timer.stop_total_time()
            self.start_stop_btn.setText("Start")
            if self._export_timer.isActive():
                self._export_timer.stop()
            set_editable_all_layers(self.viewer, False)
            show_info(f"Global timer stopped at {self.global_timer.get_total_time():.2f}s and export paused")
        else:
            self.global_timer.start_total_time()
            self.start_stop_btn.setText("Stop")
            if not self._export_timer.isActive():
                self._export_timer.start()
            set_editable_all_layers(self.viewer, True)
            show_info("Global timer started and export timer activated")

    def _on_reset_clicked(self):
        self._export_timer.stop()
        for tracker in (self.ptt, self.stt, self.ltt):
            tracker.timeMap.clear()
        self.global_timer.reset()
        self.viewer.layers.clear()
        self.stt.disconnect_all()
        self.ltt._disconnect_handlers()


    def on_save_clicked(self):
        if self.global_timer.is_running:
            self.global_timer.stop_total_time()
            show_info(f"Global timer stopped at {self.global_timer.get_total_time():.2f}s")
        svgs = self._export_svgs()
        files = self._export_data_files()
        self._export_json(svgs, files)

    def _export_cycle(self):
        svgs = self._export_svgs()
        files = self._export_data_files()
        self._export_json(svgs, files)

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
            if isinstance(layer, Image):
                continue
            name = layer.name or layer.__class__.__name__
            svg_name = f"{name}_{id(layer)}.svg"
            svg_path = os.path.join(export_dir, svg_name)

            fig, ax = plt.subplots()
            if isinstance(layer, Shapes):
                segs = [np.asarray(s) for s in layer.data]
                lc = LineCollection(segs)
                ax.add_collection(lc)
                ax.autoscale()
            elif isinstance(layer, Points):
                pts = np.asarray(layer.data)
                ax.scatter(pts[:, 0], pts[:, 1], s=20)
            elif isinstance(layer, Labels):
                lbl = layer.data
                for val in np.unique(lbl):
                    if val == 0: continue
                    for c in measure.find_contours(lbl == val, 0.5):
                        ax.plot(c[:, 1], c[:, 0], linewidth=1)
                ax.invert_yaxis()
                ax.set_aspect('equal')
            fig.savefig(svg_path, format='svg', bbox_inches='tight', pad_inches=0)
            plt.close(fig)
            svg_files.append(svg_name)
        return svg_files

    def _export_data_files(self):
        #Export each non-image layer’s raw data to .npy for accurate re-import.
        data_files = []
        export_dir = self._time_tracker_dir
        os.makedirs(export_dir, exist_ok=True)

        for layer in self.viewer.layers:
            if isinstance(layer, Image):
                continue
            name = layer.name or layer.__class__.__name__
            file_name = f"{name}_{id(layer)}.npy"
            file_path = os.path.join(export_dir, file_name)
            if isinstance(layer, Shapes):
                np.save(file_path, layer.data, allow_pickle=True)
            else:
                np.save(file_path, layer.data)
            entry = {"type": layer.__class__.__name__, "name": name, "file": file_name}
            if isinstance(layer, Shapes):
                entry["shape_type"] = list(layer.shape_type)
            data_files.append(entry)
        return data_files

    def _export_json(self, layer_svgs, layer_files):
        self.global_timer.update_total_time_on_fly()
        on_time = self.pause_timer.get_onImage()
        off_time = self.pause_timer.get_offImage()
        data = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
            "on_image_time_seconds": on_time,
            "off_image_time_seconds": off_time,
            "per_layer_data": self.get_all_time_maps(),
            "layer_svgs": layer_svgs,
            "layer_files": layer_files,
        }

        path = os.path.join(self._time_tracker_dir, 'time_tracker_data.json')
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        show_info(f"Exported JSON + SVGs + data files to {path}")

    def load_json(self):
        """Load raw layer data and timing from JSON manifest."""
        path, _ = QFileDialog.getOpenFileName(None, "Open time_tracker_data.json",
                                                  self._time_tracker_dir, "JSON files (*.json)")
        if not path:
            return
        with open(path) as f:
            data = json.load(f)
        from napari.layers import Image
        for layer in list(self.viewer.layers):
            if not isinstance(layer, Image):
                self.viewer.layers.remove(layer)
        for entry in data.get("layer_files", []):
            ltype = entry['type']
            name = entry['name']
            file_name = entry['file']
            file_path = os.path.join(self._time_tracker_dir, file_name)
            if not os.path.exists(file_path):
                show_info(f"Layer file missing: {file_name}")
                continue
            arr = np.load(file_path, allow_pickle=True)
            if ltype == 'Shapes':
                shapes = [np.asarray(s) for s in arr]
                shape_types = entry.get("shape_type")
                self.viewer.add_shapes(shapes, name=name, shape_type=shape_types)
            elif ltype == 'Points':
                self.viewer.add_points(arr, name=name)
            elif ltype == 'Labels':
                self.viewer.add_labels(arr, name=name)

            def clean(raw):
                return {int(k): raw[k] if isinstance(raw[k], (list, tuple)) else float(raw[k]) for k in raw}
            self.ptt.timeMap.clear()
            for idx, t in enumerate(data.get("per_layer_data", {}).get("points", {}).values()):
                layers = [ly for ly in self.viewer.layers if isinstance(ly, Points)]
                if idx < len(layers): self.ptt.timeMap[layers[idx]] = clean(t)
            self.stt.timeMap.clear()
            for idx, t in enumerate(data.get("per_layer_data", {}).get("shapes", {}).values()):
                layers = [ly for ly in self.viewer.layers if isinstance(ly, Shapes)]
                if idx < len(layers): self.stt.timeMap[layers[idx]] = clean(t)
            self.ltt.timeMap.clear()
            for idx, t in enumerate(data.get("per_layer_data", {}).get("labels", {}).values()):
                layers = [ly for ly in self.viewer.layers if isinstance(ly, Labels)]
                if idx < len(layers): self.ltt.timeMap[layers[idx]] = clean(t)

            self.pause_timer.durations_on_image = data.get("on_image_time_seconds", 0)
            self.pause_timer.durations_off_image = data.get("off_image_time_seconds", 0)

            show_info("Annotation layers, time maps, and on/off-image durations restored.")

    def show_histogram(self):
        start_dash_app(self._time_tracker_dir)
