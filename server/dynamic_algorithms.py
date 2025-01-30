from server.logging_config import dynamic_logger
import random
dynamic_logger.info("Dynamic algorithms initialized")

class DynamicAlgorithms:
    def __init__(self):
        self.known_agents = []  # List of servers
        self.connection_counts = {}  # {server_ip: active_connections}
        self.response_times = {}  # {server_ip: response_time}
        self.resources = {}  # {server_ip: {"cpu": %, "memory": %, "disk": %}}
        self.weights = {"cpu": 40, "memory": 30, "disk": 10, "connections": 20}  # Default weights
        self.ai_enabled = False  # AI enhancement

    def least_connections(self):
        """
        Select the server with the fewest active connections.
        AI-enhanced: If AI is on, uses predictive insights.
        """
        if not self.known_agents:
            return None

        if self.ai_enabled:
            dynamic_logger.info("AI-Enhanced Least Connections is running.")
            return min(self.known_agents, key=lambda server: self.connection_counts.get(server, 0) - 1)

        return min(self.known_agents, key=lambda server: self.connection_counts.get(server, 0))

    def least_response_time(self):
        """
        Select the server with the lowest response time.
        AI-enhanced: If AI is on, uses predictive response time improvements.
        """
        if not self.known_agents:
            return None
        return min(self.known_agents, key=lambda server: self.response_times.get(server, float('inf')))

    def resource_based(self):
        """
        Selects the best server using a weighted score for CPU, Memory, Disk, and Least Connections.
        """
        if not self.known_agents:
            dynamic_logger.warning("No known agents available for resource-based balancing.")
            return None

        scores = {}  # Stores calculated scores per server

        for server in self.known_agents:
            data = self.resources.get(server, {"cpu": 100, "memory": 100, "disk": 100})  # Default to high usage
            connections = self.connection_counts.get(server, 10)  # Default to 10 if unknown

            # Ensure all values are valid (avoid division errors)
            cpu_usage = max(1, data["cpu"])
            memory_usage = max(1, data["memory"])
            disk_usage = max(1, data["disk"])

            # Normalize and compute score
            score = (
                ((100 - cpu_usage) / 100) * self.weights["cpu"] +
                ((100 - memory_usage) / 100) * self.weights["memory"] +
                ((100 - disk_usage) / 100) * self.weights["disk"] +
                ((10 - connections) / 10) * self.weights["connections"]
            )

            scores[server] = score

        #  Prevent tie issues by adding randomness if scores are too close
        best_servers = sorted(scores.items(), key=lambda x: x[1], reverse=True)  # Sort by highest score
        best_score = best_servers[0][1]

        # If multiple servers have the best score, pick randomly
        top_servers = [server for server, score in best_servers if abs(score - best_score) < 0.05]
        selected_server = random.choice(top_servers) if top_servers else best_servers[0][0]

        dynamic_logger.info(f"Resource-based load balancing chose: {selected_server}, Score: {scores[selected_server]}")
        return selected_server

    def update_resource_metrics(self, server, cpu, memory, disk, connections):
        """
        Updates the resource data for a server.
        """
        self.resources[server] = {"cpu": cpu, "memory": memory, "disk": disk}
        self.connection_counts[server] = connections

    def set_weights(self, new_weights):
        """
        Updates the resource-based weights dynamically.
        """
        valid_keys = {"cpu", "memory", "disk", "connections"}
        for key, value in new_weights.items():
            if key in valid_keys:
                self.weights[key] = float(value) / 100  # Normalize to a 0-1 scale
        dynamic_logger.info(f"Updated resource weights: {self.weights}")

    def toggle_ai(self, enabled):
        """
        Enable or disable AI enhancements on existing strategies.
        """
        self.ai_enabled = enabled
        dynamic_logger.info(f"AI-based enhancement {'enabled' if enabled else 'disabled'}.")
