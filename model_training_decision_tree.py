import sys
import pandas as pd
import joblib
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split


def train_decision_tree(csv_path, timestamp):
    # Load the labeled network traffic data from the CSV file
    data = pd.read_csv(csv_path)

    # Convert the "Time" column to datetime format
    data["Time"] = pd.to_datetime(data["Time"], format="%H:%M:%S:%f")

    # Drop unnecessary columns
    data = data.drop(["FB", "TB", "Time", "Sample"], axis=1)

    print(data.head())
    print(data.columns)

    # Remove rows with NaN values
    print(data.shape)
    data = data.dropna()
    print(data.shape)

    # Separate features and labels
    X = data.drop(["Is Attack"], axis=1)
    y = data["Is Attack"]

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=27
    )

    # Create and train the decision tree model
    model = DecisionTreeClassifier(random_state=27)
    model.fit(X_train, y_train)

    # Predict on the test data
    y_pred = model.predict(X_test)

    # Evaluate the model's performance
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"Accuracy: {accuracy}")
    print(f"Precision: {precision}")
    print(f"Recall: {recall}")
    print(f"F1 Score: {f1}")

    # Save the trained model with timestamp
    model_filename = f"decision_tree_model_{timestamp}.pkl"
    joblib.dump(model, model_filename)
    print(f"Model saved as {model_filename}")

    # Predict on the entire dataset
    predictions = model.predict(X)

    # Create a DataFrame with the original data and predicted labels
    results = pd.DataFrame(data)
    results["Predicted Label"] = predictions

    # Save the results to a new CSV file with timestamp
    results_filename = f"prediction_results_tree_{timestamp}.csv"
    results.to_csv(results_filename, index=False)
    print(f"Prediction results saved to '{results_filename}'")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python model_training_decision_tree.py <path_to_csv> <timestamp>")
        sys.exit(1)

    csv_path = sys.argv[1]
    timestamp = sys.argv[2]
    train_decision_tree(csv_path, timestamp)
