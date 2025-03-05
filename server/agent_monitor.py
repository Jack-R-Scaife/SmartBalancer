import time
from datetime import datetime
from app import db, create_app
from app.models import Server, LoadBalancerSetting,Strategy,PredictiveLog
import threading
import socket, os
import json
import logging
import binascii
import zipfile
from server.logging_config import main_logger, traffic_logger
from server.dynamic_algorithms import DynamicAlgorithms
from server.static_algorithms import StaticAlgorithms
from server.traffic_store import TrafficStore
from threading import Lock
main_logger.info("Agent monitor starting")
traffic_logger.debug("Traffic logger initialized")
db_lock = Lock()

class LoadBalancer:
    _instance = None
    _lock = threading.Lock()  # To ensure thread safety
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LoadBalancer, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):  
            main_logger.info("Initializing LoadBalancer")
            self.app = create_app()
            self.known_agents = []  # List of known agent IP addresses
            self.strategy_executor = StaticAlgorithms()
            self.dynamic_executor = DynamicAlgorithms()
            self.load_agents_from_db()
            self.load_saved_strategies()  # New step to load strategies
            self.initialized = True

    def load_agents_from_db(self):
        main_logger.info("Loading agents from the database")
        with self.app.app_context():
            try:
                servers = Server.query.order_by(Server.ip_address).all()  # Sort agents by IP
                self.known_agents = [server.ip_address for server in servers]  # Clear and rebuild list
                for ip in self.known_agents:
                    main_logger.debug(f"Loaded agent with IP {ip} from database")
            except Exception as e:
                main_logger.error(f"Error loading agents from database: {e}")

    def add_agent(self, agent_ip):
        """
        Add a new agent's IP address to the list of known agents.
        This method allows the load balancer to track which agents it should monitor.
        """
        main_logger.info(f"Attempting to add agent with IP: {agent_ip}")
        with self.app.app_context():
            if agent_ip not in self.known_agents:
                self.known_agents.append(agent_ip)
                main_logger.info(f"Agent {agent_ip} added to known agents")
            else:
                main_logger.warning(f"Agent {agent_ip} already exists in known agents")

    def send_tcp_request(self, ip_address, port, command, payload=None):
        """
        Send a command to an agent over TCP and return the response.
        Logs all key steps and errors for debugging.
        """
        main_logger.info(f"Preparing to send command '{command}' to {ip_address}:{port}")
        try:
            # Log the IP, port, and command
            with socket.create_connection((ip_address, port), timeout=5) as sock:
                # Prepare the request
                request = {"command": command}
                if payload:
                    request.update(payload)
                main_logger.debug(f"Sending request: {request}")
                sock.sendall(json.dumps(request).encode('utf-8'))
                # Receive the response in chunks
                data = b""
                while True:
                    chunk = sock.recv(65536)  
                    if not chunk:
                        break
                    data += chunk
                main_logger.debug(f"Raw response received: {data.decode('utf-8')}")
                # Decode and parse the JSON response
                response = json.loads(data.decode('utf-8'))
                main_logger.info(f"Parsed response: {response}")
                return response
        except json.JSONDecodeError as e:
            main_logger.error(f"Malformed JSON response from {ip_address}: {e}")
            return {"status": "error", "message": "Malformed JSON response"}
        except Exception as e:
            main_logger.error(f"Communication error with {ip_address}: {e}")
            return {"status": "error", "message": str(e)}

    def fetch_alerts_from_all_agents(self):
        """
        Fetch alerts from all known agents using TCP.
        """
        main_logger.info("Fetching alerts from all known agents")
        alerts = []
        for ip in self.known_agents:
            try:
                # Send the TCP request to fetch alerts
                response = self.send_tcp_request(ip, 9000, "alerts")
                if response.get("status") == "success":
                    agent_alerts = response.get("alerts", [])
                    for alert in agent_alerts:
                        if "timestamp" not in alert:
                            main_logger.warning(f"Missing 'timestamp' in alert from {ip}: {alert}")
                    alerts.extend(agent_alerts)  # Append alerts directly
                    main_logger.debug(f"Alerts fetched from {ip}: {agent_alerts}")
                else:
                    alerts.append({"ip": ip, "error": response.get("message")})
                    main_logger.warning(f"Failed to fetch alerts from {ip}: {response.get('message')}")
            except Exception as e:
                main_logger.error(f"Error fetching alerts from {ip}: {e}")
        return alerts
    
    def ping_agents(self):
        """
        Ping all known agents and update their status in the database.
        Adjusts the interval based on the agent's status.
        """
        main_logger.info("Pinging all known agents")
        with self.app.app_context():
            status_mapping = {
                1: "healthy",
                2: "overloaded",
                3: "critical",
                4: "down",
                5: "idle",
                6: "maintenance"
            }

            retry_count = 0
            max_retries = 5

            # Retry logic for when no agents are available
            while retry_count <= max_retries:
                if not self.known_agents:
                    main_logger.info(f"[DEBUG] Current known agents: {self.known_agents}")
                    retry_count += 1

                    if retry_count > max_retries:
                        main_logger.info(f"No agents found after multiple attempts. Waiting for 20 seconds before trying again.")
                        time.sleep(20)
                        retry_count = 0  # Reset retry count after waiting
                    else:
                        main_logger.info(f"Retrying... Attempt {retry_count}/{max_retries}")
                        time.sleep(2)  # Small delay before next retry attempt
                else:
                    # If agents are found, break the retry loop
                    main_logger.info(f"Currently monitoring agents: {self.known_agents}")
                    break

            # Reset retry count for other purposes
            retry_count = 0
            main_logger.info(f"Currently monitoring agents: {self.known_agents}")
            
            agent_intervals = {}  # To store ping intervals for each agent

            for agent_ip in self.known_agents:
                # Default interval is 1 second unless otherwise specified
                interval = agent_intervals.get(agent_ip, 1)
                try:
                    start_time = time.time()
                    response = self.send_tcp_request(agent_ip, 9000, "health")
                    response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    main_logger.info(f"Raw response from agent {agent_ip}: {response}")

                    agent_status = "down"  # Default value for agent_status

                    if response.get("status") == "success":
                        agent_status_code = response.get("health")
                        if agent_status_code is not None:
                            # Map numeric status to string
                            agent_status = status_mapping.get(agent_status_code, "down")
                            main_logger.info(f"Agent {agent_ip} status: {agent_status}")

                            # Update status in the database
                            server = Server.query.filter_by(ip_address=agent_ip).first()
                            if server:
                                server.status = agent_status
                                db.session.commit()
                            # Update DynamicAlgorithms with response time
                            self.dynamic_executor.response_times[agent_ip] = response_time  

                            # Adjust interval based on the agent's status
                            if agent_status in ['idle', 'down']:
                                interval = 10  # Slow down checks for idle or down agents
                            else:
                                interval = 1  # Keep checks fast for active agents

                            # Update the interval for next time
                            agent_intervals[agent_ip] = interval
                        else:
                            main_logger.info(f"No status returned from agent {agent_ip}")
                            self.update_server_status(agent_ip, "offline")
                            self.dynamic_executor.response_times[agent_ip] = float('inf')
                            agent_intervals[agent_ip] = 30  # Default slower interval for offline agents
                    else:
                        main_logger.info(f"Agent {agent_ip} is not responding.")
                        self.update_server_status(agent_ip, "offline")
                        self.dynamic_executor.response_times[agent_ip] = float('inf')
                        agent_intervals[agent_ip] = 10  # Slow interval for unresponsive agents

                except Exception as e:
                    main_logger.error(f"Error with TCP connection to agent {agent_ip}: {e}")
                    self.update_server_status(agent_ip, "offline")
                    self.dynamic_executor.response_times[agent_ip] = float('inf')
                    agent_intervals[agent_ip] = 10  # Slow interval for agents that caused an error

            # Return the calculated intervals for further use in sleep
            return agent_intervals

                    
    def monitor_agents(self):
        """
        Continuously monitor the agents by periodically pinging them.
        Adjust the interval based on the agent's current status.
        """
        agent_intervals = {}  # To store intervals per agent (IP-based)
        main_logger.info("Starting agent monitoring loop")
        while True:
            # Ping all the known agents and get their intervals
            agent_intervals = self.ping_agents()

            # Use the shortest interval for sleeping between pings
            min_interval = min(agent_intervals.values(), default=1)
            time.sleep(min_interval)

    def update_server_status(self,ip_address,status):
        # Find the server by IP address and update its status
        server = Server.query.filter_by(ip_address=ip_address).first()
        if server:
            server.status = status  # Update the status in the database
            db.session.commit()
        

    def fetch_metrics_from_selected_agent(self, scenario=None, group_id=None):
        """
        Fetch system metrics and log traffic using the active strategy from the database.
        The active strategy for the group is fetched and used to select the next agent.
        """
        main_logger.info("Fetching metrics using active strategy")
        metrics = []
        traffic_store = TrafficStore.get_instance()
        window_size = 30
        now = time.time()

        # Get the active strategy for the provided group_id, defaulting to "Round Robin" if not set.
        active_strategy = self.get_group_strategy(group_id) if group_id else "Round Robin"
        main_logger.info(f"Active strategy for group {group_id}: {active_strategy}")

        # Select the next agent based on the active strategy.
        if active_strategy == "Round Robin":
            selected_agent = self.strategy_executor.round_robin()
        elif active_strategy == "Weighted Round Robin":
            selected_agent = self.strategy_executor.weighted_round_robin()
        elif active_strategy == "Least Connections":
            selected_agent = self.dynamic_executor.least_connections()
        elif active_strategy == "Least Response Time":
            selected_agent = self.dynamic_executor.least_response_time()
        elif active_strategy == "Resource-Based":
            selected_agent = self.dynamic_executor.resource_based()
        else:
            main_logger.warning(f"Unknown strategy '{active_strategy}', defaulting to Round Robin.")
            selected_agent = self.strategy_executor.round_robin()

        if not selected_agent:
            main_logger.warning("No agent selected by active strategy!")
            return metrics

        try:
            # Determine the group for the selected agent.
            group_id = self.lookup_group_id_for_agent(selected_agent)
            
            # Measure round-trip time for the metrics request.
            start_time = time.time()
            response = self.send_tcp_request(selected_agent, 9000, "metrics")
            round_trip_ms = (time.time() - start_time) * 1000

            if response.get("status") == "success":
                system_metrics = response.get("metrics", {})
                main_logger.debug(f"System metrics from {selected_agent}: {system_metrics}")

                # Retrieve traffic data for the selected agent within the rolling window.
                agent_traffic = traffic_store.get_traffic_data(agent_ip=selected_agent)
                recent_traffic = [entry for entry in agent_traffic if (now - entry["timestamp"]) <= window_size]
                traffic_rate = sum(e["value"] for e in recent_traffic)
                traffic_volume = len(recent_traffic)
                main_logger.info(f"For agent {selected_agent}, traffic_rate={traffic_rate}, volume={traffic_volume}")

                # Log metrics if there's significant traffic.
                if traffic_rate > 0:
                    connections_count = system_metrics.get("connections", 0)

                    # **Fix: Ensure correct indentation for db_lock**
                    with db_lock:
                        log_entry = PredictiveLog(
                            timestamp=datetime.utcnow(),  # Ensure millisecond precision
                            server_ip=selected_agent,
                            response_time=round_trip_ms,
                            cpu_usage=system_metrics.get("cpu_total", 0),
                            memory_usage=system_metrics.get("memory", 0),
                            connections=connections_count,
                            traffic_rate=traffic_rate,
                            traffic_volume=traffic_volume,
                            scenario=scenario or "default_scenario",
                            strategy=active_strategy or "Unknown",
                            group_id=group_id
                        )
                        db.session.add(log_entry)
                        db.session.commit()

                else:
                    main_logger.info(f"No significant traffic for {selected_agent}; skipping DB insert.")

                metrics.append({"ip": selected_agent, "metrics": system_metrics})
            else:
                error_msg = response.get("message", "Unknown error")
                metrics.append({"ip": selected_agent, "error": error_msg})
                main_logger.warning(f"Failed to fetch metrics from {selected_agent}: {error_msg}")

        except Exception as e:
            metrics.append({"ip": selected_agent, "error": str(e)})
            main_logger.error(f"Error fetching metrics from {selected_agent}: {e}")
            db.session.rollback()  # Prevent database corruption

        return metrics

    def get_group_strategy(self, group_id):
        """
        Retrieve the strategy for a specific group dynamically.
        """
        with self.app.app_context():
            setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
            if not setting:
                main_logger.warning(f"No strategy found for group {group_id}")
                return None
            strategy = Strategy.query.get(setting.active_strategy_id)
            return strategy.name if strategy else None

    def simulate_traffic(self, traffic_config):
        """Simulate traffic and route requests based on group-specific strategies."""
        traffic_logger.info(f"Simulate traffic invoked with config: {traffic_config}")

        # Validate traffic_config
        required_keys = ["url", "type", "rate", "duration"]
        for key in required_keys:
            if key not in traffic_config:
                traffic_logger.error(f"Missing key '{key}' in traffic_config: {traffic_config}")
                return {"status": "error", "message": f"Missing key '{key}' in traffic_config"}

        scenario = traffic_config.get("scenario", "default_scenario")

        if not self.known_agents:
            traffic_logger.warning("No known agents available for traffic simulation.")
            return {"status": "error", "message": "No agents available for traffic simulation"}

        traffic_store = TrafficStore.get_instance()
        rate = traffic_config["rate"]
        duration = traffic_config["duration"]

        for _ in range(duration):
            current_time = time.time()  # use float timestamp for high precision
            for _ in range(rate):
                try:
                    # Get target agent and group (existing code)
                    target_agent = None
                    group_id = None
                    for agent_ip in self.known_agents:
                        group_id = self.lookup_group_id_for_agent(agent_ip)
                        if group_id:
                            target_agent = agent_ip
                            break

                    if not target_agent or not group_id:
                        traffic_logger.error("No agents with valid group association found")
                        return {"status": "error", "message": "No agents with valid group configuration"}

                    # Execute group-specific strategy
                    target_agent = self.execute_strategy(group_id)
                    if not target_agent:
                        traffic_logger.warning("No agent selected by the strategy.")
                        continue

                    traffic_logger.info(
                        "Traffic predictive data logged",
                        extra={
                            "timestamp": current_time,
                            "target_agent": target_agent,
                            "rate": rate,
                            "duration": duration,
                        }
                    )
                    response = self.send_tcp_request(target_agent, 9000, "simulate_traffic", payload=traffic_config)
                    traffic_logger.debug(f"Traffic sent to {target_agent}: {response}")

                    # Store traffic data with high precision timestamp
                    traffic_store.append_traffic_data(target_agent, current_time, 1)
                    self.fetch_metrics_from_selected_agent(scenario=scenario, group_id=group_id)

                except Exception as e:
                    traffic_logger.error(f"Error sending traffic simulation command: {str(e)}")
                    continue

            time.sleep(1)

        return {"status": "success", "message": "Traffic simulation completed"}

    

    def lookup_group_id_for_agent(self, ip_address):
        """
        Given an agent's IP address, return the group_id of the group this server belongs to.
        If server or group association is not found, return None.
        """
        with self.app.app_context():
            # 1) Find the server row
            server = Server.query.filter_by(ip_address=ip_address).first()
            if not server:
                return None

            # 2) Check the linking table (ServerGroupServer)
            from app.models import ServerGroupServer
            association = ServerGroupServer.query.filter_by(server_id=server.server_id).first()
            if association:
                return association.group_id
            else:
                return None
    
    def set_active_strategy(self, strategy_name, group_id):
        """
        Set the active strategy for a specific group.
        """
        with self.app.app_context():
            # Fetch the LoadBalancerSetting for the group
            setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
            if not setting:
                main_logger.error(f"No LoadBalancerSetting found for group {group_id}")
                return

            # Fetch the Strategy by name
            strategy = Strategy.query.filter_by(name=strategy_name).first()
            if not strategy:
                main_logger.error(f"Strategy {strategy_name} not found in the database")
                return

            # Update the active strategy for the group
            setting.active_strategy_id = strategy.strategy_id
            db.session.commit()
            main_logger.info(f"Active strategy for group {group_id} set to {strategy_name}")


    def execute_strategy(self, group_id):
        """
        Execute the strategy for the specified group.
        """
        if not self.known_agents:
            raise ValueError("No agents available for routing.")

        # Fetch the strategy for the group dynamically
        strategy = self.get_group_strategy(group_id)
        main_logger.debug(f"Executing strategy for group {group_id}: {strategy}")

        self.strategy_executor.known_agents = self.known_agents
        self.dynamic_executor.known_agents = self.known_agents

        # Fetch settings for the target group
        with self.app.app_context():
            setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
        
        strategies = []
        if setting:
            # Parse failover_priority correctly
            strategies = [strategy]
            if setting.failover_priority:
                strategies += [s.strip() for s in setting.failover_priority.split(",")]  # Split by comma without space

        main_logger.debug(f"Strategies to evaluate: {strategies}")
        
        for strat in strategies:
            main_logger.debug(f"Evaluating strategy: {strat}")
            try:
                if strat == "Round Robin":
                    return self.strategy_executor.round_robin()
                elif strat == "Weighted Round Robin":
                    return self.strategy_executor.weighted_round_robin()
                elif strat == "Least Connections":
                    return self.dynamic_executor.least_connections()
                elif strat == "Least Response Time":
                    return self.dynamic_executor.least_response_time()
                elif strat.strip() == "Resource-Based":  # Handle whitespace
                    return self.dynamic_executor.resource_based()
                else:
                    raise ValueError(f"Unsupported strategy: {strat}")
            except Exception as e:
                main_logger.error(f"Strategy {strat} failed: {e}", exc_info=True)

        raise ValueError(f"No valid strategy found for group {group_id}.")


    
    def load_saved_strategies(self):
        """
        Load saved strategies for all groups from the database.
        """
        main_logger.info("Loading saved strategies for all groups")
        with self.app.app_context():
            settings = LoadBalancerSetting.query.all()
            for setting in settings:
                strategy = Strategy.query.get(setting.active_strategy_id)
                if strategy:
                    main_logger.info(f"Loaded strategy '{strategy.name}' for group {setting.group_id}")
   
    
    def fetch_logs_from_all_agents(self):
        """
        Fetch logs from all known agents using TCP (get_logs).
        The agent returns 'zip_data' in hex. We unhex it, write the .zip to disk,
        then extract it into /logs (or ./logs).
        Return a list describing success/error for each agent.
        """
        logs_dir = "./logs"  # or "/logs" if you prefer absolute
        os.makedirs(logs_dir, exist_ok=True)

        results = []

        for ip in self.known_agents:
            agent_result = {"ip": ip}
            try:
                response = self.send_tcp_request(ip, 9000, "get_logs")

                if response.get("status") == "success" and "zip_data" in response:
                    # Convert hex back to raw bytes
                    zip_data = binascii.unhexlify(response["zip_data"])

                    # Write the zip to disk
                    zip_path = os.path.join(logs_dir, f"{ip}_logs.zip")
                    with open(zip_path, "wb") as f:
                        f.write(zip_data)

                    # Extract them into logs_dir
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(logs_dir)

                    os.remove(zip_path)  # Clean up after extraction
                    agent_result["status"] = "success"

                else:
                    # Either "status" wasn't success or no "zip_data"
                    agent_result["status"] = "error"
                    agent_result["message"] = response.get("message", "Unknown error")

            except Exception as e:
                agent_result["status"] = "error"
                agent_result["message"] = str(e)

            results.append(agent_result)

        return results


        
    def fetch_all_metrics(self, scenario=None, group_id=None):
        main_logger.info("Fetching metrics from all agents")
        metrics = []
        for agent in self.known_agents:
            try:
                start_time = time.time()
                response = self.send_tcp_request(agent, 9000, "metrics")
                round_trip_ms = (time.time() - start_time) * 1000
                if response.get("status") == "success":
                    system_metrics = response.get("metrics", {})
                    main_logger.debug(f"System metrics from {agent}: {system_metrics}")
                    metrics.append({"ip": agent, "metrics": system_metrics})
                else:
                    error_msg = response.get("message", "Unknown error")
                    metrics.append({"ip": agent, "error": error_msg})
                    main_logger.warning(f"Failed to fetch metrics from {agent}: {error_msg}")
            except Exception as e:
                metrics.append({"ip": agent, "error": str(e)})
                main_logger.error(f"Error fetching metrics from {agent}: {e}")
        return metrics


if __name__ == "__main__":
    load_balancer = LoadBalancer()
    # Start monitoring the agents, pinging them every 10 seconds
    load_balancer.monitor_agents()