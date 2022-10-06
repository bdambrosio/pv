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
aadc = ads1x15.ADS1115(i2c,72,2) 

while True:

    v1 = aadc.read(1,2)
    utime.sleep_ms(20)
    s=utime.ticks_us()
    i1 = aadc.read(1,0)
    en=utime.ticks_us()
    i1 = (i1+aadc.read(1,0))/2

    utime.sleep_ms(20)
    
    #scale into volts/amps
    volts = aadc.raw_to_v(v1)
    amps =  aadc.raw_to_v(i1)
    print("V",v1, volts, "; I", i1, amps, "read (0,1) time:", en-s)
    gc.collect()
    utime.sleep(1)

