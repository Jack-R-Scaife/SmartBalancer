import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.agent_monitor import LoadBalancer

def test_round_robin():
    # Initialize LoadBalancer and set known agents
    load_balancer = LoadBalancer()
    load_balancer.known_agents = ["192.168.1.101", "192.168.1.102", "192.168.1.103"]  # Simulated agents
    load_balancer.set_active_strategy("Round Robin")

    # Simulate multiple requests and log the selected agents
    print("Testing Round Robin Strategy:")
    selected_agents = []
    for i in range(10):  # Simulate 10 requests
        selected_agent = load_balancer.execute_strategy()
        selected_agents.append(selected_agent)
        print(f"Request {i+1}: Routed to {selected_agent}")

    # Verify the round-robin sequence
    expected_sequence = load_balancer.known_agents * (len(selected_agents) // len(load_balancer.known_agents))
    expected_sequence += load_balancer.known_agents[:len(selected_agents) % len(load_balancer.known_agents)]

    print("\nExpected Sequence:", expected_sequence)
    print("Selected Agents:", selected_agents)

    assert selected_agents == expected_sequence, "Round Robin strategy is not working as expected."
    print("\nTest passed: Round Robin strategy is working correctly.")

if __name__ == "__main__":
    test_round_robin()
