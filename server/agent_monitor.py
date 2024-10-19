import requests
import time
from app import db, create_app
from app.models import Server
import threading

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
        if not hasattr(self, "initialized"):  # Avoid reinitializing
        # Initialize the LoadBalancer with an empty list to store agent IP addresses
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

            while retry_count <= max_retries:
                if not self.known_agents:
                    print("No agents are currently being monitored") 
                    retry_count +=1

                    if retry_count > max_retries:
                        print("No agents found after multiple attempts. Waiting for 20 seconds before trying again.")
                        time.sleep(20)
                        retry_count = 0  # Reset retry count after waiting
                    else:
                        print(f"Retrying... Attempt {retry_count}/{max_retries}")
                        time.sleep(2)  # Small delay before next retry attempt (can be adjusted)
                else:
                    # If agents are found, break the retry loop
                    print(f"Currently monitoring agents: {self.known_agents}")
                    break

            retry_count = 0
            print(f"Currently monitoring agents: {self.known_agents}")
            
            agent_intervals = {}  # To store ping intervals for each agent

            for agent_ip in self.known_agents:
                # Default interval is 1 second unless otherwise specified
                interval = agent_intervals.get(agent_ip, 1)
                try:
                    response = requests.get(f"http://{agent_ip}:8000/health", timeout=5)
                    print(f"Raw response from agent {agent_ip}: {response.text}")

                    if response.status_code == 200:
                        agent_status_code = response.json().get('st', None)

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
                    print(f"Error pinging agent {agent_ip}: {e}")
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
    

if __name__ == "__main__":
    load_balancer = LoadBalancer()
    # Start monitoring the agents, pinging them every 10 seconds
    load_balancer.monitor_agents()