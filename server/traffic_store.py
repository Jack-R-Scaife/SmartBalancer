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
            # If the last entry is for the same second AND same agent, aggregate
            if (self._traffic_data
                and self._traffic_data[-1]["timestamp"] == timestamp
                and self._traffic_data[-1]["agent_ip"] == agent_ip):
                self._traffic_data[-1]["value"] += rate
            else:
                # Add a new entry with the agent IP
                self._traffic_data.append({
                    "agent_ip": agent_ip,
                    "timestamp": timestamp,
                    "value": rate
                })

            # Keep only the last X entries
            self._traffic_data = self._traffic_data[-10000:]
