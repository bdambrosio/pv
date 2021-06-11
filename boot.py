# This file is executed on every boot (including wake-boot from deepsleep)

#try:
#  import usocket as socket
#except:
#  import socket

import uos, machine
import gc
import network

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
