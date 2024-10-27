from flask import Blueprint, render_template, jsonify,session,redirect,url_for
from app import db
from app.models import Server, ServerGroup, ServerGroupServer  # Import necessary models
from sqlalchemy import text

# Blueprint definition
main_blueprint = Blueprint('main', __name__)

# Root route - could be your dashboard
@main_blueprint.route('/')
def index():
    session['sub_links_open'] = False
    return render_template('dashboard.html')


# Web UI route for the server details page
@main_blueprint.route('/server')
def servers():
    session['sub_links_open'] = False
    # Query all servers
    servers = Server.query.all()
    
    # Prepare data for the template
    server_data = []
    for server in servers:
        # Get server group(s)
        groups = [association.server_group.name for association in server.server_group_associations]
        group_names = ', '.join(groups)
        
        # Get latest resource usage (Assuming you have a ResourceUsage model)
        server_info = {
            'group': group_names ,
            'status': server.status,
            'name': getattr(server, 'name', 'N/A'),  # Use 'N/A' if name is not available
            'ip_address': server.ip_address,
            'cpu_usage': 'N/A',
            'memory_usage':'N/A',
            'disk_usage': 'N/A',
            'network_traffic':'N/A',
        }
        server_data.append(server_info)
    
    return render_template('server.html', servers=server_data)


# Web UI route for the server details page
@main_blueprint.route('/overview')
def overview():
    session['sub_links_open'] = True
    return render_template('serverOverview.html')


@main_blueprint.route('/process_threads')
def process_threads():
    session['sub_links_open'] = True
    return render_template('process&threads.html')

@main_blueprint.route('/serverNetwork')
def server_network():
    return render_template('serverNetwork.html')


@main_blueprint.route('/rules')
def rules():
    session['sub_links_open'] = False
    return render_template('rules.html')

@main_blueprint.route('/memory_storage')
def memory_storage():
    session['sub_links_open'] = True
    return render_template("serverMemory.html")


@main_blueprint.route('/loadbalance')
def loadbalance():
    session['sub_links_open'] = True
    return render_template("loadbalance.html")


@main_blueprint.route('/server_power')
def server_power():
    session['sub_links_open'] = True
    return render_template("serverPower.html")

@main_blueprint.route('/configRules')
def configrules():
    session['sub_links_open'] = False
    return render_template('configureRules.html')


@main_blueprint.route('/toggle_sublinks', methods=['POST'])
def toggle_sublinks():
    # Update the session to keep sub-links open
    session['sub_links_open'] = True
    
    # You can also handle additional logic based on the server_id if needed
    # server_id = request.json.get('server_id')

    return jsonify({'message': 'Sub-links toggled successfully!'})