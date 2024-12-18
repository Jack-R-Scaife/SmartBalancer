from app.models import Strategy, LoadBalancerSetting
from server.static_algorithms import StaticAlgorithms
from server.dynamic_algorithms import DynamicAlgorithms
from app import db

class StrategyManager:
    static_algorithms = StaticAlgorithms()
    dynamic_algorithms = DynamicAlgorithms()
    @staticmethod
    def activate_strategy(strategy_name):
        """
        Activates the specified load balancing strategy in the backend.
        """
        # Fetch the strategy from the database
        strategy = Strategy.query.filter_by(name=strategy_name).first()
        if not strategy:
            raise ValueError(f"Invalid strategy name: {strategy_name}")

        # Check if the strategy is already active
        load_balancer_setting = LoadBalancerSetting.query.first()
        if load_balancer_setting and load_balancer_setting.active_strategy_id == strategy.strategy_id:
            return f"{strategy_name} strategy is already active."

        # Update the active strategy in LoadBalancerSetting
        if not load_balancer_setting:
            # Create a new load balancer setting if it doesn't exist
            load_balancer_setting = LoadBalancerSetting(
                failover_priority="",
                predictive_enabled=False,
                active_strategy_id=strategy.strategy_id
            )
            db.session.add(load_balancer_setting)
        else:
            load_balancer_setting.active_strategy_id = strategy.strategy_id

        db.session.commit()
    
        # Trigger the appropriate logic in StaticAlgorithms
        if strategy_name == "Round Robin":
            StrategyManager.static_algorithms.round_robin()
        elif strategy_name == "Weighted Round Robin":
            StrategyManager.static_algorithms.set_weights({})
        elif strategy_name == "Least Connections":
            StrategyManager.dynamic_algorithms.least_connections()
        elif strategy_name == "Least Response Time":
            StrategyManager.dynamic_algorithms.response_time()
        elif strategy_name == "Resource-Based":
            StrategyManager.dynamic_algorithms.resource_based()
        else:
            print(f"[ERROR] Unsupported strategy: {strategy_name}")
            raise ValueError(f"Unsupported strategy: {strategy_name}")

        return f"{strategy_name} strategy activated successfully."