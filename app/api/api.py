# app/api/api.py
from flask import Blueprint, request, jsonify, Response,redirect,url_for,flash
from server.server_manager import ServerManager
from server.servergroups import update_server_group,get_servers_and_groups,remove_groups,create_group_with_servers,get_servers_by_group
from app.models import Server,LoadBalancerSetting,Strategy
import json,os
import random,logging
from server.traffic_store import TrafficStore
from server.strategy_manager import StrategyManager
# Define the blueprint for API routes
api_blueprint = Blueprint('api', __name__)
from server.agent_monitor import LoadBalancer
from server.logs_manager import scan_logs
from flask import render_template
from flask import make_response
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
    
@api_blueprint.route('/simulate_traffic', methods=['POST'])
def simulate_traffic():
    try:
        from server.agent_monitor import LoadBalancer
        load_balancer = LoadBalancer()

        traffic_config = request.json
        logging.info(f"Received traffic_config: {traffic_config}")

        if not traffic_config:
            return jsonify({"error": "Missing traffic configuration"}), 400

        load_balancer.simulate_traffic(traffic_config)
        return jsonify({"message": "Traffic simulation started"}), 200
    except Exception as e:
        logging.error(f"Error in /simulate_traffic: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route('/traffic', methods=['GET'])
def get_traffic_data():
    """
    API endpoint to fetch real-time traffic data for the dashboard.
    """
    traffic_store = TrafficStore.get_instance()
    traffic_data = traffic_store.get_traffic_data()
    logging.info(f"Serving traffic_data: {traffic_data}")
    return jsonify(traffic_data)

@api_blueprint.route('/servers/<int:group_id>', methods=['GET'])
def fetch_servers(group_id):
    """
    API endpoint to fetch servers for a given group ID.
    :param group_id: ID of the group to fetch servers for.
    :return: JSON response containing server data.
    """
    try:
        servers = get_servers_by_group(group_id)
        return jsonify({"status": "success", "servers": servers})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@api_blueprint.route('/load_balancer/set_strategy', methods=['POST'])
def set_load_balancer_strategy():
    """
    API endpoint to set the load balancing strategy for a specific server group.
    """
    try:
        # Parse the request JSON
        data = request.json
        group_id = data.get('group_id')  # Extract group_id
        strategies = data.get('strategies')  # Extract strategies list

        # Validate input
        if not group_id or not strategies:
            return jsonify({"status": "error", "message": "Group ID and Strategy Name are required."}), 400

        # Use the first strategy from the list (if multiple strategies are provided)
        strategy_name = strategies[0]

        # Call the function to apply the strategy
        result = StrategyManager.apply_strategy_to_group(strategy_name, group_id)

        # Set the active strategy in the LoadBalancer
        if result["status"] == "success":
            load_balancer = LoadBalancer()
            load_balancer.set_active_strategy(strategy_name)

        return jsonify(result), 200 if result["status"] == "success" else 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_blueprint.route('/load_balancer/active_strategy/<int:group_id>', methods=['GET'])
def get_active_strategy(group_id):
    try:
        setting = LoadBalancerSetting.query.filter_by(active_strategy_id=group_id).first()
        if not setting:
            return jsonify({"status": "error", "message": "No active strategy found for this group."}), 404

        strategy = Strategy.query.get(setting.active_strategy_id)
        if not strategy:
            return jsonify({"status": "error", "message": "Strategy not found."}), 404

        return jsonify({
            "status": "success",
            "strategy_name": strategy.name,
            "method_type": strategy.method_type
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
def scan_logs(directory='./logs'):
    try:
        logs = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.log'):
                    full_path = os.path.join(root, file)
                    logs.append({
                        "name": file,
                        "path": full_path,
                        "size": os.path.getsize(full_path),
                        "modified": os.path.getmtime(full_path)
                    })
        return logs
    except Exception as e:
        print(f"Error scanning logs: {e}")
        return []

@api_blueprint.route('/logs', methods=['GET'])
def get_logs():
    """
    API endpoint to fetch .log files from the file system.
    """
    logs = scan_logs()  # Default directory is ./logs
    return jsonify({"status": "success", "logs": logs}), 200

@api_blueprint.route('/logs/content', methods=['GET'])
def get_log_content():
    """
    API endpoint to fetch the content of a specific log file or its metadata.
    """
    log_path = request.args.get('path')
    print(f"Requested log path: {log_path}")  # Debugging

    try:
        if log_path.endswith('.meta'):
            print(f"Fetching metadata for: {log_path}")
            if not os.path.exists(log_path):
                return jsonify({"status": "success", "meta": {"system": {}, "user": {}}}), 200

            with open(log_path, 'r') as file:
                meta_data = json.load(file)
            return jsonify({"status": "success", "meta": meta_data}), 200

        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Log file not found: {log_path}")

        with open(log_path, 'r') as file:
            content = file.readlines()
        return jsonify({"status": "success", "content": content}), 200

    except Exception as e:
        print(f"Error in get_log_content: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/logs/view', methods=['GET'])
def view_log_page():
    """
    Render the detailed log view page.
    """
    log_path = request.args.get('path')
    if not log_path:
        return "Log path is required.", 400

    # Optionally, validate the log path
    if not os.path.exists(log_path) or not log_path.endswith('.log'):
        return "Log file not found.", 404

    # Render the log view template and pass the normalized log_path
    return render_template('log_view.html', log_path=log_path.replace("\\", "/"))

@api_blueprint.route('/logs/custom_rules', methods=['GET', 'POST'])
def custom_rules():
    """
    GET: Fetch custom rules.
    POST: Save user-defined custom rules.
    """
    if request.method == 'GET':
        try:
            with open('./custom_rules.json', 'r') as file:
                rules = json.load(file)
            return jsonify({"status": "success", "rules": rules}), 200
        except FileNotFoundError:
            # If no rules file exists, return an empty list
            return jsonify({"status": "success", "rules": []}), 200
        except Exception as e:
            print(f"Error fetching custom rules: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    elif request.method == 'POST':
        data = request.json
        rules = data.get("rules", [])
        try:
            with open('./custom_rules.json', 'w') as file:
                json.dump(rules, file)
            return jsonify({"status": "success", "message": "Custom rules saved."}), 200
        except Exception as e:
            print(f"Error saving custom rules: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/logs/highlight', methods=['POST'])
def save_highlight():
    """
    API endpoint to save user-defined highlights.
    """
    try:
        data = request.json
        log_path = data.get("path")
        highlights = data.get("highlights", {})

        if not log_path:
            raise ValueError("Log path is required.")

        meta_path = f"{log_path}.meta"

        # Load existing metadata if it exists
        try:
            with open(meta_path, 'r') as meta_file:
                meta_data = json.load(meta_file)
        except FileNotFoundError:
            meta_data = {"system": {}, "user": {}}  # Initialize structure if file doesn't exist

        # Ensure `system` and `user` keys exist in the metadata
        if "system" not in meta_data:
            meta_data["system"] = {}
        if "user" not in meta_data:
            meta_data["user"] = {}

        # Update user highlights
        meta_data["user"].update(highlights)

        # Save updated metadata
        with open(meta_path, 'w') as meta_file:
            json.dump(meta_data, meta_file)

        return jsonify({"status": "success", "message": "Highlights saved."}), 200

    except Exception as e:
        print(f"Error saving highlights: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@api_blueprint.route('/logs/highlight/clear', methods=['POST'])
def clear_highlights():
    """
    API endpoint to clear user-defined highlights for a given log file's .meta.
    """
    try:
        data = request.json
        log_path = data.get("path")

        if not log_path:
            raise ValueError("Log path is required.")

        meta_path = f"{log_path}.meta"

        # If there's no .meta file, there's nothing to clear
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as meta_file:
                meta_data = json.load(meta_file)

            # Just reset the "user" highlights
            if "user" in meta_data:
                meta_data["user"] = {}

            # If you also want to clear system highlights, uncomment below:
            # meta_data["system"] = {}

            # Save updated metadata
            with open(meta_path, 'w') as meta_file:
                json.dump(meta_data, meta_file)

        return jsonify({"status": "success", "message": "User highlights cleared."}), 200

    except Exception as e:
        print(f"Error clearing highlights: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500