#!/usr/bin/env python3

from dataclasses import dataclass
import time, toml, os, sys
from sense_hat import SenseHat
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision


CONFIG_FILE = "config.toml"


@dataclass
class Config:
    sampling_period: int = 10  # in seconds
    influx_url: str = "http://localhost:8086"
    influx_bucket: str = "humidity"
    influx_org: str = "wernerfamily"
    influx_token: str = ""


def log(*args):
    print(*args, file=sys.stderr)


config = Config()
with open(os.path.join(os.path.dirname(__file__), CONFIG_FILE)) as f:
    for key, val in toml.load(f).items():
        if hasattr(config, key.lower()):
            setattr(config, key.lower(), val)
        else:
            log("ERROR: Unknown config value:", key, "- Skipping.")


sense = SenseHat()
client = InfluxDBClient(config.influx_url, config.influx_token, org=config.influx_org)
write_api = client.write_api(SYNCHRONOUS)


def get_point():
    return (
        Point("humidity")
        .tag("sensor", 1)
        .field("humidity", float(sense.get_humidity()))
        .field("pressure", float(sense.get_pressure()))
        .field(
            "temperature_from_humidity", float(sense.get_temperature_from_humidity())
        )
        .field(
            "temperature_from_pressure", float(sense.get_temperature_from_pressure())
        )
        .time(int(time.time()), WritePrecision.S)
    )


log("Initial measurement:", get_point())  # First measurement is often a bit weird
time.sleep(1)
log("Second measurement:", get_point())
log("Started...")

while True:
    p = get_point()
    log(p)
    write_api.write(config.influx_bucket, config.influx_org, p)
    time.sleep(config.sampling_period)
