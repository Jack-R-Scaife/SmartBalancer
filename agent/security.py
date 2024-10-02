from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

class SecureChannel:
    def __init__(self):
        """
        Initialize the SecureChannel class, which generates a public/private RSA key pair
        when the agent starts.
        """
        # Generate a private key for the agent using RSA algorithm
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,  # Public exponent, a value commonly set to 65537 for better security
            key_size=2048,  # Key size in bits (2048 bits is standard for RSA keys)
            backend=default_backend()
        )

    def get_public_key(self):
        """
        Return the public key from the generated private key.
        This public key will be shared with the load balancer to allow encrypted communication.
        """
        public_key = self.private_key.public_key()  # Derive the public key from the private key
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM, 
            format=serialization.PublicFormat.SubjectPublicKeyInfo  # Standard format for public keys
        ).decode('utf-8')  # Convert the byte string to a UTF-8 string for easy transmission

    def authenticate(self, client_public_key_pem, challenge_message, signature):
        """
        Authenticate the client by verifying a signature made with the client's private key.
        The challenge message is sent and should be signed by the client with its private key,
        and then verified with the client's public key.
        """
        try:
            client_public_key = serialization.load_pem_public_key(
                client_public_key_pem,
                backend=default_backend() 
            )

            # Verify that the signature matches the challenge message, using the client's public key
            client_public_key.verify(
                signature, 
                challenge_message,  
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),  # Mask Generation Function for padding
                    salt_length=padding.PSS.MAX_LENGTH  # The salt length used in the padding
                ),
                hashes.SHA256()  # Hashing algorithm used to create the signature
            )
            # If no exception is raised, the authentication is successful
            print("SecureChannel: Client authenticated successfully.")
            return True
        except Exception as e:
            # If any error occurs (e.g., wrong signature), the authentication has failed
            print(f"SecureChannel: Authentication failed - {e}")
            return False