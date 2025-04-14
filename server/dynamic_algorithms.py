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
        self.lock = threading.Lock()  # Protect shared resources

    def least_connections(self, ai_enabled=False):
        """Select the server with the least active connections."""
        with self.lock:
            if not self.known_agents:
                return None
                
            if ai_enabled:
                dynamic_logger.info("Using AI-enhanced least connections algorithm")
                try:
                    # Fetch server-specific metrics and predictions
                    import requests
                    metrics_response = requests.get("http://127.0.0.1:5000/api/metrics/all")
                    predictions_response = requests.get("http://127.0.0.1:5000/api/predicted_traffic")
                    
                    if metrics_response.status_code == 200 and predictions_response.status_code == 200:
                        metrics_data = metrics_response.json()
                        predictions_data = predictions_response.json()
                        
                        # Process metrics for each server
                        server_connections = {}
                        for metric in metrics_data:
                            if 'ip' in metric and 'metrics' in metric:
                                ip = metric['ip']
                                connections = metric['metrics'].get('connections', self.connection_counts.get(ip, 0))
                                server_connections[ip] = connections
                        
                        # Group predictions by server
                        server_predictions = {}
                        for pred in predictions_data:
                            if 'agent_ip' in pred and 'value' in pred:
                                ip = pred['agent_ip']
                                if ip not in server_predictions:
                                    server_predictions[ip] = []
                                server_predictions[ip].append(pred['value'])
                        
                        # Calculate effective connection counts
                        effective_connections = {}
                        
                        for server in self.known_agents:
                            # Start with current connection count
                            current = server_connections.get(server, self.connection_counts.get(server, 0))
                            
                            # Get predictions for this server
                            predictions = server_predictions.get(server, [])
                            
                            if predictions:
                                # Calculate average predicted traffic increase/decrease
                                avg_prediction = sum(predictions) / len(predictions)
                                
                                # Estimate future connections based on prediction
                                # Higher predicted traffic = higher effective connections
                                prediction_factor = avg_prediction / 50  # Scale factor
                                projected_increase = current * prediction_factor
                                
                                # Calculate effective connections
                                effective = current + max(0, projected_increase)
                                effective_connections[server] = effective
                            else:
                                # No prediction data - use current connections
                                effective_connections[server] = current
                        
                        dynamic_logger.debug(f"Current connections: {server_connections}")
                        dynamic_logger.debug(f"AI-enhanced effective connections: {effective_connections}")
                        
                        # Find server with minimum effective connections
                        if effective_connections:
                            min_server = min(effective_connections.items(), key=lambda x: x[1])[0]
                            dynamic_logger.info(f"AI-enhanced least connections chose: {min_server}")
                            return min_server
                
                except Exception as e:
                    dynamic_logger.error(f"Error in AI-enhanced least connections: {e}")
                    dynamic_logger.warning("Falling back to standard least connections algorithm")
            else:
                # Standard least connections algorithm (exactly as in original)
                connections = {server: self.connection_counts.get(server, 0) for server in self.known_agents}
                if not connections:
                    return random.choice(self.known_agents) if self.known_agents else None
                    
                min_conn = min(connections.values())
                candidates = [server for server, conn in connections.items() if conn == min_conn]
                return random.choice(candidates)
    
    def least_response_time(self, ai_enabled=False):
        with self.lock:
            if not self.known_agents:
                return None
                
            if ai_enabled:
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
            else:
                # Standard least response time algorithm (also used as fallback)
                effective_rts = {server: self.response_times.get(server, float('inf')) for server in self.known_agents}
                min_rt = min(effective_rts.values())
                candidates = [server for server, rt in effective_rts.items() if rt == min_rt]
                return random.choice(candidates)


    def resource_based(self, ai_enabled=False):
        """Compute a weighted score for each server and return the best one."""
        with self.lock:
            if not self.known_agents:
                dynamic_logger.warning("No known agents available for resource-based balancing.")
                return None
                
            if ai_enabled:
                dynamic_logger.info("Using AI-enhanced resource-based algorithm")
                try:
                    # Fetch server-specific metrics and predictions
                    import requests
                    metrics_response = requests.get("http://127.0.0.1:5000/api/metrics/all")
                    predictions_response = requests.get("http://127.0.0.1:5000/api/predicted_traffic")
                    
                    if metrics_response.status_code == 200 and predictions_response.status_code == 200:
                        metrics_data = metrics_response.json()
                        predictions_data = predictions_response.json()
                        
                        # Create maps for easy lookups
                        server_metrics = {m['ip']: m['metrics'] for m in metrics_data if 'ip' in m and 'metrics' in m}
                        
                        # Group predictions by server
                        server_predictions = {}
                        for pred in predictions_data:
                            if 'agent_ip' in pred and 'value' in pred:
                                ip = pred['agent_ip']
                                if ip not in server_predictions:
                                    server_predictions[ip] = []
                                server_predictions[ip].append(pred['value'])
                        
                        # Calculate AI-enhanced resource scores per server
                        ai_scores = {}
                        
                        for server in self.known_agents:
                            # Get resource data for this server
                            base_data = self.resources.get(server, {"cpu": 100, "memory": 100, "disk": 100})
                            connections = self.connection_counts.get(server, 10)
                            
                            # Real-time metrics from API may be more current
                            metrics = server_metrics.get(server, {})
                            cpu_usage = metrics.get('cpu_total', base_data["cpu"])
                            memory_usage = metrics.get('memory', base_data["memory"])
                            disk_usage = metrics.get('disk', base_data["disk"])
                            current_connections = metrics.get('connections', connections)
                            
                            # Avoid division by zero
                            cpu_usage = max(1, cpu_usage)
                            memory_usage = max(1, memory_usage)
                            disk_usage = max(1, disk_usage)
                            
                            # Calculate base score from current metrics
                            base_score = (
                                ((100 - cpu_usage) / 100) * self.weights["cpu"] +
                                ((100 - memory_usage) / 100) * self.weights["memory"] +
                                ((100 - disk_usage) / 100) * self.weights["disk"] +
                                ((10 - current_connections) / 10) * self.weights["connections"]
                            )
                            
                            # Get server-specific predictions
                            predictions = server_predictions.get(server, [])
                            
                            if predictions:
                                # Calculate average predicted traffic
                                avg_prediction = sum(predictions) / len(predictions)
                                
                                # Calculate a prediction factor (0.7-1.3)
                                # Lower predicted traffic = higher score
                                prediction_factor = 1.3 - (avg_prediction / 100) * 0.6
                                prediction_factor = max(0.7, min(1.3, prediction_factor))
                                
                                # Apply prediction factor to base score
                                ai_scores[server] = base_score * prediction_factor
                            else:
                                # No prediction data - use base score
                                ai_scores[server] = base_score
                        
                        dynamic_logger.debug(f"AI-enhanced resource scores: {ai_scores}")
                        
                        # Choose the best server based on score
                        if ai_scores:
                            best_server = max(ai_scores.items(), key=lambda x: x[1])[0]
                            dynamic_logger.info(f"AI-enhanced resource-based chose: {best_server}, Score: {ai_scores[best_server]}")
                            return best_server
                
                except Exception as e:
                    dynamic_logger.error(f"Error in AI-enhanced resource-based: {e}")
                    dynamic_logger.warning("Falling back to standard resource-based algorithm")
            
            else:
                # Standard resource-based algorithm (exactly as in original)
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
                if not best_servers:
                    return None
        
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
