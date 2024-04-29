import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np

# Load the data from the CSV file
data = pd.read_csv("prediction_results_tree.csv")

# Sort the data by time columns
data = data.sort_values(by=["Hour", "Minute", "Second", "Microsecond"])

# Convert time columns to timedelta and calculate seconds
data["Time"] = pd.to_timedelta(
    data["Hour"].astype(str)
    + ":"
    + data["Minute"].astype(str)
    + ":"
    + data["Second"].astype(str)
    + "."
    + data["Microsecond"].astype(str)
)
data["Seconds"] = data["Time"].dt.total_seconds()

# Specify the FB and TB combinations to plot
fb_tb_combinations = [
    (7, 1),
    (4, 10),
    (3, 2),
    (5, 4),
    (1, 14),
]  # Update with your desired combinations

# Create the main window
root = tk.Tk()
root.title("Live Demo")

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
lines = [[] for _ in range(7)]
colors = ["blue", "orange", "green", "red", "purple"]
for i, (fb, tb) in enumerate(fb_tb_combinations):
    for j in range(7):
        if j == 0:
            (line,) = axs[j].plot(
                [], [], lw=1, label=f"FB {fb} to TB {tb}", color=colors[i]
            )
            lines[j].append(line)
        else: 
            (line,) = axs[j].plot(
                [], [], lw=1)
            lines[j].append(line)
for ax in axs[:7]:
    ax.legend()

# Set the time window size (in seconds)
time_window = 60

# Initialize the attack information plot
attack_ax = axs[7]
attack_ax.set_title("Attack Information")
attack_ax.set_xlabel("Time (s)")
attack_ax.set_yticks([])
attack_ax.set_ylim(0, 1)


# Function to update the plots
def update_plots(frame):
    min_time = data["Seconds"].min()
    max_time = data["Seconds"].max()

    start_time = max(min_time, frame - time_window)
    end_time = min(max_time, frame)

    # Clear the attack information plot
    attack_ax.clear()
    attack_ax.set_title("Attack Information")
    attack_ax.set_xlabel("Time (s)")
    attack_ax.set_yticks([])
    attack_ax.set_ylim(0, 1)

    for i, (fb, tb) in enumerate(fb_tb_combinations):
        thread_data = data[
            (data["FB"] == fb)
            & (data["TB"] == tb)
            & (data["Seconds"] >= start_time)
            & (data["Seconds"] <= end_time)
        ]

        if len(thread_data) > 1:
            time = thread_data["Seconds"]
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
                # Interpolate metric values
                interp_time = np.linspace(
                    time.iloc[0], time.iloc[-1], num=len(time) * 10
                )
                interp_metric = np.interp(interp_time, time, metric)

                lines[j][i].set_data(interp_time, interp_metric)

            # Check if an attack was identified for this specific thread
            thread_attack_data = thread_data[
                thread_data["Predicted Label"].isin([0, 1])
                & (thread_data["Predicted Label"] == 1)
            ]
            if len(thread_attack_data) > 0:
                attack_times = thread_attack_data["Seconds"].values
                for attack_time in attack_times:
                    # Add a vertical line to the attack information plot
                    attack_ax.axvline(
                        x=attack_time, color=colors[i], linestyle="-", linewidth=1.5
                    )
                    attack_ax.text(
                        attack_time,
                        0.5,
                        f"FB {fb} to TB {tb}",
                        rotation=90,
                        ha="right",
                        va="center",
                        fontsize=8,
                        color=colors[i],
                    )

    # Set x-axis limits to show the specified time window
    for ax in axs:
        ax.set_xlim(start_time, end_time)
        ax.relim()
        ax.autoscale_view(True, True, True)

    # Redraw the canvas
    canvas.draw()

    # Schedule the next update
    if frame < max_time:
        root.after(100, update_plots, frame + 1)


# Start the live demo
update_plots(data["Seconds"].min())
root.mainloop()
