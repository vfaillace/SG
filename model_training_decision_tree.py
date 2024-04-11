import pandas as pd
import joblib
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

# Load the labeled network traffic data from the CSV file
data = pd.read_csv("network_traffic.csv")

# Convert the "Time" column to datetime format
data["Time"] = pd.to_datetime(data["Time"], format="%H:%M:%S:%f")

# Extract numerical features from the "Time" column
data["Hour"] = data["Time"].dt.hour
data["Minute"] = data["Time"].dt.minute
data["Second"] = data["Time"].dt.second
data["Microsecond"] = data["Time"].dt.microsecond

# Drop the original "Time" column
data = data.drop(["Time"], axis=1)

# Separate features and labels
X = data.drop(["Is Attack"], axis=1)
y = data["Is Attack"]

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train the decision tree model
model = DecisionTreeClassifier(random_state=42)
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

# Save the trained model
joblib.dump(model, "decision_tree_model.pkl")

# Predict on the entire dataset
predictions = model.predict(X)

# Create a DataFrame with the original data and predicted labels
results = pd.DataFrame(data)
results["Predicted Label"] = predictions

# Save the results to a new CSV file
results.to_csv("prediction_results_tree.csv", index=False)
print("Prediction results saved to 'prediction_results_tree.csv'")
