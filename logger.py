#!/usr/bin/env python3

from dataclasses import dataclass
from collections import deque
from statistics import median
import time, toml, os, sys
from sense_hat import SenseHat
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision


CONFIG_FILE = "config.toml"
DISPLAY_WINDOW = 5 * 60
COLOR_OK = [80, 100, 255]
COLOR_BAD = [255, 0, 0]
COLOR_OFF = [0, 0, 0]
MIN_H = 20
MAX_H = 50


@dataclass
class Config:
    room: str
    sampling_period: int  # in seconds
    influx_url: str  # "http://localhost:8086"
    influx_org: str  # "wernerfamily"
    influx_token: str
    influx_bucket: str  # "humidity"


@dataclass
class Measurement:
    humidity: float
    pressure: float
    temperature_from_humidity: float
    temperature_from_pressure: float
    time: int

    @classmethod
    def take(cls):
        return cls(
            float(sense.get_humidity()),
            float(sense.get_pressure()),
            float(sense.get_temperature_from_humidity()),
            float(sense.get_temperature_from_pressure()),
            int(time.time()),
        )

    def to_influx_point(self):
        return (
            Point("humidity")
            .tag("sensor", config.room)
            .field("humidity", self.humidity)
            .field("pressure", self.pressure)
            .field("temperature_from_humidity", self.temperature_from_humidity)
            .field("temperature_from_pressure", self.temperature_from_pressure)
            .time(self.time, WritePrecision.S)
        )


def pixel_row(h):
    h = max(MIN_H, min(h, MAX_H))
    on = round(8 * (h - MIN_H) / (MAX_H - MIN_H))
    return [COLOR_OK if h < 40 else COLOR_BAD] * on + [COLOR_OFF] * (8 - on)


def history_windows(t):
    rows = []
    for i, h in enumerate(history):
        if h.time < t:
            if len(rows) == 8:
                break
            rows.append([])
            t -= DISPLAY_WINDOW
        rows[-1].append(h.humidity)
    while len(history) > i + 1:
        history.pop()
    while len(rows) < 8:
        rows.append([])
    return [(median(r) if r else MIN_H) for r in reversed(rows)]


def log(*args):
    print(*args, file=sys.stderr)


with open(os.path.join(os.path.dirname(__file__), CONFIG_FILE)) as f:
    vals = {key.lower(): val for key, val in toml.load(f).items()}
    config = Config(**vals)


sense = SenseHat()
sense.low_light = True
client = InfluxDBClient(config.influx_url, config.influx_token, org=config.influx_org)
write_api = client.write_api(SYNCHRONOUS)


# First measurement is often a bit weird
log("Initial measurement:", Measurement.take())
time.sleep(1)
log("Second measurement:", Measurement.take())
log("Started...")

history = deque()
max_history = 20 + 7 * DISPLAY_WINDOW / config.sampling_period

while True:
    m = Measurement.take()
    history.appendleft(m)
    windows = history_windows(m.time + 1)
    sense.set_pixels(sum(map(pixel_row, windows), []))

    write_api.write(config.influx_bucket, config.influx_org, m.to_influx_point())
    time.sleep(config.sampling_period)
