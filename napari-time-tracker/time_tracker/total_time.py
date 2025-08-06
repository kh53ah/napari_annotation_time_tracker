import time


class TotalTimer:
    """
    A timer class for tracking cumulative elapsed time across multiple intervals.

    This class allows starting, stopping, and updating a total time counter,
    which accumulates time even across pauses. It can also return or reset
    the total tracked time.
    """

    def __init__(self):
        """
        Initialize the TotalTimer with zero total time and not running.
        """
        self.is_running = False
        self.start_time = None
        self.total_time = 0.0

    def start_total_time(self):
        """
        Start or resume timing.

        Records the current time as the starting point for a new timing session.
        Does nothing if the timer is already running.
        """
        self.is_running = True
        self.start_time = time.time()

    def stop_total_time(self):
        """
        Stop timing and accumulate the elapsed time.

        If the timer was running, calculates the elapsed time since it was last
        started and adds it to the total time. Then stops the timer.
        """
        self.is_running = False
        if self.start_time is not None:
            current_session_elapsed = time.time() - self.start_time
            self.total_time += current_session_elapsed
            self.start_time = None

    def update_total_time_on_fly(self):
        """
        Update total time without stopping the timer.

        Adds the time elapsed since the last update to the total time
        and resets the start time. This is useful for periodically
        sampling time without stopping the timer.
        """
        if self.is_running and self.start_time is not None:
            current_elapsed_since_last_update = time.time() - self.start_time
            self.total_time += current_elapsed_since_last_update
            self.start_time = time.time()

    def get_total_time(self):
        """
        Get the total accumulated time.

        Returns:
            float: Total elapsed time in seconds.
        """
        return self.total_time

    def reset(self):
        """
        Reset the timer to its initial state.

        Stops the timer and clears the accumulated total time.
        """
        self.is_running = False
        self.start_time = None
        self.total_time = 0.0
