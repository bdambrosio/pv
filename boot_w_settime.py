# This file is executed on every boot (including wake-boot from deepsleep)

#try:
#  import usocket as socket
#except:
#  import socket

import uos, machine
import gc
import network
import utime
from machine import RTC

# set real-time clock from internet
import ntptime
rtc = RTC()

try:
    ntptime.settime() # set the rtc datetime from the remote server
except:
    print("ntptime failure")
#example conversion of UTC to local
startup_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)

import esp
esp.osdebug(None)

ssid = 'BruceJane'
password = '1947NWnw!'

station = network.WLAN(network.STA_IF)

station.active(True)

while station.isconnected() == False:
  station.connect(ssid, password)

print('Connection successful')
print(station.ifconfig())

gc.collect()
