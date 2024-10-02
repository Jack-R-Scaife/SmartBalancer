from app import create_app, db
from server.agent_monitor import LoadBalancer
import threading

app = create_app()

def start_agent_monitoring():
    """
    Function to start agent monitoring in a separate thread.
    """
    load_balancer = LoadBalancer()
    # Start monitoring in a background thread
    monitor_thread = threading.Thread(target=load_balancer.monitor_agents, daemon=True)
    monitor_thread.start()

if __name__ == '__main__':
   with app.app_context():
      db.create_all()

   # Start the agent monitoring when the Flask app starts
   start_agent_monitoring()
   app.run(debug=True)
