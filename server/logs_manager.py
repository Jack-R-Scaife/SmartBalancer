import os
import gzip
from datetime import datetime

def store_agent_logs(agent_ip, logs):
    """Store agent logs in agent-specific directory with rotation"""
    log_dir = os.path.join("./logs", f"agent_{agent_ip}")
    os.makedirs(log_dir, exist_ok=True)
    
    # Store logs in compressed format
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(log_dir, f"{current_date}.log.gz")
    
    # Keep only last 7 days of logs
    existing_logs = sorted([f for f in os.listdir(log_dir) if f.endswith(".gz")])
    while len(existing_logs) > 7:
        os.remove(os.path.join(log_dir, existing_logs.pop(0)))

    # Write new logs in compressed format
    with gzip.open(log_path, 'at') as f:
        for log in logs.get('logs', []):
            f.write(f"{log.get('content', '')}\n")

def scan_logs(directory="./logs"):
    """Scan for logs organized by agent IP including load balancer logs"""
    log_structure = {}
    
    try:
        # Process all files in the root of the logs directory as load balancer logs.
        lb_logs = []
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path) and entry.endswith(".log"):
                stats = os.stat(full_path)
                modified = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                lb_logs.append({
                    "name": entry,
                    "path": full_path,
                    "size": stats.st_size,
                    "modified": modified  # UK format
                })
        if lb_logs:
            log_structure["load_balancer"] = lb_logs

        # Process directories that start with "agent_" as agent logs.
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isdir(full_path) and entry.startswith("agent_"):
                ip = entry[6:]
                log_structure[ip] = []
                for log_file in os.listdir(full_path):
                    if log_file.endswith(".log") or log_file.endswith(".gz"):
                        file_path = os.path.join(full_path, log_file)
                        stats = os.stat(file_path)
                        modified = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                        log_structure[ip].append({
                            "name": log_file,
                            "path": file_path,
                            "size": stats.st_size,
                            "modified": modified  # UK format
                        })
    except Exception as e:
        print(f"Error scanning logs: {e}")
    return log_structure