import threading
import socket
import time
from alert_manager import AlertManager
from handlers import LinkHandler
from health_check import HealthCheck
from resource_monitor import ResourceMonitor
from security import SecureChannel
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from flask import Flask, jsonify, request
from flask_compress import Compress
import json
import traceback  
import logging
from response_factory import ResponseFactory
# Initialize Flask app
app = Flask(__name__)
resource_monitor = ResourceMonitor()
health_check_instance = HealthCheck()
compress = Compress()
compress.init_app(app)

class Agent:
    def __init__(self, server_id):
        self.server_id = server_id
        self.load_balancer_ip = None
        self.link_handler = None
        self.secure_channel = SecureChannel()
        self.is_running = False
        self.tcp_server_socket = None
        self.alert_manager_thread = None
        self.start_alert_manager()
        logging.info(f"Agent initialized with server_id: {self.server_id}")

    def set_load_balancer_ip(self, ip_address):
        """
        Set the load balancer's IP address dynamically.
        """
        if not self.load_balancer_ip:
            self.load_balancer_ip = ip_address
            self.link_handler = LinkHandler(load_balancer_ip=self.load_balancer_ip)
            logging.info(f"Load Balancer IP set to {self.load_balancer_ip}")

    def link_to_load_balancer(self):
        """
        Link the server to the load balancer.
        """
        try:
            if self.is_running:
                logging.info("Agent is already linked to the load balancer. Skipping relink.")
                return True

            if not self.load_balancer_ip:
                logging.info("Load Balancer IP is not set. Waiting for TCP connection to link.")
                return False

            ip_address = self.get_ip_address()
            public_key = self.secure_channel.get_public_key()
            signature = self.generate_signature(public_key)

            success = self.link_handler.link(public_key, ip_address, signature, b'challenge message')

            if success and success.get("status") == "success":
                logging.info("Agent successfully linked to load balancer.")
                self.is_running = True
                return True
            else:
                logging.error(f"Failed to link to load balancer. Response: {success}")
                return False
        except Exception as e:
            logging.error(f"Error linking to load balancer: {e}")
            logging.debug(traceback.format_exc())
            return False

    def get_ip_address(self):
        """
        Get the actual IP address of the server.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip_address = s.getsockname()[0]
            logging.info(f"Server IP address determined: {ip_address}")
            return ip_address
        except Exception as e:
            logging.error(f"Error getting IP address: {e}")
            logging.debug(traceback.format_exc())
            return None
        finally:
            s.close()

    def generate_signature(self, message):
        """
        Generate a digital signature for the public key.
        """
        try:
            if isinstance(message, str):
                message = message.encode('utf-8')
            private_key = self.secure_channel.private_key
            signature = private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            logging.info("Signature generated successfully.")
            return signature
        except Exception as e:
            logging.error(f"Error generating signature: {e}")
            logging.debug(traceback.format_exc())
            return None


    def reconnect_loop(self, retry_interval=5):
        """
        Attempt to reconnect periodically.
        """
        while not self.is_running:
            logging.info("Attempting to reconnect to load balancer...")
            success = self.link_to_load_balancer()
            if success:
                logging.info("Reconnected to load balancer.")
                self.is_running = True
                return
            else:
                logging.info(f"Retrying connection in {retry_interval} seconds...")
                time.sleep(retry_interval)

    def start(self):
        self.is_running = True
        threading.Thread(target=self.run_tcp_server, daemon=True).start()

    def run_tcp_server(self):
        """
        Run a simple TCP server to listen for link requests.
        """
        try:
            self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server_socket.bind(("0.0.0.0", 9000))
            self.tcp_server_socket.listen(5)
            logging.info("TCP Server listening on port 9000...")

            while True:
                try:
                    client_socket, addr = self.tcp_server_socket.accept()
                    logging.info(f"TCP Connection established with {addr}")
                    threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
                except OSError as e:
                    logging.error(f"Error in TCP server loop: {e}")
        except Exception as e:
            logging.error(f"Unhandled exception in TCP server: {e}")
            logging.debug(traceback.format_exc())
        finally:
            if self.tcp_server_socket:
                self.tcp_server_socket.close()
            logging.info("TCP Server has stopped.")

    def run(self):
        try:
            logging.info("Starting agent main loop...")
            while self.is_running:
                try:
                    if self.load_balancer_ip:
                        current_status = health_check_instance.determine_status(self.load_balancer_ip)
                        logging.info(f"Current health status: {current_status}")
                    else:
                        logging.info("Waiting for load balancer to initiate connection...")
                    time.sleep(5)
                except Exception as e:
                    logging.error(f"Error in main loop iteration: {e}")
                    logging.debug(traceback.format_exc())
        except Exception as e:
            logging.error(f"Unhandled exception in main loop: {e}")
            logging.debug(traceback.format_exc())
        finally:
            logging.info("Exiting the main loop.")

    def stop(self):
        logging.info(f"Stopping agent {self.server_id}...")
        self.is_running = False
        if self.tcp_server_socket:
            self.tcp_server_socket.close()
        logging.info("Agent stopped successfully.")

    def handle_client(self, client_socket):
        """
        Handle incoming TCP requests from the load balancer.
        """
        try:
            # Get the IP of the client (load balancer)
            ip_address = client_socket.getpeername()[0]
            if not self.load_balancer_ip:
                self.set_load_balancer_ip(ip_address)

            # Receive and process the request
            data = client_socket.recv(65536).decode('utf-8')  # Receive up to 4 KB of data
            logging.info(f"[DEBUG] Received raw data: {data}")

            # Parse the received JSON request
            request = json.loads(data)
            command = request.get("command")

            logging.info(f"[DEBUG] Received command: {command}, Request Data: {request}")

            # Handle different commands
            if command == "link":
                response = self.handle_link(client_socket)
            elif command == "health":
                response = self.health_check()
            elif command == "delink":
                response = self.delink_server()
            elif command == "metrics":
                response = self.get_metrics()
            elif command == "alerts":
                response = self.get_alerts()
            else:
                response = {"status": "error", "message": "Unknown command"}

            logging.info(f"[DEBUG] Sending response: {response}")

            # Send the JSON response
            client_socket.sendall(json.dumps(response).encode('utf-8'))
        except json.JSONDecodeError as e:
            logging.error(f"[ERROR] Failed to parse JSON: {e}")
            error_response = {"status": "error", "message": "Invalid JSON format"}
            client_socket.sendall(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            logging.error(f"[ERROR] Error handling client: {e}")
            error_response = {"status": "error", "message": str(e)}
            client_socket.sendall(json.dumps(error_response).encode('utf-8'))
        finally:
            client_socket.close()


    def start_alert_manager(self):
        """
        Start the AlertManager thread to update alerts periodically.
        """
        if self.alert_manager_thread is None or not self.alert_manager_thread.is_alive():
            logging.info("Starting AlertManager thread.")
            self.alert_manager_thread = threading.Thread(
                target=AlertManager.update_alerts,
                args=(self.get_ip_address(),),
                daemon=True
            )
            self.alert_manager_thread.start()
        else:
            logging.info("AlertManager thread is already running.")


    def get_alerts(self):
        """
        Handle 'alerts' command to return cached alerts.
        """
        try:
            alerts = AlertManager.get_cached_alerts()
            logging.info(f"Returning cached alerts: {alerts}")
            return alerts
        except Exception as e:
            logging.error(f"Error fetching cached alerts: {e}")
            logging.debug(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    def handle_link(self,client_socket):
        """
        Handle 'link' command to dynamically set load balancer IP and return public key.
        """
        try:
            # Get the source IP of the TCP request (load balancer's IP)
            ip_address = client_socket.getpeername()[0]
            self.set_load_balancer_ip(ip_address)
            public_key = self.secure_channel.get_public_key()
            if isinstance(public_key, bytes):
                public_key = public_key.decode('utf-8')
            return {"status": "success", "public_key": public_key}
        except Exception as e:
            logging.error(f"Error handling link: {e}")
            return {"status": "error", "message": str(e)}

    def health_check(self):
        """
        Handle 'health' command to return the agent's health status.
        """
        if not self.load_balancer_ip:
            logging.warning("Health check requested, but Load balancer IP is not set.")
            return {"status": "error", "message": "Load balancer IP not set"}

        status = health_check_instance.determine_status(self.load_balancer_ip)
        logging.info(f"Health check result: {status}")
        return {"status": "success", "ip": self.get_ip_address(), "health": status}

    def delink_server(self):
        """
        Handle 'delink' command to stop the agent and clear sensitive data.
        """
        self.stop()  # Stop the agent
        self.secure_channel.private_key = None  # Clear the private key
        return {"status": "success", "message": "Server delinked and stopped successfully"}

    def get_metrics(self):
        """
        Handle 'metrics' command to return resource metrics.
        """
        try:
            metrics = resource_monitor.monitor(interval=20)
            return {"status": "success", "ip": self.get_ip_address(), "metrics": metrics}
        except Exception as e:
            print(f"Error generating metrics: {e}")
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Create the agent instance without hardcoding the load balancer IP
    agent_instance = Agent(server_id="server-1234")
    # Start the agent
    agent_instance.start()
    while True:
        time.sleep(10)

