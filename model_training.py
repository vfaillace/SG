import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

# Load the labeled network traffic data from the CSV file
data = pd.read_csv("network_traffic.csv")

# Separate features and labels
X = data.drop(["Is Attack"], axis=1)
y = data["Is Attack"]

# Assign higher weight to the "Packet Dropped" feature
packet_dropped_weight = 10
X["Packet Dropped"] = X["Packet Dropped"] * packet_dropped_weight

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train the Isolation Forest model
model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
model.fit(X_train)

# Predict on the test data
y_pred = model.predict(X_test)

y_pred_binary = [0 if pred == 1 else 1 for pred in y_pred]

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
import joblib
joblib.dump(model, "isolation_forest_model.pkl")

# Predict on the entire dataset
X["Packet Dropped"] = X["Packet Dropped"] / packet_dropped_weight  # Revert the weight for prediction
predictions = model.predict(X)

# Convert the predictions to binary labels (-1 for anomaly, 1 for normal)
predictions_binary = [1 if pred == 1 else 0 for pred in predictions]

# Create a DataFrame with the original data and predicted labels
results = pd.DataFrame(data)
results["Predicted Label"] = predictions_binary

# Save the results to a new CSV file
results.to_csv("prediction_results.csv", index=False)

print("Prediction results saved to 'prediction_results.csv'")