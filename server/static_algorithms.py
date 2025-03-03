import logging
from server.logging_config import round_robin_logger

class StaticAlgorithms:
    def __init__(self):
        # Initialize the list of servers, current index for round-robin, and weights for weighted round-robin
        self.known_agents = []
        self.current_index = 0
        self.index_weights = []

        
    def round_robin(self):
        """Select the next server in the list using round-robin and log the process."""
        if not self.known_agents:
            round_robin_logger.warning("Round Robin called with no known agents!")
            return None  # Return None if no servers are available
        
        # Log before selection
        round_robin_logger.debug(f"BEFORE: Index: {self.current_index}, Known Agents: {self.known_agents}")
        
        server = self.known_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.known_agents)  # Move to the next server
        
        # Log after selection
        round_robin_logger.debug(f"AFTER: Selected Server: {server}, Next Index: {self.current_index}")
        return server
    
    def set_weights(self, weights):
        # Generate an expanded list of servers based on their weights
        self.index_weights = [
            server for server, weight in weights.items() for _ in range(weight)
        ]

    def weighted_round_robin(self):
        # Select the next server in the weighted list
        if not self.index_weights:
            return None  # Return None if no servers are available
        server = self.index_weights[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.index_weights)  # Move to the next server
        return server
