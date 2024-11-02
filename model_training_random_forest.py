import sys
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def train_random_forest(csv_path, timestamp):
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

    # Convert data to numeric
    for col in feature_columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    # Create labels by finding which attack type is active
    def get_attack_type(row):
        active_attacks = [
            col.replace("attack_", "") for col in attack_columns if row[col] == 1
        ]
        return active_attacks[0] if active_attacks else "none"

    # Separate features and create labels
    X = data[feature_columns]
    y = data[attack_columns].apply(get_attack_type, axis=1)

    print("\nLabel distribution:")
    print(y.value_counts())

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=27, stratify=y
    )

    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Create and train the Random Forest model
    model = RandomForestClassifier(n_estimators=100, random_state=27)
    model.fit(X_train_scaled, y_train)

    # Predict and evaluate
    y_pred = model.predict(X_test_scaled)

    # Print evaluation metrics
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Print feature importance
    feature_importance = pd.DataFrame(
        {"feature": feature_columns, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    print("\nFeature Importance (non-zero):")
    print(feature_importance[feature_importance["importance"] > 0])

    # Save both model and scaler
    model_dict = {"model": model, "scaler": scaler}
    model_filename = f"random_forest_model_{timestamp}.pkl"
    joblib.dump(model_dict, model_filename)
    print(f"\nModel saved as {model_filename}")

    # Predict on entire dataset
    X_full_scaled = scaler.transform(X)
    predictions = model.predict(X_full_scaled)

    # Create results DataFrame
    results = pd.DataFrame(X)
    results["Predicted_Attack_Type"] = predictions

    # Add original labels for comparison
    for col in attack_columns:
        results[f"Original_{col}"] = data[col]

    # Save results
    results_filename = f"prediction_results_random_forest_{timestamp}.csv"
    results.to_csv(results_filename, index=False)
    print(f"Prediction results saved to '{results_filename}'")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python model_training_random_forest.py <path_to_csv> <timestamp>")
        sys.exit(1)

    csv_path = sys.argv[1]
    timestamp = sys.argv[2]
    train_random_forest(csv_path, timestamp)
