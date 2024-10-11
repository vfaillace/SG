import sys
import os
import traceback
import socket
import json
import joblib
import logging
import threading
from sklearn.base import BaseEstimator

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ModelStats:
    def __init__(self, model_name, is_supervised):
        self.model_name = model_name
        self.is_supervised = is_supervised
        self.prediction_count = 0
        self.true_positives = 0
        self.true_negatives = 0
        self.false_positives = 0
        self.false_negatives = 0

    def update(self, prediction, is_attack):
        self.prediction_count += 1
        if self.is_supervised:
            if prediction == 1 and is_attack == 1:
                self.true_positives += 1
            elif prediction == 0 and is_attack == 0:
                self.true_negatives += 1
            elif prediction == 1 and is_attack == 0:
                self.false_positives += 1
            elif prediction == 0 and is_attack == 1:
                self.false_negatives += 1
        else:
            if prediction == 1 and is_attack == 1:
                self.true_positives += 1
            elif prediction == -1 and is_attack == 0:
                self.true_negatives += 1
            elif prediction == 1 and is_attack == 0:
                self.false_positives += 1
            elif prediction == -1 and is_attack == 1:
                self.false_negatives += 1

    def get_stats(self):
        accuracy = (
            (self.true_positives + self.true_negatives) / self.prediction_count
            if self.prediction_count > 0
            else 0
        )
        precision = (
            self.true_positives / (self.true_positives + self.false_positives)
            if (self.true_positives + self.false_positives) > 0
            else 0
        )
        recall = (
            self.true_positives / (self.true_positives + self.false_negatives)
            if (self.true_positives + self.false_negatives) > 0
            else 0
        )
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "total_predictions": self.prediction_count,
            "true_positives": self.true_positives,
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
        }


def load_model(model_path):
    return joblib.load(model_path)


def is_supervised_model(model):
    return hasattr(model, "classes_")


def predict(model, data):
    if is_supervised_model(model):
        return model.predict([data])[0]
    else:
        prediction = model.predict([data])[0]
        return 1 if prediction == 1 else 0


def send_to_cpp(prediction, model_name, conn):
    try:
        conn.sendall(
            json.dumps({"prediction": float(prediction), "model": model_name}).encode()
        )
    except Exception as e:
        logger.error(f"Error sending prediction to C++: {e}")


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
                    save_model(model, json_data["path"])
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
                # Handle prediction as before
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
                is_attack = json_data.get("Is Attack", 0)
                prediction = predict(model, features)
                send_to_cpp(prediction, model_name, conn)

                stats.update(prediction, is_attack)

    except Exception as e:
        logger.error(f"Error processing data for {model_name}: {e}")
    finally:
        conn.close()
        logger.info(f"Connection closed for {model_name}")
        log_stats(stats)


def save_model(model, path):
    try:
        joblib.dump(model, path)
        logger.info(f"Model saved to {path}")
    except Exception as e:
        logger.error(f"Error saving model to {path}: {e}")
        raise


def log_stats(stats):
    logger.info(f"Statistics for {stats.model_name}:")
    logger.info(f"{stats.model_name}: Total predictions: {stats.prediction_count}")
    logger.info(f"{stats.model_name}: True positives: {stats.true_positives}")
    logger.info(f"{stats.model_name}: True negatives: {stats.true_negatives}")
    logger.info(f"{stats.model_name}: False positives: {stats.false_positives}")
    logger.info(f"{stats.model_name}: False negatives: {stats.false_negatives}")

    model_stats = stats.get_stats()
    logger.info(f"{stats.model_name}: Accuracy: {model_stats['accuracy']:.4f}")
    logger.info(f"{stats.model_name}: Precision: {model_stats['precision']:.4f}")
    logger.info(f"{stats.model_name}: Recall: {model_stats['recall']:.4f}")
    logger.info(f"{stats.model_name}: F1 Score: {model_stats['f1_score']:.4f}")


def run_prediction(model_path, port):
    model_name = os.path.basename(model_path)
    model = load_model(model_path)
    is_supervised = is_supervised_model(model)
    stats = ModelStats(model_name, is_supervised)
    logger.info(
        f"Loaded {'supervised' if is_supervised else 'unsupervised'} model from {model_path}"
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", port))
        s.listen()
        logger.info(
            f"Waiting for connection from C++ for {model_name} on port {port}..."
        )

        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_connection, args=(conn, addr, model_name, model, stats)
            ).start()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        model_path = sys.argv[1]
        port = int(sys.argv[2])
        run_prediction(model_path, port)
    else:
        logger.error("Usage: python prediction_script.py <model_path> <port>")
