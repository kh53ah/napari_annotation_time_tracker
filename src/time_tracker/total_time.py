import time
from napari.utils.notifications import show_info


class TotalTimer:
    def __init__(self):
        self.is_running = False  #Check, is the timer currently running
        self.start_time = None  #Saves the last time the timer was started
        self.total_time = 0.0  #Totals the total elapsed time

    def start_total_time(self):
        #show_info('Press Start, to begin')
        self.is_running = True
        self.start_time = time.time()

    def stop_total_time(self):
        self.is_running = False
        if self.start_time is not None:  #Check whether start_time is set
            current_session_elapsed = time.time() - self.start_time
            self.total_time += current_session_elapsed
            self.start_time = None  #Reset start time
        print(f"Total accumulated time: {self.total_time:.2f} seconds.")

    def update_total_time_on_fly(self):
        if self.is_running and self.start_time is not None:
            current_elapsed_since_last_update = time.time() - self.start_time
            self.total_time += current_elapsed_since_last_update
            self.start_time = time.time()

    def get_total_time(self):
        return self.total_time

    def reset(self):
        self.is_running = False
        self.start_time = None
        self.total_time = 0.0
