import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
import threading
import queue
from datetime import datetime
import joblib
from sklearn.preprocessing import LabelEncoder
import simulation_script


# Load the trained model
model = joblib.load("decision_tree_model.pkl")

# Initialize LabelEncoder for categorical variables
le_source = LabelEncoder()
le_target = LabelEncoder()

# Create the main window
root = tk.Tk()
root.title("Real-time Network Visualization")

# Create a figure and subplots for the metrics
fig = Figure(figsize=(12, 16), dpi=100)
axs = fig.subplots(8, 1)

# Set plot labels and titles
metric_labels = [
    "Packets Dropped",
    "Average Queue",
    "System Occupancy",
    "Service Rate",
    "TD",
    "RTT",
    "Arrival Rate",
]
for i, label in enumerate(metric_labels):
    axs[i].set_title(label)
    axs[i].set_xlabel("Time (s)")
    axs[i].set_ylabel(label)

# Create a canvas to display the plots
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
canvas.get_tk_widget().pack()

# Initialize the plots
lines = {}
colors = ['blue', 'orange', 'green', 'red']
fb_tb_combinations = [(i, j) for i in range(1, 4) for j in range(1, 4) if i != j]
#fb_tb_combinations = [(1,2), (2,1)]

# Create a dictionary to store data for each FB-TB combination
data_storage = {combo: pd.DataFrame() for combo in fb_tb_combinations}

# Set the time window size (in seconds)
time_window = 60

# Initialize the attack information plot
attack_ax = axs[7]
attack_ax.set_title("Attack Information")
attack_ax.set_xlabel("Time (s)")
attack_ax.set_yticks([])
attack_ax.set_ylim(0, 1)

# Create a queue for communication between threads
data_queue = queue.Queue()

def parse_custom_datetime(time_str):
    return datetime.strptime(time_str, "%H:%M:%S:%f")

def process_sample(data):
    # Convert data to DataFrame
    df = pd.DataFrame([data])

    # Preprocess the data
    parsed_time = parse_custom_datetime(df["Time"].iloc[0])
    df["Hour"] = parsed_time.hour
    df["Minute"] = parsed_time.minute
    df["Second"] = parsed_time.second
    df["Microsecond"] = parsed_time.microsecond
    df["Seconds"] = parsed_time.timestamp()

    # Ensure 'Arrival Time' and 'Sample' columns are present
    if "Arrival Time" not in df.columns:
        df["Arrival Time"] = df["Time"]
    if "Sample" not in df.columns:
        df["Sample"] = 1

    # Select features for prediction
    features = [
        "FB", "TB", "IAT", "TD", "Arrival Time", "PC", "Packet Size",
        "Acknowledgement Packet Size", "RTT", "Average Queue Size",
        "System Occupancy", "Arrival Rate", "Service Rate", "Packet Dropped",
        "Sample", "Hour", "Minute", "Second", "Microsecond"
    ]
    X = df[features]

    # Make prediction
    try:
        prediction = model.predict(X)[0]
        df["Predicted Label"] = prediction
        print(f"From: {df['FB'].iloc[0]} To: {df['TB'].iloc[0]} Time: {df['Time'].iloc[0]}, Predicted: {'Attack' if prediction == 1 else 'Normal'}, Actual: {'Attack' if df['Is Attack'].iloc[0] == 1 else 'Normal'}")
        return df
    except Exception as e:
        print(f"Error making prediction: {str(e)}")
        return None

def update_plots():
    current_time = datetime.now().timestamp()
    start_time = current_time - time_window

    # Clear the attack information plot
    attack_ax.clear()
    attack_ax.set_title("Attack Information")
    attack_ax.set_xlabel("Time (s)")
    attack_ax.set_yticks([])
    attack_ax.set_ylim(0, 1)

    print(f"Updating plots. Data storage keys: {list(data_storage.keys())}")

    for i, (fb, tb) in enumerate(fb_tb_combinations):
        if (fb, tb) in data_storage:
            thread_data = data_storage[(fb, tb)]
            if not thread_data.empty:
                # Convert 'Seconds' to relative time
                thread_data['RelativeTime'] = thread_data['Seconds'] - thread_data['Seconds'].min()
                thread_data = thread_data[thread_data['RelativeTime'] <= time_window]

                if len(thread_data) > 1:
                    print(f"Plotting data for FB {fb} to TB {tb}. Data points: {len(thread_data)}")
                    time = thread_data['RelativeTime']
                    metrics = [
                        thread_data["Packet Dropped"],
                        thread_data["Average Queue Size"],
                        thread_data["System Occupancy"],
                        thread_data["Service Rate"],
                        thread_data["TD"],
                        thread_data["RTT"],
                        thread_data["Arrival Rate"],
                    ]

                    for j, metric in enumerate(metrics):
                        if (fb, tb) not in lines:
                            lines[(fb, tb)] = []
                            for k in range(7):
                                color = colors[(fb-1) % len(colors)]
                                if k == 0:
                                    (line,) = axs[k].plot(
                                        [], [], lw=1, label=f"FB {fb} to TB {tb}", color=color
                                    )
                                else:
                                    (line,) = axs[k].plot([], [], lw=1, color=color)
                                lines[(fb, tb)].append(line)
                            for ax in axs[:7]:
                                ax.legend()
                        lines[(fb, tb)][j].set_data(time, metric)

                    # Check if an attack was identified for this specific thread
                    thread_attack_data = thread_data[thread_data["Predicted Label"] == 1]
                    if len(thread_attack_data) > 0:
                        attack_times = thread_attack_data["RelativeTime"].values
                        for attack_time in attack_times:
                            # Add a vertical line to the attack information plot
                            attack_ax.axvline(
                                x=attack_time, color=colors[(fb-1) % len(colors)], linestyle="-", linewidth=1.5
                            )
                            attack_ax.text(
                                attack_time,
                                0.5,
                                f"FB {fb} to TB {tb}",
                                rotation=90,
                                ha="right",
                                va="center",
                                fontsize=8,
                                color=colors[(fb-1) % len(colors)],
                            )
                else:
                    print(f"Not enough data points for FB {fb} to TB {tb}. Current data points: {len(thread_data)}")
            else:
                print(f"No data for FB {fb} to TB {tb}")

    # Set x-axis limits to show the specified time window
    for ax in axs:
        ax.set_xlim(0, time_window)
        ax.relim()
        ax.autoscale_view(True, True, True)

    # Redraw the canvas
    canvas.draw()

    # Schedule the next update
    root.after(100, update_plots)

def prediction_worker():
    while True:
        try:
            data = data_queue.get(timeout=1)
            if data is None:
                break
            processed_data = process_sample(data)
            if processed_data is not None:
                fb, tb = processed_data["FB"].iloc[0], processed_data["TB"].iloc[0]
                if 1 <= fb <= 4 and 1 <= tb <= 4 and fb != tb:
                    if (fb, tb) not in data_storage:
                        data_storage[(fb, tb)] = pd.DataFrame()
                    data_storage[(fb, tb)] = pd.concat([data_storage[(fb, tb)], processed_data], ignore_index=True)
                    print(f"Added data for FB {fb} to TB {tb}. Total data points: {len(data_storage[(fb, tb)])}")
            data_queue.task_done()
        except queue.Empty:
            pass

# Start the prediction worker thread
prediction_thread = threading.Thread(target=prediction_worker)
prediction_thread.daemon = True
prediction_thread.start()

# Start the plot update loop
root.after(100, update_plots)

# Run the simulation in a separate thread
simulation_thread = threading.Thread(target=simulation_script.run_simulation, args=(data_queue,))
simulation_thread.daemon = True
simulation_thread.start()

# Start the Tkinter event loop
root.mainloop()

print("Real-time visualization complete.")