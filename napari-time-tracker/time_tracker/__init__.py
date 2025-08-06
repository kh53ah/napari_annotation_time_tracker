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
from .pause_time import CanvasTimeTracker
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
        self.pause_timer = CanvasTimeTracker(self.viewer)
        self._export_timer = QTimer(self)
        self._export_timer.setInterval(30_000)
        self._export_timer.timeout.connect(self._export_cycle)
        # create 'Time_Tracker' directory next to napari installation
        napari_dir = os.path.dirname(napari.__file__)
        self._time_tracker_dir = os.path.join(napari_dir, 'Time_Tracker')
        os.makedirs(self._time_tracker_dir, exist_ok=True)



        # build UI
        layout = QVBoxLayout()

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
        else:
            self.global_timer.start_total_time()
            self.start_stop_btn.setText("Stop")
            if not self._export_timer.isActive():
                self._export_timer.start()
            set_editable_all_layers(self.viewer, True)

    def _on_reset_clicked(self):
        self._export_timer.stop()
        self.start_stop_btn.setText("Start / Stop")
        for tracker in (self.ptt, self.stt, self.ltt):
            tracker.timeMap.clear()
        self.global_timer.reset()
        self.viewer.layers.clear()
        self.stt.disconnect_all()
        self.ltt._disconnect_handlers()


    def on_save_clicked(self):
        """
        Handle the 'Save' button click event.

        Stops the global timing if running, resets UI controls,
        disables editing on all layers, and prompts the user
        to select a directory. Exports SVGs, data files, and JSON
        manifest to both the selected directory and the internal
        tracker directory.
        """
        if self.global_timer.is_running:
            self.global_timer.stop_total_time()
            self.start_stop_btn.setText("Start")
            if self._export_timer.isActive():
                self._export_timer.stop()
            set_editable_all_layers(self.viewer, False)
        user_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if not user_dir:
            return
        for target_dir in [self._time_tracker_dir, user_dir]:
            svgs = self._export_svgs(target_dir)
            files = self._export_data_files(target_dir)
            self._export_json(svgs, files, target_dir)

        show_info(f"Saved data to: {user_dir} and {self._time_tracker_dir}")

    def _export_cycle(self):
        """
        Perform a periodic export cycle.

        Exports SVGs and data files to the internal tracker directory
        and updates the JSON manifest accordingly.
        """
        svgs = self._export_svgs(self._time_tracker_dir)
        files = self._export_data_files(self._time_tracker_dir)
        self._export_json(svgs, files,self._time_tracker_dir)

    def get_all_time_maps(self):
        """
        Aggregate and format timing data for all tracked layers.

        Returns
         -------
            dict
                A dictionary with three keys ('points', 'shapes', 'labels'), each
                mapping layer names to their respective timing statistics. Simple
                maps yield {layer_name: {object_id: time_seconds}} and triple maps
                yield {layer_name: {object_id: [start, end, duration]}}.
        """
        points_raw = self.ptt.get_time_map()
        shapes_raw = self.stt.get_time_map()
        labels_raw = self.ltt.get_time_map()

        def stringify_simple(layer_map):
            # Converts time map to: {layer_name: {obj_id: time_in_seconds}}
            return {
                layer.name or f"layer_{id(layer)}": {
                    int(obj): float(t)
                    for obj, t in times.items()
                    if t is not None  # skip incomplete entries
                }
                for layer, times in layer_map.items()
            }

        def stringify_triple(layer_map):
            # Converts time map to: {layer_name: {obj_id: [start_time, end_time, duration]}}
            return {
                layer.name or f"layer_{id(layer)}": {
                    int(obj): [float(v) for v in vals]
                    for obj, vals in times.items()
                    if vals is not None and all(v is not None for v in vals)  # skip incomplete
                }
                for layer, times in layer_map.items()
            }

        return {
            "points": stringify_simple(points_raw),
            "shapes": stringify_triple(shapes_raw),
            "labels": stringify_triple(labels_raw),
        }

    def _export_svgs(self, export_dir):
        """
        Export current viewer layers as SVG files.

        Parameters
        ----------
            export_dir : str
                Directory path to save generated SVG files.

            Returns
             -------
            list of str
                Filenames of the SVG files created for each non-image layer.
        """
        svg_files = []
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

    def _export_data_files(self, export_dir):
        """
        Export raw layer data as NumPy files.

        Parameters
        ----------
            export_dir : str
                Directory path to save the .npy data files.

            Returns
            -------
            list of dict
                Metadata entries for each data file, including type, name, and filename.
        """
        data_files = []
        os.makedirs(export_dir, exist_ok=True)

        for layer in self.viewer.layers:
            if isinstance(layer, Image):
                continue

            name = layer.name or layer.__class__.__name__
            file_name = f"{name}_{id(layer)}.npy"
            file_path = os.path.join(export_dir, file_name)

            if isinstance(layer, Shapes):
                # wrap list-of-arrays into a 1-D object array so np.save can handle varying shapes
                obj_arr = np.array(layer.data, dtype=object)
                np.save(file_path, obj_arr, allow_pickle=True)

            else:
                np.save(file_path, layer.data)

            entry = {
                "type": layer.__class__.__name__,
                "name": name,
                "file": file_name,
            }
            data_files.append(entry)
        return data_files

    def _export_json(self, layer_svgs, layer_files, export_dir):
        """
        Write a JSON manifest summarizing exported files and timing data.

        Parameters
         ----------
            layer_svgs : list of str
                Filenames of exported SVG files.
            layer_files : list of dict
                Metadata entries for exported data files.
            export_dir : str
                Directory path where the JSON manifest will be written.
        """
        self.global_timer.update_total_time_on_fly()
        on_time = self.pause_timer.get_onCanvas()
        off_time = self.pause_timer.get_offCanvas()
        data = {
            "timestamp": time.time(),
            "global_time_seconds": self.global_timer.get_total_time(),
            "on_canvas_time_seconds": on_time,
            "off_canvas_time_seconds": off_time,
            "per_layer_data": self.get_all_time_maps(),
            "layer_svgs": layer_svgs,
            "layer_files": layer_files,
        }

        path = os.path.join(export_dir, 'time_tracker_data.json')
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        show_info(f"Exported JSON + SVGs + data files to {path}")

    def load_json(self):
        """
        Load and restore layer data and timing from a JSON manifest.

        Opens a file dialog to select the JSON file, removes existing annotation layers,
        recreates layers from saved data, and restores timing maps and on/off-canvas durations.
        """
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Open time_tracker_data.json",
            self._time_tracker_dir,
            "JSON files (*.json)"
        )
        if not path:
            return

        # 1) Read JSON
        with open(path) as f:
            data = json.load(f)

        # 2) Remove any existing annotation layers
        from napari.layers import Image
        for layer in list(self.viewer.layers):
            if not isinstance(layer, Image):
                self.viewer.layers.remove(layer)

        # 3) Re-create each saved layer
        from napari.layers import Shapes, Points, Labels
        for entry in data.get("layer_files", []):
            ltype = entry["type"]
            name = entry["name"]
            file_name = entry["file"]
            file_path = os.path.join(self._time_tracker_dir, file_name)

            if not os.path.exists(file_path):
                show_info(f"Layer file missing: {file_name}")
                continue

            arr = np.load(file_path, allow_pickle=True)

            if ltype == "Shapes":
                shapes = arr.tolist()
                shape_types = entry.get("shape_type", ["polygon"] * len(shapes))
                self.viewer.add_shapes(
                    shapes,
                    name=name,
                    shape_type=shape_types,
                )

            elif ltype == "Points":
                pts = np.asarray(arr)
                self.viewer.add_points(pts, name=name)

            elif ltype == "Labels":
                lbl = np.asarray(arr)
                self.viewer.add_labels(lbl, name=name)

        # 4) Restore each timeMap in one pass
        def clean(raw):
            return {
                int(k): raw[k] if isinstance(raw[k], (list, tuple)) else float(raw[k])
                for k in raw
            }

        # Points
        self.ptt.timeMap.clear()
        for idx, t in enumerate(data.get("per_layer_data", {}).get("points", {}).values()):
            pts_layers = [ly for ly in self.viewer.layers if isinstance(ly, Points)]
            if idx < len(pts_layers):
                self.ptt.timeMap[pts_layers[idx]] = clean(t)

        # Shapes
        self.stt.timeMap.clear()
        for idx, t in enumerate(data.get("per_layer_data", {}).get("shapes", {}).values()):
            shp_layers = [ly for ly in self.viewer.layers if isinstance(ly, Shapes)]
            if idx < len(shp_layers):
                self.stt.timeMap[shp_layers[idx]] = clean(t)

        # Labels
        self.ltt.timeMap.clear()
        for idx, t in enumerate(data.get("per_layer_data", {}).get("labels", {}).values()):
            lbl_layers = [ly for ly in self.viewer.layers if isinstance(ly, Labels)]
            if idx < len(lbl_layers):
                self.ltt.timeMap[lbl_layers[idx]] = clean(t)

        # 5) Restore pause‐timer durations
        self.pause_timer.durations_on_canvas = data.get("on_canvas_time_seconds", 0)
        self.pause_timer.durations_off_canvas = data.get("off_canvas_time_seconds", 0)

        # 6) Re-connect trackers and prime their “previous count”
        def select(layer):
            sel = self.viewer.layers.selection
            sel.clear()
            sel.add(layer)

        # Shapes tracker
        shape_layers = [ly for ly in self.viewer.layers if isinstance(ly, Shapes)]
        if shape_layers:
            shp = shape_layers[0]
            select(shp)
            self.stt.disconnect_all()
            self.stt._connected_shape_layer = shp
            self.stt._previous_shape_count = len(shp.data)
            self.stt.shape_connect()

        # Points tracker
        point_layers = [ly for ly in self.viewer.layers if isinstance(ly, Points)]
        if point_layers:
            pts = point_layers[0]
            select(pts)
            # assume your PointsTimeTracker has _previous_point_count
            self.ptt._previous_point_count = len(pts.data)
            self.ptt.start()

        # Labels tracker
        label_layers = [ly for ly in self.viewer.layers if isinstance(ly, Labels)]
        if label_layers:
            lbl = label_layers[0]
            select(lbl)
            # assume your LabelsStart has _previous_label_count
            self.ltt._previous_label_count = len(lbl.data)
            self.ltt.start()

        # 7) Leave the Shapes layer selected so the user can continue drawing
        if shape_layers:
            select(shape_layers[0])

        show_info("Annotation layers, time maps, and on/off-canvas durations restored.")

    def show_histogram(self):
        start_dash_app(self._time_tracker_dir)
