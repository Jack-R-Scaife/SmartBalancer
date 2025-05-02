import time,os,socket,threading
from alert_manager import AlertManager
from handlers import LinkHandler
from health_check import HealthCheck
from resource_monitor import ResourceMonitor
from security import SecureChannel
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from flask import Flask, jsonify, request
from flask_compress import Compress
import json,requests,traceback,logging 
from response_factory import ResponseFactory
import zipfile
import io,binascii
# Flask app Setup
app = Flask(__name__)
resource_monitor = ResourceMonitor()
health_check_instance = HealthCheck()
compress = Compress()
compress.init_app(app)

logging.basicConfig(
    filename="agent.log",  # Use logs directory
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
# ---- Agent Class ----
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
        self.connection_count = 0  
        logging.info(f"Agent initialized with server_id: {self.server_id}")
  

        self.logger = logging.getLogger(f"Agent")
        handler = logging.FileHandler(f"agent.log")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

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
        self.connection_count += 1 
        try:
            # Get the IP of the client (load balancer)
            ip_address = client_socket.getpeername()[0]
            if not self.load_balancer_ip:
                self.set_load_balancer_ip(ip_address)

            # Receive and process the request
            data = client_socket.recv(65536).decode('utf-8')  # Receive up to 64 KB of data
            logging.info(f"[DEBUG] Received raw data: {data}")

            # Parse the received JSON request
            request = json.loads(data)
            command = request.get("command")
            logging.info(f"[DEBUG] Received command: {command}, Request Data: {request}")

            # Handle different commands
            if command == "link":
                response = self.handle_link(client_socket)
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            elif command == "health":
                response = self.health_check()
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            elif command == "delink":
                response = self.delink_server()
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            elif command == "metrics":
                response = self.get_metrics()
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            elif command == "get_logs":
                response = self.get_logs()
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            elif command == "gather_metrics":
                response = self.gather_metrics()
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            elif command == "alerts":
                response = self.get_alerts()
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            elif command == "delete_log":
                # Expect payload to contain "log_name"
                payload = request.get("payload", {})
                log_name = payload.get("log_name")
                if not log_name:
                    response = {"status": "error", "message": "Missing log_name in payload"}
                else:
                    agent_log_path = os.path.normpath(os.path.join(os.getcwd(), log_name))
                    # Ensure the computed path is within the current working directory
                    if not agent_log_path.startswith(os.getcwd()):
                        response = {"status": "error", "message": "Invalid log path"}
                    elif os.path.exists(agent_log_path):
                        try:
                            os.remove(agent_log_path)
                            response = {"status": "success", "message": "Log deleted on agent"}
                        except Exception as e:
                            response = {"status": "error", "message": str(e)}
                    else:
                        response = {"status": "error", "message": "Log file not found on agent"}
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            elif command == "simulate_traffic":
                # Extract the traffic configuration
                if "payload" in request:
                    traffic_config = request.get("payload")
                else:
                    # If payload is not provided, assume config keys are top-level
                    traffic_config = {key: request.get(key) for key in ["url", "type", "rate", "duration"]}

                logging.info(f"Received traffic_config: {traffic_config}")

                # Validate traffic_config
                if not isinstance(traffic_config, dict) or any(value is None for value in traffic_config.values()):
                    logging.error(f"Invalid payload for simulate_traffic: {traffic_config}")
                    response = {"status": "error", "message": "Invalid or missing traffic configuration."}
                else:
                    logging.info(f"Executing traffic simulation with config: {traffic_config}")
                    threading.Thread(target=self.simulate_traffic, args=(traffic_config,), daemon=True).start()
                    response = {"status": "success", "message": "Traffic simulation started."}
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            else:
                response = {"status": "error", "message": "Unknown command"}
                client_socket.sendall(json.dumps(response).encode('utf-8'))

        except json.JSONDecodeError as e:
            logging.error(f"[ERROR] Failed to parse JSON: {e}")
            error_response = {"status": "error", "message": "Invalid JSON format"}
            client_socket.sendall(json.dumps(error_response).encode('utf-8'))
        except BrokenPipeError as e:
            logging.error(f"[ERROR] Broken pipe error: {e}")
        except Exception as e:
            logging.error(f"[ERROR] Error handling client: {e}")
            error_response = {"status": "error", "message": str(e)}
            client_socket.sendall(json.dumps(error_response).encode('utf-8'))
        finally:
            self.connection_count -= 1
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
            logging.info(f"Sending cached alerts: {alerts}")
            return alerts
        except Exception as e:
            logging.error(f"Error fetching alerts: {e}")
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
            metrics["connections"] = self.connection_count
            return {"status": "success", "ip": self.get_ip_address(), "metrics": metrics}
        except Exception as e:
            print(f"Error generating metrics: {e}")
            return {"status": "error", "message": str(e)}



    def simulate_traffic(self, config):
        """
        Simulate traffic based on the configuration received from the load balancer.
        """
        try:
            if not config:
                self.logger.error("Received an empty or None config.")
                return {"status": "error", "message": "Traffic configuration is missing."}

            # Validate required keys
            required_keys = ["url", "type", "rate", "duration"]
            for key in required_keys:
                if key not in config:
                    self.logger.error(f"Missing key in config: {key}")
                    return {"status": "error", "message": f"Missing key in config: {key}"}

            # Extract configuration
            url = config["url"]
            req_type = config["type"]
            rate = config["rate"]
            duration = config["duration"]
            self.logger.info(f"Simulating {req_type.upper()} traffic to {url} at {rate} req/s for {duration} seconds.")

            end_time = time.time() + duration
            while time.time() < end_time:
                for _ in range(rate):
                    try:
                        if req_type.lower() == "get":
                            requests.get(url)
                        elif req_type.lower() == "post":
                            requests.post(url, data={"key": "value"})
                        self.logger.debug(f"Sent {req_type.upper()} request to {url}")
                    except Exception as e:
                        self.logger.error(f"Error during traffic simulation: {str(e)}")
                time.sleep(1)

            self.logger.info("Traffic simulation completed.")
            return {"status": "success", "message": "Traffic simulation completed"}
        except Exception as e:
            self.logger.error(f"Error in simulate_traffic: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_logs(self):
        """
        Fetch log files, compress them into a zip archive, and return as a binary response.
        """
        log_dir = "."  # Root directory
        zip_buffer = io.BytesIO()  # In-memory buffer for the zip file

        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for root, _, files in os.walk(log_dir):
                    for file in files:
                        if file.endswith(".log"):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, log_dir)
                            zip_file.write(file_path, arcname)

            if zip_buffer.getbuffer().nbytes == 0:
                # No logs were added to the zip
                return {"status": "error", "message": "No logs found"}

            zip_buffer.seek(0)
            return {
                "status": "success",
                "zip_data": zip_buffer.read().hex(),  # Convert binary to hex for JSON
            }
        except Exception as e:
            logging.error(f"Error compressing logs: {e}")
            return {"status": "error", "message": str(e)}

        
    def gather_metrics(self):
        """
        Collect comprehensive metrics including system resources, health, alerts, and logs.
        """
        try:
            # Initialize result dictionary
            metrics = {
                "server_id": self.server_id,
                "timestamp": time.time(),
                "system": {},
                "health": {},
                "alerts": [],
                "logs": [],
                "ping": {}
            }

            # System Resource Metrics
            system_metrics = resource_monitor.monitor(interval=1)
            metrics["system"] = {
                "cpu_usage": system_metrics["cpu_total"],
                "memory_usage": system_metrics["memory"],
                "disk_read_speed": system_metrics["disk_read_MBps"],
                "disk_write_speed": system_metrics["disk_write_MBps"],
                "network_send_speed": system_metrics["net_send_MBps"],
                "network_receive_speed": system_metrics["net_recv_MBps"]
            }

            # Health Metrics
            if self.load_balancer_ip:
                health_status = health_check_instance.determine_status(self.load_balancer_ip)
                metrics["health"] = {"status_code": health_status}
            else:
                metrics["health"] = {"status_code": "unknown"}

            # Alerts
            alerts = AlertManager.get_cached_alerts()
            metrics["alerts"] = alerts.get("alerts", [])

            # Logs
            logs_response = self.get_logs()
            if logs_response.get("status") == "success":
                metrics["logs"] = logs_response.get("logs", [])

            # Ping Metrics
            if self.load_balancer_ip:
                latency = health_check_instance.check_ping(self.load_balancer_ip)
                metrics["ping"] = {"latency_ms": latency}

            logging.info(f"Gathered metrics: {metrics}")
            return metrics
        except Exception as e:
            logging.error(f"Error gathering metrics: {e}")
            logging.debug(traceback.format_exc())
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Create the agent instance without hardcoding the load balancer IP
    agent_instance = Agent(server_id="server-1234")
    # Start the agent
    agent_instance.start()
    while True:
        time.sleep(10)

