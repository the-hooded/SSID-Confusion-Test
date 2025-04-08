import argparse
import os
import subprocess
import signal
import sys
import textwrap # Keep this import

# Function to create Hostapd configuration files
# --- THIS VERSION CREATES OPEN (UNENCRYPTED) NETWORKS FOR TESTING ---
def create_hostapd_config(ssid, iface, filename):
    # --- TEMPORARY TEST ---
    print(f"!!! CREATING TEST OPEN CONFIG for {iface} !!!")
    config = textwrap.dedent(f"""\
        interface={iface}
        ssid={ssid}_OPEN_TEST
        hw_mode=g
        channel=1
        # WPA stuff commented out for testing
        #wpa=2
        #wpa_passphrase=yourpassword
        #wpa_key_mgmt=WPA-PSK
        #wpa_pairwise=TKIP # TKIP is weak, avoid if possible
        #rsn_pairwise=CCMP
    """)
    # --- END TEMPORARY TEST ---
    with open(filename, 'w') as file:
        file.write(config)
# --- END OF MODIFIED FUNCTION ---

# Function to start Hostapd
def start_hostapd(config_file):
    # Run hostapd. Consider adding error handling/checking here if needed.
    # Stderr/Stdout are not captured by default, errors might print to console
    # where hostapd runs, not necessarily where the python script runs.
    print(f"Attempting to start hostapd with config: {config_file}")
    return subprocess.Popen(['hostapd', config_file])

# Function to start tcpdump
def start_tcpdump(iface, output_file):
    print(f"Attempting to start tcpdump on interface: {iface} writing to {output_file}")
    # Ensure interface is up before starting tcpdump? hostapd should handle this.
    # Consider adding error checking for tcpdump startup.
    return subprocess.Popen(['tcpdump', '-i', iface, '-w', output_file])

# Cleanup function to delete config files and stop processes
def cleanup(config_files, processes):
    print("\nCleaning up...")
    # Terminate processes first
    for process in reversed(processes): # Stop tcpdump before hostapd potentially
        try:
            print(f"Terminating process {process.pid}...")
            process.terminate()
            process.wait(timeout=5) # Wait a bit for termination
        except ProcessLookupError:
            print(f"Process {process.pid} already terminated.")
        except subprocess.TimeoutExpired:
            print(f"Process {process.pid} did not terminate gracefully, killing.")
            process.kill()
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
    sys.exit(0)

# Signal handler for cleanup on script termination
def signal_handler(sig, frame):
    print(f"Signal {sig} received, initiating cleanup...")
    # Call cleanup with the globally defined lists
    # Note: Using globals like this is functional but might be improved
    # in larger applications by using classes or passing state.
    cleanup(config_files, processes)

# Main function
def main():
    parser = argparse.ArgumentParser(description="Automate SSID Confusion test with Hostapd and tcpdump")
    parser.add_argument("interface_legit", help="Network interface for legitimate SSID (e.g., wlan0)")
    parser.add_argument("interface_fake", help="Network interface for fake SSID (e.g., wlan1)")
    parser.add_argument("legit_ssid", help="Legitimate SSID")
    parser.add_argument("fake_ssid", help="Fake SSID")
    args = parser.parse_args()

    # Define these as global so the signal handler can access them via cleanup()
    global config_files, processes
    config_files = ['hostapd_legit.conf', 'hostapd_fake.conf']
    processes = []

    # Ensure cleanup happens even if errors occur before signal handling setup
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create Hostapd configuration files (using the modified function)
        print("Creating hostapd config files...")
        create_hostapd_config(args.legit_ssid, args.interface_legit, config_files[0])
        create_hostapd_config(args.fake_ssid, args.interface_fake, config_files[1])
        print("Config files created.")

        # Start Hostapd for both SSIDs
        processes.append(start_hostapd(config_files[0]))
        processes.append(start_hostapd(config_files[1]))

        # Start tcpdump on the fake interface
        # Give hostapd a moment to potentially bring up the interface
        import time
        time.sleep(3) # Add a small delay before starting tcpdump
        processes.append(start_tcpdump(args.interface_fake, 'tcpdump_output.pcap'))

        # Keep the script running
        print("\nSetup complete. Hostapd and tcpdump should be running.")
        print(f"Broadcasting '{args.legit_ssid}_OPEN_TEST' on {args.interface_legit}") # Updated SSID
        print(f"Broadcasting '{args.fake_ssid}_OPEN_TEST' on {args.interface_fake}")   # Updated SSID
        print(f"Capturing traffic on {args.interface_fake} to tcpdump_output.pcap")
        print("\nPress Ctrl+C to stop the script and clean up.")

        # Wait indefinitely for a signal
        signal.pause()

    except Exception as e:
        print(f"\n--- An error occurred during setup: {e} ---")
        print("--- Initiating cleanup due to error ---")
        # Restore original handlers before cleanup to avoid recursion if cleanup errors
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        cleanup(config_files, processes)
        sys.exit(1) # Exit with error status

if __name__ == "__main__":
    main()
