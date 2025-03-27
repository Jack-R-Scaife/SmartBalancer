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
                
            if self.ai_enabled:
                dynamic_logger.info("Using AI-enhanced least connections algorithm")
                try:
                    # Get load balancer instance for predictions
                    from server.agent_monitor import LoadBalancer
                    load_balancer = LoadBalancer()
                    
                    # Get current scenario
                    scenario = getattr(load_balancer, 'current_scenario', 'baseline_low')
                    
                    # Get predictions
                    import requests
                    response = requests.get("http://127.0.0.1:5000/api/predicted_traffic")
                    if response.status_code == 200:
                        predictions = response.json()
                        
                        # Calculate effective connection counts with predicted growth
                        effective_counts = {}
                        
                        for server in self.known_agents:
                            # Start with current connection count
                            current_connections = self.connection_counts.get(server, 0)
                            
                            # Get server-specific predictions
                            server_predictions = [p for p in predictions if p.get('agent_ip') == server]
                            
                            # Default forecast (no growth)
                            forecast_growth = 0
                            
                            if server_predictions:
                                # Calculate predicted traffic growth
                                current_traffic = server_predictions[0].get('current_traffic', 0) if server_predictions else 0
                                future_traffic = sum(p.get('value', 0) for p in server_predictions[:5]) / min(5, len(server_predictions))
                                
                                # Only factor in growth, not reduction
                                if current_traffic > 0 and future_traffic > current_traffic:
                                    growth_rate = future_traffic / current_traffic
                                    forecast_growth = current_connections * (growth_rate - 1) * 0.5
                                
                                # Scenario-specific adjustments
                                if scenario == 'baseline_high':
                                    forecast_growth *= 1.5
                                elif scenario == 'baseline_medium':
                                    pass  # No adjustment
                                else:  # baseline_low
                                    forecast_growth *= 0.5
                            
                            # Calculate effective connections
                            effective_counts[server] = current_connections + max(0, int(forecast_growth))
                        
                        dynamic_logger.debug(f"Current connections: {self.connection_counts}")
                        dynamic_logger.debug(f"AI-adjusted effective connections: {effective_counts}")
                        
                        # Find minimum effective connection count
                        min_effective = min(effective_counts.values())
                        
                        # Get all servers with the minimum effective count
                        candidates = [server for server, count in effective_counts.items() if count == min_effective]
                        
                        # Randomly choose one candidate to break ties
                        return random.choice(candidates)
                
                except Exception as e:
                    dynamic_logger.error(f"Error in AI-enhanced least connections: {e}")
                    # Fall back to standard algorithm if AI enhancement fails
                    dynamic_logger.warning("Falling back to standard least connections due to error")
            
            # Standard least connections algorithm (also used as fallback)
            effective_counts = {server: self.connection_counts.get(server, 0) for server in self.known_agents}
            min_count = min(effective_counts.values())
            candidates = [server for server, count in effective_counts.items() if count == min_count]
            return random.choice(candidates)


    def least_response_time(self):
        with self.lock:
            if not self.known_agents:
                return None
                
            if self.ai_enabled:
                dynamic_logger.info("Using AI-enhanced least response time algorithm")
                try:
                    # Get load balancer instance for predictions
                    from server.agent_monitor import LoadBalancer
                    load_balancer = LoadBalancer()
                    
                    # Get current scenario
                    scenario = getattr(load_balancer, 'current_scenario', 'baseline_low')
                    
                    # Get all metrics
                    all_metrics = load_balancer.fetch_all_metrics()
                    
                    # Get predictions
                    import requests
                    response = requests.get("http://127.0.0.1:5000/api/predicted_traffic")
                    if response.status_code == 200:
                        predictions = response.json()
                        
                        # Calculate effective response times that factor in predicted spikes
                        effective_rts = {}
                        
                        for server in self.known_agents:
                            # Start with current response time
                            current_rt = self.response_times.get(server, 100)  # Default to 100ms
                            
                            # Get server-specific predictions and metrics
                            server_predictions = [p for p in predictions if p.get('agent_ip') == server]
                            server_metrics = next((a for a in all_metrics if a.get('ip') == server and 'metrics' in a), None)
                            
                            # Default latency risk factor (no risk)
                            latency_risk = 0
                            
                            if server_predictions and server_metrics and 'metrics' in server_metrics:
                                metrics = server_metrics['metrics']
                                
                                # Metrics that typically affect response time
                                cpu_usage = metrics.get('cpu_total', 0)
                                
                                # Predicted future traffic
                                future_traffic = sum(p.get('value', 0) for p in server_predictions[:3]) / min(3, len(server_predictions))
                                current_traffic = server_predictions[0].get('current_traffic', 0) if server_predictions else 0
                                
                                # Calculate latency risk factors (0-1 scale)
                                # High CPU usage is a strong indicator
                                cpu_risk = max(0, (cpu_usage - 70) / 30) if cpu_usage > 70 else 0
                                
                                # Traffic growth can indicate congestion
                                traffic_risk = 0
                                if current_traffic > 0 and future_traffic > current_traffic:
                                    growth_pct = (future_traffic - current_traffic) / current_traffic
                                    traffic_risk = min(1, growth_pct)
                                
                                # Combine risk factors
                                latency_risk = (cpu_risk * 0.6) + (traffic_risk * 0.4)
                                
                                # Scenario-specific adjustments
                                if scenario == 'baseline_high':
                                    latency_risk *= 1.5
                                elif scenario == 'baseline_medium':
                                    pass  # No adjustment
                                else:  # baseline_low
                                    latency_risk *= 0.7
                            
                            # Cap latency risk at 1.0
                            latency_risk = min(1.0, latency_risk)
                            
                            # Calculate effective response time
                            effective_rts[server] = current_rt * (1 + latency_risk)
                        
                        dynamic_logger.debug(f"Current response times: {self.response_times}")
                        dynamic_logger.debug(f"AI-adjusted effective response times: {effective_rts}")
                        
                        # Find minimum effective response time
                        min_effective_rt = min(effective_rts.values())
                        
                        # Get all servers with close to minimum (within 10%)
                        threshold = min_effective_rt * 1.1
                        candidates = [server for server, rt in effective_rts.items() if rt <= threshold]
                        
                        # Randomly choose one candidate
                        return random.choice(candidates)
                
                except Exception as e:
                    dynamic_logger.error(f"Error in AI-enhanced least response time: {e}")
                    # Fall back to standard algorithm
                    dynamic_logger.warning("Falling back to standard least response time due to error")
            
            # Standard least response time algorithm (also used as fallback)
            effective_rts = {server: self.response_times.get(server, float('inf')) for server in self.known_agents}
            min_rt = min(effective_rts.values())
            candidates = [server for server, rt in effective_rts.items() if rt == min_rt]
            return random.choice(candidates)


    def resource_based(self):
        """Compute a weighted score for each server and return the best one."""
        with self.lock:
            if not self.known_agents:
                dynamic_logger.warning("No known agents available for resource-based balancing.")
                return None
                
            if self.ai_enabled:
                dynamic_logger.info("Using AI-enhanced resource-based algorithm")
                try:
                    # Get load balancer instance
                    from server.agent_monitor import LoadBalancer
                    load_balancer = LoadBalancer()
                    
                    # Get current scenario
                    scenario = getattr(load_balancer, 'current_scenario', 'baseline_low')
                    
                    # Get predictions
                    import requests
                    response = requests.get("http://127.0.0.1:5000/api/predicted_traffic")
                    if response.status_code == 200:
                        predictions = response.json()
                        
                        # Calculate AI-enhanced resource scores
                        ai_scores = {}
                        
                        for server in self.known_agents:
                            # Get resource data for this server
                            data = self.resources.get(server, {"cpu": 100, "memory": 100, "disk": 100})
                            connections = self.connection_counts.get(server, 10)
                            
                            # Avoid division by zero
                            cpu_usage = max(1, data["cpu"])
                            memory_usage = max(1, data["memory"])
                            disk_usage = max(1, data["disk"])
                            
                            # Standard resource score calculation
                            base_score = (
                                ((100 - cpu_usage) / 100) * self.weights["cpu"] +
                                ((100 - memory_usage) / 100) * self.weights["memory"] +
                                ((100 - disk_usage) / 100) * self.weights["disk"] +
                                ((10 - connections) / 10) * self.weights["connections"]
                            )
                            
                            # Get server-specific predictions
                            server_predictions = [p for p in predictions if p.get('agent_ip') == server]
                            
                            # Default efficiency factor (neutral)
                            efficiency_factor = 1.0
                            
                            if server_predictions:
                                # Get predicted future metrics
                                future_traffic = sum(p.get('value', 0) for p in server_predictions[:5]) / min(5, len(server_predictions))
                                
                                # Calculate predicted future resource usage
                                if future_traffic > 0:
                                    # Estimate resource usage per unit of traffic
                                    resource_per_request = (cpu_usage + memory_usage) / 200  # Normalize to 0-1 scale
                                    
                                    # Predict efficiency based on resource usage per request
                                    efficiency_factor = max(0.5, min(1.5, 1.5 - resource_per_request))
                                
                                # Scenario-specific adjustments
                                if scenario == 'baseline_high':
                                    efficiency_weight = 0.6
                                elif scenario == 'baseline_medium':
                                    efficiency_weight = 0.4
                                else:  # baseline_low
                                    efficiency_weight = 0.2
                                
                                # Blend base score and efficiency factor
                                blended_score = (base_score * (1 - efficiency_weight)) + (base_score * efficiency_factor * efficiency_weight)
                                ai_scores[server] = blended_score
                            else:
                                ai_scores[server] = base_score
                        
                        dynamic_logger.debug(f"AI-enhanced resource scores: {ai_scores}")
                        
                        # Sort servers by score (highest first)
                        sorted_servers = sorted(ai_scores.items(), key=lambda x: x[1], reverse=True)
                        
                        # Get highest score
                        best_score = sorted_servers[0][1]
                        
                        # Find all servers with similar scores (within 5%)
                        threshold = best_score * 0.95
                        candidates = [server for server, score in sorted_servers if score >= threshold]
                        
                        # Randomly select from top candidates
                        return random.choice(candidates)
                
                except Exception as e:
                    dynamic_logger.error(f"Error in AI-enhanced resource-based algorithm: {e}")
                    dynamic_logger.warning("Falling back to standard resource-based algorithm due to error")
            
            # Standard resource-based algorithm (also used as fallback)
            scores = {}
            for server in self.known_agents:
                data = self.resources.get(server, {"cpu": 100, "memory": 100, "disk": 100})
                connections = self.connection_counts.get(server, 10)
                # Avoid division by zero
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
