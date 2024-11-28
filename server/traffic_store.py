from threading import Lock

class TrafficStore:
    _instance = None
    _traffic_data = []
    _lock = Lock()

    @staticmethod
    def get_instance():
        if TrafficStore._instance is None:
            TrafficStore()
        return TrafficStore._instance

    def __init__(self):
        if TrafficStore._instance is not None:
            raise Exception("This is a singleton class. Use get_instance() to access it.")
        TrafficStore._instance = self

    def get_traffic_data(self):
        with self._lock:
            return self._traffic_data

    def append_traffic_data(self, timestamp, rate):
        with self._lock:
            # Check if the last entry is for the same second
            if self._traffic_data and self._traffic_data[-1]["timestamp"] == timestamp:
                # Aggregate rates for the same second
                self._traffic_data[-1]["value"] += rate
            else:
                # Add a new entry
                self._traffic_data.append({"timestamp": timestamp, "value": rate})

            # Keep only the last 100 entries
            self._traffic_data = self._traffic_data[-100:]
        self._traffic_data = self._traffic_data[-10000:]
