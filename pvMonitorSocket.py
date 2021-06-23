import machine
from machine import Pin, ADC, I2C
import utime
import ujson as json
import uio
import network
import ssd1306
import gc
#import micropython
try:
    import usocket as socket
except:
    import socket
# set real-time clock from internet
import ntptime
from machine import RTC

rtc = RTC()
try:
    ntptime.settime() # set the rtc datetime from the remote server
except:
    print("ntptime failure")
print(rtc.datetime())

import ads1x15

oled_width = const(128)
oled_height = const(64)

#I2c to talk to Adafruit ADC
i2c = machine.I2C(scl=Pin(5), sda=Pin(4) )   # create and init as a master

# Adafruit ads1115
# 1115 i2c addr = 72 -> addr pin to gnd, 5 -> max gain
aadc = ads1x15.ADS1115(i2c,72,5) 
# Display driver
oled_present=True
try:
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c, addr=60)
    oled.text('PV Monitor', 10, 0)
    
except:
    oled_present=False
    
_time = rtc.datetime()
if oled_present:
    oled.fill_rect(0, 16, 128, 48, 0)
    oled.text(str(_time[0]),  5, 16)
    oled.text(str(_time[1]), 42, 16)
    oled.text(str(_time[2]), 60, 16)
    oled.text(str(_time[4]), 80, 16)
    oled.text(str(_time[5]), 100, 16)
              
    oled.show()

def checkWlan():
    if not wlan.isconnected():
        while not wlan.connect():
            try:
                wlan.connect()
            except:
                pass

#get network object so we can check connection status
checkWlan()
wlan = network.WLAN(network.STA_IF);
ipaddr = wlan.ifconfig()[0]

#hack because i damaged ADC 0 and 1 on this board.
if '148' in ipaddr:
    is_damaged_ADS1115 = True
    print("damaged_ADS1115 hack True")
    
# start socket service
sock_addr=socket.getaddrinfo('0.0.0.0', 1884)[0][-1]

def makeSocket():
    #assumes any prior socket on this port has been closed
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(sock_addr)
    s.listen(5)
    return s

s = makeSocket()
print('listening on', ipaddr)


measurements = {}
jsonVolts = {'value':-1.0}
jsonAmps = {'value':-1.0}
measurements['voltage'] = jsonVolts
measurements['current'] = jsonAmps

default_scale = {'v_scale':398.8, 'v_offset':-0.011, 'i_scale':75, 'i_offset':0.011
#micropython.mem_info()

v1 = -1
v2 = -1
i1 = -1
i2 = -1
ads_present = True

try:
    v1 = aadc.read(0,2)
except:
    ads_present = False

if ads_present: # absent for test sensor for testing pvScrape comm
    utime.sleep_ms(200)
    i1 = aadc.read(0,0,1)
    utime.sleep_ms(200)
    v2 = aadc.read(0,2)
    utime.sleep_ms(200)
    i2 = aadc.read(0,0,1)
    print ("v1", v1, "i1",i1)
    print ("v2", v2, "i2",i2)

while True:
    cl = None
    try:
        s.settimeout(5)
        cl, addr = s.accept()
    except:
        pass
    if cl is None:
        if not wlan.isconnected():
            print("timeout on accept, wlan down")
            s.close()
            checkWlan()
            s=makeSocket()
        continue
    #new connection, try to get scale and report data
    try:
        s.settimeout(5)
        _jsonScale = cl.recv(256)
        # print("received", _jsonScale)
        _scale = json.loads(_jsonScale)
    except:
        print("failed to get scale")
        _scale = default_scale
    if _jsonScale is None and not wlan.isconnected():
        print("timeout on scale recv, wlan down")
        s.close()
        checkWlan()
        s=makeSocket()
        continue

    #got scale, now get raw measurements, scale, and report back
    v = -1.0
    i = -1.0
    # denoise: take two readings a sec apart and average
    if ads_present:
        _v1 = aadc.read(0,2)
        utime.sleep_ms(200)
        if is_damaged_ADS1115:
            _i1 = aadc.read(0,3)
        else:
            _i1 = aadc.read(0,0,1)
        utime.sleep_ms(200)
        _v2 = aadc.read(0,2)
        utime.sleep_ms(200)
        if is_damaged_ADS1115:
            _i2 = aadc.read(0,3)
        else:
            _i2 = aadc.read(0,0,1)
        v = (_v1+_v2)/2
        i = (_i1+_i2)/2
        
    #scale into volts/amps
    volts = (aadc.raw_to_v(v) - _scale['v_offset'] ) *_scale['v_scale']
    amps =   (aadc.raw_to_v(i) - _scale['i_offset'] ) * _scale['i_scale']
    print(v, aadc.raw_to_v(v), volts, "; ", i, aadc.raw_to_v(i), amps)
    #publish readings via mqtt and store in table
    jsonVolts['value'] = volts
    jsonAmps['value'] = amps
.015
    _i0 = aadc.read(0,0)
    _i1 = aadc.read(0,1)
    _i2 = aadc.read(0,2)
    _i3 = aadc.read(0,3)
    print(_i0, _i1, _i2, _i3)


    try:
        s.settimeout(3)
        cl.send(json.dumps(measurements))
    except:
        cl.close()

    _time = rtc.datetime()
    if oled_present:
        oled.fill_rect(0, 16, 128, 48, 0)
        oled.text(str(_time[0]),  5, 16)
        oled.text(str(_time[1]), 42, 16)
        oled.text(str(_time[2]), 60, 16)
        oled.text(str(_time[4]), 80, 16)
        oled.text(str(_time[5]), 100, 16)
        
        oled.text("V ",   4,32)
        oled.text(str(int(volts*10)), 24, 32)
        oled.text("I ",   66,32)
        oled.text(str(int(amps*10)),  80, 32)
        oled.show()
    gc.collect()
    # print('Initial free: {} allocated: {}'.format(gc.mem_free(), gc.mem_alloc()))
