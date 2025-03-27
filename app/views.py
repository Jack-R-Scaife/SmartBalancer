from flask import Blueprint, render_template, jsonify,session,redirect,url_for,request
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

@main_blueprint.route('/userDoc')
def userDoc():
    session['sub_links_open'] = False
    return render_template('userDoc.html')

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
        
        # Get latest resource usage
        server_info = {
            'server_id': server.server_id,
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

# Web UI route for the server details page
@main_blueprint.route('/train')
def train():
    session['sub_links_open'] = False
    return render_template('train.html')

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

@main_blueprint.route('/logs')
def logs():
    session['sub_links_open'] = False
    return render_template('logs.html')

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
    # Get the subpage (default to 'editgroup' if not provided)
    subpage = request.args.get('page', 'editgroup')
    return render_template('configureRules.html', subpage=subpage)


@main_blueprint.route('/toggle_sublinks', methods=['POST'])
def toggle_sublinks():
    # Update the session to keep sub-links open
    session['sub_links_open'] = True
    
    return jsonify({'message': 'Sub-links toggled successfully!'})

@main_blueprint.route('/configRules/methods')
def config_methods():
    session['sub_links_open'] = False
    group_id = request.args.get('group_id')
    return render_template('config_methods.html', group_id=group_id)

@main_blueprint.route('/configRules/show')
def config_show_rules():
    session['sub_links_open'] = False
    group_id = request.args.get('group_id')
    #Query all rules from the database
    from app.models import Rule
    rules = Rule.query.order_by(Rule.priority.asc()).all()  # Order by priority
    return render_template('config_show_rules.html', group_id=group_id, rules=rules)

@main_blueprint.route('/configRules/add')
def config_add_rules():
    session['sub_links_open'] = False
    group_id = request.args.get('group_id')
    return render_template('config_add_rules.html', group_id=group_id)