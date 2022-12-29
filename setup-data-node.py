#!/usr/bin/env python3

import os, time

SCRIPT_URL = (
    "https://raw.githubusercontent.com/benediktwerner/humidity-logger/master/logger.py"
)
SERVICE_URL = "https://raw.githubusercontent.com/benediktwerner/humidity-logger/master/humidity-logger.service"
SAMPLING_PERIOD = 5  # seconds
INFLUX_TOKEN = "ytKaItj-tj3vjjoWWcl2bS9Vx0Bi6rzShgNyDT-6bzy2y-Ur47byRnOEVVIcASDPig37KgFPpovxD8gvAsGatA=="
INFLUX_HOST = "humidity1"
INFLUX_PORT = 8086
INFLUX_ORG = "wernerfamily"
INFLUX_BUCKET = "humidity"

os.system("sudo apt-get install -y sense-hat python3-pip")
os.system("pip install 'influxdb-client[ciso]'")

os.system("mkdir ~/humidity-logger")
os.system(f"wget '{SCRIPT_URL}' -O ~/humidity-logger/logger.py")
os.system(f"wget '{SERVICE_URL}' -O ~/humidity-logger/humidity-logger.service")
os.system("sudo mv ~/humidity-logger/humidity-logger.service /etc/systemd/system/")

with open("~/humidity-logger/config.toml", "w") as f:
    print(f'ROOM = "{input("Room name: ")}"', file=f)
    print(f"SAMPLING_PERIOD = {SAMPLING_PERIOD}", file=f)
    print(f'INFLUX_TOKEN = "{INFLUX_TOKEN}"', file=f)
    print(f'INFLUX_URL = "http://{INFLUX_HOST}:{INFLUX_PORT}"', file=f)
    print(f'INFLUX_ORG = "{INFLUX_ORG}"', file=f)
    print(f'INFLUX_BUCKET = "{INFLUX_BUCKET}"', file=f)

print("Wrote configuration to ~/humidity-logger/config.toml")

os.system("sudo systemctl enable humidity-logger")

if input("Start service? (Y/n) ").strip().lower() in ("", "y"):
    os.system("sudo systemctl start humidity-logger")
else:
    print("Run 'sudo systemctl start humidity-logger' to start")
