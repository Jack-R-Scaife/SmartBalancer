from app import create_app, db
from server.agent_monitor import LoadBalancer
from server.server_manager import ServerManager
import threading

app = create_app()
app.secret_key = 'your_super_secret_key'

def start_agent_monitoring():
    """
    Function to start agent monitoring in a separate thread.
    """
    load_balancer = LoadBalancer()
    # Start monitoring in a background thread
    monitor_thread = threading.Thread(target=load_balancer.monitor_agents, daemon=True)
    monitor_thread.start()

if __name__ == '__main__':
    # Ensure the database tables are created before starting the server
    with app.app_context():
        db.create_all()

    # Initialize ServerManager after the database tables are created
    server_manager = ServerManager(app)

    # Start the agent monitoring when the Flask app starts
    start_agent_monitoring()
    
    # Run the Flask application
    app.run(debug=True)
