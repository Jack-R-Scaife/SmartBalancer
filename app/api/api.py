# app/api/api.py
from flask import Blueprint, request, jsonify, Response,redirect,url_for,flash
import joblib
import pandas as pd
from app import db
from server.server_manager import ServerManager
from server.servergroups import update_server_group,get_servers_and_groups,remove_groups,create_group_with_servers,get_servers_by_group
from app.models import Server,LoadBalancerSetting,Strategy,Rule,ServerGroup
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
from server.dynamic_algorithms import DynamicAlgorithms
status_mapping = {
    "healthy": 1,
    "overloaded": 2,
    "critical": 3,
    "down": 4,
    "idle": 5
}
model_path = os.path.join('Predictive_Model', 'lightgbm_model.pkl')
if os.path.exists(model_path):
    model = joblib.load(model_path)
    print("Predictive model loaded successfully.")
else:
    model = None
    print("No predictive model found. The load balancer will work without predictions until a model is trained.")


# Threshold for significant prediction error (e.g., 10%)
threshold_error = 0.1

@api_blueprint.route('/predicted_traffic', methods=['GET'])
def get_predicted_traffic():
    """
    Predicts overall traffic rate based on dynamically fetched real-time metrics from all agents.
    """
    try:
        load_balancer = LoadBalancer()
        agent_metrics = load_balancer.fetch_metrics_from_all_agents()

        if not agent_metrics:
            api_logger.error("No metrics available from agents.")
            return jsonify([]), 200  # Return an empty array

        # Aggregate real-time metrics across all agents
        num_agents = len(agent_metrics)
        aggregated_metrics = {
            'cpu_usage': sum(agent['metrics'].get('cpu_total', 0) for agent in agent_metrics) / num_agents,
            'memory_usage': sum(agent['metrics'].get('memory', 0) for agent in agent_metrics) / num_agents,
            'connections': sum(agent['metrics'].get('connections', 0) for agent in agent_metrics),
            'traffic_rate': sum(agent['metrics'].get('traffic_rate', 0) for agent in agent_metrics),
        }

        # Fetch scenario and strategy dynamically
        scenario = agent_metrics[0].get('scenario', 'default_scenario')
        group_id = agent_metrics[0].get('group_id', 1)  # Default to group 1 if missing
        strategy = load_balancer.get_group_strategy(group_id) or "Round Robin"

        aggregated_metrics['scenario'] = scenario
        aggregated_metrics['strategy'] = strategy

        # Prepare data for model prediction
        feature_df = pd.DataFrame([aggregated_metrics])

        # One-hot encoding for `scenario` and `strategy`
        feature_df = pd.get_dummies(feature_df, columns=['scenario', 'strategy'], dummy_na=False)
        if model is not None:
            expected_features = model.feature_names_in_
            feature_df = feature_df.reindex(columns=expected_features, fill_value=0)
        else:
            # If no model, simply log and return empty predictions.
            api_logger.info("Predictive model not trained yet. Returning empty predictions.")
            return jsonify([]), 200

        # Predict traffic for the next 10 seconds if a model is available
        predictions = []
        current_time = datetime.now()
        for i in range(60):
            prediction = model.predict(feature_df)[0]
            future_timestamp = (current_time + timedelta(seconds=i)).timestamp()
            predictions.append({'timestamp': future_timestamp, 'value': prediction})

        return jsonify(predictions), 200  # Always return an array

    except Exception as e:
        api_logger.error(f"Error in traffic prediction: {e}")
        return jsonify([]), 200  # Return an empty array if an error occurs



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
    API endpoint to set load balancing strategy and update the database.
    Supports multiple strategies in priority order.
    """
    try:
        data = request.json
        group_id = data.get("group_id")
        strategies = data.get("strategies", [])
        ai_enabled = data.get("ai_enabled", False)
        weights = data.get("weights", {})

        if not group_id:
            return jsonify({"status": "error", "message": "Group ID is required."}), 400

        if not strategies:
            return jsonify({"status": "error", "message": "At least one strategy is required."}), 400

        # ✅ FIX: Pass Correct Strategy Order
        result = StrategyManager.apply_multiple_strategies_to_group(strategies, group_id, ai_enabled)

        # ✅ Apply weights only if Resource-Based is in Priority 1
        if strategies[0] == "Resource-Based":
            StrategyManager.dynamic_algorithms.set_weights({k: float(v) for k, v in weights.items() if v})

        # ✅ Reload active strategies to ensure correct application
        load_balancer = LoadBalancer()
        load_balancer.load_saved_strategies()

        return jsonify(result), 200 if result["status"] == "success" else 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_blueprint.route('/load_balancer/active_strategy/<int:group_id>', methods=['GET'])
def get_active_strategy(group_id):
    try:
        setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
        if not setting:
            return jsonify({"status": "error", "message": "No active strategy found for this group."}), 404

        strategy = Strategy.query.get(setting.active_strategy_id)
        return jsonify({
            "status": "success",
            "strategy_name": strategy.name,
            "method_type": strategy.method_type,
            "ai_enabled": setting.predictive_enabled
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
        data = request.json
        if not data.get('name') or not data.get('action') or not data.get('rule_type'):
            return jsonify({"status": "error", "message": "Name, action, and rule type are required."}), 400

        result = create_rule(data)

        if result["status"] == "success":
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/rules/delete/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    """
    Deletes a rule from the database.
    """
    try:
        rule = Rule.query.get(rule_id)
        if not rule:
            return jsonify({"status": "error", "message": "Rule not found"}), 404
        
        db.session.delete(rule)
        db.session.commit()
        
        return jsonify({"status": "success", "message": "Rule deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
   
@api_blueprint.route('/rules/update_status/<int:rule_id>', methods=['POST'])
def update_rule_status(rule_id):
    """
    Updates the enable/disable status of a rule.
    """
    try:
        data = request.json
        rule = Rule.query.get(rule_id)

        if not rule:
            return jsonify({"status": "error", "message": "Rule not found"}), 404
        
        rule.status = data.get("status", True)  # Toggle status based on checkbox
        db.session.commit()
        
        return jsonify({"status": "success", "message": f"Rule status updated to {'enabled' if rule.status else 'disabled'}"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@api_blueprint.route('/rules/update_priority', methods=['POST'])
def update_rule_priority():
    """
    Updates rule priorities dynamically based on drag-and-drop order.
    """
    try:
        data = request.json
        for rule_data in data["rules"]:
            rule = Rule.query.get(rule_data["rule_id"])
            if rule:
                rule.priority = rule_data["priority"]

        db.session.commit()
        return jsonify({"status": "success", "message": "Rule priorities updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    


@api_blueprint.route('/load_balancer/group_strategy', methods=['POST'])
def set_group_strategy():
    """
    Set strategy for a specific group and optionally enable AI.
    """
    data = request.json
    group_id = data.get("group_id")
    strategy_name = data.get("strategy")
    ai_enabled = data.get("ai_enabled", False)

    if not group_id or not strategy_name:
        return jsonify({"status": "error", "message": "Group ID and strategy are required."}), 400

    try:
        result = StrategyManager.apply_strategy_to_group(strategy_name, group_id, ai_enabled)
        return jsonify(result), 200 if result["status"] == "success" else 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@api_blueprint.route('/load_balancer/resource_weights/<int:group_id>', methods=['GET'])
def get_resource_weights(group_id):
    """Returns current resource-based weight settings for a group"""
    try:
        weights = DynamicAlgorithms().weights
        return jsonify({
            "status": "success",
            "weights": {
                "cpu": weights.get("cpu", 0.4) * 100,  # Convert to percentage
                "memory": weights.get("memory", 0.3) * 100,
                "disk": weights.get("disk", 0.2) * 100,
                "connections": weights.get("connections", 0.1) * 100
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/load_balancer/settings/<int:group_id>', methods=['GET'])
def get_load_balancer_settings(group_id):
    """Get full load balancer settings for a group"""
    try:
        setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
        if not setting:
            return jsonify({"status": "error", "message": "No settings found"}), 404

        strategy = Strategy.query.get(setting.active_strategy_id)
        return jsonify({
            "status": "success",
            "active_strategy": strategy.name if strategy else None,
            "failover_priority": setting.failover_priority.split(", ") if setting.failover_priority else [],
            "ai_enabled": setting.predictive_enabled
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@api_blueprint.route('/get_groups', methods=['GET'])
def get_groups():
    groups = ServerGroup.query.all()
    groups_list = [{"group_id": g.group_id, "name": g.name} for g in groups]
    return jsonify({"groups": groups_list})


# Servers Endpoint - Add required fields
@api_blueprint.route('/get_servers', methods=['GET'])
def get_servers():
    servers = Server.query.all()
    servers_list = [{"ip": s.ip_address, "name": f"Server {s.server_id}"} for s in servers]
    return jsonify({"servers": servers_list})

# Countries Endpoint - Match frontend expectations
@api_blueprint.route('/get_countries', methods=['GET'])
def get_countries():
    region = request.args.get("region", "NA")
    countries = {
        "NA": [{"code": "US", "name": "United States"}],
        "EU": [{"code": "DE", "name": "Germany"}],
        "AS": [{"code": "CN", "name": "China"}],
        "AF": [{"code": "NG", "name": "Nigeria"}],
        "SA": [{"code": "BR", "name": "Brazil"}]
    }
    return jsonify({"countries": countries.get(region, [])})

@api_blueprint.route('/get_load_methods', methods=['GET'])
def get_load_methods():
    methods = [
        {"id": "round_robin", "name": "Round Robin"},
        {"id": "least_connections", "name": "Least Connections"},
        {"id": "weighted", "name": "Weighted Round Robin"},
        {"id": "resource", "name": "Resource-Based"}
    ]
    return jsonify(methods)