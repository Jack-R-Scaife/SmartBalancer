import os
from datetime import datetime

def scan_logs(directory="./logs"):
    """
    Recursively scan the given directory for .log files.
    :param directory: The root directory to scan.
    :return: A list of dictionaries containing log file details.
    """
    log_files = []
    try:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".log"):
                    file_path = os.path.join(root, file)
                    stats = os.stat(file_path)
                    log_files.append({
                        "name": file,
                        "path": file_path,
                        "size": stats.st_size,
                        "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                    })
    except Exception as e:
        print(f"Error scanning for logs: {e}")
    return log_files
