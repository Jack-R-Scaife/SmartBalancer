from app.models import Rule, ServerGroup
from app import db

def create_rule(data):
    """
    Handles the creation of a new rule.
    Supports Traffic, Geo, Time, and Load-based rules.
    """
    try:
        rule_type = data['rule_type']

        if rule_type == 'traffic':
            return create_traffic_rule(data)
        elif rule_type == 'geo':
            return create_geo_rule(data)
        elif rule_type == 'time':
            return create_time_rule(data)
        elif rule_type == 'load':
            return create_load_rule(data)
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
        new_rule = Rule(
            name=data['name'],
            description=data.get('description', ''),
            rule_type='traffic',
            priority=data.get('priority', 1),
            action=data['action'],
            status=data.get('status', True),
            source_ip_range=data.get('source_ip_range'),
            protocol=data.get('protocol'),
            port=data.get('port'),
            traffic_limit=data.get('traffic_limit'),
            redirect_target_type=data.get('redirect_target_type'),
            redirect_target=data.get('redirect_target'),
            schedule=data.get('schedule', {})
        )

        # Associate with server groups
        associate_rule_with_groups(new_rule, data.get('server_groups', []))

        db.session.add(new_rule)
        db.session.commit()
        return {"status": "success", "message": f"Traffic-Based rule '{new_rule.name}' created successfully."}

    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": f"Error creating Traffic-Based rule: {str(e)}"}

def create_geo_rule(data):
    """
    Handles creation of a Geo-Based rule.
    """
    try:
        new_rule = Rule(
            name=data['name'],
            description=data.get('description', ''),
            rule_type='geo',
            priority=data.get('priority', 1),
            action=data['action'],
            status=data.get('status', True),
            source_ip_range=data.get('source_ip_range'),
            redirect_target=data.get('redirect_target')
        )

        associate_rule_with_groups(new_rule, data.get('server_groups', []))

        db.session.add(new_rule)
        db.session.commit()
        return {"status": "success", "message": f"Geo-Based rule '{new_rule.name}' created successfully."}

    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": f"Error creating Geo-Based rule: {str(e)}"}

def create_time_rule(data):
    """
    Handles creation of a Time-Based rule.
    """
    try:
        new_rule = Rule(
            name=data['name'],
            description=data.get('description', ''),
            rule_type='time',
            priority=data.get('priority', 1),
            action=data['action'],
            status=data.get('status', True),
            schedule=data.get('schedule', {})
        )

        associate_rule_with_groups(new_rule, data.get('server_groups', []))

        db.session.add(new_rule)
        db.session.commit()
        return {"status": "success", "message": f"Time-Based rule '{new_rule.name}' created successfully."}

    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": f"Error creating Time-Based rule: {str(e)}"}

def create_load_rule(data):
    """
    Handles creation of a Load-Based rule.
    """
    try:
        new_rule = Rule(
            name=data['name'],
            description=data.get('description', ''),
            rule_type='load',
            priority=data.get('priority', 1),
            action=data['action'],
            status=data.get('status', True),
            traffic_limit=data.get('traffic_limit')
        )

        associate_rule_with_groups(new_rule, data.get('server_groups', []))

        db.session.add(new_rule)
        db.session.commit()
        return {"status": "success", "message": f"Load-Based rule '{new_rule.name}' created successfully."}

    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": f"Error creating Load-Based rule: {str(e)}"}

def associate_rule_with_groups(rule, group_ids):
    """
    Helper function to associate a rule with server groups.
    """
    for group_id in group_ids:
        group = ServerGroup.query.get(group_id)
        if group:
            rule.server_groups.append(group)
