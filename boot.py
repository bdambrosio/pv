# This file is executed on every boot (including wake-boot from deepsleep)
import network
import time
import micropython
#ssid = 'BruceJaneAP'
#password='97694083'
ssid = 'BruceJane'
password='1947NWnw!'

micropython.kbd_intr(ord('q')) # allow an interrupt before launching app
station = network.WLAN(network.STA_IF)
station.active(True)
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
    for i in range(60):
        print("waiting", (60-i), "secs")
        time.sleep(1)
    #import pvSensor_C3
except KeyboardInterrupt:
    pass
