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
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c, addr=60)
oled.text('PV Monitor', 10, 0)
_time = rtc.datetime()

oled.fill_rect(0, 16, 128, 48, 0)
oled.text(str(_time[0]),  5, 16)
oled.text(str(_time[1]), 42, 16)
oled.text(str(_time[2]), 60, 16)
oled.text(str(_time[4]), 80, 16)
oled.text(str(_time[5]), 100, 16)
              
oled.show()

#get network object so we can check connection status
sta_if = network.WLAN(network.STA_IF);

# start socket service
s = socket.socket()
addr = socket.getaddrinfo('0.0.0.0', 1884)[0][-1]
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(5)

print('listening on', addr)

# json structures for publishing values
# publish for two locations, comment out as appropriate
#jsonVolts = dict(units='pv.battery.output.voltage')
#jsonAmps = dict(units='pv.battery.output.current')
jsonVolts = dict(units='pv.battery.input.voltage')
jsonAmps = dict(units='pv.battery.input.current')

measurements = {}
measurements['voltage'] = jsonVolts
measurements['current'] = jsonAmps

default_scale = {'voltage':398.8, 'current':1454.5}
#micropython.mem_info()
v1 = aadc.read(0,2)
utime.sleep_ms(200)
i1 = aadc.read(0,0,1)
utime.sleep_ms(200)
v2 = aadc.read(0,2)
utime.sleep_ms(200)
i2 = aadc.read(0,0,1)
    
print ("v1", v1, "i1",i1)
print ("v2", v2, "i2",i2)

while True:
    cl, addr = s.accept()
    try:
        _jsonScale = cl.recv(256)
        # print("received", _jsonScale)
        _scale = json.loads(_jsonScale)
    except:
        print("failed to get scale")
        _scale = default_scale
    # denoise: take two readings a sec apart and average
    _v1 = aadc.read(0,2)
    utime.sleep_ms(200)
    _i1 = aadc.read(0,0,1)
    utime.sleep_ms(200)
    _v2 = aadc.read(0,2)
    utime.sleep_ms(200)
    _i2 = aadc.read(0,0,1)
    v = (_v1+_v2)/2
    i = (_i1+_i2)/2
    
    #scale into volts/amps
    volts =  aadc.raw_to_v(v)*_scale['voltage']
    amps =  aadc.raw_to_v(i) * _scale['current']
    #print(v, i, volts, amps)
    #publish readings via mqtt and store in table
    jsonVolts['value'] = volts
    jsonAmps['value'] = amps
    # At this point in the code you must consider how to handle
    # connection errors.  And how often to resume the connection.
    if not sta_if.isconnected():
      print("network connection lost")
      while not sta_if.connect():
        # If the connection is successful, the is_conn_issue
        # method will not return a connection error.
        print("reconnecting to network")
        sta_if.connect()
    cl.send(json.dumps(measurements))
    cl.close()

    _time = rtc.datetime()
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
