import pandas as pd
import joblib

def test_random_forest(model_path, test_data):
    """
    Tests the trained Random Forest model with sample test cases.

    Args:
        model_path (str): Path to the trained model file.
        test_data (list[dict]): List of test cases as dictionaries.

    Returns:
        None
    """
    try:
        # Load the trained model
        model = joblib.load(model_path)

        # Convert test data into a DataFrame
        test_df = pd.DataFrame(test_data)

        # One-hot encode categorical variables to match training features
        test_df = pd.get_dummies(test_df, columns=['server_ip', 'scenario', 'strategy'])

        # Align test data with the model's expected features
        expected_features = model.feature_names_in_
        test_df = test_df.reindex(columns=expected_features, fill_value=0)

        # Make predictions
        predictions = model.predict(test_df)

        # Print predictions for each test case
        for i, (test_case, prediction) in enumerate(zip(test_data, predictions)):
            print(f"Test Case {i + 1}: {test_case}")
            print(f"Predicted Traffic Rate (1 min into future): {prediction}\n")

    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    # Path to the trained model
    model_file = "random_forest_model.pkl"

    # Define test cases (simulated input data)
    test_cases = [
        {
            'server_ip': '192.168.1.93',
            'cpu_usage': 40,
            'memory_usage': 50,
            'connections': 10,
            'traffic_volume': 10,
            'scenario': 'low',
            'strategy': 'Round Robin'
        },
        {
            'server_ip': '192.168.1.205',
            'cpu_usage': 70,
            'memory_usage': 60,
            'connections': 20,
            'traffic_volume': 50,
            'scenario': 'medium',
            'strategy': 'Round Robin'
        },
        {
            'server_ip': '192.168.1.93',
            'cpu_usage': 90,
            'memory_usage': 80,
            'connections': 30,
            'traffic_volume': 100,
            'scenario': 'high',
            'strategy': 'Round Robin'
        }
    ]

    # Run the test
    test_random_forest(model_file, test_cases)