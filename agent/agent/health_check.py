import psutil
import subprocess
import random
from resource_monitor import ResourceMonitor
class HealthCheck:
    """
    Performs health checks on the server and determines its status.
    """

    def __init__(self):
        self.resource_monitor = ResourceMonitor()  # Initialize the ResourceMonitor
        self.maintenance_mode = False  # This could be toggled by user commands

    def check_ping(self, ip_address):
        """
        Check the server's network latency by pinging the load balancer.
        :param ip_address: The IP address of the load balancer to ping.
        :return: Ping latency in milliseconds, or -1 if unreachable.
        """
        try:
            result = subprocess.run(['ping', '-c', '1', ip_address], stdout=subprocess.PIPE)
            if result.returncode == 0:
                # Extract the ping time from the output
                output = result.stdout.decode('utf-8')
                latency = float(output.split('time=')[1].split(' ms')[0])
                return latency
            else:
                return -1  # Ping failed, server is unreachable
        except Exception as e:
            print(f"Error pinging load balancer: {e}")
            return -1

    def check_resources(self):
        """
        Checks the server's resource usage.
        :return: A dictionary containing CPU, memory, and disk usage percentages.
        """
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        return {
            'cpu': cpu_usage,
            'memory': memory_usage,
            'disk': disk_usage
        }

    def determine_status(self, ip_address):
        """
        Determine the health status of the server based on resource usage, ping, and maintenance mode.
        :return: The server's status as a string (e.g., 'kealthy', 'Overloaded', 'Down', etc.).
        """
        # If maintenance mode is on, the server is in maintenance
        if self.maintenance_mode:
            return "6"

        # Check the ping to the load balancer
        ping_latency = self.check_ping(ip_address)
        print(f"Ping latency to {ip_address}: {ping_latency} ms")
        if ping_latency == -1:
            return 4
        
        # Check resource usage
        resources = self.resource_monitor.monitor()
        cpu_usage = resources['cpu_total']
        memory_usage = resources['memory']
        disk_usage = resources['disk_read_MBps'] + resources['disk_write_MBps']
        
        # Thresholds for different statuses
        if cpu_usage > 90 or memory_usage > 90 or disk_usage > 90:
            return 3  # Critical
        elif cpu_usage > 75 or memory_usage > 75 or disk_usage > 80:
            return 2  # Overloaded
        elif cpu_usage < 10 and memory_usage < 10 and ping_latency < 50:
            return 5  # Idle
        else:
            return 1

    def set_maintenance_mode(self, mode):
        """
        Toggles the server's maintenance mode.
        :param mode: True to enable maintenance mode, False to disable.
        """
        self.maintenance_mode = mode
