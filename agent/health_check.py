import psutil
import subprocess
import random
from resource_monitor import ResourceMonitor

class HealthCheck:
    """
    Performs health checks on the server and determines its status.
    """

    def __init__(self, cpu_thresholds=None, memory_thresholds=None, disk_thresholds=None):
        self.resource_monitor = ResourceMonitor()  # Initialize the ResourceMonitor
        self.maintenance_mode = False  # This could be toggled by user commands
        
        # Revised thresholds for determining health status
        self.cpu_thresholds = cpu_thresholds or {'overloaded': 85, 'idle': 20}
        self.memory_thresholds = memory_thresholds or {'overloaded': 85, 'idle': 20}
        self.disk_thresholds = disk_thresholds or {'overloaded': 85, 'idle': 20}

    def check_ping(self, ip_address):
        """
        Check the server's network latency by pinging the load balancer.
        :param ip_address: The IP address of the load balancer to ping.
        :return: Ping latency in milliseconds, or -1 if unreachable.
        """
        try:
            # Determine platform-specific ping command
            ping_command = ['ping', '-n', '1', ip_address] if psutil.WINDOWS else ['ping', '-c', '1', ip_address]
            result = subprocess.run(ping_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                # Extract latency from the output
                output = result.stdout.decode('utf-8')
                latency = float(output.split('time=')[1].split('ms')[0].strip())
                return latency
            else:
                print(f"Ping failed: {result.stderr.decode('utf-8')}")
                return -1
        except Exception as e:
            print(f"Error pinging {ip_address}: {e}")
            return -1

    def check_resources(self):
        """
        Checks the server's resource usage.
        :return: A dictionary containing CPU, memory, and disk usage percentages.
        """
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent  # Overall disk usage percentage

            return {
                'cpu': cpu_usage,
                'memory': memory_usage,
                'disk': disk_usage
            }
        except Exception as e:
            print(f"Error checking resources: {e}")
            return {'cpu': -1, 'memory': -1, 'disk': -1}

    def determine_status(self, ip_address):
        """
        Determine the health status of the server based on resource usage, ping, and maintenance mode.
        """
        if not ip_address:
            print("Error: No IP address provided for health check.")
            return 4
        if self.maintenance_mode:
            return 6  # Maintenance

        # Check the ping latency
        ping_latency = self.check_ping(ip_address)
        print(f"Ping latency to {ip_address}: {ping_latency} ms")
        if ping_latency == -1:
            return 4  # Down

        # Check resource usage
        resources = self.check_resources()
        cpu_usage = resources['cpu']
        memory_usage = resources['memory']
        disk_usage = resources['disk']

        # Log resource values for debugging
        print(f"Resource Usage - CPU: {cpu_usage}%, Memory: {memory_usage}%, Disk: {disk_usage}%")

        # Determine status based on thresholds
        if cpu_usage >= self.cpu_thresholds['overloaded'] or \
           memory_usage >= self.memory_thresholds['overloaded'] or \
           disk_usage >= self.disk_thresholds['overloaded']:
            print("Status: Overloaded")
            return 2  # Overloaded
        elif cpu_usage <= self.cpu_thresholds['idle'] and \
             memory_usage <= self.memory_thresholds['idle'] and \
             ping_latency < 50:
            print("Status: Idle")
            return 5  # Idle
        else:
            print("Status: Healthy")
            return 1  # Healthy

    def set_maintenance_mode(self, mode):
        """
        Toggles the server's maintenance mode.
        :param mode: True to enable maintenance mode, False to disable.
        """
        self.maintenance_mode = mode
        print(f"Maintenance mode set to {'enabled' if mode else 'disabled'}")
