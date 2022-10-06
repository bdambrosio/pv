import machine
from machine import ADC, Pin, WDT
import utime
import ujson as json
import network
import gc
from machine import RTC
#import micropython
try:
    import usocket as socket
except:
    import socket

vPin = Pin(0)
iPin = Pin(4)

rtc = RTC()
wdt = WDT()
_time = rtc.datetime()

def checkWlan():
    while not wlan.isconnected():
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
        s.settimeout(1)
        cl, addr = s.accept()
    except:
        pass
    if cl is not None:
        #new connection, try to get scale and report data
        #don't actually use scale locally anymore, but code left incase we add server->sensor info later
        _jsonScale = None
        try:
            s.settimeout(1)
            _jsonScale = cl.recv(256)
            # print("received", _jsonScale)
            #_scale = json.loads(_jsonScale)
        except:
            print("failed to get scale")
            #_scale = default_scale

    # got scale or not, make a reading anyway
    #    get raw measurements and scale
    v = -1.0
    i = -1.0
    # denoise: take two readings a sec apart and average
    _v1 = vadc.read_uv()
    utime.sleep_ms(20)
    _i1 = aadc.read_uv()
    utime.sleep_ms(20)
    _v2 = vadc.read_uv
    utime.sleep_ms(20)
    _i2 = aadc.read_uv()
    v = (_v1+_v2)/2
    i = (_i1+_i2)/2
        
    #scale into volts/amps
    volts = aadc.raw_to_v(v)
    amps =   aadc.raw_to_v(i)
    print(v, volts, "; ", i, amps)
    if cl is not None:
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

    wdt.feed()
    # gc.collect()
    # print('Initial free: {} allocated: {}'.format(gc.mem_free(), gc.mem_alloc()))
