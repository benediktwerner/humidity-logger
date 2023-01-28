# Raspberry Pi Humidity Logger

- Grafana Dashboard: `localhost:3000`
- IndexDB Dashboard: `localhost:8086`

## Setup Grafana and InfluxDB node

1. Install Raspberry OS Lite 64-bit using Raspberry Imager (https://www.raspberrypi.com/software/) and boot the Pi
    - Make sure to activate SSH and setup WiFi
2. SSH onto the Pi from a PC in the same WiFi: `ssh username@domainNameOrIpOfThePi`
3. Install InfluxDB: https://docs.influxdata.com/influxdb/v2.6/install/?t=Raspberry+Pi

```bash
wget -q https://repos.influxdata.com/influxdb.key
echo '23a1c8836f0afc5ed24e0486339d7cc8f6790b83886c4c96995b88a061c5bb5d influxdb.key' | sha256sum -c && cat influxdb.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdb.gpg > /dev/null
echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdb.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list
sudo apt-get update && sudo apt-get install -y influxdb2
sudo systemctl enable influxdb
sudo systemctl start influxdb
sudo systemctl status influxdb
influx setup
```

4. Install Grafana (https://grafana.com/tutorials/install-grafana-on-raspberry-pi/)

```bash
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install -y grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
sudo systemctl status grafana-server
```

5. Create InfluxDB token for Grafana:
    - via the CLI: `influx auth create --org <name of the org created during influx setup> --all-access -d grafana`
    - via the InfluxDB dashboard at `http://domainNameOrIpOfThePi:8086` (easiest to give it all access)
6. Go to `http://domainNameOrIpOfThePi:3000` and log in with `admin:admin`
7. Setup InflxuDB data source in Grafana using the token created above and `localhost:8086` as the endpoint
    - Refer [configure-grafana-to-use-influxql](https://docs.influxdata.com/influxdb/v2.6/tools/grafana/?t=InfluxQL#configure-grafana-to-use-influxql)

## Setup data collection node

Can also be done on the Grafana/InfluxDB node (in which case you'd ofc skip step 1).

1. Install Raspberry OS Lite 64-bit using Raspberry Imager (https://www.raspberrypi.com/software/) and boot the Pi
    - Make sure to activate SSH and setup WiFi
2. SSH onto the Pi from a PC in the same WiFi: `ssh username@domainNameOrIpOfThePi`
3. Continue with Option 1 or 2

### Option 1: Use the setup script

> **Note**: Currently the value of influx host is hardcoded to `localhost`. The script will fetch the values of token, org, and bucket automatically based on the
> values provided when script executes `influx setup` command, please ensure to provide values for each fields.

4. Run `curl 'https://raw.githubusercontent.com/benediktwerner/humidity-logger/master/setup-data-node.sh' | /bin/bash`

### Option 2: Do it manually
4. Install sense-hat lib: `sudo apt-get install -y sense-hat`
5. Install influxdb lib: `sudo apt-get install -y python3-pip && pip install 'influxdb-client[ciso]'`
6. Copy `logger.py` from this repo to `~/humidity-logger/logger.py`
7. Copy `config.toml.example` from this repo to `~/humidity-logger/config.toml` and adjust the values
    - You can create an InfluxDB token via the InfluxDB UI at `http://domainNameOrIpOfThePi:8086` (give it write access to the bucket you want to use or just all buckets) or via `influx auth create --org <org name> --write-buckets`. You can reuse the same token for all data nodes.
8. Copy `humidity-logger.service` from this repo to `/etc/systemd/system/`
9. Edit the file and change all instances of `wernerfamily` to the username running on the pi (run `whoami` to find out what it is)
10.  Enable and start the service:
```bash
sudo systemctl enable humidity-logger
sudo systemctl start humidity-logger
```
