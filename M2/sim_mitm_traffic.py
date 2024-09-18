import random
from datetime import datetime
import time as time_module
import simpy
from SimComponents import PacketGenerator, PacketSink, SwitchPort, PortMonitor

import numpy as np
import pandas as pd
import csv
import threading
import matplotlib.pyplot as plt

# Global variable definition
time_s = datetime.now()
time_e = datetime.now()

def Measurements(FB, TB, IAT, TD, PC, RTT, avqs, so, AR, pd, Time, sample, is_attack):
    """
    Function to write simulation measurements to a CSV file.
    """
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
    list_row = []

    for i in range(min(len(), len(sample))):  # Iterate over the shorter of the two lists
        list_temp = [
            FB[i],
            TB[i],
            IAT[i],
            TD[i],
            ATm[i],
            PC[i],
            PACKSZ[i],
            ACKSZ[i],
            RTT[i],
            avqs[i],
            so[i],
            AR[i],
            SR[i],
            pd[i],
            Time[i],
            sample[i],
            is_attack[i],
        ]
        list_row.append(list_temp)

    with open("mitm1_network_traffic.csv", "w", newline="") as entry:
        writer = csv.writer(entry)
        writer.writerow(list_column)
        writer.writerows(list_row)

def sampling(sampletime, sample):
    """
    Function to sample the simulation time.
    """
    s = 1
    p = sampletime[0]
    for i in range(len(sampletime)):
        if sampletime[i] - p > 0.125:
            s += 1
            p = sampletime[i]
        sample.append(s)

# Set up arrival and packet size distributions
adistl = np.zeros(shape=(1000))
for i in range(1000):
    adistl[i] = random.expovariate(0.5)

def adist():
    return random.choice(adistl)

sdist_list = np.zeros(shape=(1000))
for i in range(1000):
    sdist_list[i] = random.expovariate(0.1)

def sdist():
    return random.choice(sdist_list)

sdistL = np.zeros(shape=(1000))
for i in range(1000):
    sdistL[i] = 1300

def sdistL():
    return random.choice(sdistL)

sdistLack = np.zeros(shape=(1000))
for i in range(1000):
    sdistLack[i] = 64

def sdistLack():
    return random.choice(sdistLack)

samp_dist_list = np.zeros(shape=(1000))
for i in range(1000):
    samp_dist_list[i] = random.expovariate(1.0)

def samp_dist():
    return random.choice(samp_dist_list)

def Rhop1(n, nack, time_s, time_e, sampl, is_attack=False):
    """
    Function to simulate a single-hop network and measure various metrics.
    """
    k = 1
    pd = 0
    env = simpy.Environment()

    # Create packet generators and sink
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
    switch_port = SwitchPort(env, port_rate_norm if not is_attack else port_rate_attack, qlimit_norm if not is_attack else qlimit_attack)
    pm = PortMonitor(env, switch_port, samp_dist)

    # Wire packet generators, switch ports, and sinks together
    pg.out = switch_port
    switch_port.out = ps

    # Run simulation
    env.run(until=15)
    pg2 = PacketGenerator(env, "", arr, sack)
    ps2 = PacketSink(env, debug=False, rec_arrivals=True, absolute_arrivals=False)
    pg2.out = switch_port
    switch_port.out = ps2
    env.run(until=16)

    # Calculate metrics
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
    if so == 0:
        sr = AR
    else:
        sr = AR / so

    avqs = sum(pm.sizes) / k
    pd = pg.packets_sent - ps.packets_rec
    time_now = datetime.now()
    timed = time_module.time()
    Time = time_now.strftime("%H:%M:%S:%f")

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

def busping(fb, tb, n, is_attack=False):
    """
    Function to simulate network traffic between buses.
    """
    for i in range(1, n):
        if fb != i:
            try:
                (
                    sr,
                    acksz,
                    packsz,
                    AT,
                    AVQS,
                    SO,
                    ar,
                    samptime,
                    time,
                    rtt,
                    td,
                    iat,
                    pr,
                    PD,
                    is_attack_flag,
                ) = Rhop1(sdistL, sdistLack, time_s, time_e, sampl, is_attack)
                SR.append(sr)
                ACKSZ.append(acksz)
                PACKSZ.append(packsz)
                ATm.append(AT)
                AR.append(ar)
                so.append(SO)
                RTT.append(rtt)
                TD.append(td)
                IAT.append(iat)
                PR.append(pr)
                Time.append(time)
                sampletime.append(samptime)
                avqs.append(AVQS)
                pd.append(PD)
                FB.append(fb)
                TB.append(i)
                is_attack_list.append(is_attack_flag)
            except Exception as e:
                print(f"Exception occurred in Rhop1 during busping: {str(e)}")

def mitm_attack(duration, victim_fb, victim_tb, attacker_fb):
    """
    Function to simulate a Man-in-the-Middle (MITM) attack.
    """
    start_time = time_module.time()
    end_time = start_time + duration

    while time_module.time() < end_time:
        try:
            # Simulate the attacker intercepting traffic from victim_fb to victim_tb
            (
                sr,
                acksz,
                packsz,
                AT,
                AVQS,
                SO,
                ar,
                samptime,
                time_str,
                rtt,
                td,
                iat,
                pr,
                PD,
                is_attack_flag,
            ) = Rhop1(sdistL, sdistLack, time_s, time_e, sampl, is_attack=True)

            # Simulate the attacker modifying the intercepted traffic
            modified_packsz = packsz + random.randint(100, 500)  # Increase packet size
            modified_rtt = rtt + random.uniform(0.1, 0.5)  # Increase RTT
            modified_td = td + random.uniform(0.1, 0.5)  # Increase transmission delay

            # Simulate the attacker relaying the modified traffic to victim_tb
            (
                sr_relay,
                acksz_relay,
                packsz_relay,
                AT_relay,
                AVQS_relay,
                SO_relay,
                ar_relay,
                samptime_relay,
                time_str_relay,
                rtt_relay,
                td_relay,
                iat_relay,
                pr_relay,
                PD_relay,
                is_attack_flag_relay,
            ) = Rhop1(sdistL, sdistLack, time_s, time_e, sampl, is_attack=True)

            # Append the attacker's and relay traffic data to the respective lists
            SR.append(sr)
            ACKSZ.append(acksz)
            PACKSZ.append(modified_packsz)
            ATm.append(AT)
            AR.append(ar)
            so.append(SO)
            RTT.append(modified_rtt)
            TD.append(modified_td)
            IAT.append(iat)
            PR.append(pr)
            Time.append(time_str)
            sampletime.append(samptime)
            avqs.append(AVQS)
            pd.append(PD)
            FB.append(attacker_fb)
            TB.append(victim_tb)
            is_attack_list.append(is_attack_flag)

            SR.append(sr_relay)
            ACKSZ.append(acksz_relay)
            PACKSZ.append(packsz_relay)
            ATm.append(AT_relay)
            AR.append(ar_relay)
            so.append(SO_relay)
            RTT.append(rtt_relay)
            TD.append(td_relay)
            IAT.append(iat_relay)
            PR.append(pr_relay)
            Time.append(time_str_relay)
            sampletime.append(samptime_relay)
            avqs.append(AVQS_relay)
            pd.append(PD_relay)
            FB.append(victim_fb)
            TB.append(victim_tb)
            is_attack_list.append(is_attack_flag_relay)

            print(f"MITM Attack: Attacker {attacker_fb} intercepting traffic from {victim_fb} to {victim_tb}")
        except Exception as e:
            print(f"Exception occurred in MITM attack: {str(e)}")

        time_module.sleep(random.uniform(0.1, 0.5))  # Add random delays between attack packets

# Variables for switch function in simulation
port_rate_norm = 100000.0
qlimit_norm = 1000000
port_rate_attack = 10000.0  # Lower port rate for attack traffic
qlimit_attack = 100000  # Lower queue limit for attack traffic
n = 14

if __name__ == "__main__":
    (
        FB,
        TB,
        RTT,
        TD,
        PR,
        IAT,
        Time,
        sample,
        sampletime,
        AR,
        SR,
        so,
        avqs,
        pd,
        ACKSZ,
        ATm,
        PACKSZ,
        is_attack_list,
    ) = ([] for _ in range(18))
    start = time_module.time()
    end = time_module.time()
    sampl = 1

    mitm_duration = 120  # Duration of the MITM attack in seconds
    mitm_victim_fb = 1  # Source bus (victim) whose traffic is being intercepted
    mitm_victim_tb = 14  # Destination bus (victim) whose traffic is being intercepted
    mitm_attacker_fb = 7  # Attacker's bus from which the MITM attack is launched

    # Start MITM attack thread
    mitm_thread = threading.Thread(target=mitm_attack, args=(mitm_duration, mitm_victim_fb, mitm_victim_tb, mitm_attacker_fb))
    mitm_thread.start()

    while end < start + 120:
        # Start threads for each bus ping
        t1 = threading.Thread(target=busping, args=(1, TB, n))
        t1.start()
        t8 = threading.Thread(target=busping, args=(8, TB, n))
        t8.start()
        t3 = threading.Thread(target=busping, args=(3, TB, n))
        t3.start()
        t10 = threading.Thread(target=busping, args=(10, TB, n))
        t10.start()
        t5 = threading.Thread(target=busping, args=(5, TB, n))
        t5.start()
        t12 = threading.Thread(target=busping, args=(12, TB, n))
        t12.start()
        t7 = threading.Thread(target=busping, args=(7, TB, n))
        t7.start()
        t9 = threading.Thread(target=busping, args=(9, TB, n))
        t9.start()
        t2 = threading.Thread(target=busping, args=(2, TB, n))
        t2.start()
        t11 = threading.Thread(target=busping, args=(11, TB, n))
        t11.start()
        t4 = threading.Thread(target=busping, args=(4, TB, n))
        t4.start()
        t13 = threading.Thread(target=busping, args=(13, TB, n))
        t13.start()
        t6 = threading.Thread(target=busping, args=(6, TB, n))
        t6.start()
        end = time_module.time()

    # Wait for all threads to complete
    t1.join()
    t8.join()
    t3.join()
    t10.join()
    t5.join()
    t12.join()
    t7.join()
    t9.join()
    t2.join()
    t11.join()
    t4.join()
    t13.join()
    t6.join()

    # Wait for MITM attack thread to finish
    mitm_thread.join()

    sampling(sampletime, sample)
    Measurements(FB, TB, IAT, TD, PR, RTT, avqs, so, AR, pd, Time, sample, is_attack_list)