import utime
import json
import network
import socket
from ST7735 import TFT
from sysfont import sysfont
from machine import SPI,Pin
from machine import RTC

# set real-time clock from internet
import ntptime
rtc = RTC()

try:
    ntptime.settime() # set the rtc datetime from the remote server
except:
    print("ntptime failure")
#example conversion of UTC to local
rtc.datetime()    # get the date and time in UTC
startup_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)
print(startup_time)

spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
tft=TFT(spi,16,17,18)
tft.initr()
tft.rotation(1)
tft.rgb(True)
tft.fill(TFT.BLACK)

font_height = sysfont['Height']
_scale = 1.25
vPrev=50.0
iPrev=2.0

# 
last_reading_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)
def new_measurement(topic, msg, retain, dup):
    global font_height, line_1_scale, line_2_scale, last_reading_time
    last_reading_time = utime.localtime(utime.mktime(utime.localtime()) - 8*3600)
    line_height = font_height * _scale
    block_height = 2* line_height + 2 #for 2 lines + line space
    print(topic, msg)
    print(last_reading_time)
    measurement = json.loads(msg)
    if 'units' in measurement.keys():
        v = line_height+2 # leave 2 rows at top
        if 'output' in topic:
            v=v + block_height +4 # for inter-block spacing
        if 'current' in topic:
            v=v + line_height + 2
            value = measurement['value']
        else:
            value = measurement['value']

        tft.fillrect([0,v-1],[158,block_height+1], TFT.BLACK)
        tft.text((4, v), str(topic[3:], 'ascii'), TFT.WHITE, sysfont, line_1_scale, nowrap=True)
        v = v + line_2_height + 2
        tft.text((4, v), "Value: {0:4.2f}".format(value), TFT.GREEN,
                 sysfont, line_2_scale, nowrap=True)

#get network object so we can check connection status
sta_if = network.WLAN(network.STA_IF);

# start socket
# start socket service
addr = socket.getaddrinfo('0.0.0.0', 1885)[0][-1]
print(addr)

while True:
    # print("checking connection")
    utime.sleep(2)
    if not sta_if.isconnected():
      print("network connection lost")
      while not sta_if.connect():
        # If the connection is successful, the is_conn_issue
        # method will not return a connection error.
        print("reconnecting to network")
        sta_if.connect()
    # ok, connected to network, try openning connection to pv monitor hardware
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.connect(('192.168.1.148',1884))
    except OSError:
        print ('Socket connect failed! Loop up and try socket again')
        utime.sleep( 5.0)
        continue

    try:
        req=s.read()
    except OSError:
        print ('Socket timeout, loop and try recv() again')
        utime.sleep( 5.0)
        continue
    #except:
    #    print('Other Socket err, exit and try creating socket again')
    #    # break from loop
    #    break
    print ('received', str(req, 'utf8'))
    try:
       s.close()
    except:
       pass
    



