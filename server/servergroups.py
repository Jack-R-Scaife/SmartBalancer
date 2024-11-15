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
    
def remove_groups(group_ids):
    """
    Removes multiple groups and their associations from the database.

    Args:
        group_ids (list): A list of group IDs to remove.

    Returns:
        dict: A dictionary with the status of the operation and a message.
    """
    try:
        # Find all groups that match the given IDs
        groups = ServerGroup.query.filter(ServerGroup.group_id.in_(group_ids)).all()

        if not groups:
            return {'message': 'No groups found for the provided IDs.', 'status': False}

        # Collect group IDs that are successfully deleted
        deleted_group_ids = []

        # Loop through each group and delete it
        for group in groups:
            # Delete associations in the ServerGroupServer table
            ServerGroupServer.query.filter_by(group_id=group.group_id).delete()

            # Delete the group itself
            db.session.delete(group)
            deleted_group_ids.append(group.group_id)

        db.session.commit()

        return {"status": True, "message": f"Groups with IDs {group_ids} removed successfully."}
    except Exception as e:
        print(f"Error deleting groups: {e}")  # Log for debugging
        return {"status": False, "message": "Failed to delete groups"}
    
def create_group_with_servers(name, description, server_ids):
    try:
        # Validate input
        if not name or not description:
            return {"status": "error", "message": "Group name and description are required."}

        # Check if group name already exists
        existing_group = ServerGroup.query.filter_by(name=name).first()
        if existing_group:
            return {"status": "error", "message": "A group with this name already exists."}

        # Create the group
        new_group = ServerGroup(name=name, description=description)
        db.session.add(new_group)
        db.session.flush()  # Flush to get the new group_id

        # Associate servers with the new group
        for server_id in server_ids:
            server = Server.query.get(server_id)
            if server:  # Ensure server exists
                association = ServerGroupServer(server_id=server.server_id, group_id=new_group.group_id)
                db.session.add(association)

        # Commit all changes
        db.session.commit()

        return {"status": "success", "message": f"Group '{name}' created successfully with {len(server_ids)} servers."}
    except Exception as e:
        db.session.rollback()
        print(f"Error creating group with servers: {e}")
        return {"status": "error", "message": "Failed to create group."}