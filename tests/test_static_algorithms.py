import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.static_algorithms import StaticAlgorithms

# Create an instance of the StaticAlgorithms class
lb = StaticAlgorithms()

# Add some dummy servers
lb.known_agents = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]

# Test Round Robin
print("Testing Round Robin:")
for _ in range(6):  # Call round_robin 6 times to cycle through the servers
    print(lb.round_robin())

# Test Weighted Round Robin
print("\nTesting Weighted Round Robin:")
weights = {"192.168.1.1": 2, "192.168.1.2": 1, "192.168.1.3": 3}
lb.set_weights(weights)
for _ in range(12):  # Call weighted_round_robin 12 times
    print(lb.weighted_round_robin())
