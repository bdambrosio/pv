import machine
from machine import Pin, WDT
import utime
import ujson as json
import network
#import gc
import ads1x15
try:
    import usocket as socket
except:
    import socket
#try:
#    ntptime.settime() # set the rtc datetime from the remote server
#except:
#    print("ntptime failure")
wdt = WDT(timeout=8000)
#I2c to talk to Adafruit ADC
i2c = machine.SoftI2C(scl=Pin(8), sda=Pin(9) )   # create and init as a master
print(i2c.scan())
# Adafruit ads1115
# 1115 i2c addr = 72 -> addr pin to gnd, '2' -> gain parameter, 2 = +/- 2.048V in (1 = +/-4v) 
aadc = ads1x15.ADS1115(i2c,72,4) 
#_time = rtc.datetime()

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
            print("received", _jsonScale)
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
    vCnt = 0; v = 0
    iCnt = 0; i = 0
    # denoise: take several readings and average
    for cnt in range(4):
        try:
            _v = aadc.read(0,2)
            if _v > 0.0:
                v += _v
                vCnt += 1
        except:
            print("error reading voltage")
        utime.sleep_ms(20)
        try:
            _i = aadc.read(0,0,1)
            if _i != 0.0:
                i += _i
                iCnt += 1
        except:
            print("error reading current")
        utime.sleep_ms(20)

    if vCnt > 0: v = v/vCnt
    if iCnt > 0: i = i/iCnt
        
    #scale into volts/amps
    #volts = aadc.raw_to_v(v)
    #amps =   aadc.raw_to_v(i)
    volts = v
    amps = i
    print(v, volts, "; ", i, amps)
    #publish readings via mqtt and store in table
    jsonVolts['value'] = volts
    jsonAmps['value'] = amps
    if cl is not None: # ie, if this measuement is requested
        try:
            s.settimeout(1)
            cl.send(json.dumps(measurements))
            cl.close()
        except:
            s.close()
            checkWlan()
            s=makeSocket()
    
    wdt.feed()
    # print('Initial free: {} allocated: {}'.format(gc.mem_free(), gc.mem_alloc()))
