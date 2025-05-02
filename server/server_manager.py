# server_manager.py
from app import db
from app.models import Server, ServerGroup, ServerGroupServer, Authentication
from cryptography.hazmat.primitives import serialization
from .agent_monitor import LoadBalancer 

class ServerManager:
    def __init__(self, app):
        self.app = app
        # Initialize the ServerManager with an instance of the LoadBalancer class.
        self.load_balancer = LoadBalancer()

    def update_server_status(self, ip_address, status):
        server = Server.query.filter_by(ip_address=ip_address).first()
        if server:
            server.status = status
            db.session.commit()

    def link_server(self, ip_address, dynamic_grouping, public_key_pem):
        # Debugging: Log the incoming IP address
        print(f"[DEBUG] link_server called with IP: {ip_address}")

        #  check if the server is already linked by querying the database using the server's IP address.
        existing_server = Server.query.filter_by(ip_address=ip_address).first()
        if existing_server:
            print(f"[DEBUG] Server with IP {ip_address} already exists in the database.")
            return {'message': 'Server already linked.', 'status': False}
        
        try:
            # Debugging: Log public key decoding attempt
            print(f"[DEBUG] Decoding public key for server with IP: {ip_address}")
            public_key_str = public_key_pem
        except Exception as e:
            print(f"[ERROR] Failed to decode public key for IP {ip_address}: {str(e)}")
            return {'message': f'Failed to decode public key: {str(e)}', 'status': False}
        
        try:
            # Debugging: Log the creation of an authentication record
            print(f"[DEBUG] Creating authentication record for IP: {ip_address}")
            authentication_entry = Authentication(public_key=public_key_str)
            db.session.add(authentication_entry)
            db.session.commit()

            print(f"[DEBUG] Linking server with IP: {ip_address} to authentication entry.")
            new_server = Server(
                ip_address=ip_address,
                status='offline',
                auto_connect=False,
                public_key=authentication_entry.key_id
            )
            db.session.add(new_server)
            db.session.commit()

            # Register the server (agent) with the load balancer.
            print(f"[DEBUG] Registering server with IP: {ip_address} with the load balancer.")
            self.load_balancer.add_agent(ip_address)

            if dynamic_grouping:
                print(f"[DEBUG] Handling dynamic grouping for server with IP: {ip_address}.")
                self.handle_dynamic_grouping(new_server)

            print(f"[DEBUG] Successfully linked server with IP: {ip_address}")
            return {'message': 'Server linked successfully.', 'status': True}

        except Exception as e:
            print(f"[ERROR] Failed to link server with IP {ip_address}: {str(e)}")
            db.session.rollback()
            return {'message': f'Failed to link server: {str(e)}', 'status': False}

    def handle_dynamic_grouping(self, server):
        """
        This method handles adding a server to a dynamic group if dynamic grouping is enabled.
        If the dynamic group doesn't exist, it will create one. If the group exists and has space,
        the server will be added to the group.
        """
        # Define the name of the dynamic group.
        group_name = 'Dynamic Group'
        
        # Check if the dynamic group already exists in the database.
        dynamic_group = ServerGroup.query.filter_by(name=group_name).first()

        if not dynamic_group:
            # If the dynamic group doesn't exist, create a new group.
            dynamic_group = ServerGroup(name=group_name, server_count=1, max_servers=10)  # Default max of 10 servers.
            db.session.add(dynamic_group)  # Add the new group to the session.
            db.session.commit()  # Commit the changes.
        else:
            # If the dynamic group already exists, check if it has space for more servers.
            if dynamic_group.server_count >= dynamic_group.max_servers:
                # If the group is full, raise an exception to prevent adding more servers.
                raise Exception('Dynamic group is full.')
            # Otherwise, increase the server count in the group.
            dynamic_group.server_count += 1
            db.session.commit()  # Commit the updated server count to the database.

        # Create an association between the server and the dynamic group.
        server_group_association = ServerGroupServer(
            server_id=server.server_id,
            group_id=dynamic_group.group_id
        )
        db.session.add(server_group_association)  # Add the association to the session.
        db.session.commit()  # Commit the changes to the database.

    def remove_server(self, ip_address):
        """
        Remove a server from the database, notify the agent to stop, and clean up associated records.
        """
        try:
            # Notify the agent to stop
            response = self.load_balancer.send_tcp_request(ip_address, 9000, "delink")
            if response.get("status") == "success":
                print(f"Successfully notified agent {ip_address} to stop.")
            else:
                print(f"Failed to notify agent {ip_address}: {response.get('message')}")

            with self.app.app_context():
                # Find the server by IP address
                server = Server.query.filter_by(ip_address=ip_address).first()
                if server:
                    # Remove associations in the ServerGroupServer table
                    ServerGroupServer.query.filter_by(server_id=server.server_id).delete()

                    # Remove the server from the database
                    db.session.delete(server)
                    db.session.commit()

                    # Remove from LoadBalancer known_agents
                    self.load_balancer.known_agents = [
                        ip for ip in self.load_balancer.known_agents if ip != ip_address
                    ]

                    print(f"Successfully removed server {ip_address}.")
                    return {'message': f'Server with IP {ip_address} removed successfully.', 'status': True}
                else:
                    return {'message': 'Server not found.', 'status': False}

        except Exception as e:
            db.session.rollback()
            print(f"Error removing server {ip_address}: {e}")
            return {'message': f'Error removing server: {str(e)}', 'status': False}
