import random
import threading
from server.logging_config import dynamic_logger

class DynamicAlgorithms:
    def __init__(self):
        # Shared state for dynamic selection
        self.known_agents = []  # List of server IPs
        self.connection_counts = {}  # {server_ip: active_connections}
        self.response_times = {}  # {server_ip: response_time}
        self.resources = {}  # {server_ip: {"cpu": %, "memory": %, "disk": %}}
        self.weights = {"cpu": 40, "memory": 30, "disk": 10, "connections": 20}
        self.ai_enabled = False  # Flag for AI-enhanced logic
        self.lock = threading.Lock()  # Protect shared resources

    def least_connections(self):
        with self.lock:
            if not self.known_agents:
                return None
            # Build a dictionary of effective connection counts.
            # If AI is enabled, subtract 1 (placeholder for future AI logic).
            if self.ai_enabled:
                effective_counts = {server: self.connection_counts.get(server, 0) - 1 for server in self.known_agents}
                dynamic_logger.info("AI-Enhanced Least Connections is running (placeholder logic).")
            else:
                effective_counts = {server: self.connection_counts.get(server, 0) for server in self.known_agents}
            # Determine the minimum count.
            min_count = min(effective_counts.values())
            # Get all servers with the minimum count.
            candidates = [server for server, count in effective_counts.items() if count == min_count]
            # Randomly choose one candidate to break ties.
            return random.choice(candidates)


    def least_response_time(self):
        with self.lock:
            if not self.known_agents:
                return None
            # Build a dictionary of response times.
            effective_rts = {server: self.response_times.get(server, float('inf')) for server in self.known_agents}
            # Find the minimum response time.
            min_rt = min(effective_rts.values())
            # Get all servers with that minimum response time.
            candidates = [server for server, rt in effective_rts.items() if rt == min_rt]
            # Randomly choose one to break ties.
            return random.choice(candidates)


    def resource_based(self):
        """Compute a weighted score for each server and return the best one."""
        with self.lock:
            if not self.known_agents:
                dynamic_logger.warning("No known agents available for resource-based balancing.")
                return None

            scores = {}
            for server in self.known_agents:
                data = self.resources.get(server, {"cpu": 100, "memory": 100, "disk": 100})
                connections = self.connection_counts.get(server, 10)
                # Avoid division by zero by ensuring a minimum value
                cpu_usage = max(1, data["cpu"])
                memory_usage = max(1, data["memory"])
                disk_usage = max(1, data["disk"])
                score = (
                    ((100 - cpu_usage) / 100) * self.weights["cpu"] +
                    ((100 - memory_usage) / 100) * self.weights["memory"] +
                    ((100 - disk_usage) / 100) * self.weights["disk"] +
                    ((10 - connections) / 10) * self.weights["connections"]
                )
                scores[server] = score

            best_servers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            best_score = best_servers[0][1]
            # If scores are nearly tied, randomly select among them
            top_servers = [server for server, score in best_servers if abs(score - best_score) < 0.05]
            selected_server = random.choice(top_servers) if top_servers else best_servers[0][0]
            dynamic_logger.info(f"Resource-based load balancing chose: {selected_server}, Score: {scores[selected_server]}")
            return selected_server

    def update_resource_metrics(self, server, cpu, memory, disk, connections):
        """Update metrics for a specific server."""
        with self.lock:
            self.resources[server] = {"cpu": cpu, "memory": memory, "disk": disk}
            self.connection_counts[server] = connections

    def set_weights(self, new_weights):
        """Update the weighting factors; new weights should be provided as percentages."""
        with self.lock:
            valid_keys = {"cpu", "memory", "disk", "connections"}
            for key, value in new_weights.items():
                if key in valid_keys:
                    self.weights[key] = float(value) / 100  # Normalize to a 0–1 scale
            dynamic_logger.info(f"Updated resource weights to: {self.weights}")

    def toggle_ai(self, enabled):
        """
        Enable or disable AI enhancements on existing strategies.
        """
        self.ai_enabled = enabled
        dynamic_logger.info(f"AI-based enhancement {'enabled' if enabled else 'disabled'}.")
