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
    description = db.Column(db.String(200), nullable=False,)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    server_count = db.Column(db.Integer, nullable=False, default=0)
    max_servers = db.Column(db.Integer, nullable=False, default=10)

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
    
    # Relationship to Strategy
    strategy = db.relationship('Strategy', backref='load_balancer_settings')

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

class Template(db.Model):
    __tablename__ = 'Template'

    template_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    settings = db.Column(db.JSON, nullable=True)

class Rule(db.Model):
    __tablename__ = 'Rules'

    rule_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rule_type = db.Column(db.Enum('geo', 'traffic', 'resource'), nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    Strategies_strategy_id = db.Column(db.Integer, db.ForeignKey('Strategies.strategy_id'), nullable=False)
    
    # Relationship to Strategy
    strategy = db.relationship('Strategy', backref='rules')

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
