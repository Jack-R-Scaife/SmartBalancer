import threading
import time
from response_factory import ResponseFactory

class AlertManager:
    _cached_alerts = {"status": "success", "ip": None, "alerts": []}  # Cached alerts
    _lock = threading.Lock()

    @staticmethod
    def update_alerts(ip_address):
        """
        Periodically update the cached alerts.
        """
        while True:
            try:
                with AlertManager._lock:
                    alerts = ResponseFactory.generate_alerts()
                    AlertManager._cached_alerts = {
                        "status": "success",
                        "ip": ip_address,
                        "alerts": alerts
                    }
            except Exception as e:
                # Log error and reset the cached alerts
                AlertManager._cached_alerts = {
                    "status": "error",
                    "message": str(e),
                    "ip": ip_address,
                    "alerts": []
                }
            time.sleep(2)  # Adjust the interval for periodic updates

    @staticmethod
    def get_cached_alerts():
        """
        Retrieve the latest cached alerts.
        """
        with AlertManager._lock:
            return AlertManager._cached_alerts