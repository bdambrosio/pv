# This file is executed on every boot (including wake-boot from deepsleep)
import network
import time
import micropython
ssid = 'BruceJaneAP'
password='97694083'
#ssid = 'BruceJane'
#password='1947NWnw!'
from machine import UART
uart=UART(0,115200)
micropython.kbd_intr(ord('q')) # allow an interrupt before launching app
station = network.WLAN(network.STA_IF)
station.active(True)
time.sleep(.2)
while station.isconnected() == False:
    print ("connecting...")
    try:
        station.connect(ssid, password)
        time.sleep(.2)
    except Exception as e:
        print(e)
        time.sleep(.2)
print(station.ifconfig())
try:
    micropython.kbd_intr(ord('q')) # allow an interrupt before launching app
    for i in range(10):
        print("waiting", (10-i), "secs")
        if uart.any() > 0: break
        time.sleep(1)
    import pvSensor_C3
except KeyboardInterrupt:
    pass
