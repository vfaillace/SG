import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
)
from sklearn.model_selection import train_test_split


def train_decision_tree(csv_path, timestamp):
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

    print("\nTraining data shape:", X_train.shape)
    print("Training labels shape:", y_train.shape)

    print("\nTraining set distribution:")
    print(y_train.value_counts())
    print("\nTest set distribution:")
    print(y_test.value_counts())

    # Train model
    model = DecisionTreeClassifier(random_state=27)
    model.fit(X_train, y_train)

    # Predict and evaluate
    y_pred = model.predict(X_test)

    print("\nModel Performance Metrics:")
    print(f"Accuracy: {accuracy_score(y_test, y_pred)}")
    print(
        f"Precision (weighted): {precision_score(y_test, y_pred, average='weighted')}"
    )
    print(f"Recall (weighted): {recall_score(y_test, y_pred, average='weighted')}")
    print(f"F1 Score (weighted): {f1_score(y_test, y_pred, average='weighted')}")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save model
    model_filename = f"decision_tree_model_{timestamp}.pkl"
    joblib.dump(model, model_filename)
    print(f"\nModel saved as {model_filename}")

    # Predict on entire dataset
    predictions = model.predict(X)

    # Create results DataFrame
    results = pd.DataFrame(X)
    results["Predicted_Attack_Type"] = predictions

    # Add original labels for comparison
    for col in attack_columns:
        results[f"Original_{col}"] = data[col]

    # Save results
    results_filename = f"prediction_results_tree_{timestamp}.csv"
    results.to_csv(results_filename, index=False)
    print(f"Prediction results saved to '{results_filename}'")

    # Print non-zero feature importance
    feature_importance = pd.DataFrame(
        {"feature": feature_columns, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    print("\nFeature Importance (non-zero):")
    print(feature_importance[feature_importance["importance"] > 0])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python model_training_decision_tree.py <path_to_csv> <timestamp>")
        sys.exit(1)

    csv_path = sys.argv[1]
    timestamp = sys.argv[2]
    train_decision_tree(csv_path, timestamp)
