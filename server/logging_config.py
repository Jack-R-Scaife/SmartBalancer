import os
import logging
import re
from logging.handlers import RotatingFileHandler

# Define the logs directory
LOGS_DIR = "./logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Log record factory to add defaults
old_factory = logging.getLogRecordFactory()

def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    if not hasattr(record, 'server'):
        record.server = "N/A"
    return record

logging.setLogRecordFactory(record_factory)

class CustomRotatingHandler(RotatingFileHandler):
    def __init__(self, filename, **kwargs):
        # Ensure filename ends with .log
        if not filename.endswith('.log'):
            filename += '.log'
        super().__init__(filename, **kwargs)

    def doRollover(self):
        if self.backupCount > 0:
            log_dir = os.path.dirname(self.baseFilename)
            pattern = re.compile(rf"^{re.escape(os.path.basename(self.baseFilename))}\.(\d+)\.log$")
            backups = []

            for f in os.listdir(log_dir):
                match = pattern.match(f)
                if match:
                    backups.append(int(match.group(1)))

            for num in sorted(backups, reverse=True)[self.backupCount:]:
                os.remove(os.path.join(log_dir, f"{os.path.basename(self.baseFilename)}.{num}.log"))

        super().doRollover()

def custom_namer(default_name):
    """
    Proper naming format: filename.number.log
    """
    base = os.path.basename(default_name)
    dir_name = os.path.dirname(default_name)
    
    # Extract base name and rotation number
    match = re.match(r"(.*?)\.(\d+)$", base)
    if match:
        base_name, num = match.groups()
        return os.path.join(dir_name, f"{base_name}.{num}.log")
    return os.path.join(dir_name, f"{base}.log")

def setup_logger(name, log_file, level=logging.DEBUG):
    # Ensure log_file ends with .log
    if not log_file.endswith('.log'):
        log_file += '.log'
    
    log_path = os.path.join(LOGS_DIR, log_file)
    
    handler = CustomRotatingHandler(
        log_path,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,  # Keep 3 backups
        encoding='utf-8',
        delay=True
    )
    handler.namer = custom_namer
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s - Server: %(server)s'
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

# Pre-configured loggers (now with consistent .log extension)
main_logger = setup_logger("agent_monitor", "agent_monitor.log")
traffic_logger = setup_logger("traffic", "traffic.log")
dynamic_logger = setup_logger("dynamic_algorithms", "dynamic_algorithms.log")
api_logger = setup_logger("api", "api.log")
round_robin_logger = setup_logger("round_robin_debug", "round_robin_debug.log")
weights_logger = setup_logger("weights_debug", "weights_debug.log")
enhanced_strategy_logger = setup_logger("enhanced_strategy", "enhanced_strategy.log")
non_enhanced_strategy_logger = setup_logger("non_enhanced_strategy", "non_enhanced_strategy.log")