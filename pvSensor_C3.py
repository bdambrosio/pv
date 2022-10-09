import machine
from machine import Pin, I2C, UART, WDT, ADC
import ina219_chris
import utime
import ujson as json
import network
import sys
try:
    import usocket as socket
except:
    import socket
#try:
#    ntptime.settime() # set the rtc datetime from the remote server
#except Exception as e:
#    print("ntptime failure",e)

uart=UART(0)

wdt = WDT(timeout=8000)

#I2c to talk to INA219
i2c = machine.SoftI2C(scl=Pin(8), sda=Pin(9) )   # create and init as a master
print(i2c.scan())
# 
ina = ina219 = ina219_chris.INA219(.0069, i2c, max_expected_amps=20, address= 0x40)
ina.configure()
#print('v',ina.voltage())
print('i', ina.current())
adc = ADC(Pin(0))

#_time = rtc.datetime()

def checkWlan():
    global wlan
    wlan = network.WLAN(network.STA_IF);
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
    if uart.any() : break
    try:
        s.settimeout(5)
        cl, addr = s.accept()
    except:
        pass
    if cl is None:
        wdt.feed()
        continue
    #new connection, try to get scale and report data
    #don't actually use scale locally anymore, but code left incase we add server->sensor info later
    print('connection')
    _jsonScale = None
    try:
        s.settimeout(1)
        _jsonScale = cl.recv(256)
    except:
        print("failed to get scale")
        _scale = default_scale

    #got scale, now get raw measurements, scale, and report back
    volts = adc.read_uv()
    amps =   ina219.current()
    print("V:",volts, "uv; A:", amps,"(ina219)")
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
    #except KeyboardInterrupt:
	#s.close()
	#sys.exit()
