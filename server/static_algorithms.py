class StaticAlgorithms:
    def __init__(self):
        # Initialize the list of servers, current index for round-robin, and weights for weighted round-robin
        self.known_agents = []
        self.current_index = 0
        self.index_weights = []

        
    def round_robin(self):
        # Select the next server in the list using round-robin
        if not self.known_agents:
            return None  # Return None if no servers are available
        server = self.known_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.known_agents)  # Move to the next server
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
