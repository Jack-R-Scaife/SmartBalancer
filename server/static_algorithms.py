import threading
import logging
from server.logging_config import round_robin_logger,weights_logger

class StaticAlgorithms:
    def __init__(self):
    # List of servers and index state for round-robin and weighted round-robin
        self.known_agents = []
        self.current_index = 0
        self.index_weights = []
        self.lock = threading.Lock()  # Protect shared state

    def round_robin(self, ai_enabled=False):
        """Round-robin load balancing, optionally enhanced with AI predictions."""
        with self.lock:
            if not self.known_agents:
                return None

            if ai_enabled:
                try:
                    # Fetch current metrics and predicted traffic from API
                    import requests
                    metrics = requests.get("http://127.0.0.1:5000/api/metrics/all").json()
                    predictions = requests.get("http://127.0.0.1:5000/api/predicted_traffic").json()

                    # Map predicted values to each server IP
                    prediction_map = {}
                    for pred in predictions:
                        prediction_map.setdefault(pred['agent_ip'], []).append(pred['value'])

                    # Score servers based on CPU usage and predicted load
                    scored_servers = []
                    for server in metrics:
                        ip = server['ip']
                        cpu = server['metrics'].get('cpu_total', 0)
                        avg_pred = sum(prediction_map.get(ip, [0])) / len(prediction_map.get(ip, [0]))
                        score = (100 - cpu) * 0.7 + (100 - avg_pred) * 0.3
                        scored_servers.append((ip, score))

                    # Select the highest scoring server (AI-based ordering)
                    scored_servers.sort(key=lambda x: x[1], reverse=True)
                    ordered = [s[0] for s in scored_servers]
                    selected = ordered[self.current_index % len(ordered)]
                    self.current_index += 1
                    return selected
                except:
                    # On failure, fall back to standard round-robin
                    pass

            # Standard round-robin: return server in sequential order
            selected = self.known_agents[self.current_index % len(self.known_agents)]
            self.current_index += 1
            return selected

    def set_weights(self, weights):
        """Set weights for weighted round-robin; resets index for consistency."""
        with self.lock:
            # Convert weight values if necessary (they should already be integers)
            self.index_weights = [
                server for server, weight in weights.items() for _ in range(weight)
            ]
            self.current_index = 0
            weights_logger.debug(f"Received weights: {weights}")
            weights_logger.debug(f"Constructed weighted list: {self.index_weights}")

    def weighted_round_robin(self, ai_enabled=False):
        """Select the next server from the weighted list in a thread-safe manner."""
        with self.lock:
            if not self.index_weights:
                return None
                
            if ai_enabled:
                weights_logger.info("Using AI-enhanced weighted round robin algorithm")
                try:
                    # Get metrics for each server
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
                        
                        # Create an adjusted weight list
                        dynamic_weights = {}
                        
                        # Calculate base weights from current index_weights
                        base_weights = {}
                        for ip in self.known_agents:
                            base_weights[ip] = self.index_weights.count(ip)
                        
                        # Process each server individually
                        for ip in self.known_agents:
                            # Get metrics for this server
                            metrics = server_metrics.get(ip, {})
                            cpu_usage = metrics.get('cpu_total', 0)
                            memory_usage = metrics.get('memory', 0)
                            
                            # Get prediction average
                            predictions = server_predictions.get(ip, [0])
                            avg_prediction = sum(predictions) / len(predictions) if predictions else 0
                            
                            # Start with base weight
                            weight = base_weights.get(ip, 1)
                            
                            # Calculate weight adjustment using metrics and predictions
                            # Favor servers with low CPU, low memory, and low predicted traffic                        
                            performance_factor = (100 - cpu_usage) / 100
                            memory_factor = (100 - memory_usage) / 100
                            prediction_factor = (100 - min(100, avg_prediction)) / 100
                            
                            # Combine factors
                            adjustment = (performance_factor * 0.4 + 
                                        memory_factor * 0.3 + 
                                        prediction_factor * 0.3)
                            
                            # Apply adjustment (0.5x to 1.5x of original weight)
                            adjusted_weight = max(1, int(weight * max(0.5, min(1.5, adjustment))))
                            dynamic_weights[ip] = adjusted_weight
                        
                        weights_logger.debug(f"Base weights: {base_weights}")
                        weights_logger.debug(f"AI-adjusted weights: {dynamic_weights}")
                        
                        # Create new weighted server list
                        new_index_weights = []
                        for ip, count in dynamic_weights.items():
                            new_index_weights.extend([ip] * count)
                        
                        if new_index_weights:
                            # Select using the new weights
                            if self.current_index >= len(new_index_weights):
                                self.current_index = 0
                                
                            server = new_index_weights[self.current_index]
                            self.current_index = (self.current_index + 1) % len(new_index_weights)
                            
                            weights_logger.info(f"AI-Enhanced Weighted RR selected: {server}")
                            return server
                
                except Exception as e:
                    weights_logger.error(f"Error in AI-enhanced weighted round robin: {e}")
                    weights_logger.warning("Falling back to standard weighted round robin")
            else:        
                # Standard weighted round robin (same as original code)
                if self.current_index >= len(self.index_weights):
                    self.current_index = 0
                server = self.index_weights[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.index_weights)
                return server