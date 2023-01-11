#!/usr/bin/env python3

import os, pwd

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


def system(cmd):
    print(">", cmd)
    res = os.system(cmd)
    if res != 0:
        print(f"`{cmd}` returned with exit code {res}")
        exit(res)


system("sudo apt-get install -y sense-hat python3-pip")
system("pip install 'influxdb-client[ciso]'")

system("mkdir -p ~/humidity-logger")
system(f"wget '{SCRIPT_URL}' -O ~/humidity-logger/logger.py")
system(f"wget '{SERVICE_URL}' -O ~/humidity-logger/humidity-logger.service")

service_fname = os.path.expanduser("~/humidity-logger/humidity-logger.service")

with open(service_fname, "r") as f:
    service_content = f.read()

with open(service_fname, "w") as f:
    f.write(service_content.replace("wernerfamily", pwd.getpwuid(os.getuid())))

system("sudo mv ~/humidity-logger/humidity-logger.service /etc/systemd/system/")
system("sudo chown root:root /etc/systemd/system/humidity-logger.service")

with open(os.path.expanduser("~/humidity-logger/config.toml"), "w") as f:
    print(f'ROOM = "{input("Room name: ")}"', file=f)
    print(f"SAMPLING_PERIOD = {SAMPLING_PERIOD}", file=f)
    print(f'INFLUX_TOKEN = "{INFLUX_TOKEN}"', file=f)
    print(f'INFLUX_URL = "http://{INFLUX_HOST}:{INFLUX_PORT}"', file=f)
    print(f'INFLUX_ORG = "{INFLUX_ORG}"', file=f)
    print(f'INFLUX_BUCKET = "{INFLUX_BUCKET}"', file=f)

print("Wrote configuration to ~/humidity-logger/config.toml")

system("sudo systemctl enable humidity-logger")

if input("Start service? (Y/n) ").strip().lower() in ("", "y"):
    system("sudo systemctl restart humidity-logger")
else:
    print("Run 'sudo systemctl start humidity-logger' to start")
