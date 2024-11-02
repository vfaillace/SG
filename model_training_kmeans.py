import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import classification_report, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
from kneed import KneeLocator

def find_optimal_k(X, k_range):
    """Find optimal k using both elbow method and silhouette analysis"""
    print("\nFinding optimal k...")
    inertias = []
    silhouette_scores = []
    k_values = range(2, k_range + 1)

    for k in k_values:
        print(f"Testing k={k}")
        kmeans = KMeans(n_clusters=k, random_state=27)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(X, kmeans.labels_))

    # Elbow method
    kl = KneeLocator(list(k_values), inertias, curve="convex", direction="decreasing")
    elbow_k = kl.elbow

    # Plot results
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(k_values, inertias, "bx-")
    plt.xlabel("k")
    plt.ylabel("Inertia")
    plt.title("Elbow Method")
    if elbow_k:
        plt.axvline(x=elbow_k, color="r", linestyle="--", label=f"Elbow at k={elbow_k}")
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(k_values, silhouette_scores, "rx-")
    plt.xlabel("k")
    plt.ylabel("Silhouette Score")
    plt.title("Silhouette Analysis")
    plt.axvline(x=k_values[np.argmax(silhouette_scores)], color="b", 
                linestyle="--", label=f"Best at k={k_values[np.argmax(silhouette_scores)]}")
    plt.legend()

    plt.tight_layout()
    plt.savefig(f"kmeans_optimization_{timestamp}.png")
    plt.close()

    return elbow_k, k_values[np.argmax(silhouette_scores)], silhouette_scores

def train_kmeans(csv_path, timestamp):
    # Load the data
    print("Loading data...")
    data = pd.read_csv(csv_path)

    # Identify attack label columns
    attack_columns = [col for col in data.columns if col.startswith("attack_")]
    print(f"Detected attack label columns: {attack_columns}")

    # Convert attack columns to int
    for col in attack_columns:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)

    # Create labels by finding which attack type is active (same as decision tree/random forest)
    def get_attack_type(row):
        active_attacks = [col.replace("attack_", "") for col in attack_columns if row[col] == 1]
        return active_attacks[0] if active_attacks else "none"

    # Identify feature columns
    columns_to_drop = ["FB", "TB", "Time", "Sample"]
    feature_columns = [col for col in data.columns 
                      if col not in columns_to_drop and col not in attack_columns]

    print("\nFeature columns:")
    print(feature_columns)

    # Convert data to numeric and handle NaN values
    X = data[feature_columns].apply(pd.to_numeric, errors="coerce")
    y = data[attack_columns].apply(get_attack_type, axis=1)

    print("\nLabel distribution:")
    print(y.value_counts())

    # Split the data
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=27, stratify=y
        )
    except ValueError as e:
        print("Warning: Could not perform stratified split due to class imbalance.")
        print("Performing regular split instead.")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=27
        )

    # Handle missing values and scale features
    imputer = SimpleImputer(strategy="mean")
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imputed)
    X_test_scaled = scaler.transform(X_test_imputed)

    # Set number of clusters based on unique attack types plus extra clusters for variation
    unique_attacks = len(set(y))
    # optimal_k = max(unique_attacks * 2, 5)  # At least 2 clusters per attack type
    optimal_k = unique_attacks + 1
    print(f"\nUsing k = {optimal_k} (based on {unique_attacks} unique attack types)")

    # Train KMeans
    print("\nTraining KMeans model...")
    model = KMeans(n_clusters=optimal_k, random_state=27)
    model.fit(X_train_scaled)

    # Analyze cluster compositions
    train_clusters = model.predict(X_train_scaled)
    cluster_distributions = []

    print("\nAnalyzing cluster compositions:")
    for i in range(optimal_k):
        mask = train_clusters == i
        if sum(mask) > 0:
            cluster_dist = y_train[mask].value_counts(normalize=True)
            cluster_distributions.append((i, cluster_dist))
            print(f"\nCluster {i} distribution:")
            print(cluster_dist)
            print(f"Total samples in cluster: {sum(mask)}")

    # Map clusters to attack types based on dominant class
    cluster_mappings = {}
    for cluster_id, dist in cluster_distributions:
        if len(dist) > 0:
            dominant_class = dist.idxmax()
            dominant_ratio = dist.max()
            cluster_mappings[cluster_id] = dominant_class

    print("\nCluster mappings:")
    for cluster, attack_type in cluster_mappings.items():
        print(f"Cluster {cluster} -> {attack_type}")

    # Function to map clusters to attack types
    def map_clusters_to_attacks(cluster_labels):
        return np.array([cluster_mappings.get(label, "none") for label in cluster_labels])

    # Predict on test set
    y_pred = map_clusters_to_attacks(model.predict(X_test_scaled))

    # Print evaluation metrics
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save model and related objects
    model_dict = {
        "model": model,
        "scaler": scaler,
        "imputer": imputer,
        "cluster_mappings": cluster_mappings,
        "optimal_k": optimal_k,
    }

    model_filename = f"kmeans_model_{timestamp}.pkl"
    joblib.dump(model_dict, model_filename)
    print(f"\nModel saved as {model_filename}")

    # Predict on entire dataset
    X_full_imputed = imputer.transform(X)
    X_full_scaled = scaler.transform(X_full_imputed)
    predictions = map_clusters_to_attacks(model.predict(X_full_scaled))

    # Calculate accuracy per class
    unique_labels = sorted(set(y))
    print("\nPer-class accuracy:")
    for label in unique_labels:
        mask = y == label
        if sum(mask) > 0:
            accuracy = sum((predictions == label) & mask) / sum(mask)
            print(f"{label}: {accuracy:.2%}")

    # Create results DataFrame
    results = pd.DataFrame(X)
    results["Predicted_Attack_Type"] = predictions
    results["Cluster"] = model.predict(X_full_scaled)

    # Add original labels for comparison
    for col in attack_columns:
        results[f"Original_{col}"] = data[col]

    # Save results
    results_filename = f"prediction_results_kmeans_{timestamp}.csv"
    results.to_csv(results_filename, index=False)
    print(f"\nPrediction results saved to '{results_filename}'")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python model_training_kmeans.py <path_to_csv> <timestamp>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    timestamp = sys.argv[2]
    train_kmeans(csv_path, timestamp)
