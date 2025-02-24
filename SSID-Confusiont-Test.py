import argparse
import os
import subprocess
import signal
import sys

# Function to create Hostapd configuration files
def create_hostapd_config(ssid, iface, filename):
    config = f"""
    interface={iface}
    ssid={ssid}
    hw_mode=g
    channel=1
    macaddr_acl=0
    auth_algs=1
    ignore_broadcast_ssid=0
    wpa=2
    wpa_passphrase=yourpassword
    wpa_key_mgmt=WPA-PSK
    wpa_pairwise=TKIP
    rsn_pairwise=CCMP
    """
    with open(filename, 'w') as file:
        file.write(config.strip())

# Function to start Hostapd
def start_hostapd(config_file):
    return subprocess.Popen(['hostapd', config_file])

# Function to start tcpdump
def start_tcpdump(iface, output_file):
    return subprocess.Popen(['tcpdump', '-i', iface, '-w', output_file])

# Cleanup function to delete config files and stop processes
def cleanup(config_files, processes):
    for config_file in config_files:
        if os.path.exists(config_file):
            os.remove(config_file)
    for process in processes:
        process.terminate()
    sys.exit(0)

# Signal handler for cleanup on script termination
def signal_handler(sig, frame):
    cleanup(config_files, processes)

# Main function
def main():
    parser = argparse.ArgumentParser(description="Automate SSID Confusion test with Hostapd and tcpdump")
    parser.add_argument("interface_legit", help="Network interface for legitimate SSID (e.g., wlan0)")
    parser.add_argument("interface_fake", help="Network interface for fake SSID (e.g., wlan1)")
    parser.add_argument("legit_ssid", help="Legitimate SSID")
    parser.add_argument("fake_ssid", help="Fake SSID")
    args = parser.parse_args()

    global config_files, processes
    config_files = ['hostapd_legit.conf', 'hostapd_fake.conf']
    processes = []

    # Create Hostapd configuration files
    create_hostapd_config(args.legit_ssid, args.interface_legit, config_files[0])
    create_hostapd_config(args.fake_ssid, args.interface_fake, config_files[1])

    # Start Hostapd for both SSIDs
    processes.append(start_hostapd(config_files[0]))
    processes.append(start_hostapd(config_files[1]))

    # Start tcpdump
    processes.append(start_tcpdump(args.interface_fake, 'tcpdump_output.pcap'))

    # Register signal handler for cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep the script running
    print("Press Ctrl+C to stop the script and clean up.")
    signal.pause()

if __name__ == "__main__":
    main()
