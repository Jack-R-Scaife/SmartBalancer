from app import db
from app.models import Server, ServerGroup, ServerGroupServer, Authentication
from flask import jsonify

def update_server_group(server_id, group_id):
    if not server_id or not group_id:
        return {'status': 'error', 'message': 'Server ID and Group ID are required'}

    try:
        # Remove existing group associations for the server
        ServerGroupServer.query.filter_by(server_id=server_id).delete()

        # Create a new group association
        new_association = ServerGroupServer(server_id=server_id, group_id=group_id)
        db.session.add(new_association)
        db.session.commit()
        
        return {'status': 'success', 'message': 'Server group updated successfully'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_servers_and_groups():
    try:
        servers = Server.query.all()
        groups = ServerGroup.query.all()

        server_data = []
        for server in servers:
            group_association = ServerGroupServer.query.filter_by(server_id=server.server_id).first()
            group_info = None
            if group_association:
                group = ServerGroup.query.get(group_association.group_id)
                if group:
                    group_info = {
                        'group_id': str(group.group_id),
                        'name': group.name
                    }

            server_data.append({
                'server_id': str(server.server_id),
                'server_ip': server.ip_address,
                'group': group_info
            })

        group_data = [{'group_id': str(group.group_id), 'name': group.name} for group in groups]

        return {'status': 'success', 'servers': server_data, 'groups': group_data}
    except Exception as e:
        print("Error fetching servers and groups:", e)
        return {'status': 'error', 'message': str(e)}