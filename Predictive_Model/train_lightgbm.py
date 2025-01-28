import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib

def train_lightgbm(input_path, model_output_path):
    """
    Trains a LightGBM model for aggregated traffic prediction.

    Args:
        input_path (str): Path to the cleaned and aggregated CSV file.
        model_output_path (str): Path to save the trained model.
    """
    try:
        # Load the dataset
        data = pd.read_csv(input_path)

        # Create lagged target for prediction
        data['traffic_rate_sum_10s'] = data['traffic_rate'].shift(-10)
        data = data.dropna()  # Drop rows with NaN values

        # Define features and target
        X = data[['cpu_usage', 'memory_usage', 'connections', 'traffic_rate']]
        y = data['traffic_rate_sum_10s']

        # Split the data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train the LightGBM model
        model = LGBMRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate the model
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        print(f"Model Evaluation:\nMean Squared Error: {mse}\nR-squared: {r2}")

        # Save the model
        joblib.dump(model, model_output_path)
        print(f"Model saved to {model_output_path}")

    except Exception as e:
        print(f"Error training model: {e}")

if __name__ == "__main__":
    # Define file paths
    input_csv = "prepared_training_data.csv"
    model_output = "lightgbm_model.pkl"

    # Train the LightGBM model
    train_lightgbm(input_csv, model_output)
