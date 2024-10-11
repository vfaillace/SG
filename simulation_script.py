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

time_s = datetime.now()
time_e = datetime.now()
print_lock = threading.Lock()
all_data = []
simulation_running = True
dos_attack_active = False
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
                data["Is Attack"],
            ]
            sock.sendall(json.dumps(ordered_data).encode())
        except Exception as e:
            print(f"Error sending data to C++: {e}")


def send_to_queue_and_process(data, output_queue, is_attack=False):
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
        "Is Attack",
    ]
    data_dict = dict(zip(list_column, data))

    with print_lock:
        if is_attack:
            logger.info(
                f"DOS Attack: From Bus {data_dict['FB']} to Bus {data_dict['TB']}"
            )

    output_queue.put(data_dict)
    send_to_cpp(data_dict)
    all_data.append(data)


def adist():
    return random.expovariate(0.5)


def sdist():
    return random.expovariate(0.1)


def sdistL():
    return 1300


def sdistLack():
    return 64


def samp_dist():
    return random.expovariate(1.0)


def Rhop1(from_bus, to_bus, time_s, time_e, sampl, process_func, is_attack=False):
    k = 1
    pd = 0
    env = simpy.Environment()

    a = random.expovariate(7)

    def arr():
        return a if not is_attack else random.expovariate(1000)

    s = random.expovariate(0.001)

    def psz():
        return s

    sa = random.expovariate(0.064)

    def sack():
        return sa

    AR = float(s) / float(a)
    ps = PacketSink(env, debug=False, rec_arrivals=True, absolute_arrivals=False)
    pg = PacketGenerator(env, "Greg", arr, psz)
    switch_port = SwitchPort(
        env,
        port_rate_norm if not is_attack else port_rate_attack,
        qlimit_norm if not is_attack else qlimit_attack,
    )
    pm = PortMonitor(env, switch_port, samp_dist)

    pg.out = switch_port
    switch_port.out = ps

    env.run(until=15)

    pg2 = PacketGenerator(env, "", arr, sack)
    ps2 = PacketSink(env, debug=False, rec_arrivals=True, absolute_arrivals=False)
    pg2.out = switch_port
    switch_port.out = ps2

    env.run(until=16)

    RTT = sum(ps.waits) / len(ps.waits) if len(ps.waits) > 0 else 0
    RTT += sum(ps2.waits) / len(ps2.waits) if len(ps2.waits) > 0 else 0
    RTT += sum(ps.arrivals) / len(ps.arrivals)
    TD = sum(ps.waits) / len(ps.waits) if len(ps.waits) > 0 else 0
    IAT = a
    AT = sum(ps.arrivals) / len(ps.arrivals)
    pasz = s
    acksz = sa

    for i in range(len(pm.sizes)):
        if pm.sizes[i] != 0:
            k += 1

    so = sum(pm.sizes) / len(pm.sizes)
    sr = AR / so if so != 0 else AR

    avqs = sum(pm.sizes) / k
    pd = pg.packets_sent - ps.packets_rec
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
            1 if is_attack else 0,
        ],
        process_func,
        is_attack,
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
        1 if is_attack else 0,
    )


def busping(fb, n, sampl, process_func):
    global dos_attack_active, simulation_running, dos_fb
    while simulation_running and not stop_event.is_set():
        for i in range(1, n):
            if fb != i and (fb != dos_fb or not dos_attack_active):
                try:
                    Rhop1(fb, i, time_s, time_e, sampl, process_func, is_attack=False)
                except Exception as e:
                    logger.info(f"Exception occurred in Rhop1 during busping: {str(e)}")
        time.sleep(random.uniform(0.1, 0.5))


def dos_attack(duration, attack_fb, sampl, process_func):
    global dos_attack_active, simulation_running, dos_fb
    start_time = time.time()
    end_time = start_time + duration
    dos_attack_active = True
    while simulation_running and time.time() < end_time and not stop_event.is_set():
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
                        is_attack=True,
                    )
                except Exception as e:
                    logger.info(
                        f"Exception occurred in Rhop1 during dos attack: {str(e)}"
                    )
        time.sleep(random.uniform(0.1, 0.5))
    dos_attack_active = False
    dos_fb = None
    logger.info(f"DoS attack from Bus {attack_fb} has ended.")


port_rate_norm = 100000.0
qlimit_norm = 1000000
port_rate_attack = 10000.0
qlimit_attack = 100000
n = 4
dos_fb = 2


def run_simulation(
    port, include_dos, total_simulation_time, dos_attack_time, start_simulation
):
    global sock, simulation_running, dos_attack_active, stop_event

    try:
        logger.info("PYTHON: IN SIMULATION")
        stop_event.clear()
        start = time.time()
        sampl = 1

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
            t.start()
            threads.append(t)

        if include_dos:
            dos_start_time = start + (total_simulation_time - dos_attack_time) / 2
            dos_thread = threading.Thread(
                target=dos_attack, args=(dos_attack_time, dos_fb, sampl, queue.Queue())
            )
            dos_thread.start()
            threads.append(dos_thread)

        simulation_end_time = start + total_simulation_time
        while time.time() < simulation_end_time and not stop_event.is_set():
            if include_dos and time.time() >= dos_start_time and not dos_attack_active:
                dos_attack_active = True
            time.sleep(0.1)

        logger.info("Simulation complete")
        simulation_running = False

        for t in threads:
            t.join()

        write_to_csv()

        if sock is not None:
            sock.close()

    except Exception as e:
        print(f"Error in Python simulation: {str(e)}")
        traceback.print_exc()


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
        "Is Attack",
    ]

    with open("network_traffic.csv", "w", newline="") as entry:
        writer = csv.writer(entry)
        writer.writerow(list_column)
        writer.writerows(all_data)

    logger.info(
        "CSV file 'network_traffic.csv' has been created with all simulation data."
    )


def stop_simulation():
    global stop_event
    stop_event.set()


if __name__ == "__main__":
    output_queue = queue.Queue()
    include_dos = len(sys.argv) > 1 and sys.argv[1].lower() == "true"

    # Handle the port parameter
    port = None
    if len(sys.argv) > 2:
        if sys.argv[2].lower() == "none":
            port = None
        else:
            try:
                port = int(sys.argv[2])
            except ValueError:
                print(f"Invalid port value: {sys.argv[2]}")
                sys.exit(1)

    total_simulation_time = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    dos_attack_time = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    start_simulation = len(sys.argv) > 5 and sys.argv[5].lower() == "true"

    run_simulation(
        port, include_dos, total_simulation_time, dos_attack_time, start_simulation
    )
