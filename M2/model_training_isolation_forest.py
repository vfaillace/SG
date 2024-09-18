import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

# Load the labeled network traffic data from the CSV file
data = pd.read_csv("network_traffic.csv")

# Separate features and labels
X = data[["Packet Dropped", "Average Queue Size", "System Occupancy", "Service Rate", "TD", "RTT", "Arrival Rate"]]
y = data["Is Attack"]

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train the Isolation Forest model
model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
model.fit(X_train)

# Predict on the test data
y_pred = model.predict(X_test)
y_pred_binary = [0 if pred == -1 else 1 for pred in y_pred]

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
joblib.dump(model, "isolation_forest_model.pkl")

# Predict on the entire dataset
predictions = model.predict(X)
predictions_binary = [0 if pred == -1 else 1 for pred in predictions]

# Create a DataFrame with the original data and predicted labels
results = pd.DataFrame(data)
results["Predicted Label"] = predictions_binary

# Save the results to a new CSV file
results.to_csv("prediction_results_forest.csv", index=False)
print("Prediction results saved to 'prediction_results_forest.csv'")
