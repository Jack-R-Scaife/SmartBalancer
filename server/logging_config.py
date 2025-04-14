import os
import logging
from logging.handlers import RotatingFileHandler

# Define the logs directory
LOGS_DIR = "./logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Log record factory to add defaults
old_factory = logging.getLogRecordFactory()

def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    # Set default for "server" field if not provided
    if not hasattr(record, 'server'):
        record.server = "N/A"
    return record

# Apply the custom factory globally
logging.setLogRecordFactory(record_factory)

def setup_logger(name, log_file, level=logging.DEBUG):
    # Create the log file path with the logs directory
    log_file_path = os.path.join(LOGS_DIR, log_file)
    
    # Create a RotatingFileHandler
    handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,  # Keep up to 3 backup files
        encoding='utf-8',
        delay=True
    )
    
    # Define a custom namer for the log files
    def custom_namer(default_name):
        base_name = os.path.splitext(default_name)[0]  # Remove .log
        if base_name[-1].isdigit():  # If already has number
            return default_name
        count = 1
        while os.path.exists(f"{base_name}.{count}.log"):
            count += 1
        return f"{base_name}.{count}.log"
    
    # Assign the custom namer
    handler.namer = custom_namer
    
    # Define the log format
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s - Server: %(server)s'
    )
    handler.setFormatter(formatter)

    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

# Pre-configured loggers for different modules
main_logger = setup_logger("agent_monitor", "agent_monitor.log", level=logging.DEBUG)
traffic_logger = setup_logger("traffic", "traffic.log")
dynamic_logger = setup_logger("dynamic_algorithms", "dynamic_algorithms.log")
api_logger = setup_logger("api", "api.log")
round_robin_logger = setup_logger("round_robin_debug", "round_robin_debug.log", level=logging.DEBUG)
weights_logger = setup_logger("weights_debug", "weights_debug.log", level=logging.DEBUG)
enhanced_strategy_logger = setup_logger("enhanced_strategy", "enhanced_strategy.log")
non_enhanced_strategy_logger = setup_logger("non_enhanced_strategy", "non_enhanced_strategy.log")
