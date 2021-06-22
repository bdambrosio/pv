# pv display for Pi0 using python3 and PySimpleGUI
import time
from time import ctime
from datetime import datetime
import pytz
import json
import paho.mqtt.client as mqtt
import threading

Vin = ' 00.0'
Vout = ' 00.0'
Iin = ' 00.0'
Iout = ' 00.0'
ptz = pytz.timezone('America/Los_Angeles')
utc = pytz.timezone('UTC')
now = utc.localize(datetime.utcnow())
Time = str(now.astimezone(ptz))[:-13]

import PySimpleGUI as sg
sg.theme('DarkAmber')   # Add a little color to your windows
sg.set_options(font=('Helvetica', 14))
# All the stuff inside your window. This is the PSG magic code compactor...
layout = [  [sg.Text('PV Monitor'), sg.Text(Time, key='-time-')],
            [sg.Text('Battery In   V: '), sg.Text(Vin, key='-Vin-'),
             sg.Text(' I: '), sg.Text(Iin, key='-Iin-')],
            [sg.Text('Battery Out  V: '), sg.Text(Vout, key='-Vout-'),
             sg.Text(' I: '), sg.Text(Iout, key='-Iout-')]
            ]

# Create the Window
window = sg.Window('Window Title', layout, no_titlebar=True)

def new_measurement(client, userdata, msg):
    topic = msg.topic
    measurement = json.loads(msg.payload)
    #print(topic, measurement)
    now = utc.localize(datetime.utcnow())
    Time = str(now.astimezone(ptz))[:-13]
    window['-time-'].update(Time)
    if 'output' in topic:
        if 'current' in topic:
            Iout = " {0:5.2f}".format(measurement)
            window['-Iout-'].update(Iout)
            print(Iout)
        else:
            Vout = " {0:5.2f}".format(measurement)
            window['-Vout-'].update(Vout)
        
    elif 'input' in topic:
        if 'current' in topic:
            Iin = " {0:5.2f}".format(measurement)
            window['-Iin-'].update(Iin)
        else:
            Vin = " {0:5.2f}".format(measurement)
            window['-Vin-'].update(Vin)
    
# start mqtt client
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT connect success")
    else:
        print(f"MQTT connect fail with code {rc}")

print("New MQT session being set up")
client = mqtt.Client() 
client.on_connect = on_connect
client.on_message = new_measurement
client.username_pw_set(username='mosq', password='1947nw')
client.connect("192.168.1.117", 1883, 60) 

client.subscribe('pv.battery.output.voltage')
client.subscribe("pv.battery.output.current")
client.subscribe('pv.battery.input.voltage')
client.subscribe("pv.battery.input.current")

def PSGEvents():
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
    window.close()

def MQTT_Msgs():
    while True:
        client.loop()
        time.sleep(1)
        
t1 = threading.Thread(target=PSGEvents)
t2 = threading.Thread(target=MQTT_Msgs)
t1.start()
t2.start()



