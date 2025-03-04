import json
import time
from threading import Lock
class TrafficStore:
    _instance = None
    _traffic_data = []
    _lock = Lock()
    _file_path = "./traffic_data.json"

    @staticmethod
    def get_instance():
        if TrafficStore._instance is None:
            TrafficStore()
        return TrafficStore._instance

    def __init__(self):
        if TrafficStore._instance is not None:
            raise Exception("This is a singleton class. Use get_instance() to access it.")
        TrafficStore._instance = self
        self.load_traffic_data()  

    def get_traffic_data(self, agent_ip=None):
        """
        Retrieve traffic data, optionally filtering by agent IP.
        """
        with self._lock:
            if agent_ip:
                return [entry for entry in self._traffic_data if entry["agent_ip"] == agent_ip]
            return self._traffic_data

    def append_traffic_data(self, agent_ip, timestamp, rate):
        with self._lock:
            # If the last entry is for the same agent and the timestamp difference is very small, aggregate.
            if (self._traffic_data and 
                self._traffic_data[-1]["agent_ip"] == agent_ip and 
                abs(self._traffic_data[-1]["timestamp"] - timestamp) < 0.01):
                self._traffic_data[-1]["value"] += rate
            else:
                # Otherwise, add a new entry with high‑precision timestamp.
                self._traffic_data.append({
                    "agent_ip": agent_ip,
                    "timestamp": timestamp,  # using float timestamp for sub-second precision
                    "value": rate
                })

            # Keep only the last X entries.
            self._traffic_data = self._traffic_data[-10000:]
            self.save_traffic_data()


    def save_traffic_data(self):
        """Save traffic data to a JSON file."""
        with open(self._file_path, "w") as f:
            json.dump(self._traffic_data, f)

    def load_traffic_data(self):
        """Load previous traffic data from file."""
        try:
            with open(self._file_path, "r") as f:
                self._traffic_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._traffic_data = []