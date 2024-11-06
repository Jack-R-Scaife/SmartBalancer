# app/api/api.py
from flask import Blueprint, request, jsonify, Response
from server.server_manager import ServerManager
import requests
from app.models import Server
import json
# Define the blueprint for API routes
api_blueprint = Blueprint('api', __name__)

status_mapping = {
    "healthy": 1,
    "overloaded": 2,
    "critical": 3,
    "down": 4,
    "idle": 5
}

# Route to link a server
@api_blueprint.route('/servers/link', methods=['POST'])
def link_server():
    server_data = request.json
    ip_address = server_data.get('ip_address')
    dynamic_grouping = server_data.get('dynamic_grouping', False)

    if not ip_address:
        return jsonify({'message': 'IP address is required.'}), 400

    try:
        # Send a request to the agent at the given IP address to get the public key
        agent_response = requests.post(f"http://{ip_address}:8000/link")  # Assuming agent is listening on port 8000
        agent_data = agent_response.json()

        # Extract the public key from the agent's response
        public_key = agent_data.get('public_key')

        if not public_key:
            return jsonify({'message': 'Public key not received from the agent'}), 400

        # Pass the public key and IP to ServerManager to handle linking
        server_manager = ServerManager()
        result = server_manager.link_server(ip_address, dynamic_grouping, public_key)

        if result['status']:
            return jsonify({'message': result['message']}), 200
        else:
            return jsonify({'message': result['message']}), 500

    except requests.exceptions.RequestException as e:
        return jsonify({'message': f'Error contacting agent: {str(e)}'}), 500
    
# Route to get server status
@api_blueprint.route('/server_status', methods=['GET'])
def get_server_status():
    servers = Server.query.all()  # Fetch all servers from the database
    server_status_list = []
    
    for server in servers:
        numeric_status = status_mapping.get(server.status, 4)  # Default to "down" if status is not recognized
        server_status_list.append({
            "ip": server.ip_address,
            "s": numeric_status
    })

    response_data = json.dumps(server_status_list, separators=(',', ':'))  # Minify the response
    return Response(response_data, content_type='application/json')

# api.py
@api_blueprint.route('/servers/remove/<ip_address>', methods=['DELETE'])
def remove_server(ip_address):
    server_manager = ServerManager()
    result = server_manager.remove_server(ip_address)
    status_code = 200 if result['status'] else 404
    return jsonify({'message': result['message']}), status_code