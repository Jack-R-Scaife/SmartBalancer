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

def get_log_content(log_path):
    """
    Fetches the content of a specific log file.
    """
    try:
        if not os.path.exists(log_path):
            return {"status": "error", "message": "Log file not found."}, 404

        # Open the file and ensure the content is properly decoded
        with open(log_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace problematic escape sequences for rendering
        processed_content = content.replace('\\', '')

        return {"status": "success", "content": processed_content}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500