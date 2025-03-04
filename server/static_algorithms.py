import threading
import logging
from server.logging_config import round_robin_logger

class StaticAlgorithms:
    def __init__(self):
        # List of servers and index state for round-robin and weighted round-robin
        self.known_agents = []
        self.current_index = 0
        self.index_weights = []
        self.lock = threading.Lock()  # Protect shared state

    def round_robin(self):
        """Select the next server using round-robin with thread safety."""
        with self.lock:
            if not self.known_agents:
                round_robin_logger.warning("Round Robin called with no known agents!")
                return None
            round_robin_logger.debug(f"BEFORE: Index: {self.current_index}, Known Agents: {self.known_agents}")
            server = self.known_agents[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.known_agents)
            round_robin_logger.debug(f"AFTER: Selected Server: {server}, Next Index: {self.current_index}")
            return server

    def set_weights(self, weights):
        """Set weights for weighted round-robin; resets index for consistency."""
        with self.lock:
            self.index_weights = [
                server for server, weight in weights.items() for _ in range(weight)
            ]
            self.current_index = 0

    def weighted_round_robin(self):
        """Select the next server from the weighted list in a thread-safe manner."""
        with self.lock:
            if not self.index_weights:
                return None
            server = self.index_weights[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.index_weights)
            return server