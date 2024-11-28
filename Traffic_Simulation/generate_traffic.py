import logging
import threading
import time
import requests, traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Initialize Flask app and logging
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename="generate_traffic.log",  # Dedicated log file
    level=logging.DEBUG,  # Log DEBUG and above
    format="%(asctime)s - %(levelname)s - %(message)s",
)

@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

traffic_logger = logging.getLogger("traffic")
traffic_handler = logging.FileHandler("traffic.log")
traffic_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
traffic_handler.setFormatter(traffic_formatter)
traffic_logger.addHandler(traffic_handler)
traffic_logger.setLevel(logging.INFO)

def generate_traffic(url, req_type, rate, duration):
    end_time = time.time() + duration
    traffic_logger.info(f"Starting traffic simulation: {req_type.upper()} {url} at {rate} req/s for {duration} seconds.")
    while time.time() < end_time:
        for _ in range(rate):
            try:
                if req_type.lower() == 'get':
                    requests.get(url)
                elif req_type.lower() == 'post':
                    requests.post(url, data={'key': 'value'})
                traffic_logger.debug(f"Sent {req_type.upper()} request to {url}")
            except Exception as e:
                traffic_logger.error(f"Error sending {req_type.upper()} request to {url}: {str(e)}")
        time.sleep(1)
    traffic_logger.info("Traffic simulation complete.")

@app.route('/simulate_traffic', methods=['POST'])
def simulate_traffic():
    try:
        data = request.json
        config = data.get('config', {})
        traffic_logger.info(f"Received traffic simulation request: {config}")

        # Forward the request to the load balancer
        load_balancer_url = "http://127.0.0.1:5000/api/simulate_traffic"  # Replace with actual IP
        response = requests.post(load_balancer_url, json=config)

        if response.status_code == 200:
            return jsonify({"message": "Traffic simulation request forwarded to load balancer"}), 200
        else:
            return jsonify({"error": f"Error forwarding request: {response.text}"}), response.status_code
    except Exception as e:
        traffic_logger.error(f"Error in simulate_traffic: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)