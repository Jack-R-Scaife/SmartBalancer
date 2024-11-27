# app/api/api.py
from flask import Blueprint, request, jsonify, Response,redirect,url_for,flash
from server.server_manager import ServerManager
from server.servergroups import update_server_group,get_servers_and_groups,remove_groups,create_group_with_servers
from app.models import Server
import json
import random
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
        # Use LoadBalancer to send a TCP request to the agent
        from server.agent_monitor import LoadBalancer
        load_balancer = LoadBalancer()
        response = load_balancer.send_tcp_request(ip_address, 9000, "link")

        if response.get("status") == "success":
            public_key = response.get("public_key")
            from app import create_app
            app = create_app()
            server_manager = ServerManager(app)
            result = server_manager.link_server(ip_address, dynamic_grouping, public_key)

            if result['status']:
                return jsonify({'message': result['message']}), 200
            else:
                return jsonify({'message': result['message']}), 500
        else:
            return jsonify({'message': f'Error linking server: {response.get("message")}'}), 500

    except Exception as e:
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

@api_blueprint.route('/servers/remove/<ip_address>', methods=['DELETE'])
def remove_server(ip_address):
    from app import create_app
    app = create_app()
    server_manager = ServerManager(app)
    result = server_manager.remove_server(ip_address)
    status_code = 200 if result['status'] else 404
    return jsonify({'message': result['message']}), status_code


@api_blueprint.route('/server_count', methods=['GET'])
def get_server_count():
    # Query the database to count the servers
    server_count = Server.query.count()
    return jsonify({'count': server_count})

@api_blueprint.route('/servers/update_group', methods=['POST'])
def api_update_server_group():
    data = request.json
    server_id = data.get('server_id')
    group_id = data.get('group_id')

    result = update_server_group(server_id, group_id)
    return jsonify(result) if result['status'] == 'success' else jsonify(result), 400

    
@api_blueprint.route('/servers/groups', methods=['GET'])
def api_get_servers_and_groups():
    response_data = get_servers_and_groups()
    return jsonify(response_data), 200 if response_data['status'] == 'success' else 500

@api_blueprint.route('/groups/delete', methods=['POST'])
def api_remove_groups():
    try:
        # Parse the incoming JSON payload
        data = request.json
        group_ids = data.get('group_ids', [])  # Extract group IDs

        if not group_ids:
            return jsonify({"status": "error", "message": "No group IDs provided"}), 400

        # Pass `group_ids` to the helper function
        response_data = remove_groups(group_ids)

        # Check the response and return appropriate status code
        if response_data['status']:
            return jsonify(response_data), 200
        else:
            return jsonify(response_data), 500
    except Exception as e:
        # Log the error for debugging
        print(f"Exception in api_remove_groups: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500

@api_blueprint.route('/groups/create', methods=['POST'])
def api_create_group():
    try:
        # Parse the incoming JSON payload
        data = request.json
        name = data.get('name')
        description = data.get('description')
        server_ids = data.get('servers', [])

        # Call the function to create the group in servergroups.py
        result = create_group_with_servers(name, description, server_ids)

        if result['status'] == 'success':
            return jsonify({"status": "success", "message": result['message']}), 200
        else:
            return jsonify({"status": "error", "message": result['message']}), 400
    except Exception as e:
        print(f"Error in api_create_group: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@api_blueprint.route('/metrics/all', methods=['GET'])
def api_get_all_metrics():
    from server.agent_monitor import LoadBalancer
    load_balancer = LoadBalancer()
    try:
        metrics = load_balancer.fetch_metrics_from_all_agents()  # Now TCP-based
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_blueprint.route('/alerts', methods=['GET'])
def api_get_alerts():
    try:
        from server.agent_monitor import LoadBalancer
        # Create an instance of LoadBalancer
        load_balancer = LoadBalancer()
        
        # Send TCP requests to all agents to get alerts
        alerts = load_balancer.fetch_alerts_from_all_agents()
        
        # Return the alerts with a successful response if they exist
        return jsonify({'status': 'success', 'data': alerts}), 200
    except Exception as e:
        # In case of any errors, return a server error response
        return jsonify({'status': 'error', 'message': str(e)}), 500
    