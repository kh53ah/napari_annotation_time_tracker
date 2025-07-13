import time
import warnings

warnings.filterwarnings(
    "ignore",
    message="Public access to Window.qt_viewer is deprecated"
)

class LabelTimeTracker:
    #tracks user interaction time per label in a Napari Labels layer.
    #Attributes:
    #active (bool): Whether a timing session is currently active.
    #current_label (int or None): The label ID being timed.
    #start_time (float or None): Timestamp when current stroke began.
    #time_per_label (dict): Cumulative time per label_id.
    #timeList (list): Durations (seconds) of individual strokes.
    def __init__(self):
        self.active = False
        self.current_label = None
        self.start_time = None
        self.time_per_label = {}  # label_id -> total time in seconds
        self.timeList = []        # individual stroke times

    def start(self, label_id):
        #begin timing on a new session on a label
        #Args:
        #label_id(int): The identifier of the label being drawn / erased.
        if not self.active and label_id is not None:
            self.active = True
            self.current_label = label_id
            self.start_time = time.time()

    def stop(self):
        #end timing on current session, update cumulative time and record it
        #Returns: float: The elapsed time of this stroke in seconds.
        if self.active and self.current_label is not None:
            elapsed = time.time() - self.start_time
            # accumulate per-label
            total = self.time_per_label.get(self.current_label, 0.0) + elapsed
            self.time_per_label[self.current_label] = total
            # log individual stroke
            self.timeList.append(elapsed)
            # reset
            self.active = False
            self.current_label = None
            self.start_time = None
            return elapsed
        return 0.0

    def report(self):
        #get function for cumulative time per label
        #Returns: dict: Mapping label id -> total time(second)
        return dict(self.time_per_label)

    def return_times(self):
        #get function for list of individual stroke durations
        #Returns: list of float: each stroke duration in floats in sequence
        return list(self.timeList)


