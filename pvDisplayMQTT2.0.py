# pv display for 8266 and 2.8" ili9341 SPI display using PH's nano-gui

import utime
import json
import network
import machine
import umqtt.simple as mqtt
from machine import SPI,Pin
from machine import RTC
import gc

gc.collect()

# set real-time clock from internet
import ntptime
rtc = RTC()
try:
    ntptime.settime() # set the rtc datetime from the remote server
except:
    print("ntptime failure")
#example conversion of UTC to local
startup_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)
print(startup_time)
#get network object so we can check connection status
sta_if = network.WLAN(network.STA_IF);

# now initialize display
from color_setup import ssd
from gui.core.nanogui import refresh
from gui.core.writer import CWriter
from gui.core.colors import *

from gui.widgets.label import Label
import gui.fonts.freesans20 as freesans20

refresh(ssd)  # Initialise and clear display.
CWriter.set_textpos(ssd, 0, 0)  # In case previous tests have altered it
wri = CWriter(ssd, freesans20, GREEN, BLACK, verbose=False)
wri.set_clip(True, True, False)

# End of boilerplate code. This is our application:
Label(wri, 2, 2, 'Hello world!')
refresh(ssd)

last_reading_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)
font_height = 16
def new_measurement(topic, msg):
    global font_height, _scale, last_reading_time
    last_reading_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)
    line_height = font_height
    block_height = 2* line_height + 2 +2 # 2 blank rows line spacing each line

    measurement = json.loads(msg)
    label = str(topic,'utf8')
    print(topic, msg)
    print(last_reading_time)
    v = line_height+2 # leave 2 rows at top
    if 'output' in topic:
        v = v + block_height + 2 # for inter-block spacing
    if 'current' in topic:
        v = v + line_height + 2

    #tft.fillrect([0,v-1],[158,line_height+2], TFT.BLACK)
    Label(wri, v, 4, label[11:])
    Label(wri, v, 128, "  {0:4.2f}".format(measurement))
    refresh(ssd)

# start mqtt client
mqtt_client=mqtt.MQTTClient('pvDisplay_mqtt', '192.168.1.101', user='mosq', password='1947nw')
# Print diagnostic messages when retries/reconnects happens

mqtt_client.set_callback(new_measurement)
# now actually establish initial connection
print("New session being set up")
mqtt_client.connect()
mqtt_client.subscribe(b'pv.battery.output.voltage')
mqtt_client.subscribe(b"pv.battery.output.current")
mqtt_client.subscribe(b'pv.battery.input.voltage')
mqtt_client.subscribe(b"pv.battery.input.current")

while True:
    if not sta_if.isconnected():
      print("network connection lost")
      while not sta_if.connect():
        # If the connection is successful, the is_conn_issue
        # method will not return a connection error.
        print("reconnecting to network")
        sta_if.connect()
      mqtt_client.reconnect()
      mqtt_client.subscribe("pv.battery.output.voltage")
      mqtt_client.subscribe("pv.battery.output.current")
    mqtt_client.wait_msg()





