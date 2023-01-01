#!/usr/bin/env python3

from dataclasses import dataclass
from collections import deque
from statistics import mean
import time, toml, os, sys, atexit, pickle
from sense_hat import (
    SenseHat,
    ACTION_PRESSED,
    ACTION_HELD,
    DIRECTION_UP,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_MIDDLE,
)
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

DIRECTORY = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(DIRECTORY, "config.toml")
HISTORY_FILE = os.path.join(DIRECTORY, "history.pickle")
HISTORY_FILE_VERSION = 1
DISPLAY_WINDOWS = [
    3 * 60 * 60,  # 24h totals, 3h windows
    60 * 60,  # 8h total, 1h windows
    20 * 60,  # 2h40m total, 20m windows
    10 * 60,  # 1h20m total, 10m windows
    5 * 60,  # 40m total, 5m windows
    60,  # 8m total, 1m windows
]
DEFAULT_DISPLAY_WINDOW = 4  # 5m windows
RESET_DISPLAY_TIMEOUT = 5 * 60
COLOR_OK = [80, 100, 255]
COLOR_BAD = [255, 0, 0]
COLOR_OFF = [0, 0, 0]
BAD_THRESHOLD = 40
DEFAULT_MIN_H = 20
DEFAULT_MAX_H = 50

DIRECTIONS = [DIRECTION_UP, DIRECTION_RIGHT, DIRECTION_DOWN, DIRECTION_LEFT]


@dataclass
class Config:
    room: str
    sampling_period: int  # in seconds
    influx_url: str  # "http://localhost:8086"
    influx_org: str  # "wernerfamily"
    influx_token: str
    influx_bucket: str  # "humidity"

    @classmethod
    def load(cls):
        with open(CONFIG_FILE) as f:
            vals = {key.lower(): val for key, val in toml.load(f).items()}
            return cls(**vals)


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
    color = COLOR_OK if h < 40 else COLOR_BAD
    h = max(min_h, min(h, max_h))
    on = round(8 * (h - min_h) / (max_h - min_h))
    return [color] * on + [COLOR_OFF] * (8 - on)


def history_windows():
    t = history[0].time + 1
    rows = []
    for h in history:
        if h.time < t:
            if len(rows) == 8:
                break
            rows.append([])
            t -= DISPLAY_WINDOWS[display_window]
        rows[-1].append(h.humidity)
    while len(rows) < 8:
        rows.append([])
    return [(mean(r) if r else min_h) for r in reversed(rows)]


def redraw():
    sense.set_pixels(sum(map(pixel_row, history_windows()), []))


def on_stick_moved(event):
    global display_window, min_h, max_h, last_input

    last_input = int(time.time())

    direction = event.direction
    if direction != DIRECTION_MIDDLE:
        direction = DIRECTIONS[(DIRECTIONS.index(direction) - 1) % 4]

    if direction == DIRECTION_MIDDLE:
        if event.action == ACTION_HELD:
            reset_display_vars()
        elif event.action == ACTION_PRESSED and max_h - min_h > 19:
            max_h -= 5
            min_h += 5
        else:
            return
    elif event.action != ACTION_PRESSED:
        return
    elif direction == DIRECTION_LEFT:
        display_window = max(0, display_window - 1)
    elif direction == DIRECTION_RIGHT:
        display_window = min(len(DISPLAY_WINDOWS) - 1, display_window + 1)
    elif direction == DIRECTION_UP:
        d = (max_h - min_h) / 4
        min_h += d
        max_h += d
    elif direction == DIRECTION_DOWN:
        d = (max_h - min_h) / 4
        min_h -= d
        max_h -= d

    redraw()


def reset_display_vars():
    global display_window, min_h, max_h
    display_window = DEFAULT_DISPLAY_WINDOW
    min_h = DEFAULT_MIN_H
    max_h = DEFAULT_MAX_H


def dump_history_to_file():
    if os.path.isfile(HISTORY_FILE):
        os.rename(HISTORY_FILE, HISTORY_FILE + ".bkp")
    with open(HISTORY_FILE, "wb") as f:
        f.write(bytes([HISTORY_FILE_VERSION]))
        pickle.dump(history, f, pickle.HIGHEST_PROTOCOL)


def read_history_from_file():
    try:
        with open(HISTORY_FILE, "rb") as f:
            version = f.read(1)[0]
            if version != HISTORY_FILE_VERSION:
                log(
                    "History file version doesn't match. Found:",
                    version,
                    "Expected:",
                    HISTORY_FILE_VERSION,
                )
                return deque()
            return pickle.load(f)
    except Exception as e:
        log("Error while loading history:", e)
        return deque()


def log(*args):
    print(*args, file=sys.stderr)


config = Config.load()
sense = SenseHat()
sense.low_light = True
sense.stick.direction_any = on_stick_moved
client = InfluxDBClient(config.influx_url, config.influx_token, org=config.influx_org)
write_api = client.write_api(SYNCHRONOUS)

history = read_history_from_file()
last_input = 0
reset_display_vars()

atexit.register(dump_history_to_file)

# First measurement is often a bit weird
log("Initial measurement:", Measurement.take())
time.sleep(1)
log("Second measurement:", Measurement.take())
log("Started...")

while True:
    m = Measurement.take()

    # clear old history
    while len(history) > 1 and history[-1].time < m.time - DISPLAY_WINDOWS[0] * 8:
        history.pop()

    # reset display parameters if no user input in a while
    if last_input < m.time - RESET_DISPLAY_TIMEOUT:
        reset_display_vars()

    history.appendleft(m)
    redraw()

    write_api.write(config.influx_bucket, config.influx_org, m.to_influx_point())
    time.sleep(config.sampling_period)
