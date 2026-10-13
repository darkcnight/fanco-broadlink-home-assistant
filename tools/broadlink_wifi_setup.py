"""Put a Broadlink on your Wi-Fi without the Broadlink app (the app can lock the device so Home Assistant
cannot control it).

1. Reset the Broadlink into AP mode: hold reset ~6 s until the LED blinks fast, release, hold again ~6 s
   until it blinks slowly. It now broadcasts a Wi-Fi network (usually "BroadlinkProv").
2. Join that network from your computer.
3. Run:  uvx --with broadlink python broadlink_wifi_setup.py
   Enter your SSID and password (2.4 GHz only). The password is read without echo.

The setup packet is sent straight to the Broadlink's own address (default 192.168.10.1). The library's
default is a broadcast, which silently goes out the wrong interface when your computer also has
Ethernet, so the Broadlink never hears it.

Security note: the Broadlink provisioning protocol sends your Wi-Fi password UNENCRYPTED over the
Broadlink's open setup network. Do this somewhere nobody else is in Wi-Fi range of that network, and
prefer a separate IoT SSID whose password you can change.

Security modes: 0 none, 1 WEP, 2 WPA1, 3 WPA2, 4 WPA1/WPA2 mixed. Try 4 if 3 does not work.
A network with no internet access (an IoT VLAN) is fine: the Broadlink works fully locally.
"""
import argparse, getpass

import broadlink

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--security", type=int, default=3, help="0 none, 1 WEP, 2 WPA1, 3 WPA2 (default), 4 WPA1/2")
ap.add_argument("--device-ip", default="192.168.10.1", help="Broadlink address on its own AP (default 192.168.10.1)")
args = ap.parse_args()

ssid = input("SSID: ")
password = getpass.getpass("Wi-Fi password: ")
broadlink.setup(ssid, password, args.security, ip_address=args.device_ip)
print("Sent. Within a few seconds the Broadlink's AP should disappear and it joins your network.")
print("Find its IP in your router's DHCP leases, and reserve it.")
