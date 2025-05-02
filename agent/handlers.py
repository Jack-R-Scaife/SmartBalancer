import socket
import json
from security import SecureChannel

class LinkHandler:
    """
    Handles linking the server to the load balancer by IP, with keypair-based authentication.
    """

    def __init__(self, load_balancer_ip):
        """
        Initialize the LinkHandler with the load balancer's IP address.
        """
        self.load_balancer_ip = load_balancer_ip  # Store the load balancer IP
        self.is_linked = False

    def send_tcp_request(self, ip_address, port, command, payload=None):
        """
        Utility function to send a command to the load balancer over TCP.
        """
        try:
            with socket.create_connection((ip_address, port), timeout=5) as sock:
                request = {"command": command}
                if payload:
                    request.update(payload)
                sock.sendall(json.dumps(request).encode('utf-8'))
                response = sock.recv(1024).decode('utf-8')
                return json.loads(response)
        except Exception as e:
            print(f"Error communicating with load balancer {ip_address}: {e}")
            return {"status": "error", "message": str(e)}

    def link(self, public_key, ip_address, signature, challenge_message):
        """
        Link the agent to the load balancer using TCP.
        """
        if self.is_linked:
            print(f"LinkHandler: Server is already linked. Skipping relink.")
            return {'message': 'Server already linked.'}

        try:
            # Ensure the public key and challenge message are in the correct format (strings)
            if isinstance(public_key, bytes):
                public_key = public_key.decode('utf-8')  # Decode if in bytes
            if isinstance(challenge_message, bytes):
                challenge_message = challenge_message.decode('utf-8') 

            # Prepare payload
            payload = {
                "public_key": public_key,
                "ip_address": ip_address,
                "signature": signature.hex(),  # Convert signature (bytes) to hex string
                "challenge_message": challenge_message
            }

            # Send TCP request to the load balancer
            response = self.send_tcp_request(self.load_balancer_ip, 9000, "link", payload)

            if response.get("status") == "success":
                print(f"LinkHandler: Server linked successfully. Response: {response}")
                self.is_linked = True  # Set flag to true after successful link
                return response
            else:
                print(f"LinkHandler: Failed to link server. Response: {response}")
                return response

        except Exception as e:
            print(f"LinkHandler: Error during linking process: {str(e)}")
            return {'message': f'Error during linking process: {str(e)}'}
        
