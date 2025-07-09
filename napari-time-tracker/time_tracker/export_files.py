import os
import json
import time

from napari.plugins._npe2 import write_layers
from napari.utils.notifications import show_info
from .points_time import PointsTimeTracker
from .shapes_time import ShapeTimeTracker
from .trigger_labels import LabelsStart

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
                    # expect list or tuple [start, end, total]
                    converted[int(obj_id)] = [float(vals[0]), float(vals[1]), float(vals[2])]
                out[key] = converted
            return out

        return {
            "points": stringify_simple(self.ptt.timeMap),
            "shapes": stringify_simple(self.stt.timeMap),
            "labels": stringify_labels(self.ltt.timeMap),
        }

    def export_json(self, export_dir: str, global_timer, filename: str = 'time_tracker_data.json') -> str:
        """
        Write timing JSON every interval. Returns JSON path or empty if no data.
        """
        os.makedirs(export_dir, exist_ok=True)
        # Update global timer
        global_timer.update_total_time_on_fly()
        data = {
            "timestamp": time.time(),
            "global_time_seconds": global_timer.get_total_time(),
            "per_layer_data": self.get_all_time_maps(),
        }
        # skip if no per-layer data
        if all(not v for v in data["per_layer_data"].values()):
            return ''
        json_path = os.path.join(export_dir, filename)
        try:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[Export_files] JSON exported to {json_path}")
            return json_path
        except Exception as e:
            show_info(f"Failed to write JSON: {e}")
            return ''

    def export_project(self, export_dir: str, project_name: str = 'time_tracker_project.yaml') -> str:
        """
        Write Napari project YAML every interval. Returns project path.
        """
        os.makedirs(export_dir, exist_ok=True)
        project_path = os.path.join(export_dir, project_name)
        # choose writer

        try:
            write_layers(project_path, self.viewer.layers)
            print(f"[Export_files] Project exported to {project_path}")
            return project_path
        except Exception as e:
            show_info(f"Failed to write project: {e}")
            return ''