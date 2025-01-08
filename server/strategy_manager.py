from app.models import Strategy, LoadBalancerSetting
from server.static_algorithms import StaticAlgorithms
from server.dynamic_algorithms import DynamicAlgorithms
from server.servergroups import ServerGroup
from server.agent_monitor import LoadBalancer
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

        load_balancer = LoadBalancer()
        load_balancer.set_active_strategy(strategy_name)
        return f"{strategy_name} strategy activated successfully."
    
    def apply_strategy_to_group(strategy_name, group_id):
        """
        Applies a load balancing strategy to a specific server group and saves it in the database.
        """
        try:
            # Fetch the strategy
            strategy = Strategy.query.filter_by(name=strategy_name).first()
            if not strategy:
                raise ValueError(f"Invalid strategy name: {strategy_name}")

            # Fetch the group
            group = ServerGroup.query.get(group_id)
            if not group:
                raise ValueError(f"Invalid group ID: {group_id}")

            # Update or create the LoadBalancerSetting for the group
            load_balancer_setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
            if not load_balancer_setting:
                # Create a new LoadBalancerSetting if one doesn't exist for this group
                load_balancer_setting = LoadBalancerSetting(
                    failover_priority="",
                    predictive_enabled=False,
                    active_strategy_id=strategy.strategy_id,
                    group_id=group_id  # Ensure group_id is explicitly set
                )
                db.session.add(load_balancer_setting)
            else:
                # Update existing LoadBalancerSetting
                load_balancer_setting.active_strategy_id = strategy.strategy_id
                load_balancer_setting.updated_at = db.func.current_timestamp()

            db.session.commit()

            load_balancer = LoadBalancer()
            load_balancer.set_active_strategy(strategy_name)
            return {"status": "success", "message": f"Strategy {strategy_name} applied to group {group_id} successfully."}

        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}