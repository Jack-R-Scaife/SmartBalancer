import pandas as pd

def clean_and_prepare_training_data(input_path, output_path):
    """
    Cleans raw data and prepares training data with 30-second rolling metrics.
    """
    try:
        # Load the dataset
        data = pd.read_csv(input_path)

        # Convert 'timestamp' to datetime
        data['timestamp'] = pd.to_datetime(data['timestamp'])

        # Sort data by timestamp
        data = data.sort_values('timestamp')

        # Initialize new columns for rolling metrics
        data['cpu_usage_avg'] = 0.0  # Explicitly set float type
        data['memory_usage_avg'] = 0.0  # Explicitly set float type
        data['connections_sum'] = 0  # Integer column for sums
        data['traffic_rate_sum'] = 0.0  # Explicitly set float type

        # Calculate rolling metrics for each server
        for server_ip in data['server_ip'].unique():
            server_data = data[data['server_ip'] == server_ip]
            rolling_window = server_data.rolling('30s', on='timestamp')

            # Cast the results to the correct dtype
            data.loc[data['server_ip'] == server_ip, 'cpu_usage_avg'] = rolling_window['cpu_usage'].mean().astype(float)
            data.loc[data['server_ip'] == server_ip, 'memory_usage_avg'] = rolling_window['memory_usage'].mean().astype(float)
            data.loc[data['server_ip'] == server_ip, 'connections_sum'] = rolling_window['connections'].sum().astype(int)
            data.loc[data['server_ip'] == server_ip, 'traffic_rate_sum'] = rolling_window['traffic_rate'].sum().astype(float)

        # Drop rows with NaN values resulting from rolling calculations
        data = data.dropna()

        # Shift the traffic rate sum to create the target
        data['traffic_rate_sum_10s'] = data.groupby('server_ip')['traffic_rate_sum'].shift(-10)

        # Save the prepared dataset
        data.to_csv(output_path, index=False)
        print(f"Training data prepared and saved to {output_path}")

    except Exception as e:
        print(f"Error preparing training data: {e}")

if __name__ == "__main__":
    input_csv = "baseline_data.csv"
    output_csv = "prepared_training_data.csv"
    clean_and_prepare_training_data(input_csv, output_csv)
