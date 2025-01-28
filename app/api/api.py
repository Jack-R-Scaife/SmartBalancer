# app/api/api.py
from flask import Blueprint, request, jsonify, Response,redirect,url_for,flash
import joblib
import pandas as pd
from server.server_manager import ServerManager
from server.servergroups import update_server_group,get_servers_and_groups,remove_groups,create_group_with_servers,get_servers_by_group
from app.models import Server,LoadBalancerSetting,Strategy,Rule
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
from server.logging_config import api_logger
from server.logging_config import main_logger, traffic_logger
from server.rules_manager import create_rule
import time,os
from datetime import datetime, timezone, timedelta
# Load the trained Random Forest model
model_path = os.path.join( 'Predictive_Model', 'lightgbm_model.pkl')
model = joblib.load(model_path)

status_mapping = {
    "healthy": 1,
    "overloaded": 2,
    "critical": 3,
    "down": 4,
    "idle": 5
}
# Threshold for significant prediction error (e.g., 10%)
threshold_error = 0.1

@api_blueprint.route('/predicted_traffic', methods=['GET'])
def get_predicted_traffic():
    """
    Predict overall traffic rate based on aggregated real-time metrics from all agents.
    """
    try:
        # Fetch metrics from all agents
        load_balancer = LoadBalancer()
        agent_metrics = load_balancer.fetch_metrics_from_all_agents()

        if not agent_metrics:
            api_logger.error("No metrics available from agents.")
            return jsonify({'error': 'No metrics available from agents'}), 500

        # Aggregate metrics across all agents
        num_agents = len(agent_metrics)
        aggregated_metrics = {
            'cpu_usage': sum(agent['metrics'].get('cpu_total', 0) for agent in agent_metrics) / num_agents,
            'memory_usage': sum(agent['metrics'].get('memory', 0) for agent in agent_metrics) / num_agents,
            'connections': sum(agent['metrics'].get('connections', 0) for agent in agent_metrics),
            'traffic_rate': sum(agent['metrics'].get('traffic_rate', 0) for agent in agent_metrics),
            'scenario': 'baseline_high',  # Replace with dynamic logic if needed
            'strategy': 'Round Robin' 
        }

        # Prepare the feature set for prediction
        feature_df = pd.DataFrame([aggregated_metrics])

        # Handle one-hot encoding for `scenario` and `strategy`
        feature_df = pd.get_dummies(feature_df, columns=['scenario', 'strategy'], dummy_na=False)
        expected_features = model.feature_names_in_
        feature_df = feature_df.reindex(columns=expected_features, fill_value=0)

        # Predict future traffic for the next 10 seconds
        predictions = []
        current_time = datetime.now()
        for i in range(10):  # Generate predictions for the next 10 seconds
            prediction = model.predict(feature_df)[0]
            future_timestamp = (current_time + timedelta(seconds=i)).timestamp()
            predictions.append({'timestamp': future_timestamp, 'value': prediction})

        api_logger.info("Traffic prediction successful.")
        return jsonify(predictions), 200

    except Exception as e:
        api_logger.error(f"Error in traffic prediction: {e}")
        return jsonify({'error': f"An error occurred: {str(e)}"}), 500


# Route to link a server
@api_blueprint.route('/servers/link', methods=['POST'])
def link_server():
    server_data = request.json
    ip_address = server_data.get('ip_address')
    dynamic_grouping = server_data.get('dynamic_grouping', False)

    if not ip_address:
        api_logger.warning("Attempt to link server without IP address")
        return jsonify({'message': 'IP address is required.'}), 400

    try:
        api_logger.info(f"Linking server with IP: {ip_address}")
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
                api_logger.info(f"Server linked successfully: {ip_address}")
                return jsonify({'message': result['message']}), 200
            else:
                api_logger.error(f"Failed to link server {ip_address}: {result['message']}")
                return jsonify({'message': result['message']}), 500
        else:
            api_logger.error(f"Error linking server {ip_address}: {response.get('message')}")
            return jsonify({'message': f'Error linking server: {response.get("message")}'}), 500

    except Exception as e:
        api_logger.error(f"Error contacting agent for IP {ip_address}: {e}")
        return jsonify({'message': f'Error contacting agent: {str(e)}'}), 500

    
# Route to get server status
@api_blueprint.route('/server_status', methods=['GET'])
def get_server_status():
    api_logger.info("Fetching server status")
    servers = Server.query.all()  # Fetch all servers from the database
    server_status_list = []
    
    for server in servers:
        numeric_status = status_mapping.get(server.status, 4)  # Default to "down" if status is not recognized
        server_status_list.append({
            "ip": server.ip_address,
            "s": numeric_status
    })
    api_logger.debug(f"Server statuses retrieved: {server_status_list}")
    response_data = json.dumps(server_status_list, separators=(',', ':'))  # Minify the response
    return Response(response_data, content_type='application/json')

@api_blueprint.route('/servers/remove/<ip_address>', methods=['DELETE'])
def remove_server(ip_address):
    api_logger.info(f"Removing server with IP: {ip_address}")
    try:
        from app import create_app
        app = create_app()
        server_manager = ServerManager(app)
        result = server_manager.remove_server(ip_address)
        status_code = 200 if result['status'] else 404
        if result['status']:
            api_logger.info(f"Server removed successfully: {ip_address}")
        else:
            api_logger.warning(f"Server not found: {ip_address}")
        return jsonify({'message': result['message']}), status_code
    except Exception as e:
        api_logger.error(f"Error removing server {ip_address}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_blueprint.route('/server_count', methods=['GET'])
def get_server_count():
    """
    API endpoint to count the number of servers in the database.
    """
    try:
        api_logger.info("Fetching server count")
        server_count = Server.query.count()
        api_logger.debug(f"Server count: {server_count}")
        return jsonify({'count': server_count})
    except Exception as e:
        api_logger.error(f"Error fetching server count: {e}")
        return jsonify({"status": "error", "message": str(e)}), 50

@api_blueprint.route('/servers/update_group', methods=['POST'])
def api_update_server_group():
    data = request.json
    server_id = data.get('server_id')
    group_id = data.get('group_id')

    if not server_id or not group_id:
        api_logger.warning("Missing server_id or group_id in update group request")
        return jsonify({"status": "error", "message": "Server ID and Group ID are required."}), 400

    api_logger.info(f"Updating group for server {server_id} to group {group_id}")
    result = update_server_group(server_id, group_id)
    if result['status'] == 'success':
        api_logger.info(f"Group updated successfully for server {server_id}")
    else:
        api_logger.error(f"Failed to update group for server {server_id}: {result['message']}")
    return jsonify(result), 200 if result['status'] == 'success' else 400

    
@api_blueprint.route('/servers/groups', methods=['GET'])
def api_get_servers_and_groups():
    api_logger.info("Fetching servers and groups")
    response_data = get_servers_and_groups()
    return jsonify(response_data), 200 if response_data['status'] == 'success' else 500

@api_blueprint.route('/groups/delete', methods=['POST'])
def api_remove_groups():
    """
    API endpoint to delete multiple groups.
    """
    try:
        # Parse the incoming JSON payload
        data = request.json
        group_ids = data.get('group_ids', [])

        # Validate input
        if not group_ids:
            api_logger.warning("No group IDs provided for deletion")
            return jsonify({"status": "error", "message": "No group IDs provided"}), 400

        # Attempt to remove groups
        api_logger.info(f"Removing groups with IDs: {group_ids}")
        response_data = remove_groups(group_ids)

        # Return a response based on the operation's success
        if response_data.get('status'):
            api_logger.info(f"Groups removed successfully: {group_ids}")
            return jsonify({"status": "success", "message": response_data['message']}), 200
        else:
            api_logger.warning(f"Some groups could not be removed: {response_data['message']}")
            return jsonify({"status": "partial", "message": response_data['message']}), 400
    except Exception as e:
        # Handle unexpected errors
        api_logger.error(f"Error in api_remove_groups: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_blueprint.route('/groups/create', methods=['POST'])
def api_create_group():
    """
    API endpoint to create a new group with servers.
    """
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')
        server_ids = data.get('servers', [])

        if not name or not description:
            api_logger.warning("Missing group name or description")
            return jsonify({"status": "error", "message": "Group name and description are required."}), 400

        api_logger.info(f"Creating group '{name}' with servers: {server_ids}")
        result = create_group_with_servers(name, description, server_ids)

        if result['status'] == 'success':
            api_logger.info(f"Group '{name}' created successfully")
            return jsonify(result), 200
        else:
            api_logger.error(f"Failed to create group '{name}': {result['message']}")
            return jsonify(result), 400
    except Exception as e:
        api_logger.error(f"Error in api_create_group: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/metrics/all', methods=['GET'])
def api_get_all_metrics():
    """
    API endpoint to fetch all metrics from agents.
    """
    api_logger.info("Fetching all metrics from agents")
    try:
        load_balancer = LoadBalancer()
        metrics = load_balancer.fetch_metrics_from_all_agents()
        api_logger.debug(f"Metrics fetched: {metrics}")
        return jsonify(metrics), 200
    except Exception as e:
        api_logger.error(f"Error fetching all metrics: {e}")
        return jsonify({"error": str(e)}), 500

@api_blueprint.route('/alerts', methods=['GET'])
def api_get_alerts():
    """
    API endpoint to fetch alerts from all agents.
    """
    api_logger.info("Fetching alerts from all agents")
    try:
        load_balancer = LoadBalancer()
        alerts = load_balancer.fetch_alerts_from_all_agents()

        # Log the raw alerts
        api_logger.debug(f"Raw alerts fetched: {alerts}")

        # Validate and filter alerts
        current_time = time.time()
        filtered_alerts = []
        for alert in alerts:
            try:
                # Check for 'timestamp' in the alert
                if "timestamp" in alert and isinstance(alert["timestamp"], (int, float)):
                    if current_time - alert["timestamp"] <= 180:  # 3-minute filter
                        filtered_alerts.append(alert)
                else:
                    api_logger.warning(f"Invalid or missing 'timestamp' in alert: {alert}")
            except Exception as e:
                api_logger.error(f"Error processing alert: {alert}, error: {e}")

        api_logger.debug(f"Filtered alerts: {filtered_alerts}")
        return jsonify({'status': 'success', 'data': filtered_alerts}), 200

    except Exception as e:
        api_logger.error(f"Error fetching alerts: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

    
@api_blueprint.route('/simulate_traffic', methods=['POST'])
def simulate_traffic():
    try:
        from server.agent_monitor import LoadBalancer
        load_balancer = LoadBalancer()

        traffic_config = request.json
        api_logger.info(f"Received traffic_config: {traffic_config}")

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
    API endpoint to fetch real-time traffic data.
    """
    traffic_store = TrafficStore.get_instance()
    traffic_data = traffic_store.get_traffic_data()

    # Debugging
    api_logger.info(f"Traffic data fetched: {traffic_data}")

    return jsonify(traffic_data), 200

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

        # Extract group_id
        group_id = data.get('group_id')
        if not group_id:
            return jsonify({"status": "error", "message": "Group ID is required."}), 400

        # Validate and convert group_id to an integer
        try:
            group_id = int(group_id)  # Convert to integer
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid group ID. Must be an integer."}), 400

        # Extract strategies from payload
        strategies = data.get('strategies')
        if not strategies:
            return jsonify({"status": "error", "message": "Strategy Name is required."}), 400

        # Use the first strategy from the list
        strategy_name = strategies[0]

        # Apply the strategy
        result = StrategyManager.apply_strategy_to_group(strategy_name, group_id)

        if result["status"] == "success":
            load_balancer = LoadBalancer()
            load_balancer.load_saved_strategies()

        return jsonify(result), 200 if result["status"] == "success" else 400

    except Exception as e:
        # Log the exception and return an error response
        logging.error(f"Error in set_load_balancer_strategy: {e}")
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
    
LOGS_DIR = "./logs"

def scan_logs(directory=LOGS_DIR):
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

@api_blueprint.route('/logs', methods=['GET'])
def get_logs():
    """
    List all log files from the local logs folder.
    """
    logs_dir = "./logs"
    logs = []

    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    for root, _, files in os.walk(logs_dir):
        for file in files:
            if file.endswith('.log'):
                full_path = os.path.join(root, file)
                logs.append({
                    "name": file,
                    "size": os.path.getsize(full_path),
                    "modified": os.path.getmtime(full_path),
                })

    return jsonify({"status": "success", "logs": logs}), 200



@api_blueprint.route('/logs/content', methods=['GET'])
def get_log_content():
    """
    API endpoint to fetch the content of a specific log file or its metadata.
    """
    raw_path = request.args.get("path")
    if not raw_path:
        return jsonify({"status": "error", "message": "Log path is required."}), 400

    # Force absolute path
    logs_dir = os.path.abspath("./logs")
    full_path = os.path.abspath(raw_path)

    # Ensure we're still inside ./logs
    if not full_path.startswith(logs_dir):
        return jsonify({"status": "error", "message": "Invalid log path."}), 400

    try:
        # If the user requested something ending in .meta, load the metadata file directly
        if full_path.endswith(".meta"):
            api_logger.info(f"Fetching metadata for: {full_path}")

            if not os.path.exists(full_path):
                # Create a new meta file if it doesn't exist
                default_meta = {"system": {}, "user": {}}
                with open(full_path, "w") as meta_file:
                    json.dump(default_meta, meta_file)

            with open(full_path, "r") as meta_file:
                meta_data = json.load(meta_file)
            return jsonify({"status": "success", "meta": meta_data}), 200

        # Otherwise, it's a request for the log content
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Log file not found: {full_path}")

        with open(full_path, "r") as file:
            content = file.readlines()

        return jsonify({"status": "success", "content": content}), 200

    except Exception as e:
        api_logger.error(f"Error in get_log_content: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_blueprint.route('/logs/view', methods=['GET'])
def view_log_page():
    """
    Serve the content of a specific log file.
    """
    log_name = request.args.get('name', '')
    logs_dir = "./logs"
    log_path = os.path.join(logs_dir, log_name)

    if not os.path.exists(log_path):
        return f"Log file not found: {log_name}", 404

    try:
        with open(log_path, 'r') as f:
            log_content = f.read()

        # Pass log_path as well as log_content to the template
        return render_template(
            'log_view.html',
            log_content=log_content,
            # maybe just store the relative path after ./logs
            log_path=os.path.relpath(log_path, start=logs_dir)
        )
    except Exception as e:
        return f"Error reading log file: {e}", 500

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
            api_logger.error(f"Error fetching custom rules: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    elif request.method == 'POST':
        data = request.json
        rules = data.get("rules", [])
        try:
            with open('./custom_rules.json', 'w') as file:
                json.dump(rules, file)
            return jsonify({"status": "success", "message": "Custom rules saved."}), 200
        except Exception as e:
            api_logger.error(f"Error saving custom rules: {e}")
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

        logs_dir = os.path.abspath("./logs")
        
        # --- Force the log_path to be under logs_dir ---
        # 1. If user gave a relative path like "somefile.log", 
        #    build the absolute path in logs_dir:
        full_log_path = os.path.join(logs_dir, log_path)
        
        # Now do the usual checks
        full_log_path = os.path.abspath(full_log_path)
        if not full_log_path.startswith(logs_dir):
            return jsonify({"status": "error", "message": "Invalid log path."}), 400

        # Build meta path
        meta_path = full_log_path + ".meta"

        # Load existing metadata if it exists, else create
        try:
            with open(meta_path, "r") as meta_file:
                meta_data = json.load(meta_file)
        except FileNotFoundError:
            meta_data = {"system": {}, "user": {}}

        # Ensure system/user in meta
        meta_data.setdefault("system", {})
        meta_data.setdefault("user", {})

        # Merge new highlights
        meta_data["user"].update(highlights)

        # Write updated metadata
        with open(meta_path, "w") as meta_file:
            json.dump(meta_data, meta_file)

        return jsonify({"status": "success", "message": "Highlights saved."}), 200

    except Exception as e:
        api_logger.error(f"Error saving highlights: {e}")
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

        logs_dir = os.path.abspath("./logs")
        full_log_path = os.path.join(logs_dir, log_path)
        full_log_path = os.path.abspath(full_log_path)

        if not full_log_path.startswith(logs_dir):
            return jsonify({"status": "error", "message": "Invalid log path."}), 400

        meta_path = full_log_path + ".meta"

        if os.path.exists(meta_path):
            with open(meta_path, 'r') as meta_file:
                meta_data = json.load(meta_file)

            # Clear out 'user' highlights
            meta_data["user"] = {}

            with open(meta_path, 'w') as meta_file:
                json.dump(meta_data, meta_file)

        return jsonify({"status": "success", "message": "User highlights cleared."}), 200

    except Exception as e:
        api_logger.error(f"Error clearing highlights: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    
@api_blueprint.route('/logs/agent', methods=['GET'])
def get_agent_logs():
    load_balancer = LoadBalancer()
    logs = load_balancer.fetch_logs_from_all_agents()

    # Format logs for frontend
    formatted_logs = []
    for agent_logs in logs:
        if "logs" in agent_logs:
            for log in agent_logs["logs"]:
                formatted_logs.append({
                    "agent_ip": agent_logs["ip"],
                    "name": log["name"],
                    "size": len(log.get("content", "")),
                    "content": log.get("content", ""),
                    "modified": log.get("modified", ""),
                })
        else:
            formatted_logs.append({
                "agent_ip": agent_logs["ip"],
                "error": agent_logs.get("error", "Unknown error")
            })

    return jsonify({"status": "success", "logs": formatted_logs}), 200

@api_blueprint.route('/metrics/aggregate', methods=['GET'])
def get_aggregated_metrics():
    """
    API endpoint to aggregate metrics from all agents.
    """
    load_balancer = LoadBalancer()
    metrics = load_balancer.fetch_all_metrics()
    return jsonify({"status": "success", "data": metrics}), 200

@api_blueprint.route('/logs/download_agents', methods=['POST'])
def download_agent_logs():
    try:
        load_balancer = LoadBalancer()
        agent_logs = load_balancer.fetch_logs_from_all_agents()
        # At this point, logs are ALREADY unzipped in ./logs
        
        return jsonify({
            "status": "success", 
            "message": "Agent logs downloaded and extracted.", 
            "results": agent_logs
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@api_blueprint.route('/rules/create', methods=['POST'])
def api_create_rule():
    """
    API endpoint to create a new rule.
    """
    try:
        # Parse request data
        data = request.json

        # Validate common fields
        if not data.get('name') or not data.get('action') or not data.get('rule_type'):
            return jsonify({"status": "error", "message": "Name, action, and rule type are required."}), 400

        # Delegate rule creation to rules_manager
        result = create_rule(data)

        if result["status"] == "success":
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500