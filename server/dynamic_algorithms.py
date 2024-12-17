class DynamicAlgorithms:
    def __init__(self):
        # Initialize server data
        self.known_agents = []  # List of server IPs
        self.connection_counts = {}  # {server_ip: active_connections}
        self.response_times = {}  # {server_ip: response_time}
        self.resources = {}  # {server_ip: resource_usage}

    def least_connections(self):
        # Return the server with the fewest active connections
        if not self.known_agents:
            return None
        return min(self.known_agents, key=lambda server: self.connection_counts.get(server, 0))

    def response_time(self):
        # Return the server with the lowest response time
        if not self.known_agents:
            return None
        return min(self.known_agents, key=lambda server: self.response_times.get(server, float('inf')))

    def resource_based(self):
        # Return the server with the most available resources
        if not self.known_agents:
            return None
        return max(self.known_agents, key=lambda server: self.resources.get(server, 0))
        
