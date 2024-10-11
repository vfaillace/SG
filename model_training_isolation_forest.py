import sys
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split


def train_isolation_forest(csv_path, timestamp):
    
    # Load the network traffic data from the CSV file
    data = pd.read_csv(csv_path)
    print (data.columns)

    data = data.drop(["FB"], axis=1)
    data = data.drop(["TB"], axis=1)
    data = data.drop(["Time"], axis=1)
    data = data.drop(["Sample"], axis=1)

    # Separate features and labels
    X = data.drop(["Is Attack"], axis=1)
    y = data["Is Attack"]
    # Keep the labels (y) separate for later evaluation
    y = data["Is Attack"]

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=27
    )

    # Create and train the Isolation Forest model
    # Note: We're not using y_train in the fit method
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=27)
    model.fit(X_train)

    # Predict on the test data
    y_pred = model.predict(X_test)
    # Convert predictions to binary format (0 for inliers, 1 for outliers)
    y_pred_binary = [1 if pred == -1 else 0 for pred in y_pred]

    # Evaluate the model's performance
    accuracy = accuracy_score(y_test, y_pred_binary)
    precision = precision_score(y_test, y_pred_binary)
    recall = recall_score(y_test, y_pred_binary)
    f1 = f1_score(y_test, y_pred_binary)

    print(f"Accuracy: {accuracy}")
    print(f"Precision: {precision}")
    print(f"Recall: {recall}")
    print(f"F1 Score: {f1}")

    # Save the trained model
    model_filename = f"isolation_forest_model_{timestamp}.pkl"
    joblib.dump(model, model_filename)
    print(f"Model saved as {model_filename}")

    # Predict on the entire dataset
    predictions = model.predict(X)
    predictions_binary = [1 if pred == -1 else 0 for pred in predictions]

    # Create a DataFrame with the original data and predicted labels
    results = pd.DataFrame(data)
    results["Predicted Label"] = predictions_binary

    # Save the results to a new CSV file
    results.to_csv("prediction_results_forest.csv", index=False)
    print("Prediction results saved to 'prediction_results_forest.csv'")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python model_training_isolation_forest.py <path_to_csv> <timestamp>")
        sys.exit(1)

    csv_path = sys.argv[1]
    timestamp = sys.argv[2]
    train_isolation_forest(csv_path, timestamp)
