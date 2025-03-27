import threading
import logging
from server.logging_config import round_robin_logger,weights_logger

class StaticAlgorithms:
    def __init__(self):
    # List of servers and index state for round-robin and weighted round-robin
        self.known_agents = []
        self.current_index = 0
        self.index_weights = []
        self.ai_enabled = False  # Add this line for AI enhancement
        self.lock = threading.Lock()  # Protect shared state

    def round_robin(self):
        """Select the next server using round-robin with thread safety."""
        with self.lock:
            if not self.known_agents:
                round_robin_logger.warning("Round Robin called with no known agents!")
                return None
                
            if self.ai_enabled:
                round_robin_logger.info("Using AI-enhanced round robin algorithm")
                try:
                    # Get load balancer instance
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
                        
                        # Create a list of agents sorted by suitability
                        agent_scores = []
                        
                        for agent in self.known_agents:
                            # Get agent-specific predictions
                            agent_predictions = [p for p in predictions if p.get('agent_ip') == agent]
                            
                            # Default score (neutral)
                            score = 0.5
                            
                            if agent_predictions:
                                # Get average predicted value for this agent
                                avg_predicted_traffic = sum(p.get('value', 0) for p in agent_predictions[:10]) / min(10, len(agent_predictions))
                                
                                # Get resource metrics for this agent
                                agent_metrics = next((a for a in all_metrics if a.get('ip') == agent and 'metrics' in a), None)
                                
                                if agent_metrics and 'metrics' in agent_metrics:
                                    # Calculate health score factors
                                    metrics = agent_metrics['metrics']
                                    cpu_factor = (100 - metrics.get('cpu_total', 0)) / 100
                                    memory_factor = (100 - metrics.get('memory', 0)) / 100
                                    connections = metrics.get('connections', 0)
                                    
                                    # Scenario-specific adjustments
                                    if scenario == 'baseline_high':
                                        score = (cpu_factor * 0.6) + (memory_factor * 0.4)
                                    elif scenario == 'baseline_medium':
                                        score = (cpu_factor * 0.4) + (memory_factor * 0.3) - (connections / 100 * 0.3)
                                    else:  # baseline_low
                                        score = 0.5  # Use regular round-robin order
                            
                            agent_scores.append((agent, score))
                        
                        # Sort agents by score (higher is better)
                        sorted_agents = sorted(agent_scores, key=lambda x: x[1], reverse=True)
                        
                        # Select from top 30% of agents using round-robin
                        top_count = max(1, int(len(sorted_agents) * 0.3))
                        top_agents = [agent for agent, _ in sorted_agents[:top_count]]
                        
                        # Apply round-robin selection among top agents
                        top_index = self.current_index % len(top_agents)
                        selected_agent = top_agents[top_index]
                        
                        # Update the main index
                        self.current_index = (self.current_index + 1) % len(self.known_agents)
                        
                        round_robin_logger.info(f"AI-Enhanced Round Robin selected: {selected_agent}")
                        return selected_agent
                
                except Exception as e:
                    round_robin_logger.error(f"Error in AI-enhanced round robin: {e}")
                    round_robin_logger.warning("Falling back to standard round robin due to error")
            
            # Standard round robin algorithm (also used as fallback)
            round_robin_logger.debug(f"BEFORE: Index: {self.current_index}, Known Agents: {self.known_agents}")
            server = self.known_agents[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.known_agents)
            round_robin_logger.debug(f"AFTER: Selected Server: {server}, Next Index: {self.current_index}")
            return server

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

    def weighted_round_robin(self):
        """Select the next server from the weighted list in a thread-safe manner."""
        with self.lock:
            if not self.index_weights:
                return None
                
            if self.ai_enabled:
                weights_logger.info("Using AI-enhanced weighted round robin algorithm")
                try:
                    # Get load balancer instance
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
                        
                        # Create dynamic weights based on predictions
                        dynamic_weights = {}
                        base_weights = {}
                        
                        # Build a map of base weights from the current index_weights
                        for agent in self.known_agents:
                            base_weights[agent] = self.index_weights.count(agent)
                        
                        # Now adjust weights based on predictions and metrics
                        for agent in self.known_agents:
                            # Start with base weight
                            dynamic_weights[agent] = base_weights.get(agent, 1)
                            
                            # Get agent-specific predictions
                            agent_predictions = [p for p in predictions if p.get('agent_ip') == agent]
                            
                            # Get agent metrics
                            agent_metrics = next((a for a in all_metrics if a.get('ip') == agent and 'metrics' in a), None)
                            
                            if agent_predictions and agent_metrics and 'metrics' in agent_metrics:
                                metrics = agent_metrics['metrics']
                                
                                # Calculate adjustment factors
                                cpu_usage = metrics.get('cpu_total', 0)
                                memory_usage = metrics.get('memory', 0)
                                
                                # Calculate capacity factor (0.1 to 2.0)
                                capacity_factor = 2.0 - ((cpu_usage + memory_usage) / (100 * 2))
                                capacity_factor = max(0.1, min(2.0, capacity_factor))
                                
                                # Scenario-specific adjustments
                                if scenario == 'baseline_high':
                                    dynamic_weights[agent] = int(dynamic_weights[agent] * capacity_factor * 1.5)
                                elif scenario == 'baseline_medium':
                                    dynamic_weights[agent] = int(dynamic_weights[agent] * capacity_factor)
                                else:  # baseline_low
                                    dynamic_weights[agent] = int(dynamic_weights[agent] * (1 + (capacity_factor - 1) * 0.5))
                                
                                # Ensure weight is at least 1
                                dynamic_weights[agent] = max(1, dynamic_weights[agent])
                        
                        weights_logger.debug(f"Original weights: {base_weights}")
                        weights_logger.debug(f"AI-adjusted weights: {dynamic_weights}")
                        
                        # Build a new weighted index list
                        new_index_weights = []
                        for agent, weight in dynamic_weights.items():
                            new_index_weights.extend([agent] * weight)
                        
                        if not new_index_weights:
                            weights_logger.warning("No valid weights after AI adjustment, using original weights")
                            new_index_weights = self.index_weights
                        
                        # Select using the new weights
                        if self.current_index >= len(new_index_weights):
                            self.current_index = 0
                            
                        server = new_index_weights[self.current_index]
                        self.current_index = (self.current_index + 1) % len(new_index_weights)
                        
                        weights_logger.info(f"AI-Enhanced Weighted Round Robin selected: {server}")
                        return server
                
                except Exception as e:
                    weights_logger.error(f"Error in AI-enhanced weighted round robin: {e}")
                    weights_logger.warning("Falling back to standard weighted round robin due to error")
            
            # Standard weighted round robin algorithm (also used as fallback)
            server = self.index_weights[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.index_weights)
            return server