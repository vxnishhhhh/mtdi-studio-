# MTDI 5.0 firmware template for MicroPython (ESP32, Pico boards, ...).
# Prints one protocol line per sample over USB serial: VALUE=512,_T=1234,_SEQ=7
import time
from machine import ADC, Pin

adc = ADC(Pin(26))          # Pico GP26 / ADC0; on ESP32 use ADC(Pin(34))
seq = 0
while True:
    value = adc.read_u16()  # replace with your sensor read
    print("VALUE={},_T={},_SEQ={}".format(value, time.ticks_ms(), seq))
    seq += 1
    time.sleep_ms(50)       # 20 lines/s
