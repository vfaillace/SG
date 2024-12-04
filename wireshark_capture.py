import sys
import time
import logging
import socket
import json
import asyncio
import threading
from datetime import datetime
import traceback
import pyshark
import queue
from concurrent.futures import ThreadPoolExecutor
import csv

print("wireshark_capture.py: Starting execution")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wireshark_capture.log')
    ]
)
logger = logging.getLogger(__name__)

# Global variables
sock = None
stop_event = threading.Event()
csv_lock = threading.Lock()  # Add lock for thread-safe CSV writing
all_data = []
capture_running = True

# Create CSV file and write headers at startup
list_column = [
    "FB", "TB", "IAT", "TD", "Arrival Time", "PC", "Packet Size",
    "Acknowledgement Packet Size", "RTT", "Average Queue Size",
    "System Occupancy", "Arrival Rate", "Service Rate", "Packet Dropped",
    "Time", "Sample", "attack_none", "attack_ddos", "attack_synflood", "attack_mitm"
]

def initialize_csv():
    with open("network_traffic.csv", "w", newline="") as entry:
        writer = csv.writer(entry)
        writer.writerow(list_column)
    logger.info("Created new network_traffic.csv file with headers")

def write_row_to_csv(data):
    """Write a single row of data to the CSV file"""
    try:
        with csv_lock, open("network_traffic.csv", "a", newline="") as entry:
            writer = csv.writer(entry)
            row = [
                data["FB"], data["TB"], data["IAT"], data["TD"],
                data["Arrival Time"], data["PC"], data["Packet Size"],
                data["Acknowledgement Packet Size"], data["RTT"],
                data["Average Queue Size"], data["System Occupancy"],
                data["Arrival Rate"], data["Service Rate"], data["Packet Dropped"],
                data["Time"], data["Sample"], data["attack_none"], 
                data["attack_ddos"], data["attack_synflood"], data["attack_mitm"]
            ]
            writer.writerow(row)
    except Exception as e:
        logger.error(f"Error writing to CSV: {e}")
        logger.error(traceback.format_exc())

class IPMapper:
    def __init__(self):
        self.ip_to_index = {}
        self.next_index = 1
        self.lock = threading.Lock()

    def get_index(self, ip):
        with self.lock:
            if ip not in self.ip_to_index:
                self.ip_to_index[ip] = self.next_index
                self.next_index += 1
            return self.ip_to_index[ip]

    def get_mapping(self):
        with self.lock:
            return {v: k for k, v in self.ip_to_index.items()}

ip_mapper = IPMapper()

class WiresharkCapture:
    def __init__(self, interface_name):
        self.interface = interface_name
        self.capture = None
        self.ip_mapper = ip_mapper
        self.stop_requested = False
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        logger.info(f"Initialized WiresharkCapture with interface: {interface_name}")

    def packet_callback(self, packet):
        """Synchronous packet processing"""
        try:
            if self.stop_requested or stop_event.is_set():
                return False

            if not hasattr(packet, 'ip'):
                return True

            src_ip = packet.ip.src
            dst_ip = packet.ip.dst

            fb = self.ip_mapper.get_index(src_ip)
            tb = self.ip_mapper.get_index(dst_ip)

            metrics = {
                "FB": fb,
                "TB": tb,
                "IAT": float(packet.time) if hasattr(packet, 'time') else 0.0,
                "TD": 0.0,
                "Arrival Time": float(packet.sniff_timestamp),
                "PC": 1,
                "Packet Size": int(packet.length),
                "Acknowledgement Packet Size": 64,
                "RTT": 0.0,
                "Average Queue Size": 0.0,
                "System Occupancy": 0.0,
                "Arrival Rate": 0.0,
                "Service Rate": 0.0,
                "Packet Dropped": 0,
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Sample": 1,
                "attack_none": 1,
                "attack_ddos": 0,
                "attack_synflood": 0,
                "attack_mitm": 0
            }

            if hasattr(packet, 'tcp'):
                metrics["RTT"] = float(packet.tcp.analysis_ack_rtt) if hasattr(packet.tcp, 'analysis_ack_rtt') else 0.0
                metrics["TD"] = float(packet.tcp.time_delta) if hasattr(packet.tcp, 'time_delta') else 0.0

            # Write to CSV immediately
            write_row_to_csv(metrics)
            
            # Store in memory and send to C++
            all_data.append(metrics)
            send_to_cpp(metrics)
            return True

        except Exception as e:
            logger.error(f"Error processing packet: {e}")
            logger.error(traceback.format_exc())
            return False

    def start_capture(self):
        """Start packet capture using synchronous approach"""
        try:
            logger.info(f"Starting capture on interface: {self.interface}")
            
            # Initialize new CSV file
            initialize_csv()
            
            # Create capture instance
            self.capture = pyshark.LiveCapture(
                interface=self.interface,
                display_filter='ip'
            )

            logger.info("Beginning packet capture...")
            
            # Use synchronous sniffing with callback
            for packet in self.capture.sniff_continuously():
                if self.stop_requested or stop_event.is_set():
                    break
                if not self.packet_callback(packet):
                    break

        except Exception as e:
            logger.error(f"Capture error: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.cleanup()

    def cleanup(self):
        logger.info("Cleaning up capture...")
        if self.capture:
            try:
                self.capture.close()
            except:
                pass
        
        logger.info("Final IP to Index mapping:")
        mapping = self.ip_mapper.get_mapping()
        for idx, ip in mapping.items():
            logger.info(f"  Index {idx}: {ip}")

    def stop_capture(self):
        self.stop_requested = True
        if self.capture:
            try:
                logger.info(f"capture stopped")
                self.capture.close()
            except:
                pass

class StopCapture(Exception):
    pass

def send_to_cpp(data):
    global sock
    if sock is not None:
        try:
            current_time = time.time()
            ordered_data = [
                data["FB"], data["TB"], data["IAT"], data["TD"],
                data["Arrival Time"], data["PC"], data["Packet Size"],
                data["Acknowledgement Packet Size"], data["RTT"],
                data["Average Queue Size"], data["System Occupancy"],
                data["Arrival Rate"], data["Service Rate"],
                data["Packet Dropped"], current_time, data["Sample"],
                data["attack_none"], data["attack_ddos"],
                data["attack_synflood"], data["attack_mitm"]
            ]
            
            json_str = json.dumps(ordered_data) + "\n"
            sock.send(json_str.encode())
            return True
        except Exception as e:
            logger.error(f"Error sending data to C++: {e}")
            logger.error(traceback.format_exc())
            return False
    return False

def verify_socket_connection(port):
    global sock
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', port))
        logger.info(f"Successfully connected to C++ on port {port}")
        return True
    except Exception as e:
        logger.error(f"Socket connection failed: {e}")
        logger.error(traceback.format_exc())
        return False

def run_capture(interface_idx, port):
    global sock, capture_running

    try:
        logger.info(f"Starting capture with interface {interface_idx} on port {port}")

        if not verify_socket_connection(port):
            logger.error("Failed to establish socket connection")
            return

        # Get available interfaces
        capture = pyshark.LiveCapture()
        interfaces = capture.interfaces
        capture.close()

        if not (0 <= interface_idx < len(interfaces)):
            logger.error(f"Invalid interface index: {interface_idx}")
            return

        interface_name = interfaces[interface_idx]
        logger.info(f"Selected interface: {interface_name}")

        wireshark = WiresharkCapture(interface_name)
        
        def check_for_stop_command():
            try:
                # Use select for non-blocking socket check
                ready = select.select([sock], [], [], 0)
                if ready[0]:
                    data = sock.recv(1024)
                    if data:
                        command = json.loads(data.decode())
                        if command.get("command") == "stop_capture":
                            return True
            except:
                pass
            return False

        # Start monitor thread
        def monitor_stop_commands():
            while capture_running and not stop_event.is_set():
                if check_for_stop_command():
                    logger.info("Stop command received")
                    wireshark.stop_capture()
                    break
                time.sleep(0.1)

        monitor_thread = threading.Thread(target=monitor_stop_commands)
        monitor_thread.daemon = True
        monitor_thread.start()

        # Start capture in current thread
        wireshark.start_capture()

        # Wait for monitor thread
        monitor_thread.join(timeout=1.0)

        # Write captured data
        write_to_csv()

    except Exception as e:
        logger.error(f"Capture failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        capture_running = False
        if sock:
            sock.close()
            sock = None


def write_to_csv():
    list_column = [
        "FB", "TB", "IAT", "TD", "Arrival Time", "PC", "Packet Size",
        "Acknowledgement Packet Size", "RTT", "Average Queue Size",
        "System Occupancy", "Arrival Rate", "Service Rate", "Packet Dropped",
        "Time", "Sample", "attack_none", "attack_ddos", "attack_synflood", "attack_mitm"
    ]

    with open("network_traffic.csv", "w", newline="") as entry:
        writer = csv.writer(entry)
        writer.writerow(list_column)
        writer.writerows(all_data)

    logger.info("CSV file 'network_traffic.csv' has been created with captured data.")

if __name__ == "__main__":
    try:
        logger.info("Script started directly")
        logger.info(f"Arguments: {sys.argv}")

        if len(sys.argv) > 2:
            interface_idx = int(sys.argv[1])
            port = int(sys.argv[2])
        else:
            logger.warning("No arguments provided, using defaults")
            interface_idx = 0
            port = 12345

        logger.info(f"Using interface_idx: {interface_idx}, port: {port}")
        run_capture(interface_idx, port)

    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        stop_event.set()