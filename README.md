## SSID Confusion Test Automation

This script automates the process of testing SSID confusion using Hostapd and tcpdump. It allows you to create and manage legitimate and fake SSIDs, capture network traffic, and clean up configurations and processes upon termination.

### Features

- **Create Hostapd Configuration Files**: Generates configuration files for both legitimate and fake SSIDs.
- **Start Hostapd**: Launches Hostapd with the specified configuration files.
- **Start tcpdump**: Captures network traffic on the specified interfaces.
- **Cleanup**: Deletes configuration files and terminates processes when the script is stopped.

### Usage

```bash
python script_name.py <interface_legit> <interface_fake> <legit_ssid> <fake_ssid>
```

- `interface_legit`: Network interface for the legitimate SSID (e.g., wlan0)
- `interface_fake`: Network interface for the fake SSID (e.g., wlan1)
- `legit_ssid`: Name of the legitimate SSID
- `fake_ssid`: Name of the fake SSID

### Example

```bash
python ssid_confusion_test.py wlan0 wlan1 LegitSSID FakeSSID
```

### Signal Handling

The script includes a signal handler to ensure proper cleanup of configuration files and processes when the script is terminated.

---