from flask import Blueprint, render_template, jsonify
from app import db
from app.models import Server, ServerGroup, ServerGroupServer  # Import necessary models
from sqlalchemy import text

# Blueprint definition
main_blueprint = Blueprint('main', __name__)


# Root route - could be your dashboard
@main_blueprint.route('/')
def index():
    return render_template('dashboard.html')


# Web UI route for the server details page
@main_blueprint.route('/server')
def servers():
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
    return render_template('serverOverview.html')


@main_blueprint.route('/process&threads')
def processnthreads():
    return render_template('process&threads.html')

@main_blueprint.route('/serverNetwork')
def serverNetwork():
    return render_template('serverNetwork.html')

# Web UI route for the server details page
@main_blueprint.route('/rules')
def rules():
    return render_template('rules.html')

