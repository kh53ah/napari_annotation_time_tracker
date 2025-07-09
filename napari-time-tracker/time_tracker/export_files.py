import json
import os
import time
from napari.layers import Shapes, Points, Labels, Image
from napari.plugins._npe2 import write_layers

from .points_time import PointsTimeTracker
from .shapes_time import ShapeTimeTracker
from .trigger_labels import LabelsStart

from napari.utils.notifications import show_info

class Export_files:
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.ptt = PointsTimeTracker(self.viewer)
        self.stt = ShapeTimeTracker(self.viewer)
        self.ltt = LabelsStart(self.viewer)

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
                converted = {}
                for obj_id, vals in label_times.items():
                    converted[int(obj_id)] = [float(vals[0]), float(vals[1]), float(vals[2])]
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

def export_project(self, export_dir, project_name='time_tracker_project.yaml'):
        """
        Save all layers to a Napari project YAML file in export_dir.
        Returns the path of the project file.
        """
        os.makedirs(export_dir, exist_ok=True)
        project_path = os.path.join(export_dir, project_name)

        write_layers(project_path, self.viewer.layers)
        print(f"[Export_files] Project exported to {project_path}")
        return project_path