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
        # Add load balancer logs first
        lb_logs = []
        for file in os.listdir(directory):
            if file.endswith(".log") and not file.startswith("agent_"):
                full_path = os.path.join(directory, file)
                stats = os.stat(full_path)
                modified = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                lb_logs.append({
                    "name": file,
                    "path": full_path,
                    "size": stats.st_size,
                    "modified": modified  # UK format
                })
        if lb_logs:
            log_structure["load_balancer"] = lb_logs

        # Add agent logs
        for agent_dir in os.listdir(directory):
            if agent_dir.startswith("agent_"):
                ip = agent_dir[6:]
                log_structure[ip] = []
                agent_path = os.path.join(directory, agent_dir)
                for log_file in os.listdir(agent_path):
                    if log_file.endswith(".log") or log_file.endswith(".gz"):
                        full_path = os.path.join(agent_path, log_file)
                        stats = os.stat(full_path)
                        modified = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                        log_structure[ip].append({
                            "name": log_file,
                            "path": full_path,
                            "size": stats.st_size,
                            "modified": modified  # UK format
                        })
    except Exception as e:
        print(f"Error scanning logs: {e}")
    return log_structure