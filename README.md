Smart Grid Anomaly Detection
This project aims to develop a system for identifying cyber attacks on a smart grid network using machine learning techniques. The system simulates normal network traffic data and various attack scenarios, trains an isolation forest model for anomaly detection, and provides insights into the detected attacks.

**Project Structure**
Data Generation: Simulates normal network traffic and attack scenarios using the SimComponents library in Python.
Data Preprocessing: Cleans and preprocesses the simulated data, handles missing values, and prepares it for training the machine learning model.
Feature Engineering: Extracts relevant features from the preprocessed data to help distinguish between normal and attack scenarios.
Model Training: Implements an isolation forest model using the scikit-learn and trains it on the preprocessed data.
Model Evaluation: Evaluates the trained model using appropriate metrics and analyzes the results to identify areas for improvement.
Attack Identification: Performs further analysis on the isolated anomalous packets to gain insights into the attack vector and targeted entities.
Integration and Testing: Integrates the attack identification component with other system components and tests the end-to-end functionality.

**Installation**
Clone the repository: git clone https://github.com/vfaillace/SG
Install the required dependencies: pip install -r requirements.txt
Generate simulated network traffic data: python sim_dos_traffic.py
Train the isolation forest model: python model_training.py
**Contact**
For any questions or inquiries, please contact vfaillace@ufl.edu
