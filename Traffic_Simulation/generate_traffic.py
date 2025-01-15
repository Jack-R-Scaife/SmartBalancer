import logging
import threading
import time
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

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
traffic_thread = None
traffic_running = False
traffic_metrics = []
events = []
url = "http://127.0.0.1:5000/api/simulate_traffic"  # Hardcoded load balancer endpoint

# Track the absolute time (time.time()) when traffic started
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
    If traffic is running, offset the user-supplied 'start_time'
    so it becomes (current_sim_time + start_time).
    Treat duration=0 as indefinite.
    """
    global events, traffic_running, traffic_start_time
    try:
        event = request.json
        if "scale" not in event or "start_time" not in event or "duration" not in event:
            return jsonify({"error": "Invalid event data. Must have scale, start_time, duration."}), 400

        # Convert the incoming data to float/int just to be safe
        event_scale = float(event["scale"])
        event_start = float(event["start_time"])
        event_duration = float(event["duration"])

        # If traffic is running, offset the user-specified start_time by the current simulation time
        if traffic_running and traffic_start_time is not None:
            current_sim_time = time.time() - traffic_start_time
            # So that "start_time": 5 means "5 seconds from now"
            event_start = current_sim_time + event_start

        # Update the event dictionary
        # (If you *don't* want indefinite events, remove the logic below for duration=0.)
        event = {
            "scale": event_scale,
            "start_time": event_start,
            "duration": event_duration,
        }

        events.append(event)
        traffic_logger.info(f"Added scaling event: {event}")
        return jsonify({"message": "Scaling event added."}), 200

    except Exception as e:
        traffic_logger.error(f"Error adding scaling event: {e}")
        return jsonify({"error": "Failed to add scaling event."}), 500

@app.route('/start_traffic', methods=['POST'])
def start_traffic():
    """
    Start continuous traffic simulation with the selected baseline
    and any existing network events.
    """
    global traffic_thread, traffic_running, traffic_start_time
    if traffic_running:
        return jsonify({"error": "Traffic simulation is already running"}), 400

    data = request.json
    baseline = data.get("baseline", "low")  # "low", "medium", "high"
    scenario = data.get("scenario", "baseline_low")
    # Map baseline to requests per second
    baseline_rate = {"low": 10, "medium": 50, "high": 100}.get(baseline, 10)
    global_current_scenario = scenario
    # Record the absolute time when traffic starts
    traffic_start_time = time.time()
    traffic_running = True

    # Start traffic thread
    traffic_thread = threading.Thread(
        target=simulate_traffic,
        args=(baseline_rate, traffic_start_time,scenario)
    )
    traffic_thread.start()

    return jsonify({"message": "Traffic simulation started"}), 200

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

def simulate_traffic(baseline_rate, start_time,scenario):
    """
    Simulate continuous traffic with adjustable baseline and
    real-time scaling events.
    :param baseline_rate: (int) baseline requests per second
    :param start_time: (float) the absolute timestamp when traffic started
    """
    global traffic_running, traffic_metrics, events

    traffic_logger.info("Starting continuous traffic simulation.")

    while traffic_running:
        # current simulation time in seconds since we started
        current_time = time.time() - start_time
        rate = baseline_rate

        # Apply any scaling events that are active
        for event in events:
            e_start = event["start_time"]
            e_scale = event["scale"]
            e_duration = event["duration"]

            # If duration=0, treat as indefinite
            if e_duration == 0:
                # indefinite event: if we've passed e_start, keep applying
                if current_time >= e_start:
                    rate = int(baseline_rate * e_scale)
            else:
                # normal finite-duration event
                if e_start <= current_time < e_start + e_duration:
                    rate = int(baseline_rate * e_scale)


        for _ in range(rate):
            try:
                response = requests.post(url, json={
                    "url": url,     
                    "type": "GET",   
                    "rate": rate,
                    "duration": 1,
                    "scenario": scenario  
                })
                traffic_logger.debug(f"Traffic sent: {response.status_code} {response.text}")
            except Exception as e:
                traffic_logger.error(f"Error sending traffic: {e}")

        # **Append one metric entry per second** (after all requests)
        traffic_metrics.append({"timestamp": time.time(), "rate": rate})
        traffic_logger.info(f"Appended metric: time={time.time()}, rate={rate}")
        time.sleep(1)

    traffic_logger.info("Traffic simulation stopped.")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
