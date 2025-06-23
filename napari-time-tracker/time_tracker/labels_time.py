import time
from qtpy.QtCore import QTimer

class LabelMouseTracker: #tracks inter action time for each label id

    def __init__(self, viewer):
        self.viewer = viewer
        self._press_connection = None
        self._release_connection = None
        self.active = False
        self.current_label = None
        self.last_start_time = None
        self.time_per_label = {}  # dict mapping label ID to total time

    def start(self, label_id):
        """
        call when user clicks a new object
        """
        if not self.active:
            self.active = True
            self.current_label = label_id
            self.last_start_time = time.time()
            print(f"[LabelTracker] Start label={label_id} at {self.last_start_time}")

    def stop(self):
        """
        end timing + add to label_id
        """
        if self.active and self.current_label is not None:
            elapsed = time.time() - self.last_start_time
            total = self.time_per_label.get(self.current_label, 0.0) + elapsed
            self.time_per_label[self.current_label] = total
            print(f"[LabelTracker] Stop label={self.current_label}, dt={elapsed:.3f}s, total={total:.3f}s")
            self.active = False
            self.current_label = None
            self.last_start_time = None

    def report(self):
        """
        dump/print results
        """
        for label_id, total in self.time_per_label.items():
            print(f"Label {label_id}: {total:.3f} seconds")
        return dict(self.time_per_label)


