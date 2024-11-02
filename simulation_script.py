import sys
import os
import traceback
import socket
import json
import time
import threading
import random
import logging
from datetime import datetime
import csv
import queue
import simpy
from SimComponents import PacketGenerator, PacketSink, SwitchPort, PortMonitor

print("simulation_script.py: Starting execution")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

n = 4
attack_fb = 2


class AttackType:
    NONE = 0
    DDOS = 1
    SYN_FLOOD = 2
    MITM_SCADA = 3


# Configuration parameters
SCADA_NORMAL_PACKET_SIZE = 256
SCADA_POLL_RATE = 4
MITM_INTERCEPT_DELAY = 0.02
MITM_PACKET_OVERHEAD = 64

ATTACK_PARAMS = {
    AttackType.NONE: {
        "packet_size": 1000,
        "arrival_rate": 7,
        "port_rate": 100000.0,
        "qlimit": 1000000,
        "processing_delay": 0,
    },
    AttackType.DDOS: {
        "packet_size": 64,
        "arrival_rate": 5000,  # Very high packet rate
        "port_rate": 5000.0,  # Severely degraded
        "qlimit": 50000,
        "processing_delay": 0.001,  # Small delay to simulate network congestion
    },
    AttackType.SYN_FLOOD: {
        "packet_size": 40,  # TCP header size
        "arrival_rate": 3000,  # Steady stream of SYN packets
        "port_rate": 5000.0,  # Degraded due to connection table exhaustion
        "qlimit": 50000,
        "processing_delay": 0.005,  # Delay from connection state tracking
    },
    AttackType.MITM_SCADA: {
        "packet_size": SCADA_NORMAL_PACKET_SIZE + MITM_PACKET_OVERHEAD,
        "arrival_rate": SCADA_POLL_RATE,
        "port_rate": 50000.0,
        "qlimit": 100000,
        "processing_delay": 0.02,  # Significant delay for packet inspection
    },
}


time_s = datetime.now()
time_e = datetime.now()
print_lock = threading.Lock()
all_data = []
simulation_running = True
attack_active = False
sock = None
stop_event = threading.Event()


def send_to_cpp(data):
    global sock
    if sock is not None:
        try:
            current_time = time.time()
            ordered_data = [
                data["FB"],
                data["TB"],
                data["IAT"],
                data["TD"],
                data["Arrival Time"],
                data["PC"],
                data["Packet Size"],
                data["Acknowledgement Packet Size"],
                data["RTT"],
                data["Average Queue Size"],
                data["System Occupancy"],
                data["Arrival Rate"],
                data["Service Rate"],
                data["Packet Dropped"],
                current_time,
                data["Sample"],
                data["attack_none"],
                data["attack_ddos"],
                data["attack_synflood"],
                data["attack_mitm"],
            ]
            json_str = json.dumps(ordered_data) + "\n"
            sock.send(json_str.encode())
            # sock.sendall(json.dumps(ordered_data).encode())
        except Exception as e:
            print(f"Error sending data to C++: {e}")


def send_to_queue_and_process(data, output_queue, attack_type=AttackType.NONE):
    list_column = [
        "FB",
        "TB",
        "IAT",
        "TD",
        "Arrival Time",
        "PC",
        "Packet Size",
        "Acknowledgement Packet Size",
        "RTT",
        "Average Queue Size",
        "System Occupancy",
        "Arrival Rate",
        "Service Rate",
        "Packet Dropped",
        "Time",
        "Sample",
        "attack_none",
        "attack_ddos",
        "attack_synflood",
        "attack_mitm",
    ]

    # Create attack flags correctly
    attack_flags = {
        "attack_none": 1 if attack_type == AttackType.NONE else 0,
        "attack_ddos": 1 if attack_type == AttackType.DDOS else 0,
        "attack_synflood": 1 if attack_type == AttackType.SYN_FLOOD else 0,
        "attack_mitm": 1 if attack_type == AttackType.MITM_SCADA else 0,
    }

    # Ensure data list has correct length before adding attack flags
    base_data = data[:16]  # First 16 columns of data

    # Add attack flags in correct order
    attack_data = [
        attack_flags["attack_none"],
        attack_flags["attack_ddos"],
        attack_flags["attack_synflood"],
        attack_flags["attack_mitm"],
    ]

    final_data = base_data + attack_data

    # Create dictionary with correct column mapping
    data_dict = dict(zip(list_column, final_data))

    with print_lock:
        if attack_type != AttackType.NONE:
            logger.info(
                f"Attack type {attack_type} from Bus {data_dict['FB']} to Bus {data_dict['TB']}"
            )

    output_queue.put(data_dict)
    send_to_cpp(data_dict)
    all_data.append(final_data)


def get_attack_delay(attack_type):
    """Calculate additional delay based on attack type"""
    base_delay = ATTACK_PARAMS[attack_type]["processing_delay"]
    if attack_type == AttackType.DDOS:
        # Add variable congestion delay based on queue size
        return base_delay + random.uniform(0.01, 0.05)
    elif attack_type == AttackType.SYN_FLOOD:
        # Add connection establishment delay
        return base_delay + random.uniform(0.05, 0.1)
    elif attack_type == AttackType.MITM_SCADA:
        # Add inspection and modification delay
        return base_delay + MITM_INTERCEPT_DELAY + random.uniform(0.1, 0.2)
    return 0


def get_packet_size(attack_type):
    """Generate appropriate packet sizes based on attack type"""
    base_size = ATTACK_PARAMS[attack_type]["packet_size"]
    if attack_type == AttackType.MITM_SCADA:
        return base_size + random.randint(0, MITM_PACKET_OVERHEAD)
    elif attack_type == AttackType.NONE:
        return random.gauss(base_size, 200)
    else:
        return base_size


def generate_attack_traffic(attack_type):
    """Generate attack traffic patterns based on type"""
    if attack_type == AttackType.MITM_SCADA:
        return 1.0 / SCADA_POLL_RATE + MITM_INTERCEPT_DELAY
    return random.expovariate(ATTACK_PARAMS[attack_type]["arrival_rate"])


def Rhop1(
    from_bus, to_bus, time_s, time_e, sampl, process_func, attack_type=AttackType.NONE
):
    k = 1
    pd = 0
    env = simpy.Environment()

    def arr():
        if attack_type == AttackType.DDOS:
            return random.expovariate(
                ATTACK_PARAMS[attack_type]["arrival_rate"]
            ) * random.uniform(0.8, 1.2)
        elif attack_type == AttackType.SYN_FLOOD:
            return random.uniform(0.0001, 0.0005)
        elif attack_type == AttackType.MITM_SCADA:
            # Slightly more variable timing for MITM to account for network conditions
            base_rate = 1.0 / ATTACK_PARAMS[attack_type]["arrival_rate"]
            jitter = random.uniform(-0.1, 0.1) * base_rate
            return base_rate + jitter + MITM_INTERCEPT_DELAY
        return random.expovariate(ATTACK_PARAMS[attack_type]["arrival_rate"])

    def psz():
        size = ATTACK_PARAMS[attack_type]["packet_size"]
        if attack_type == AttackType.MITM_SCADA:
            # More variable packet size for MITM
            return size + random.randint(0, MITM_PACKET_OVERHEAD)
        return size

    def sack():
        if attack_type == AttackType.MITM_SCADA:
            return SCADA_NORMAL_PACKET_SIZE
        elif attack_type == AttackType.SYN_FLOOD:
            return 0
        return 64

    attack_delay = get_attack_delay(attack_type)

    a = arr()
    s = psz()
    sa = sack()
    AR = float(s) / float(a) if a != 0 else float(s)

    ps = PacketSink(env, debug=False, rec_arrivals=True, absolute_arrivals=False)
    pg = PacketGenerator(env, "Greg", arr, psz)

    switch_port = SwitchPort(
        env,
        ATTACK_PARAMS[attack_type]["port_rate"],
        ATTACK_PARAMS[attack_type]["qlimit"],
    )

    pm = PortMonitor(env, switch_port, lambda: random.expovariate(1.0))

    pg.out = switch_port
    switch_port.out = ps

    env.run(until=15)

    # Calculate base metrics
    base_rtt = sum(ps.waits) / len(ps.waits) if ps.waits else 0
    packets_sent = pg.packets_sent
    packets_received = ps.packets_rec

    # Calculate packet drops based on attack type
    if attack_type == AttackType.MITM_SCADA:
        # Natural packet drops based on network conditions
        # Consider factors like:
        # 1. Queue occupancy
        queue_factor = (
            sum(pm.sizes) / ATTACK_PARAMS[attack_type]["qlimit"] if pm.sizes else 0
        )

        # 2. Network congestion approximation
        congestion_factor = base_rtt / (base_rtt + attack_delay)

        # 3. Random network errors (0.1% - 1% base error rate)
        base_error_rate = random.uniform(0.001, 0.01)

        # Calculate total drop probability
        drop_probability = (
            base_error_rate + (queue_factor * 0.05) + (congestion_factor * 0.02)
        )

        # Apply drops naturally based on conditions
        pd = int(packets_sent * drop_probability)

        # Add some randomness to avoid constant values
        pd = max(0, int(pd + random.randint(-2, 2)))

        RTT = base_rtt + attack_delay + MITM_INTERCEPT_DELAY
        TD = base_rtt + attack_delay
    elif attack_type == AttackType.SYN_FLOOD:
        # High packet drops due to connection timeouts
        pd = int(packets_sent * 0.3)
        RTT = base_rtt + attack_delay
        TD = RTT
    elif attack_type == AttackType.DDOS:
        # Very high packet drops due to congestion
        pd = int(packets_sent * 0.6)
        RTT = base_rtt * 2 + attack_delay
        TD = RTT
    else:
        # Normal traffic drops
        pd = packets_sent - packets_received
        RTT = base_rtt
        TD = RTT

    IAT = a
    AT = sum(ps.arrivals) / len(ps.arrivals) if ps.arrivals else 0
    pasz = s
    acksz = sa

    # Calculate queue metrics
    for i in range(len(pm.sizes)):
        if pm.sizes[i] != 0:
            k += 1

    # Adjust system occupancy based on attack type
    if attack_type == AttackType.DDOS:
        so = 0.95 + random.uniform(0, 0.05)
    elif attack_type == AttackType.SYN_FLOOD:
        so = 0.7 + random.uniform(0, 0.2)
    elif attack_type == AttackType.MITM_SCADA:
        # More natural occupancy calculation for MITM
        base_occupancy = sum(pm.sizes) / len(pm.sizes) if pm.sizes else 0
        so = min(0.95, base_occupancy * (1 + queue_factor))
    else:
        so = sum(pm.sizes) / len(pm.sizes) if pm.sizes else 0

    sr = AR / so if so != 0 else AR

    if attack_type == AttackType.DDOS:
        avqs = ATTACK_PARAMS[attack_type]["qlimit"] * 0.9
    elif attack_type == AttackType.SYN_FLOOD:
        avqs = ATTACK_PARAMS[attack_type]["qlimit"] * 0.6
    else:
        avqs = sum(pm.sizes) / k if k > 0 else 0

    time_now = datetime.now()
    timed = time.time()
    Time = time_now.strftime("%H:%M:%S:%f")

    send_to_queue_and_process(
        [
            from_bus,
            to_bus,
            IAT,
            TD,
            AT,
            ps.packets_rec,
            pasz,
            acksz,
            RTT,
            avqs,
            so,
            AR,
            sr,
            pd,
            Time,
            sampl,
            0,
            0,
            0,
            0,
        ],
        process_func,
        attack_type,
    )

    return (
        sr,
        acksz,
        pasz,
        AT,
        avqs,
        so,
        AR,
        timed,
        Time,
        RTT,
        TD,
        IAT,
        ps.packets_rec,
        pd,
        attack_type,
    )


bus_states = {}
bus_states_lock = threading.Lock()


def busping(fb, n, sampl, process_func):
    global simulation_running, bus_states
    while simulation_running and not stop_event.is_set():
        # Check if this bus is currently under attack
        with bus_states_lock:
            if bus_states.get(fb, False):
                time.sleep(0.1)  # Short sleep to prevent busy waiting
                continue

        for i in range(1, n):
            if fb != i:
                try:
                    Rhop1(fb, i, time_s, time_e, sampl, process_func, AttackType.NONE)
                except Exception as e:
                    logger.info(f"Exception in normal traffic: {str(e)}")
        time.sleep(random.uniform(0.1, 0.5))


def ddos_attack(duration, attack_fb, sampl, process_func):
    global attack_active, simulation_running, bus_states
    start_time = time.time()
    end_time = start_time + duration

    # Mark the bus as under attack
    with bus_states_lock:
        bus_states[attack_fb] = True
    attack_active = True

    try:
        while simulation_running and time.time() < end_time and not stop_event.is_set():
            num_sources = random.randint(10, 50)
            for _ in range(num_sources):
                for i in range(1, n):
                    if attack_fb != i:
                        try:
                            Rhop1(
                                attack_fb,
                                i,
                                time_s,
                                time_e,
                                sampl,
                                process_func,
                                attack_type=AttackType.DDOS,
                            )
                        except Exception as e:
                            logger.info(f"Exception in DDoS attack: {str(e)}")
            time.sleep(random.uniform(0.01, 0.05))
    finally:
        # Always ensure we clear the attack state
        with bus_states_lock:
            bus_states[attack_fb] = False
        attack_active = False
        logger.info(f"DDoS attack from Bus {attack_fb} has ended.")


def syn_flood_attack(duration, attack_fb, sampl, process_func):
    global attack_active, simulation_running, bus_states
    start_time = time.time()
    end_time = start_time + duration

    # Mark the bus as under attack
    with bus_states_lock:
        bus_states[attack_fb] = True
    attack_active = True

    try:
        while simulation_running and time.time() < end_time and not stop_event.is_set():
            target_port = random.randint(1, n - 1)
            if attack_fb != target_port:
                try:
                    Rhop1(
                        attack_fb,
                        target_port,
                        time_s,
                        time_e,
                        sampl,
                        process_func,
                        attack_type=AttackType.SYN_FLOOD,
                    )
                except Exception as e:
                    logger.info(f"Exception in SYN flood: {str(e)}")
            time.sleep(0.001)
    finally:
        # Always ensure we clear the attack state
        with bus_states_lock:
            bus_states[attack_fb] = False
        attack_active = False
        logger.info(f"SYN Flood attack from Bus {attack_fb} has ended.")


def mitm_scada_attack(duration, attack_fb, sampl, process_func):
    global attack_active, simulation_running, bus_states
    start_time = time.time()
    end_time = start_time + duration

    # Mark the bus as under attack
    with bus_states_lock:
        bus_states[attack_fb] = True
    attack_active = True

    try:
        while simulation_running and time.time() < end_time and not stop_event.is_set():
            for target_port in [1, 2, 3]:
                if attack_fb != target_port:
                    try:
                        Rhop1(
                            attack_fb,
                            target_port,
                            time_s,
                            time_e,
                            sampl,
                            process_func,
                            attack_type=AttackType.MITM_SCADA,
                        )
                        time.sleep(MITM_INTERCEPT_DELAY)
                    except Exception as e:
                        logger.info(f"Exception in MITM SCADA attack: {str(e)}")
            time.sleep(1.0 / SCADA_POLL_RATE)
    finally:
        # Always ensure we clear the attack state
        with bus_states_lock:
            bus_states[attack_fb] = False
        attack_active = False
        logger.info(f"MITM SCADA attack from Bus {attack_fb} has ended.")


def run_simulation(
    port, attack_type, total_simulation_time, attack_time, start_simulation
):
    global sock, simulation_running, attack_active, stop_event, bus_states

    try:
        logger.info("PYTHON: IN SIMULATION")
        stop_event.clear()
        simulation_running = True
        start = time.time()
        sampl = 1

        # Initialize bus states
        with bus_states_lock:
            bus_states.clear()
            for bus in range(1, n):
                bus_states[bus] = False

        if port is not None:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("localhost", port))
            except Exception as e:
                logger.error(f"Error setting up socket connection: {str(e)}")
                return

        threads = []
        for bus in [1, 2, 3]:
            t = threading.Thread(target=busping, args=(bus, n, sampl, queue.Queue()))
            t.daemon = True  # Make threads daemon so they exit when main thread exits
            t.start()
            threads.append(t)

        if attack_type != AttackType.NONE:
            attack_start_time = start + (total_simulation_time - attack_time) / 2
            attack_functions = {
                AttackType.DDOS: ddos_attack,
                AttackType.SYN_FLOOD: syn_flood_attack,
                AttackType.MITM_SCADA: mitm_scada_attack,
            }

            # Wait until it's time to start the attack
            while time.time() < attack_start_time and not stop_event.is_set():
                time.sleep(0.1)

            attack_thread = threading.Thread(
                target=attack_functions[attack_type],
                args=(attack_time, attack_fb, sampl, queue.Queue()),
            )
            attack_thread.daemon = True
            attack_thread.start()
            threads.append(attack_thread)

        simulation_end_time = start + total_simulation_time
        while time.time() < simulation_end_time and not stop_event.is_set():
            time.sleep(0.1)

        logger.info("Simulation complete")
        simulation_running = False
        stop_event.set()

        # Give threads a chance to clean up
        for t in threads:
            t.join(timeout=1.0)

        write_to_csv()

        if sock is not None:
            sock.close()

    except Exception as e:
        print(f"Error in Python simulation: {str(e)}")
        traceback.print_exc()
    finally:
        simulation_running = False
        stop_event.set()


def write_to_csv():
    list_column = [
        "FB",
        "TB",
        "IAT",
        "TD",
        "Arrival Time",
        "PC",
        "Packet Size",
        "Acknowledgement Packet Size",
        "RTT",
        "Average Queue Size",
        "System Occupancy",
        "Arrival Rate",
        "Service Rate",
        "Packet Dropped",
        "Time",
        "Sample",
        "attack_none",
        "attack_ddos",
        "attack_synflood",
        "attack_mitm",
    ]

    # Ensure data alignment
    aligned_data = []
    for row in all_data:
        # If the row doesn't have attack indicators (old format)
        if len(row) < len(list_column):
            # Fill in missing values
            while len(row) < len(list_column):
                row.append(0)
        # If row has extra columns (misaligned data)
        elif len(row) > len(list_column):
            # Trim to correct length, keeping only the valid data
            row = row[: len(list_column)]
        aligned_data.append(row)

    with open("network_traffic.csv", "w", newline="") as entry:
        writer = csv.writer(entry)
        writer.writerow(list_column)
        writer.writerows(aligned_data)

    logger.info(
        "CSV file 'network_traffic.csv' has been created with all simulation data."
    )


def stop_simulation():
    global stop_event
    stop_event.set()


if __name__ == "__main__":
    output_queue = queue.Queue()

    # Parse attack type from command line
    attack_type = AttackType.NONE
    if len(sys.argv) > 1:
        attack_map = {
            "none": AttackType.NONE,
            "ddos": AttackType.DDOS,
            "synflood": AttackType.SYN_FLOOD,
            "mitm": AttackType.MITM_SCADA,
        }
        attack_type = attack_map.get(sys.argv[1].lower(), AttackType.NONE)

    # Handle port parameter
    port = None
    if len(sys.argv) > 2:
        if sys.argv[2].lower() != "none":
            try:
                port = int(sys.argv[2])
            except ValueError:
                print(f"Invalid port value: {sys.argv[2]}")
                sys.exit(1)

    total_simulation_time = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    attack_time = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    start_simulation = len(sys.argv) > 5 and sys.argv[5].lower() == "true"

    run_simulation(
        port, attack_type, total_simulation_time, attack_time, start_simulation
    )
