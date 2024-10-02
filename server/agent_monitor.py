import requests
import time
from app import db, create_app
from app.models import Server

class LoadBalancer:
    def __init__(self):
        # Initialize the LoadBalancer with an empty list to store agent IP addresses
        self.app = create_app()
        self.known_agents = []  # List of known agent IP addresses
        self.load_agents_from_db() # Load agents from the database on startup
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
        with self.app.app_context():
            status_mapping = {
                1: "healthy",
                2: "overloaded",
                3: "critical",
                4: "down",
                5: "idle",
                6: "maintenance"
            }
            print(f"Currently monitoring agents: {self.known_agents}")
            
            for agent_ip in self.known_agents:
                try:
                    response = requests.get(f"http://{agent_ip}:8000/health")
                    print(f"Raw response from agent {agent_ip}: {response.text}")  # Debugging step

                    if response.status_code == 200:
                        agent_status_code = response.json().get('st', None)  # Get numeric status from agent

                        if agent_status_code is not None:
                            # Convert numeric status code to string status
                            agent_status = status_mapping.get(agent_status_code, "down")  # Default to "down" if unrecognized
                            print(f"Agent {agent_ip} status: {agent_status}")

                            # Update the server status in the database
                            server = Server.query.filter_by(ip_address=agent_ip).first()
                            if server:
                                server.status = agent_status  # Save the string status in DB
                                db.session.commit()
                        else:
                            print(f"No status returned from agent {agent_ip}")
                    else:
                        print(f"Agent {agent_ip} is not responding.")
                        self.update_server_status(agent_ip, "offline")
                except Exception as e:
                    print(f"Error pinging agent {agent_ip}: {e}")
                    self.update_server_status(agent_ip, "offline")

                    
    def monitor_agents(self, interval=10):
        """
        Continuously monitor the agents by periodically pinging them at a given interval.
        The interval parameter (in seconds) controls how often the agents are pinged.
        """
        while True:
            # Ping all the known agents
            self.ping_agents()
            # Sleep for the specified interval before checking again
            time.sleep(interval)
    
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