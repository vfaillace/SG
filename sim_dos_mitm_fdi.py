import random
from datetime import datetime
import time as time_module
import simpy
from SimComponents import PacketGenerator, PacketSink, SwitchPort, PortMonitor
import numpy as np
import pandas as pd
import csv
import threading
from queue import Queue

# Global variables
SIMULATION_DURATION = 120  # seconds
NUM_BUSES = 14
MEASUREMENT_INTERVAL = 0.1  # seconds

class Bus:
    def __init__(self, env, bus_id, output_queue):
        self.env = env
        self.bus_id = bus_id
        self.output_queue = output_queue

    def run(self):
        while True:
            yield self.env.timeout(random.expovariate(1.0))
            for target_bus in range(1, NUM_BUSES + 1):
                if self.bus_id != target_bus:
                    self.simulate_communication(target_bus)

    def simulate_communication(self, target_bus):
        measurement = {
            'timestamp': self.env.now,
            'source_bus': self.bus_id,
            'target_bus': target_bus,
            'service_rate': random.uniform(0.1, 1.0),
            'ack_size': random.randint(32, 128),
            'packet_size': random.randint(64, 1500),
            'rtt': random.uniform(0.001, 0.1),
            'transmission_delay': random.uniform(0.0001, 0.01),
            'inter_arrival_time': random.expovariate(10),
            'packets_dropped': random.randint(0, 10),
            'is_attack': 0,
            'attack_type': 'None'
        }
        self.output_queue.put(measurement)

class Attack:
    def __init__(self, env, attack_source, output_queue, attack_type):
        self.env = env
        self.attack_source = attack_source
        self.output_queue = output_queue
        self.attack_type = attack_type

    def run(self):
        while True:
            yield self.env.timeout(random.uniform(0.01, 0.1))
            for target_bus in range(1, NUM_BUSES + 1):
                if self.attack_source != target_bus:
                    self.simulate_attack(target_bus)

    def simulate_attack(self, target_bus):
        measurement = {
            'timestamp': self.env.now,
            'source_bus': self.attack_source,
            'target_bus': target_bus,
            'service_rate': random.uniform(0.01, 0.1),
            'ack_size': random.randint(32, 64),
            'packet_size': random.randint(1000, 2000),
            'rtt': random.uniform(0.1, 0.5),
            'transmission_delay': random.uniform(0.01, 0.1),
            'inter_arrival_time': random.expovariate(100),
            'packets_dropped': random.randint(50, 100),
            'is_attack': 1,
            'attack_type': self.attack_type
        }
        
        if self.attack_type == 'MITM':
            measurement['packet_size'] = random.randint(64, 1500)  # MITM might not always increase packet size
            measurement['rtt'] = random.uniform(0.05, 0.2)  # Slightly increased RTT due to interception
        elif self.attack_type == 'FDIA':
            measurement['packet_size'] = random.randint(64, 1500)  # FDIA might not change packet size
            measurement['service_rate'] = random.uniform(0.05, 0.5)  # Might affect service rate due to false data

        self.output_queue.put(measurement)

def run_simulation(env, output_queue):
    # Create and start bus threads
    buses = [Bus(env, i, output_queue) for i in range(1, NUM_BUSES + 1)]
    for bus in buses:
        env.process(bus.run())

    # Create and start attack threads
    ddos_attack = Attack(env, attack_source=5, output_queue=output_queue, attack_type='DDoS')
    mitm_attack = Attack(env, attack_source=8, output_queue=output_queue, attack_type='MITM')
    fdia_attack = Attack(env, attack_source=12, output_queue=output_queue, attack_type='FDIA')

    env.process(ddos_attack.run())
    env.process(mitm_attack.run())
    env.process(fdia_attack.run())

    # Run the simulation
    env.run(until=SIMULATION_DURATION)

def main():
    env = simpy.Environment()
    output_queue = Queue()

    # Start the simulation in a separate thread
    sim_thread = threading.Thread(target=run_simulation, args=(env, output_queue))
    sim_thread.start()

    # Collect and process measurements
    measurements = []
    start_time = time_module.time()
    while time_module.time() - start_time < SIMULATION_DURATION:
        time_module.sleep(MEASUREMENT_INTERVAL)
        while not output_queue.empty():
            measurements.append(output_queue.get())

    # Wait for the simulation thread to finish
    sim_thread.join()

    # Save measurements to CSV
    df = pd.DataFrame(measurements)
    df.to_csv("network_traffic.csv", index=False)
    print(f"Simulation complete. {len(measurements)} measurements saved to 'network_traffic.csv'")

if __name__ == "__main__":
    main()