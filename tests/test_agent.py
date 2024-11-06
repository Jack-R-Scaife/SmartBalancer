import unittest
from agent.agent import Agent

class TestAgent(unittest.TestCase):
    
    def test_agent_start_stop(self):
        """
        Test that the agent can start and stop correctly.
        """
        agent = Agent(server_id="test-server")
        agent.start()
        self.assertTrue(agent.is_running)

        agent.stop()
        self.assertFalse(agent.is_running)


if __name__ == '__main__':
    unittest.main()
