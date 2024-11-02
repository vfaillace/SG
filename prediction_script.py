import sys
import os
import traceback
import socket
import json
import joblib
import logging
import threading
import time
from sklearn.base import BaseEstimator

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ModelStats:
    def __init__(self, model_name):
        self.model_name = model_name
        self.prediction_count = 0
        self.predictions = {
            "none": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "ddos": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "synflood": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "mitm": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        }
        self.actual_counts = {"none": 0, "ddos": 0, "synflood": 0, "mitm": 0}
        # Add timing tracking
        self.total_prediction_time = 0.0
        self.prediction_times = []

    def update(self, prediction, actual_flags, prediction_time):
        """Update statistics based on prediction and actual flags."""
        self.prediction_count += 1
        # Track prediction time
        self.total_prediction_time += prediction_time
        self.prediction_times.append(prediction_time)

        # Determine actual attack type from flags (all lowercase)
        actual_type = "none"
        if actual_flags.get("attack_ddos", 0) == 1:
            actual_type = "ddos"
        elif actual_flags.get("attack_synflood", 0) == 1:
            actual_type = "synflood"
        elif actual_flags.get("attack_mitm", 0) == 1:
            actual_type = "mitm"

        # Convert prediction to lowercase for consistency
        prediction = prediction.lower()

        # Update actual counts
        self.actual_counts[actual_type] += 1

        # Update prediction counts
        if prediction == actual_type:
            # True positive for the predicted class
            self.predictions[prediction]["tp"] += 1
            # True negative for all other classes
            for attack_type in self.predictions:
                if attack_type != prediction:
                    self.predictions[attack_type]["tn"] += 1
        else:
            # False positive for predicted class
            self.predictions[prediction]["fp"] += 1
            # False negative for actual class
            self.predictions[actual_type]["fn"] += 1
            # True negative for all other classes
            for attack_type in self.predictions:
                if attack_type != prediction and attack_type != actual_type:
                    self.predictions[attack_type]["tn"] += 1

    def get_stats(self):
        """Get statistics from collected predictions."""
        total_instances = self.prediction_count if self.prediction_count > 0 else 1

        # Calculate metrics for each class
        metrics = {}
        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_tn = 0

        for attack_type, counts in self.predictions.items():
            tp = counts["tp"]
            fp = counts["fp"]
            fn = counts["fn"]
            tn = counts["tn"]

            total_tp += tp
            total_fp += fp
            total_fn += fn
            total_tn += tn

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0
            )

            metrics[attack_type] = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "support": self.actual_counts[attack_type],
                "confusion_matrix": counts,
            }

        # Calculate micro-averaged metrics
        micro_precision = (
            total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        )
        micro_recall = (
            total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        )
        micro_f1 = (
            2 * (micro_precision * micro_recall) / (micro_precision + micro_recall)
            if (micro_precision + micro_recall) > 0
            else 0
        )
        accuracy = (
            (total_tp + total_tn) / (total_tp + total_tn + total_fp + total_fn)
            if total_instances > 0
            else 0
        )

        # Calculate average prediction time
        avg_prediction_time = (
            self.total_prediction_time / self.prediction_count 
            if self.prediction_count > 0 
            else 0
        )

        return {
            "accuracy": accuracy,
            "precision": micro_precision,
            "recall": micro_recall,
            "f1_score": micro_f1,
            "total_predictions": total_instances,
            "attack_metrics": metrics,
            "avg_prediction_time": avg_prediction_time * 1000  # Convert to milliseconds
        }


def predict(model_dict, data):
    start_time = time.perf_counter()
    try:
        # Check if model is stored in a dictionary with preprocessors
        if isinstance(model_dict, dict) and "model" in model_dict:
            # Extract components
            model = model_dict["model"]
            scaler = model_dict.get("scaler")
            imputer = model_dict.get("imputer")

            # Preprocess data if necessary
            processed_data = [data]
            if imputer is not None:
                processed_data = imputer.transform(processed_data)
            if scaler is not None:
                processed_data = scaler.transform(processed_data)

            # Handle different model types
            if hasattr(model, "cluster_centers_"):  # KMeans
                cluster = model.predict(processed_data)[0]
                # Convert 'normal' to 'none' in prediction
                prediction = model_dict["cluster_mappings"].get(cluster, "none")
                result = "none" if prediction.lower() in ["normal", "none"] else prediction.lower()

            elif hasattr(model, "score_samples"):  # Isolation Forest
                score = model.score_samples(processed_data)[0]
                threshold = -0.5
                result = "ddos" if score < threshold else "none"

            else:  # Random Forest or other classifiers
                prediction = str(model.predict(processed_data)[0]).lower()
                result = "none" if prediction in ["normal", "none"] else prediction

        else:  # Model without preprocessors (like decision tree)
            prediction = str(model_dict.predict([data])[0]).lower()
            result = "none" if prediction in ["normal", "none"] else prediction

    except Exception as e:
        logger.error(f"Error making prediction: {e}", exc_info=True)
        logger.error(f"Model type: {type(model_dict)}")
        if isinstance(model_dict, dict):
            logger.error(f"Model keys: {model_dict.keys()}")
            if "cluster_mappings" in model_dict:
                logger.error(f"Cluster mappings: {model_dict['cluster_mappings']}")
        result = "none"  # Default to no attack if prediction fails

    end_time = time.perf_counter()
    return result, end_time - start_time

def handle_connection(conn, addr, model_name, model, stats):
    logger.info(f"Handling connection for {model_name} from {addr}")

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            json_data = json.loads(data.decode())

            if json_data.get("command") == "get_stats":
                stats_data = stats.get_stats()
                stats_data["model_name"] = model_name
                conn.sendall(json.dumps(stats_data).encode())
                logger.info(f"Sent statistics for {model_name}")

            elif json_data.get("command") == "save_model":
                try:
                    joblib.dump(model, json_data["path"])
                    logger.info(f"Model saved successfully to {json_data['path']}")
                    conn.sendall(
                        json.dumps(
                            {"status": "success", "message": "Model saved successfully"}
                        ).encode()
                    )
                except Exception as e:
                    error_message = f"Failed to save model: {str(e)}"
                    logger.error(error_message)
                    conn.sendall(
                        json.dumps(
                            {"status": "error", "message": error_message}
                        ).encode()
                    )

            else:
                features = [
                    json_data["IAT"],
                    json_data["TD"],
                    json_data["Arrival Time"],
                    json_data["PC"],
                    json_data["Packet Size"],
                    json_data["Acknowledgement Packet Size"],
                    json_data["RTT"],
                    json_data["Average Queue Size"],
                    json_data["System Occupancy"],
                    json_data["Arrival Rate"],
                    json_data["Service Rate"],
                    json_data["Packet Dropped"],
                ]

                attack_flags = {
                    "attack_none": json_data.get("attack_none", 0),
                    "attack_ddos": json_data.get("attack_ddos", 0),
                    "attack_synflood": json_data.get("attack_synflood", 0),
                    "attack_mitm": json_data.get("attack_mitm", 0),
                }

                prediction, pred_time = predict(model, features)
                logger.info(f"Raw prediction: {prediction}")

                # Ensure prediction is 'none' instead of 'normal'
                if prediction.lower() in ["normal", "none"]:
                    prediction = "none"

                # Send prediction back to C++
                response = {
                    "prediction": 1.0 if prediction != "none" else 0.0,
                    "attack_type": prediction,
                }
                logger.info(f"Final prediction: {prediction}")
                conn.sendall(json.dumps(response).encode())

                # Update statistics with standardized prediction and timing
                stats.update(prediction, attack_flags, pred_time)

    except Exception as e:
        logger.error(f"Error processing data for {model_name}: {e}")
        traceback.print_exc()
    finally:
        conn.close()
        logger.info(f"Connection closed for {model_name}")

def load_model(model_path):
    try:
        model = joblib.load(model_path)

        # Log model information for debugging
        if isinstance(model, dict):
            model_type = type(model["model"]).__name__
            logger.info(
                f"Loaded {model_type} model with preprocessors from {model_path}"
            )
            if "scaler" in model:
                logger.info("Model includes scaler")
            if "imputer" in model:
                logger.info("Model includes imputer")
            if "cluster_attack_ratios" in model:
                logger.info("Model includes cluster attack ratios")
        else:
            logger.info(f"Loaded {type(model).__name__} model from {model_path}")

        return model
    except Exception as e:
        logger.error(f"Error loading model from {model_path}: {e}")
        raise


def run_prediction(model_path, port):
    model_name = os.path.basename(model_path)
    model = load_model(model_path)
    stats = ModelStats(model_name)
    
    logger.info(f"Starting prediction server for {model_name} on port {port}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", port))
        s.listen()
        logger.info(f"Waiting for connection on port {port}...")

        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_connection,
                args=(conn, addr, model_name, model, stats)
            ).start()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        model_path = sys.argv[1]
        port = int(sys.argv[2])
        run_prediction(model_path, port)
    else:
        logger.error("Usage: python prediction_script.py <model_path> <port>")
