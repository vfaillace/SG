import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer


def train_isolation_forest(csv_path, timestamp):
    # Load the data
    data = pd.read_csv(csv_path)

    # Identify attack label columns
    attack_columns = [col for col in data.columns if col.startswith("attack_")]
    print(f"Detected attack label columns: {attack_columns}")

    # Convert attack columns to int
    for col in attack_columns:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)

    # Identify feature columns
    columns_to_drop = ["FB", "TB", "Time", "Sample"]
    feature_columns = [
        col
        for col in data.columns
        if col not in columns_to_drop and col not in attack_columns
    ]

    print("\nFeature columns:")
    print(feature_columns)

    X = data[feature_columns].apply(pd.to_numeric, errors="coerce")

    # Create labels by finding which attack type is active
    def get_attack_type(row):
        active_attacks = [
            col.replace("attack_", "") for col in attack_columns if row[col] == 1
        ]
        return active_attacks[0] if active_attacks else "none"

    y = data[attack_columns].apply(get_attack_type, axis=1)

    print("\nLabel distribution:")
    print(y.value_counts())

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=27, stratify=y
    )

    # Handle missing values
    imputer = SimpleImputer(strategy="mean")
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imputed)
    X_test_scaled = scaler.transform(X_test_imputed)

    # Create and train the Isolation Forest model
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=27)
    model.fit(X_train_scaled)

    # Function to convert isolation forest predictions to attack types
    def convert_predictions(X_scaled, threshold_percentile=10):
        scores = model.score_samples(X_scaled)
        threshold = np.percentile(scores, threshold_percentile)
        predictions = np.where(scores > threshold, "none", "attack")
        return predictions

    # Predict on test data
    y_pred = convert_predictions(X_test_scaled)

    # Print evaluation metrics
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save model, scaler, and imputer
    model_dict = {"model": model, "scaler": scaler, "imputer": imputer}
    model_filename = f"isolation_forest_model_{timestamp}.pkl"
    joblib.dump(model_dict, model_filename)
    print(f"\nModel saved as {model_filename}")

    # Predict on entire dataset
    X_full_imputed = imputer.transform(X)
    X_full_scaled = scaler.transform(X_full_imputed)
    predictions = convert_predictions(X_full_scaled)

    # Create results DataFrame
    results = pd.DataFrame(X)
    results["Predicted_Attack_Type"] = predictions

    # Add original labels for comparison
    for col in attack_columns:
        results[f"Original_{col}"] = data[col]

    # Save results
    results_filename = f"prediction_results_forest_{timestamp}.csv"
    results.to_csv(results_filename, index=False)
    print(f"Prediction results saved to '{results_filename}'")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python model_training_isolation_forest.py <path_to_csv> <timestamp>"
        )
        sys.exit(1)

    csv_path = sys.argv[1]
    timestamp = sys.argv[2]
    train_isolation_forest(csv_path, timestamp)
