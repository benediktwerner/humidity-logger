# This is an example that uses the complete LED matrix to display humidity as color.
# Low humidity is blue, high humidity is red.

from sense_hat import SenseHat
from time import sleep

HUMIDITY_LOW = 20.0
HUMIDITY_HI = 60.0

s = SenseHat()

while True:
    humidity = s.get_humidity()
    if humidity < HUMIDITY_LOW:
        humidity = HUMIDITY_LOW
    elif humidity > HUMIDITY_HI:
        humidity = HUMIDITY_HI
    offset = int((humidity-HUMIDITY_LOW)*6.35)
    print(offset)
    c = [offset,0,255-offset]
    print(c)
    print(humidity)
    leds = []
    for x in range(64):
        leds.append(c)
    s.set_pixels(leds)
    sleep(1)
