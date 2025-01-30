import os
import logging
from logging.handlers import RotatingFileHandler

LOGS_DIR = "./logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Define a log record factory to add defaults
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
    handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, log_file),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        delay=True
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s - Server: %(server)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

# Pre-configured loggers for different modules
main_logger = setup_logger("agent_monitor", "agent_monitor.log", level=logging.DEBUG) 
traffic_logger = setup_logger("traffic", "traffic.log")
dynamic_logger = setup_logger("dynamic_algorithms", "dynamic_algorithms.log")
api_logger = setup_logger("api", "api.log")
