import os
import gzip
from datetime import datetime

def store_agent_logs(agent_ip, logs):
    """
    Store agent logs on the load balancer by compressing them into the root logs folder.
    The agent's IP is used as a prefix for the file name.
    """
    # Define the destination directory (root logs folder)
    logs_dir = "./logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a unique log filename that starts with the agent IP.
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{agent_ip}_{current_time}.log.gz"
    log_path = os.path.join(logs_dir, filename)
    
    # keep only the latest 7 files per agent.
    existing_logs = sorted([
        f for f in os.listdir(logs_dir)
        if f.startswith(agent_ip + "_") and f.endswith(".gz")
    ])
    while len(existing_logs) > 7:
        os.remove(os.path.join(logs_dir, existing_logs.pop(0)))
    
    # Write the logs in compressed mode.
    with gzip.open(log_path, 'wt') as f:
        for log in logs.get('logs', []):
            f.write(f"{log.get('content', '')}\n")

def scan_logs(directory="./logs"):
    """
    Scan the root logs folder and group files into:
      - load_balancer: files that do not start with an IP address.
      - Each agent IP: files whose filenames start with that agent IP.
    """
    log_structure = {}
    try:
        # Initialize separate lists for load balancer logs and agent logs.
        lb_logs = []
        agent_logs = {}

        # Iterate over all files in the logs directory.
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path):
                # Determine the file's modification time in UK format.
                stats = os.stat(full_path)
                modified = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                
                # Check if filename follows the pattern agentIP_timestamp.log.gz
                # Split the filename at the underscore.
                parts = entry.split("_", 1)
                if len(parts) == 2 and parts[0].replace(".", "").isdigit():
                    # Treat this as an agent log.
                    ip = parts[0]
                    agent_logs.setdefault(ip, []).append({
                        "name": entry,
                        "path": full_path,
                        "size": stats.st_size,
                        "modified": modified
                    })
                else:
                    # Otherwise, it is assumed to be a load balancer log.
                    lb_logs.append({
                        "name": entry,
                        "path": full_path,
                        "size": stats.st_size,
                        "modified": modified
                    })
        if lb_logs:
            log_structure["load_balancer"] = lb_logs
        # Merge all agent logs into the log structure.
        log_structure.update(agent_logs)

    except Exception as e:
        print(f"Error scanning logs: {e}")
    return log_structure