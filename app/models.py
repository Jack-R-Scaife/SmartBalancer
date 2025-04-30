from app import db

class Authentication(db.Model):
    __tablename__ = 'Authentication'

    key_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_key = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Server(db.Model):
    __tablename__ = 'Servers'

    server_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip_address = db.Column(db.String(45), nullable=False, unique=True)
    status = db.Column(db.Enum('healthy', 'critical', 'overloaded', 'maintenance', 'idle', 'down', 'offline'), nullable=True, default='offline')  
    auto_connect = db.Column(db.Boolean, nullable=True, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    public_key = db.Column(db.Integer, db.ForeignKey('Authentication.key_id'), nullable=False)
    
    # Relationship to Authentication table
    authentication = db.relationship('Authentication', backref='servers')

class ServerGroup(db.Model):
    __tablename__ = 'Server_Groups'
    
    group_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(45), nullable=False, unique=True)
    description = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    server_count = db.Column(db.Integer, nullable=False, default=0)
    max_servers = db.Column(db.Integer, nullable=False, default=10)
    active_model = db.Column(db.String(100), nullable=True)


class Strategy(db.Model):
    __tablename__ = 'Strategies'

    strategy_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    method_type = db.Column(db.Enum('static', 'dynamic'), nullable=False)
    description = db.Column(db.Text, nullable=True)

class LoadBalancerSetting(db.Model):
    __tablename__ = 'Load_Balancer_Settings'

    setting_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    failover_priority = db.Column(db.String(100), nullable=False)
    predictive_enabled = db.Column(db.Boolean, nullable=True, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    active_strategy_id = db.Column(db.Integer, db.ForeignKey('Strategies.strategy_id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('Server_Groups.group_id'), nullable=False)  # Add this line

    # Relationships
    strategy = db.relationship('Strategy', backref='load_balancer_settings')
    group = db.relationship('ServerGroup', backref='load_balancer_settings') 
class ServerGroupServer(db.Model):
    __tablename__ = 'Server_Group_Servers'

    server_id = db.Column(db.Integer, db.ForeignKey('Servers.server_id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('Server_Groups.group_id'), primary_key=True)
    
    # Relationships
    server = db.relationship('Server', backref='server_group_associations')
    server_group = db.relationship('ServerGroup', backref='server_group_associations')

class ServerSetting(db.Model):
    __tablename__ = 'Server_Settings'

    setting_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cpu_utilisation = db.Column(db.Float, nullable=True)
    cpu_turbo_boost = db.Column(db.Boolean, nullable=True, default=False)
    cpu_hyperthreading = db.Column(db.Boolean, nullable=True, default=False)
    max_concurrent_theads = db.Column(db.Integer, nullable=True)
    thread_pool_size = db.Column(db.Integer, nullable=True)
    memory_frequency = db.Column(db.Float, nullable=True)
    cas_latency = db.Column(db.Integer, nullable=True)
    eec = db.Column(db.Boolean, nullable=True, default=False)
    xmp_profile = db.Column(db.String(50), nullable=True)
    memory_interleaving = db.Column(db.Boolean, nullable=True, default=False)
    raid_level = db.Column(db.String(50), nullable=True)
    disk_io_priority = db.Column(db.String(50), nullable=True)
    ssd_overprovisioning = db.Column(db.Boolean, nullable=True)
    block_size = db.Column(db.Integer, nullable=True)
    power_profile = db.Column(db.String(50), nullable=True)
    fan_speed_control = db.Column(db.String(50), nullable=True)
    max_fan_speed = db.Column(db.String(50), nullable=True)
    thermal_throttling = db.Column(db.Boolean, nullable=True, default=False)
    Servers_server_id = db.Column(db.Integer, db.ForeignKey('Servers.server_id'), nullable=False)
    
    # Relationship to Server
    server = db.relationship('Server', backref='server_settings')

class NetworkSetting(db.Model):
    __tablename__ = 'Network_Settings'

    network_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip_address = db.Column(db.String(45), nullable=False)
    subnet_mask = db.Column(db.String(45), nullable=False)
    gateway = db.Column(db.String(45), nullable=False)
    dns_primary = db.Column(db.String(45), nullable=False)
    dns_secondary = db.Column(db.String(45), nullable=True)
    mtu_size = db.Column(db.Integer, nullable=False)
    bonding_mode = db.Column(db.String(50), nullable=True)
    max_connections = db.Column(db.Integer, nullable=True)
    connection_timeout = db.Column(db.Integer, nullable=True)
    network_throttling = db.Column(db.Boolean, nullable=True, default=False)
    bandwidth_limit = db.Column(db.Float, nullable=True)
    port_forwarding = db.Column(db.Boolean, nullable=True, default=False)
    Servers_server_id = db.Column(db.Integer, db.ForeignKey('Servers.server_id'), nullable=False)
    
    # Relationship to Server
    server = db.relationship('Server', backref='network_settings')

class PortForwarding(db.Model):
    __tablename__ = 'Port_Forwarding'

    port_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    external_port = db.Column(db.Integer, nullable=False)
    internal_port = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.Enum('TCP', 'UDP'), nullable=False)
    Servers_server_id = db.Column(db.Integer, db.ForeignKey('Servers.server_id'), nullable=False)
    
    # Relationship to Server
    server = db.relationship('Server', backref='port_forwardings')


RuleServerGroup = db.Table(
    'Rule_ServerGroup',
    db.Column('rule_id', db.Integer, db.ForeignKey('Rules.rule_id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('Server_Groups.group_id'), primary_key=True)
)

class Rule(db.Model):
    __tablename__ = 'Rules'

    rule_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rule_type = db.Column(db.Enum('traffic', 'geo', 'load', 'custom'), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=1)
    action = db.Column(db.Enum('allow', 'block', 'redirect'), nullable=False)
    status = db.Column(db.Boolean, default=True)

    # Traffic-Based Rule Fields
    source_ip_range = db.Column(db.String(100), nullable=True)
    protocol = db.Column(db.Enum('http', 'https', 'tcp', 'udp'), nullable=True)
    port = db.Column(db.String(20), nullable=True)
    traffic_limit = db.Column(db.Integer, nullable=True)
    redirect_target_type = db.Column(db.Enum('group', 'server'), nullable=True)
    redirect_target = db.Column(db.String(50), nullable=True)

    # Schedule
    schedule = db.Column(db.JSON, nullable=True)  # JSON for days, start_time, end_time

    # Relationships
    server_groups = db.relationship(
        'ServerGroup',
        secondary=RuleServerGroup,  # Explicitly use RuleServerGroup
        backref=db.backref('rules', lazy='dynamic')
    )

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


class Template(db.Model):
    __tablename__ = 'Template'

    template_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    settings = db.Column(db.JSON, nullable=True)

class AccessLog(db.Model):
    __tablename__ = 'Access_Logs'

    access_log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_ip = db.Column(db.String(45), nullable=False)
    traffic_type = db.Column(db.String(45), nullable=False)
    request_data = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    Servers_server_id = db.Column(db.Integer, db.ForeignKey('Servers.server_id'), nullable=False)
    
    # Relationship to Server
    server = db.relationship('Server', backref='access_logs')

class HealthCheck(db.Model):
    __tablename__ = 'Health_Checks'

    health_check_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    check_type = db.Column(db.String(45), nullable=False)
    result = db.Column(db.Enum('pass', 'fail'), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    Servers_server_id = db.Column(db.Integer, db.ForeignKey('Servers.server_id'), nullable=False)
    
    # Relationship to Server
    server = db.relationship('Server', backref='health_checks')

class Alert(db.Model):
    __tablename__ = 'Alerts'

    alert_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_type = db.Column(db.String(45), nullable=False)
    severity = db.Column(db.Enum('info', 'warning', 'critical'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class PredictiveLog(db.Model):
    __tablename__ = 'Predictive_Logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    server_ip = db.Column(db.String(45), nullable=False)
    response_time = db.Column(db.Float, nullable=True)
    cpu_usage = db.Column(db.Float, nullable=True)
    memory_usage = db.Column(db.Float, nullable=True)
    connections = db.Column(db.Integer, nullable=True)
    traffic_rate = db.Column(db.Float, nullable=True)
    traffic_volume = db.Column(db.Integer, nullable=True)
    scenario = db.Column(db.String(50), nullable=True)  
    strategy = db.Column(db.String(50), nullable=True)

    #link to the ServerGroup table
    group_id = db.Column(db.Integer, db.ForeignKey('Server_Groups.group_id'), nullable=True)
    server_group = db.relationship('ServerGroup', backref='predictive_logs')
class StartWindowMetrics(db.Model):
    __tablename__ = 'start_window_metrics'

    metric_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp   = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    server_ip   = db.Column(db.String(45), db.ForeignKey('Servers.ip_address'), nullable=False)
    traffic_rate= db.Column(db.Float, nullable=False)
    cpu_usage   = db.Column(db.Float, nullable=True)
    memory_usage= db.Column(db.Float, nullable=True)
    disk_usage  = db.Column(db.Float, nullable=True)
    connections = db.Column(db.Integer, nullable=True)
    scenario    = db.Column(db.String(50), nullable=True)
    strategy    = db.Column(db.String(100), nullable=True)
    group_id    = db.Column(db.Integer, db.ForeignKey('Server_Groups.group_id'), nullable=True)

    # Relationships (optional)
    server      = db.relationship('Server', backref='start_window_metrics')
    group       = db.relationship('ServerGroup', backref='start_window_metrics')

def initialize_strategies():
    from app import db
    from app.models import Strategy

    default_strategies = [
        {"name": "Round Robin", "method_type": "static", "description": "Distributes traffic equally among all servers."},
        {"name": "Weighted Round Robin", "method_type": "static", "description": "Distributes traffic based on server weights."},
        {"name": "Least Connections", "method_type": "dynamic", "description": "Directs traffic to the server with the least active connections."},
        {"name": "Least Response Time", "method_type": "dynamic", "description": "Directs traffic to the server with the shortest response time."},
        {"name": "Resource-Based", "method_type": "dynamic", "description": "Balances traffic based on server resource usage."}
    ]

    for strategy_data in default_strategies:
        existing_strategy = Strategy.query.filter_by(name=strategy_data['name']).first()
        if not existing_strategy:
            new_strategy = Strategy(
                name=strategy_data['name'],
                method_type=strategy_data['method_type'],
                description=strategy_data['description']
            )
            db.session.add(new_strategy)

    db.session.commit()
    print("Strategies initialized successfully.")