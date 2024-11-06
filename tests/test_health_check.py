import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.health_check import HealthCheck

class TestHealthCheck(unittest.TestCase):

    def test_mock_resource_usage(self):
        health_check = HealthCheck()

        # Mock the resource check function to simulate specific resource usage
        health_check.check_resources = lambda: {'cpu': 50, 'memory': 40, 'disk': 50}

        # Mock ping latency to avoid actual pinging
        health_check.check_ping = lambda ip: 500  # Mock low latency

        # Run status determination
        status = health_check.determine_status('127.0.0.1')

        # Output the mocked resource usage and status
        resources = health_check.check_resources()
        print(f"Resource usage:\nCPU: {resources['cpu']}%, Memory: {resources['memory']}%, Disk: {resources['disk']}%")
        print(f"The current status of this device is: {status}")

        # Assertions to ensure correctness
        self.assertEqual(status, 'Overloaded')  # Since CPU is 85%, memory 75%, the status should be 'Overloaded'


if __name__ == '__main__':
    unittest.main()
