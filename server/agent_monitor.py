import time
from app import db, create_app
from app.models import Server
import threading
import socket
import json
import logging
from server.traffic_store import TrafficStore

# Configure logging
logging.basicConfig(
    filename='agent_monitor.log',  # Log file name
    level=logging.DEBUG,  # Log everything from DEBUG level upwards
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log format
)
traffic_logger = logging.getLogger("traffic_lb")
traffic_handler = logging.FileHandler("traffic_lb.log")
traffic_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
traffic_handler.setFormatter(traffic_formatter)
traffic_logger.addHandler(traffic_handler)
traffic_logger.setLevel(logging.INFO)
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
            self.app = create_app()
            self.known_agents = []  # List of known agent IP addresses
            self.load_agents_from_db() # Load agents from the database on startup
            self.initialized = True

    def load_agents_from_db(self):
        """
        Load all agents' IP addresses from the database and add them to known_agents.
        This ensures that previously linked agents are tracked after a restart.
        """
        with self.app.app_context():  # Ensure we're in an application context
            servers = Server.query.all()  # Fetch all servers from the DB
            for server in servers:
                self.known_agents.append(server.ip_address)
                print(f"Loaded agent with IP {server.ip_address} from database.")

    def add_agent(self, agent_ip):
        """
        Add a new agent's IP address to the list of known agents.
        This method allows the load balancer to track which agents it should monitor.
        """
        print(f"[DEBUG] Attempting to add agent with IP: {agent_ip}")
    
        with self.app.app_context():
            if agent_ip not in self.known_agents:
                self.known_agents.append(agent_ip)
                print(f"[DEBUG] Agent {agent_ip} added to known agents")
            else:
                print(f"[DEBUG] Agent {agent_ip} already exists in known agents")

    def send_tcp_request(self, ip_address, port, command, payload=None):
        """
        Send a command to an agent over TCP and return the response.
        Logs all key steps and errors for debugging.
        """
        try:
            # Log the IP, port, and command
            logging.info(f"[DEBUG] Preparing to send command '{command}' to {ip_address}:{port}")

            with socket.create_connection((ip_address, port), timeout=5) as sock:
                # Prepare the request
                request = {"command": command}
                if payload:
                    request.update(payload)

                # Log the outgoing request
                logging.info(f"[DEBUG] Sending request: {request}")
                sock.sendall(json.dumps(request).encode('utf-8'))

                # Receive the response in chunks
                data = b""
                while True:
                    chunk = sock.recv(65536)  # Read in chunks of 64 KB
                    if not chunk:
                        break
                    data += chunk

                # Log the raw response
                logging.info(f"[DEBUG] Raw response received: {data.decode('utf-8')}")

                # Decode and parse the JSON response
                response = json.loads(data.decode('utf-8'))
                logging.info(f"[DEBUG] Parsed response: {response}")
                return response

        except json.JSONDecodeError as e:
            logging.error(f"[ERROR] Malformed JSON response from {ip_address}: {e}")
            return {"status": "error", "message": "Malformed JSON response"}
        except Exception as e:
            logging.error(f"[ERROR] Communication error with {ip_address}: {e}")
            return {"status": "error", "message": str(e)}

    def fetch_metrics_from_all_agents(self):
        """
        Fetch metrics from all known agents using TCP.
        """
        metrics = []
        for ip in self.known_agents:
            logging.info(f"[DEBUG] Current known agents: {self.known_agents}")
            response = self.send_tcp_request(ip, 9000, "metrics")
            if response.get("status") == "success":
                metrics.append({
                    "ip": response.get("ip"),
                    "metrics": response.get("metrics")
                })
            else:
                metrics.append({"ip": ip, "error": response.get("message")})
        return metrics

    def fetch_alerts_from_all_agents(self):
        """
        Fetch alerts from all known agents using TCP.
        """
        alerts = []
        for ip in self.known_agents:
            try:
                # Send the TCP request to fetch alerts
                response = self.send_tcp_request(ip, 9000, "alerts")
                if response.get("status") == "success":
                    alerts.append({
                        "ip": ip,
                        "alerts": response.get("alerts", [])
                    })
                else:
                    alerts.append({"ip": ip, "error": response.get("message")})
            except Exception as e:
                alerts.append({"ip": ip, "error": f"Error communicating with agent: {str(e)}"})
        return alerts
    
    def ping_agents(self):
        """
        Ping all known agents and update their status in the database.
        Adjusts the interval based on the agent's status.
        """
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
                    logging.info(f"[DEBUG] Current known agents: {self.known_agents}")
                    print("No agents are currently being monitored") 
                    retry_count += 1

                    if retry_count > max_retries:
                        print("No agents found after multiple attempts. Waiting for 20 seconds before trying again.")
                        time.sleep(20)
                        retry_count = 0  # Reset retry count after waiting
                    else:
                        print(f"Retrying... Attempt {retry_count}/{max_retries}")
                        time.sleep(2)  # Small delay before next retry attempt
                else:
                    # If agents are found, break the retry loop
                    print(f"Currently monitoring agents: {self.known_agents}")
                    break

            # Reset retry count for other purposes
            retry_count = 0
            print(f"Currently monitoring agents: {self.known_agents}")
            
            agent_intervals = {}  # To store ping intervals for each agent

            for agent_ip in self.known_agents:
                # Default interval is 1 second unless otherwise specified
                interval = agent_intervals.get(agent_ip, 1)
                try:
                    response = self.send_tcp_request(agent_ip, 9000, "health")
                    print(f"Raw response from agent {agent_ip}: {response}")

                    agent_status = "unknown"  # Default value for agent_status

                    if response.get("status") == "success":
                        agent_status_code = response.get("health")
                        if agent_status_code is not None:
                            # Map numeric status to string
                            agent_status = status_mapping.get(agent_status_code, "down")
                            print(f"Agent {agent_ip} status: {agent_status}")

                            # Update status in the database
                            server = Server.query.filter_by(ip_address=agent_ip).first()
                            if server:
                                server.status = agent_status
                                db.session.commit()

                            # Adjust interval based on the agent's status
                            if agent_status in ['idle', 'down']:
                                interval = 10  # Slow down checks for idle or down agents
                            else:
                                interval = 1  # Keep checks fast for active agents

                            # Update the interval for next time
                            agent_intervals[agent_ip] = interval
                        else:
                            print(f"No status returned from agent {agent_ip}")
                            self.update_server_status(agent_ip, "offline")
                            agent_intervals[agent_ip] = 10  # Default slower interval for offline agents
                    else:
                        print(f"Agent {agent_ip} is not responding.")
                        self.update_server_status(agent_ip, "offline")
                        agent_intervals[agent_ip] = 10  # Slow interval for unresponsive agents

                except Exception as e:
                    print(f"Error with TCP connection to agent {agent_ip}: {e}")
                    self.update_server_status(agent_ip, "offline")
                    agent_intervals[agent_ip] = 10  # Slow interval for agents that caused an error

            # Return the calculated intervals for further use in sleep
            return agent_intervals

                    
    def monitor_agents(self):
        """
        Continuously monitor the agents by periodically pinging them.
        Adjust the interval based on the agent's current status.
        """
        agent_intervals = {}  # To store intervals per agent (IP-based)

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
        
    def fetch_metrics_from_all_agents(self):
        """
        Fetch metrics from all known agents using TCP.
        """
        metrics = []
        for ip in self.known_agents:
            try:
                # Send the TCP request to fetch metrics
                response = self.send_tcp_request(ip, 9000, "metrics")
                if response.get("status") == "success":
                    metrics.append({
                        "ip": response.get("ip"),
                        "metrics": response.get("metrics")
                    })
                else:
                    metrics.append({"ip": ip, "error": response.get("message")})
            except Exception as e:
                metrics.append({"ip": ip, "error": f"Error communicating with agent: {str(e)}"})
        return metrics


    def simulate_traffic(self, traffic_config):
        """
        Simulate traffic and aggregate traffic rates for overlapping requests.
        """
        logging.info(f"simulate_traffic invoked with: {traffic_config}")

        # Validate traffic_config
        required_keys = ["url", "type", "rate", "duration"]
        for key in required_keys:
            if key not in traffic_config:
                logging.error(f"Missing key '{key}' in traffic_config: {traffic_config}")
                return {"status": "error", "message": f"Missing key '{key}' in traffic_config"}

        if not self.known_agents:
            logging.warning("No known agents available to send traffic.")
            return {"status": "error", "message": "No agents available for traffic simulation"}

        # Get the TrafficStore instance for storing traffic data
        traffic_store = TrafficStore.get_instance()

        # Extract rate and duration
        rate = traffic_config["rate"]
        duration = traffic_config["duration"]

        # Send the traffic simulation request to all agents
        for server_ip in self.known_agents:
            try:
                response = self.send_tcp_request(server_ip, 9000, "simulate_traffic", payload=traffic_config)
                logging.info(f"Response from agent {server_ip}: {response}")
            except Exception as e:
                logging.error(f"Error sending traffic simulation command to {server_ip}: {str(e)}")
                return {"status": "error", "message": str(e)}

        # Log traffic data once per second for the duration
        for second in range(duration):
            current_time = int(time.time())  # Current time in seconds
            traffic_store.append_traffic_data(current_time, rate)
            logging.info(f"Aggregated traffic_data: {traffic_store.get_traffic_data()[-1]}")

            time.sleep(1)  # Wait for 1 second

        return {"status": "success", "message": "Traffic simulation completed"}






if __name__ == "__main__":
    load_balancer = LoadBalancer()
    # Start monitoring the agents, pinging them every 10 seconds
    load_balancer.monitor_agents()