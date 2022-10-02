# This file is executed on every boot (including wake-boot from deepsleep)

#try:
#  import usocket as socket
#except:
#  import socket

import uos, machine
import network
import utime
from machine import RTC

#import esp
#esp.osdebug(None)

ssid = 'BruceJane'
password = '1947NWnw!'

station = network.WLAN(network.STA_IF)

station.active(True)

while station.isconnected() == False:
    print ("connecting...")
    try:
        station.connect(ssid, password)
    except:
        utime.sleep(.2)

print('Connection successful')
print(station.ifconfig())

# set real-time clock from internet - doesn't work in build 387
import ntptime
rtc = RTC()

try:
    ntptime.settime() # set the rtc datetime from the remote server
except:
    print("ntptime failure")
#example conversion of UTC to local
startup_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)

print(startup_time)
import pvSensor_C3
