from app import db
from app.models import Strategy, LoadBalancerSetting
from server.static_algorithms import StaticAlgorithms
from server.dynamic_algorithms import DynamicAlgorithms
from server.servergroups import ServerGroup
from server.agent_monitor import LoadBalancer

class StrategyManager:
    static_algorithms = StaticAlgorithms()
    dynamic_algorithms = DynamicAlgorithms()

    @staticmethod
    def activate_strategy(strategy_name, group_id, ai_enabled=False):
        """
        Activate a single strategy and update its setting in the database.
        """
        strategy = Strategy.query.filter_by(name=strategy_name).first()
        if not strategy:
            raise ValueError(f"Invalid strategy name: {strategy_name}")

        load_balancer_setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
        if load_balancer_setting and load_balancer_setting.active_strategy_id == strategy.strategy_id:
            return f"{strategy_name} strategy is already active."

        if not load_balancer_setting:
            load_balancer_setting = LoadBalancerSetting(
                failover_priority="",
                predictive_enabled=ai_enabled,
                active_strategy_id=strategy.strategy_id,
                group_id=group_id
            )
            db.session.add(load_balancer_setting)
        else:
            load_balancer_setting.active_strategy_id = strategy.strategy_id
            load_balancer_setting.predictive_enabled = ai_enabled

        db.session.commit()

        # Execute the strategy logic
        if strategy_name == "Least Connections":
            StrategyManager.dynamic_algorithms.least_connections()
        elif strategy_name == "Least Response Time":
            StrategyManager.dynamic_algorithms.least_response_time()
        elif strategy_name == "Resource-Based":
            StrategyManager.dynamic_algorithms.resource_based()
        elif strategy_name == "Custom":
            # Insert custom strategy logic here as needed.
            return "Custom strategy setup required"
        else:
            raise ValueError(f"Unsupported strategy: {strategy_name}")

        if ai_enabled:
            StrategyManager.dynamic_algorithms.ai_enabled = True
            StrategyManager.static_algorithms.ai_enabled = True
        load_balancer = LoadBalancer()
        load_balancer.set_active_strategy(strategy_name, group_id)
        return f"{strategy_name} strategy activated successfully with AI enhancement: {ai_enabled}."

    @staticmethod
    def apply_strategy_to_group(strategy_name, group_id, ai_enabled=False):
        """
        Apply a single strategy to a specific server group.
        """
        try:
            strategy = Strategy.query.filter_by(name=strategy_name).first()
            if not strategy:
                raise ValueError(f"Invalid strategy name: {strategy_name}")

            group = ServerGroup.query.get(group_id)
            if not group:
                raise ValueError(f"Invalid group ID: {group_id}")

            load_balancer_setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
            if not load_balancer_setting:
                load_balancer_setting = LoadBalancerSetting(
                    failover_priority="",
                    predictive_enabled=ai_enabled,
                    active_strategy_id=strategy.strategy_id,
                    group_id=group_id
                )
                db.session.add(load_balancer_setting)
            else:
                load_balancer_setting.active_strategy_id = strategy.strategy_id
                load_balancer_setting.predictive_enabled = ai_enabled
                load_balancer_setting.updated_at = db.func.current_timestamp()

            db.session.commit()

            load_balancer = LoadBalancer()
            load_balancer.set_active_strategy(strategy_name, group_id, ai_enabled=ai_enabled)

            return {"status": "success", "message": f"Strategy {strategy_name} applied to group {group_id} successfully."}
        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}

    @staticmethod
    def apply_multiple_strategies_to_group(strategy_names, group_id, ai_enabled=False):
        """
        Apply multiple strategies to a server group:
         - The first strategy in the list is set as active.
         - Additional strategies are stored as failover priorities.
        """
        try:
            if not strategy_names:
                raise ValueError("At least one strategy must be provided.")

            # Normalize strategy names to match database entries
            name_corrections = {
                "RoundRobin": "Round Robin",
                "WeightedRoundRobin": "Weighted Round Robin",
                "LeastConnections": "Least Connections",
                "LeastResponseTime": "Least Response Time",
                "Resource-Based": "Resource-Based",
                "Custom": "Custom"
            }
            strategy_names = [name_corrections.get(s, s) for s in strategy_names]

            strategies = Strategy.query.filter(Strategy.name.in_(strategy_names)).all()
            if not strategies:
                raise ValueError(f"Invalid strategies: {strategy_names}")

            priority_1_strategy = next((s for s in strategies if s.name == strategy_names[0]), None)
            failover_strategies = [s.name for s in strategies if s.name != strategy_names[0]]

            if not priority_1_strategy:
                raise ValueError(f"Priority 1 strategy not found: {strategy_names[0]}")

            group = ServerGroup.query.get(group_id)
            if not group:
                raise ValueError(f"Invalid group ID: {group_id}")

            failover_priority_str = ",".join(failover_strategies)
            load_balancer_setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
            if not load_balancer_setting:
                load_balancer_setting = LoadBalancerSetting(
                    failover_priority=failover_priority_str,
                    predictive_enabled=ai_enabled,
                    active_strategy_id=priority_1_strategy.strategy_id,
                    group_id=group_id
                )
                db.session.add(load_balancer_setting)
            else:
                load_balancer_setting.active_strategy_id = priority_1_strategy.strategy_id
                load_balancer_setting.predictive_enabled = ai_enabled
                load_balancer_setting.failover_priority = failover_priority_str
                load_balancer_setting.updated_at = db.func.current_timestamp()

            db.session.commit()
            load_balancer = LoadBalancer()
            load_balancer.set_active_strategy(priority_1_strategy.name, group_id)

            return {"status": "success", "message": f"Strategy {priority_1_strategy.name} applied to group {group_id} successfully with failover: {failover_priority_str}."}
        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}
