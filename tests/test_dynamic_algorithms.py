import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.dynamic_algorithms import DynamicAlgorithms

# Create an instance of DynamicAlgorithms
lb = DynamicAlgorithms()

# Add dummy servers and data
lb.known_agents = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
lb.connection_counts = {"192.168.1.1": 5, "192.168.1.2": 2, "192.168.1.3": 10}
lb.response_times = {"192.168.1.1": 100, "192.168.1.2": 50, "192.168.1.3": 70}
lb.resources = {"192.168.1.1": 30, "192.168.1.2": 70, "192.168.1.3": 50}

# Test Least Connections
print("Least Connections:", lb.least_connections())  # Expected: 192.168.1.2

# Test Response Time
print("Response Time:", lb.response_time())  # Expected: 192.168.1.2

# Test Resource-Based
print("Resource-Based:", lb.resource_based())  # Expected: 192.168.1.2