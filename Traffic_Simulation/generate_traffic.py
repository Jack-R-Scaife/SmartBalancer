import logging
import threading
import time
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import random

# Initialize Flask app and logging
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename="generate_traffic.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

traffic_logger = logging.getLogger("traffic")
traffic_handler = logging.FileHandler("traffic.log")
traffic_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
traffic_handler.setFormatter(traffic_formatter)
traffic_logger.addHandler(traffic_handler)
traffic_logger.setLevel(logging.INFO)

# Global state for traffic simulation
PROTOCOLS = ["http", "https", "tcp", "udp"]
COUNTRIES = ["United States", "Germany", "China", "Nigeria", "Brazil"]
DIRECTIONS = ["incoming", "outgoing"]
traffic_thread = None
traffic_running = False
traffic_metrics = []
events = []
url = "http://127.0.0.1:5000/api/simulate_traffic"  # Hardcoded load balancer endpoint

# Variables to dynamically adjust traffic
current_baseline_rate = 10  # Default to "low"
current_scenario = "baseline_low"
traffic_start_time = None

@app.route('/')
def serve_index():
    """
    Serve the index.html file for the frontend.
    """
    return send_from_directory('frontend', 'index.html')

@app.route('/add_scaling_event', methods=['POST'])
def add_scaling_event():
    """
    Dynamically add a scaling event during traffic simulation.
    """
    global events, traffic_running, traffic_start_time
    try:
        event = request.json
        if "scale" not in event or "start_time" not in event or "duration" not in event:
            return jsonify({"error": "Invalid event data. Must have scale, start_time, duration."}), 400

        event_scale = float(event["scale"])
        event_start = float(event["start_time"])
        event_duration = float(event["duration"])

        if traffic_running and traffic_start_time is not None:
            current_sim_time = time.time() - traffic_start_time
            event_start = current_sim_time + event_start

        events.append({
            "scale": event_scale,
            "start_time": event_start,
            "duration": event_duration,
        })
        traffic_logger.info(f"Added scaling event: {event}")
        return jsonify({"message": "Scaling event added."}), 200

    except Exception as e:
        traffic_logger.error(f"Error adding scaling event: {e}")
        return jsonify({"error": "Failed to add scaling event."}), 500

@app.route('/start_traffic', methods=['POST'])
def start_traffic():
    """
    Start or dynamically update traffic simulation.
    """
    global traffic_running, current_baseline_rate, current_scenario

    data = request.json
    baseline = data.get("baseline", "low")  # "low", "medium", "high"
    scenario = data.get("scenario", "baseline_low")

    # Map baseline to requests per second
    new_baseline_rate = {"low": 10, "medium": 50, "high": 100}.get(baseline, 10)

    if traffic_running:
        # Update the baseline rate and scenario dynamically
        current_baseline_rate = new_baseline_rate
        current_scenario = scenario
        traffic_logger.info(f"Updated traffic: baseline={baseline}, scenario={scenario}")
        return jsonify({"message": "Traffic simulation updated."}), 200
    else:
        # Start the traffic simulation
        global traffic_thread, traffic_start_time
        traffic_start_time = time.time()
        traffic_running = True
        current_baseline_rate = new_baseline_rate
        current_scenario = scenario

        traffic_thread = threading.Thread(
            target=simulate_traffic,
            args=(traffic_start_time,)
        )
        traffic_thread.start()

        return jsonify({"message": "Traffic simulation started."}), 200

@app.route('/stop_traffic', methods=['POST'])
def stop_traffic():
    """
    Stop the ongoing traffic simulation.
    """
    global traffic_running
    traffic_running = False
    traffic_logger.info("Traffic simulation stopped by user.")
    return jsonify({"message": "Traffic simulation stopped."}), 200

@app.route('/traffic_metrics', methods=['GET'])
def get_traffic_metrics():
    """
    Return real-time traffic metrics for chart visualization.
    """
    return jsonify({"metrics": traffic_metrics[-100:]}), 200  # Return the last 100 metrics

def simulate_traffic(start_time):
    """
    Simulate continuous traffic with adjustable baseline and scaling events.
    Each traffic request includes additional fields:
      - protocol: one of "http", "https", "tcp", "udp"
      - port: default port for HTTP/HTTPS or random port for TCP/UDP
      - country: one of the supported countries
      - traffic_direction: "incoming" or "outgoing"
    """
    global traffic_running, traffic_metrics, events, current_baseline_rate, current_scenario

    # Optionally: Filter and combine active events here (see previous examples).
    while traffic_running:
        current_time = time.time() - start_time
        rate = current_baseline_rate

        # Example: combine active events multiplicatively
        active_events = [event for event in events 
                         if event["start_time"] <= current_time < event["start_time"] + event["duration"]]
        if active_events:
            effective_scale = 1.0
            for event in active_events:
                effective_scale *= event["scale"]
            rate = int(current_baseline_rate * effective_scale)

        # (Optional) Remove expired events to prevent buildup.
        events[:] = [event for event in events if current_time < event["start_time"] + event["duration"]]

        # Send "rate" traffic requests with a richer payload
        for _ in range(rate):
            # Select a protocol randomly
            protocol = random.choice(PROTOCOLS)
            # Determine a port: default for HTTP/HTTPS or random for TCP/UDP.
            if protocol == "http":
                port = 80
            elif protocol == "https":
                port = 443
            else:
                port = random.randint(1024, 65535)
            # Choose a country and traffic direction randomly.
            country = random.choice(COUNTRIES)
            traffic_direction = random.choice(DIRECTIONS)

            # Build the payload
            payload = {
                "url": url,                        # the endpoint (or target URL) for the simulated traffic
                "type": protocol.upper(),          # e.g., "HTTP", "HTTPS", "TCP", "UDP"
                "rate": rate,
                "duration": 1,
                "scenario": current_scenario,
                "protocol": protocol,              # added field: protocol
                "port": port,                      # added field: port number
                "country": country,                # added field: country (of origin)
                "traffic_direction": traffic_direction  # added field: incoming or outgoing
            }
            try:
                response = requests.post(url, json=payload)
                traffic_logger.debug(f"Traffic sent: {response.status_code} {response.text} with payload: {payload}")
            except Exception as e:
                traffic_logger.error(f"Error sending traffic: {e}")

        # Log the current rate as a metric (using the current timestamp)
        traffic_metrics.append({"timestamp": time.time(), "rate": rate})
        time.sleep(1)

    traffic_logger.info("Traffic simulation stopped.")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
