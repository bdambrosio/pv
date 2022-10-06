import time
import json
import umqtt as mqtt
from ST7735 import TFT
from sysfont import sysfont
from machine import SPI,Pin
import time

spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
tft=TFT(spi,16,17,18)
tft.initr()
tft.rotation(1)
tft.rgb(True)
tft.fill(TFT.BLACK)

font_height = sysfont['Height']
line_1_scale = 1.5
line_2_scale = 2
vPrev=50.0
iPrev=2.0

def smooth_v(v):
    global vPrev
    smoothed_v = (v + vPrev)/2.0
    vPrev = smoothed_v
    return smoothed_v

def smooth_i(i):
    global iPrev
    smoothed_i = (i + iPrev*2.0)/3.0 # i needs extra smoothing, esp32 ADC very noisy near lower limit
    iPrev = smoothed_i
    return smoothed_i

def new_measurement(topic, msg, retain, dup):
    global font_height, line_1_scale, line_2_scale
    line_1_height = font_height * line_1_scale
    line_2_height = font_height * line_2_scale
    block_height = line_1_height+line_2_height + 2 # +2 for interline
    print(topic, msg)
    measurement = json.loads(msg)
    if 'units' in measurement.keys():
        v = line_1_height+2 # leave 2 rows at top
        if 'current' in topic:
            v=v+block_height+4 # +4 for inter-block spacing
            value = smooth_i(measurement['value'])
        else:
            value = smooth_v(measurement['value'])

        tft.fillrect([0,v],[158,block_height], TFT.BLACK)
        tft.text((4, v), str(topic[3:], 'ascii'), TFT.WHITE, sysfont, line_1_scale, nowrap=True)
        v = v + line_2_height + 2
        tft.text((4, v), "Value: {0:4.2f}".format(value), TFT.GREEN,
                 sysfont, line_2_scale, nowrap=True)


client = mqtt.MQTTClient('pvMonitorDisplay', '192.168.1.101')
client.set_callback(new_measurement)
client.set_last_will("pv.panels.output.voltage", b'{"status": "Off"}')
client.connect()
client.subscribe("pv.panels.output.voltage")
client.subscribe("pv.battery.output.current")


while True:
    client.wait_msg()


