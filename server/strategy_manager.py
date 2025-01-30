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
    def activate_strategy(strategy_name,group_id,ai_enabled=False):
        """
        Activates a strategy and optionally enables AI enhancements.
        """
        strategy = Strategy.query.filter_by(name=strategy_name).first()
        if not strategy:
            raise ValueError(f"Invalid strategy name: {strategy_name}")

        load_balancer_setting = LoadBalancerSetting.query.first()
        if load_balancer_setting and load_balancer_setting.active_strategy_id == strategy.strategy_id:
            return f"{strategy_name} strategy is already active."

        if not load_balancer_setting:
            load_balancer_setting = LoadBalancerSetting(
                failover_priority="",
                predictive_enabled=ai_enabled,
                active_strategy_id=strategy.strategy_id
            )
            db.session.add(load_balancer_setting)
        else:
            load_balancer_setting.active_strategy_id = strategy.strategy_id
            load_balancer_setting.predictive_enabled = ai_enabled

        db.session.commit()

        # Apply strategy
        if strategy_name == "Least Connections":
            StrategyManager.dynamic_algorithms.least_connections()
        elif strategy_name == "Least Response Time":
            StrategyManager.dynamic_algorithms.least_response_time()
        elif strategy_name == "Resource-Based":
            StrategyManager.dynamic_algorithms.resource_based()
        elif strategy_name == "Custom":
            return "Custom strategy setup required"
        else:
            raise ValueError(f"Unsupported strategy: {strategy_name}")

        if ai_enabled:
            StrategyManager.dynamic_algorithms.toggle_ai(True)

        load_balancer = LoadBalancer()
        load_balancer.set_active_strategy(strategy_name, group_id)
        return f"{strategy_name} strategy activated successfully with AI enhancement: {ai_enabled}."
    
    @staticmethod
    def apply_strategy_to_group(strategy_name, group_id, ai_enabled=False):
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
                load_balancer_setting = LoadBalancerSetting(
                    failover_priority="",
                    predictive_enabled=ai_enabled,
                    active_strategy_id=strategy.strategy_id,
                    group_id=group_id
                )
                db.session.add(load_balancer_setting)
            else:
                #  Actually update the strategy in the database**
                load_balancer_setting.active_strategy_id = strategy.strategy_id
                load_balancer_setting.predictive_enabled = ai_enabled
                load_balancer_setting.updated_at = db.func.current_timestamp()

            db.session.commit()

            #  Ensure Strategy is Active in LoadBalancer**
            load_balancer = LoadBalancer()
            load_balancer.set_active_strategy(strategy_name, group_id)

            return {"status": "success", "message": f"Strategy {strategy_name} applied to group {group_id} successfully."}

        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}
        
    @staticmethod
    def apply_multiple_strategies_to_group(strategy_names, group_id, ai_enabled=False):
        """
        Applies multiple strategies to a server group.
        - Priority 1 strategy is set as active.
        - Other strategies are stored as failover priority.
        """
        try:
            if not strategy_names:
                raise ValueError("At least one strategy must be provided.")

            # ✅ Fetch strategies from DB
            strategies = Strategy.query.filter(Strategy.name.in_(strategy_names)).all()
            if not strategies:
                raise ValueError(f"Invalid strategies: {strategy_names}")

            # ✅ Ensure Priority 1 is Active
            priority_1_strategy = next((s for s in strategies if s.name == strategy_names[0]), None)
            failover_strategies = [s.name for s in strategies if s.name != strategy_names[0]]

            if not priority_1_strategy:
                raise ValueError(f"Priority 1 strategy not found: {strategy_names[0]}")

            # ✅ Fetch group
            group = ServerGroup.query.get(group_id)
            if not group:
                raise ValueError(f"Invalid group ID: {group_id}")

            # ✅ Fetch or create LoadBalancerSetting
            load_balancer_setting = LoadBalancerSetting.query.filter_by(group_id=group_id).first()
            if not load_balancer_setting:
                load_balancer_setting = LoadBalancerSetting(
                    failover_priority=", ".join(failover_strategies) if failover_strategies else None,  # Store only failover strategies
                    predictive_enabled=ai_enabled,
                    active_strategy_id=priority_1_strategy.strategy_id,  # Set Priority 1 strategy as active
                    group_id=group_id
                )
                db.session.add(load_balancer_setting)
            else:
                # ✅ Update existing settings
                load_balancer_setting.active_strategy_id = priority_1_strategy.strategy_id
                load_balancer_setting.failover_priority = ", ".join(failover_strategies) if failover_strategies else None  # Failover only
                load_balancer_setting.predictive_enabled = ai_enabled
                load_balancer_setting.updated_at = db.func.current_timestamp()

            db.session.commit()

            # ✅ Apply strategy to LoadBalancer
            load_balancer = LoadBalancer()
            load_balancer.set_active_strategy(priority_1_strategy.name, group_id)

            return {
                "status": "success",
                "message": f"Active: {priority_1_strategy.name}, Failover: {failover_strategies if failover_strategies else 'None'}"
            }

        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}


