# response_factory.py
import logging
from health_check import HealthCheck

logging.basicConfig(filename='response_factory.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

class ResponseFactory:
    @staticmethod
    def generate_alerts(ip_address):
        """
        Generate alerts when the agent's health status is NOT healthy.
        """
        logging.info("Generating alerts...")

        # Initialize health check
        health_check = HealthCheck()
        # Get health status
        health_status = health_check.determine_status(ip_address)
        resource_status = health_check.check_resources()

        # Define alert messages
        status_mapping = {
            1: "Healthy",
            2: "Overloaded",
            3: "Critical",
            4: "Down",
            5: "Idle",
            6: "Maintenance"
        }

        alerts = []

        if health_status != 1:  # If not Healthy, generate an alert
            alert_message = f"Server status: {status_mapping.get(health_status, 'Unknown')}"
            logging.warning(f"ALERT: {alert_message}")

            alerts.append({
                "type": "ALERT",
                "condition": f"Status: {status_mapping.get(health_status, 'Unknown')}",
                "source": "Health Monitor",
                "description": alert_message
            })

            # Add detailed problem breakdown
            if health_status == 2:  # Overloaded
                if resource_status['cpu'] >= health_check.cpu_thresholds['overloaded']:
                    alerts.append({
                        "type": "O",
                        "condition": f"CPU:{resource_status['cpu']}%",
                        "source": "CPU Monitor",
                        "description": f"CPU usage at {resource_status['cpu']}% exceeds threshold."
                    })
                if resource_status['memory'] >= health_check.memory_thresholds['overloaded']:
                    alerts.append({
                        "type": "O",
                        "condition": f"Memory:{resource_status['memory']}%",
                        "source": "Memory Monitor",
                        "description": f"Memory usage at {resource_status['memory']}% exceeds threshold."
                    })
                if resource_status['disk'] >= health_check.disk_thresholds['overloaded']:
                    alerts.append({
                        "type": "O",
                        "condition": f"Disk:{resource_status['disk']}%",
                        "source": "Disk Monitor",
                        "description": f"Disk usage at {resource_status['disk']}% exceeds threshold."
                    })

            if health_status == 4:  # Server Down
                alerts.append({
                    "type": "D",
                    "condition": "Ping: Unreachable",
                    "source": "Network Monitor",
                    "description": f"Server is unreachable at IP: {ip_address}"
                })

        logging.info(f"Generated alerts: {alerts}")
        return alerts