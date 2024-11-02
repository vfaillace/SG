import pyshark
import time
from collections import defaultdict
import statistics
import logging
from datetime import datetime
import csv
import numpy as np
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NetworkMetricsRecorder:
    def __init__(self, interface_name):
        self.interface = interface_name
        self.running = False
        self.capture = None

        # Store connection data
        self.connections = defaultdict(
            lambda: {
                "packets": [],
                "sizes": [],
                "times": [],
                "tcp_flags": [],
                "protocols": [],
                "retransmissions": 0,
                "last_metrics_time": time.time(),
            }
        )

        # Store all samples for CSV
        self.samples = []

        # Metrics update interval
        self.update_interval = 1.0  # 1 second

    def start_capture(self):
        """Start capturing network traffic"""
        try:
            logger.info(f"Starting capture on interface: {self.interface}")
            self.running = True

            # Set up capture with display filter for common protocols
            self.capture = pyshark.LiveCapture(
                interface=self.interface, display_filter="ip"  # Capture all IP traffic
            )

            # Process packets
            for packet in self.capture.sniff_continuously():
                if not self.running:
                    break
                self._process_packet(packet)

        except KeyboardInterrupt:
            logger.info("Capture stopped by user")
        except Exception as e:
            logger.error(f"Error during capture: {str(e)}")
        finally:
            self.save_to_csv()

    def stop_capture(self):
        """Stop the capture and save data"""
        self.running = False
        if self.capture:
            self.capture.close()
        self.save_to_csv()

    def _process_packet(self, packet):
        """Process a single packet and record metrics"""
        try:
            if not hasattr(packet, "ip"):
                return

            # Basic packet information
            src_ip = packet.ip.src
            dst_ip = packet.ip.dst
            timestamp = float(packet.sniff_timestamp)
            length = int(packet.length)
            protocol = (
                packet.transport_layer
                if hasattr(packet, "transport_layer")
                else "Unknown"
            )

            conn_key = (src_ip, dst_ip)
            conn_data = self.connections[conn_key]

            # Update connection data
            conn_data["packets"].append(packet)
            conn_data["sizes"].append(length)
            conn_data["times"].append(timestamp)
            conn_data["protocols"].append(protocol)

            # Record TCP-specific data
            if hasattr(packet, "tcp"):
                conn_data["tcp_flags"].append(
                    {
                        "syn": packet.tcp.flags_syn,
                        "ack": packet.tcp.flags_ack,
                        "rst": packet.tcp.flags_reset,
                        "fin": packet.tcp.flags_fin,
                    }
                )

                # Check for retransmissions
                if hasattr(packet.tcp, "analysis_retransmission"):
                    conn_data["retransmissions"] += 1

            # Calculate metrics periodically
            current_time = time.time()
            if current_time - conn_data["last_metrics_time"] >= self.update_interval:
                self._calculate_and_store_metrics(conn_key, conn_data)
                conn_data["last_metrics_time"] = current_time

                # Maintain a rolling window of data (last 60 seconds)
                cutoff_time = current_time - 60
                for key in ["packets", "sizes", "times", "tcp_flags", "protocols"]:
                    if conn_data["times"]:
                        while conn_data[key] and conn_data["times"][0] < cutoff_time:
                            conn_data[key].pop(0)

        except Exception as e:
            logger.error(f"Error processing packet: {str(e)}")

    def _calculate_and_store_metrics(self, conn_key, conn_data):
        """Calculate available metrics and store them"""
        src_ip, dst_ip = conn_key
        current_time = time.time()

        # Only calculate metrics if we have enough data
        if not conn_data["times"] or not conn_data["sizes"]:
            return

        # Time window for rate calculations (last 5 seconds)
        window = 5.0
        recent_times = [t for t in conn_data["times"] if t >= current_time - window]
        recent_sizes = conn_data["sizes"][-len(recent_times) :]

        # Calculate directly measurable metrics
        metrics = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_ip": src_ip,
            "dest_ip": dst_ip,
            # Packet metrics
            "packet_count": len(recent_times),
            "packet_rate": len(recent_times) / window if recent_times else 0,
            "avg_packet_size": statistics.mean(recent_sizes) if recent_sizes else 0,
            "min_packet_size": min(recent_sizes) if recent_sizes else 0,
            "max_packet_size": max(recent_sizes) if recent_sizes else 0,
            # Timing metrics
            "inter_arrival_time": (
                statistics.mean(np.diff(recent_times)) if len(recent_times) > 1 else 0
            ),
            "last_packet_time": recent_times[-1] if recent_times else current_time,
            # Throughput metrics
            "bytes_per_second": sum(recent_sizes) / window if recent_times else 0,
            # TCP metrics
            "retransmissions": conn_data["retransmissions"],
            "protocol": max(
                set(conn_data["protocols"]), key=conn_data["protocols"].count
            ),
        }

        # Calculate TCP flag statistics if available
        if conn_data["tcp_flags"]:
            tcp_metrics = {
                "syn_count": sum(1 for f in conn_data["tcp_flags"] if f["syn"] == "1"),
                "rst_count": sum(1 for f in conn_data["tcp_flags"] if f["rst"] == "1"),
                "fin_count": sum(1 for f in conn_data["tcp_flags"] if f["fin"] == "1"),
            }
            metrics.update(tcp_metrics)

        # Store the sample
        self.samples.append(metrics)

        # Print current metrics
        print("\n" + "=" * 80)
        print(f"Connection Metrics ({metrics['timestamp']})")
        print("=" * 80)
        for key, value in metrics.items():
            print(f"{key}: {value}")
        print("-" * 80)

    def save_to_csv(self):
        """Save all collected metrics to CSV file"""
        if not self.samples:
            logger.warning("No samples to save")
            return

        filename = f"network_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Get all possible fields from all samples
        fieldnames = set()
        for sample in self.samples:
            fieldnames.update(sample.keys())
        fieldnames = sorted(list(fieldnames))

        try:
            with open(filename, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for sample in self.samples:
                    writer.writerow(sample)
            logger.info(f"Saved metrics to {filename}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")


def main():
    import sys

    # List available interfaces
    try:
        print("Available network interfaces:")
        capture = pyshark.LiveCapture()
        interfaces = capture.interfaces
        for i, interface in enumerate(interfaces):
            print(f"{i}: {interface}")
    except Exception as e:
        print(f"Error listing interfaces: {e}")
        return

    # Get interface from command line or user input
    if len(sys.argv) > 1:
        interface = sys.argv[1]
    else:
        try:
            interface_idx = int(input("\nEnter interface number to monitor: "))
            interface = interfaces[interface_idx]
        except (ValueError, IndexError):
            print("Invalid interface selection")
            return

    print(f"\nStarting network monitoring on interface: {interface}")
    print("Press Ctrl+C to stop capturing")

    recorder = NetworkMetricsRecorder(interface)

    try:
        recorder.start_capture()
    except KeyboardInterrupt:
        print("\nStopping capture...")
        recorder.stop_capture()
    except Exception as e:
        print(f"Error during capture: {e}")
    finally:
        print("Capture ended")


if __name__ == "__main__":
    main()
