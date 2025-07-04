import time
from napari.utils.notifications import show_info

class TotalTimer:
    def __init__(self):

        self.is_running = False #Prüfung, läuft der Timer gerade

        self.start_time = None #Speichert, wann Timer zuletzt gestartet wurde

        self.total_elapsed_time = 0.0 #Summiert die gesamte verstrichene Zeit



    def start_total_time(self):
        if not self.is_running:
            show_info('Drücke Start, um zu beginnen')
            self.is_running = True
            self.start_time = time.time()

    def stop_total_time(self):
        if self.is_running:
            self.is_running = False
            if self.start_time is not None: #Überprüfung, ob start_time gesetzt ist
                current_session_elapsed = time.time() - self.start_time
                self.total_elapsed_time += current_session_elapsed
                self.start_time = None #start time zurücksetzen

    def get_total_time(self):
        if self.is_running:
            return self.total_elapsed_time + (time.time() - self.start_time)
        return self.total_elapsed_time



    #def reset(self): für später?
     #   self.is_running = False
      #  self.start_time = None
       # self.total_elapsed_time = 0.0


