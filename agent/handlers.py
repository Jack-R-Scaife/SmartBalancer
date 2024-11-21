import socket
import requests
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

    def link(self, public_key, ip_address, signature, challenge_message):
        """
        Link the agent to the load balancer.
        """
        if self.is_linked:
            print(f"LinkHandler: Server is already linked. Skipping relink.")
            return {'message': 'Server already linked.'}
        try:
            # Ensure the public key and challenge message are in the correct format (strings)
            if isinstance(public_key, bytes):
                public_key = public_key.decode('utf-8')  # Decode if in bytes
            if isinstance(challenge_message, bytes):
                challenge_message = challenge_message.decode('utf-8')  # Decode if in bytes

            # Send a request to the load balancer API
            response = requests.post(
                f"http://{self.load_balancer_ip}:8000/link",
                json={
                    'public_key': public_key,  # Now guaranteed to be a string
                    'ip_address': ip_address,  # No decoding needed for IP
                    'signature': signature.hex(),  # Convert signature (bytes) to hex string
                    'challenge_message': challenge_message  # Now guaranteed to be a string
                }
            )
            
            if response.status_code == 200:
                print(f"LinkHandler: Server linked successfully. Response: {response.json()}")
                self.is_linked = True  # Set flag to true after successful link
                return response.json()
            else:
                print(f"LinkHandler: Failed to link server. Response: {response.json()}")
                return response.json()

        except Exception as e:
            print(f"LinkHandler: Error contacting load balancer: {str(e)}")
            return {'message': f'Error contacting load balancer: {str(e)}'}
        
