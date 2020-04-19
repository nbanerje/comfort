import time
from machine import Pin
from ds18x20 import DS18X20
from onewire import OneWire

# DS18B20 data line connected to pin P10
ow = OneWire(Pin('P8', mode=Pin.OUT))
temp = DS18X20(ow)

while True:
    print(temp.read_temp_async())
    time.sleep(1)
    temp.start_conversion()
    time.sleep(1)

