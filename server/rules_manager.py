from app.models import Rule, ServerGroup
from app import db

def create_rule(data):
    """
    Handles the creation of a new rule.
    """
    try:
        rule_type = data['rule_type']

        # Traffic-Based Rule Logic
        if rule_type == 'traffic':
            return create_traffic_rule(data)
        else:
            return {"status": "error", "message": f"Unsupported rule type: {rule_type}"}

    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": f"Failed to create rule: {str(e)}"}

def create_traffic_rule(data):
    """
    Handles creation of a Traffic-Based rule.
    """
    try:
        # Extract specific fields for Traffic-Based rules
        source_ip_range = data.get('source_ip_range')
        protocol = data.get('protocol')
        port = data.get('port')
        traffic_limit = data.get('traffic_limit')
        redirect_target_type = data.get('redirect_target_type')
        redirect_target = data.get('redirect_target')

        # Validate required fields
        if not source_ip_range or not protocol:
            return {"status": "error", "message": "Source IP range and protocol are required for Traffic-Based rules."}

        # Create the rule
        new_rule = Rule(
            name=data['name'],
            description=data.get('description', ''),
            rule_type='traffic',
            priority=data.get('priority', 1),
            action=data['action'],
            status=data.get('status', True),
            source_ip_range=source_ip_range,
            protocol=protocol,
            port=port,
            traffic_limit=traffic_limit,
            redirect_target_type=redirect_target_type,
            redirect_target=redirect_target,
            schedule=data.get('schedule', {}),
        )

        # Associate rule with server groups
        group_ids = data.get('server_groups', [])
        for group_id in group_ids:
            group = ServerGroup.query.get(group_id)
            if group:
                new_rule.server_groups.append(group)

        db.session.add(new_rule)
        db.session.commit()

        return {"status": "success", "message": f"Traffic-Based rule '{new_rule.name}' created successfully."}

    except Exception as e:
        return {"status": "error", "message": f"Error creating Traffic-Based rule: {str(e)}"}
