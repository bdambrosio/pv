import machine
from machine import Pin, I2C
import utime
import ujson as json
import uio
import network
import gc
import ads1x15
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

#I2c to talk to Adafruit ADC
i2c = machine.I2C(scl=Pin(5), sda=Pin(4) )   # create and init as a master

# Adafruit ads1115
# 1115 i2c addr = 72 -> addr pin to gnd, '2' -> gain parameter, 2 = +/- 2.048V in (1 = +/-4v) 
aadc = ads1x15.ADS1115(i2c,72,4) 
_time = rtc.datetime()

def checkWlan():
    if not wlan.isconnected():
        while not wlan.connect():
            try:
                wlan.connect()
            except:
                pass

#get network object so we can check connection status
wlan = network.WLAN(network.STA_IF);
ipaddr = wlan.ifconfig()[0]
checkWlan()

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

v1 = -1
v2 = -1
i1 = -1
i2 = -1

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
    #don't actually use scale locally anymore, but code left incase we add server->sensor info later
    _jsonScale = None
    try:
        s.settimeout(1)
        _jsonScale = cl.recv(256)
        # print("received", _jsonScale)
        _scale = json.loads(_jsonScale)
    except:
        print("failed to get scale")
        _scale = default_scale
    if _jsonScale is None:
        print("timeout on scale recv, wlan down")
        s.close()
        checkWlan()
        s=makeSocket()
        continue

    #got scale, now get raw measurements, scale, and report back
    v = -1.0
    i = -1.0
    # denoise: take two readings a sec apart and average
    _v1 = aadc.read(1,2)
    utime.sleep_ms(20)
    _i1 = aadc.read(1,0)
    utime.sleep_ms(20)
    _v2 = aadc.read(1,2)
    utime.sleep_ms(20)
    _i2 = aadc.read(1,0)
    v = (_v1+_v2)/2
    i = (_i1+_i2)/2
        
    #scale into volts/amps
    volts = aadc.raw_to_v(v)
    amps =   aadc.raw_to_v(i)
    print(v, volts, "; ", i, amps)
    #publish readings via mqtt and store in table
    jsonVolts['value'] = volts
    jsonAmps['value'] = amps

    try:
        s.settimeout(3)
        cl.send(json.dumps(measurements))
        cl.close()
    except:
        s.close()
        checkWlan()
        s=makeSocket()

    gc.collect()
    # print('Initial free: {} allocated: {}'.format(gc.mem_free(), gc.mem_alloc()))
