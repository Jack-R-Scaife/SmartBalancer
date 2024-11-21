import threading
import time
from handlers import LinkHandler
from health_check import HealthCheck
from resource_monitor import ResourceMonitor
from security import SecureChannel
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from flask import Flask, jsonify, request
from flask_compress import Compress
import random
# Initialize Flask app
app = Flask(__name__)
resource_monitor = ResourceMonitor()  #
health_check_instance = HealthCheck()
compress = Compress()
compress.init_app(app)
app.config['COMPRESS_ALGORITHM'] = 'brotli'
app.config['COMPRESS_LEVEL'] = 11
class Agent:
    def __init__(self, server_id):
        self.server_id = server_id
        self.load_balancer_ip = None  # Initialize as None to capture dynamically later
        self.link_handler = None  # Will be initialized once load_balancer_ip is set
        self.secure_channel = SecureChannel()
        self.is_running = False

    def set_load_balancer_ip(self, ip_address):
        """
        Set the load balancer's IP address dynamically.
        """
        if not self.load_balancer_ip:
            self.load_balancer_ip = ip_address
            self.link_handler = LinkHandler(load_balancer_ip=self.load_balancer_ip)
            print(f"Load Balancer IP set to {self.load_balancer_ip}")

    def link_to_load_balancer(self):
        """
        Link the server to the load balancer.
        This sends the public key and other necessary data to the load balancer.
        """
        if self.is_running:
            print("Agent is already linked to the load balancer. Skipping relink.")
            return True
    
        if not self.load_balancer_ip:
            print("Load Balancer IP is not set. Cannot link.")
            return False
        
        ip_address = self.get_ip_address()  # Get the server's IP address
        public_key = self.secure_channel.get_public_key()  # Get the public key in PEM format
        signature = self.generate_signature(public_key)  # Sign the public key with the private key

        # Send the public key, IP address, and signature to the load balancer
        success = self.link_handler.link(public_key, ip_address, signature, b'challenge message')

        if success:
            print("Agent successfully linked to load balancer.")
            return True
        else:
            print("Failed to link to load balancer.")
            if success.get('message') == 'Server already linked.':
                print("Server is already linked. Stopping further attempts.")
                return True  # Stop retrying
            return False

    def get_ip_address(self):
        """
        Get the actual IP address of the server from the proper network interface.
        """
        import socket
        # Use socket to get the actual IP of the agent, not the loopback address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to an external server to get the network interface IP
            s.connect(('8.8.8.8', 80))  # Google's DNS server is used just to get the route
            ip_address = s.getsockname()[0]
        finally:
            s.close()
        return ip_address

    def generate_signature(self, message):
        """
        Generate a digital signature for the public key using the agent's private key.
        """
        if isinstance(message, str):
            message = message.encode('utf-8')  # Convert string to bytes

        private_key = self.secure_channel.private_key
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    def reconnect_loop(self, retry_interval=5):
        """
        Periodically attempt to reconnect to the load balancer.
        """
        while not self.is_running:
            success = self.link_to_load_balancer()
            if success:
                print("Reconnected to load balancer.")
                self.is_running = True
                return  # Exit the loop once connected successfully.
            else:
                print(f"Retrying connection in {retry_interval} seconds...")
                time.sleep(retry_interval)

    def start(self):
        self.is_running = True
        while not self.link_to_load_balancer():
            print("Retrying connection in 5 seconds...")
            time.sleep(5)

        app.run(host="0.0.0.0", port=8000)

    def run(self):
        """
        Run the agent's main loop to monitor resources and health.
        """
        while self.is_running:
            current_status = health_check_instance.determine_status(self.load_balancer_ip)
            print(f"Current health status: {current_status}")
            self.link_handler.handle()
            time.sleep(5)

    def stop(self):
        """
        Stop the agent.
        """
        self.is_running = False
        print(f"Agent {self.server_id} stopped.")


# Flask route to respond to the load balancer's request to link the server
@app.route('/link', methods=['POST'])
def link_server():
    """
    Handle request from load balancer to link server and return public key.
    """
    print("Request received by agent.")  # Debugging message
    
    # Dynamically set the load balancer IP from the incoming request
    agent_instance.set_load_balancer_ip(request.remote_addr)

    # Retrieve the public key and ensure it's in string format
    public_key = agent_instance.secure_channel.get_public_key()
    
    if isinstance(public_key, bytes):
        public_key = public_key.decode('utf-8')

    return jsonify({
        "public_key": public_key
    })

# Flask route to respond to health check requests
@app.route('/health', methods=['GET'])
def health_check():
    # If load_balancer_ip is not set, capture it from the incoming request
    if not agent_instance.load_balancer_ip:
        agent_instance.set_load_balancer_ip(request.remote_addr)
    
    # Determine the status of the agent
    status = health_check_instance.determine_status(agent_instance.load_balancer_ip)
    
    # Log the status for debugging purposes
    print(f"Determined status for agent {agent_instance.get_ip_address()}: {status}")
    
    # Return the JSON response using 'st' for status
    return jsonify({"ip": agent_instance.get_ip_address(), "st": status}), 200

@app.route('/delink', methods=['POST'])
def delink_server():
    """
    Handle request to delink the server from the load balancer.
    This will stop the agent and remove any association with the load balancer.
    """
    print("Received de-link request. Stopping agent.")
    agent_instance.stop()  # Stop the agent
    # Clear any sensitive data, if needed (e.g., public/private keys)
    agent_instance.secure_channel.private_key = None  # Remove private key
    return jsonify({"message": "Server delinked and stopped successfully"}), 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        metrics = resource_monitor.monitor(interval=20)  
        return jsonify({"ip": agent_instance.get_ip_address(), "metric": metrics}), 200
    except Exception as e:
        print(f"Error in /metrics: {str(e)}")
        return jsonify({"error": f"Failed to generate metrics: {str(e)}"}), 500



if __name__ == "__main__":
    # Create the agent instance without hardcoding the load balancer IP
    agent_instance = Agent(server_id="server-1234")
    
    # Start the agent
    agent_instance.start()


