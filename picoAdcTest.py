import machine
from machine import ADC
import time
voltMeter = ADC(26)
while True:
    v = voltMeter.read_u16()
    print (v)
    time.sleep(1)
    
