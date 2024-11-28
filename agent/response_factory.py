# response_factory.py
import logging
from health_check import HealthCheck

logging.basicConfig(filename='response_factory.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

class ResponseFactory:
    @staticmethod
    def generate_alerts():
        """
        Generate a list of alerts based on the HealthCheck class.
        Each alert includes: type, condition, source, and description.
        """
        logging.info("Generating alerts...")

        # Initialize the HealthCheck instance
        health_check = HealthCheck()
        resource_status = health_check.check_resources()

        # Pre-fetch thresholds to minimize repeated dictionary lookups
        thresholds = {
            'cpu': health_check.cpu_thresholds,
            'memory': health_check.memory_thresholds,
            'disk': health_check.disk_thresholds
        }

        # Prepare alerts list
        alerts = []

        # Helper function to determine type based on thresholds
        def determine_type(value, metric):
            if value >= thresholds[metric]['overloaded']:
                return "O"  # Overload
            return "H"  # Healthy

        # Generate alerts for each resource
        for metric, usage in resource_status.items():
            if metric not in thresholds:
                continue  # Skip unknown metrics

            type_key = determine_type(usage, metric)
            if type_key == "O":  # Only log overloaded conditions
                alerts.append({
                    "type": type_key, 
                    "condition": f"{metric.upper()}:{usage}%",  
                    "source": f"{metric.capitalize()} Monitor",
                    "description": f"{metric.capitalize()} usage at {usage}% exceeds threshold."
                })
                logging.warning(f"Overloaded condition detected: {metric.capitalize()} usage at {usage}% exceeds threshold.")

        # Check if the server is down based on resource and ping checks
        ip_address = "192.168.1.2
        if health_check.check_ping(ip_address) == -1:
            logging.error(f"Server is down. Unable to reach IP: {ip_address}")
            alerts.append({
                "type": "D",
                "condition": "Ping: Unreachable",
                "source": "Network Monitor",
                "description": f"Unable to reach server at IP: {ip_address}. Server might be down."
            })

        # No need to add a healthy alert if no issues are found, frontend will handle "No alerts" display

        logging.info(f"Generated alerts: {alerts}")
        return alerts
