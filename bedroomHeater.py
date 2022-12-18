import requests
import json
import time
import paho.mqtt.client as mqtt
import threading
import math
import sys
from datetime import datetime, timezone
from dateutil.parser import parse

tmpBdrm = -1.0; tmpKtchn = -1.0

heaterStateValid = False
heaterOn = False

def start_heating():
    global heaterState, heaterStateValid
    try:
        rc = client.publish('cmnd/SP104/Power', 'ON')
        print("starting heating", rc)
        heaterState = True
        heaterStateValid = True
    except:
        print ("error starting heating")

def stop_heating():
    global heaterState, heaterStateValid
    try:
        rc = client.publish('cmnd/SP104/Power', 'OFF')
        print('stopping heating', rc)
        heaterState = False
        heaterStateValid = True
    except:
        print ("error stopping heating")

def new_measurement(client, userdata, msg):
    global tmpBdrm, tmpKtchn, heaterState, heaterStateValid
    topic = msg.topic
    try:
        measurement = json.loads(msg.payload)
        if 'SP104' in topic:
            heaterState = (measurement["POWER"] == 'ON')
            heaterStateValid = True
            print(heaterState)
            return
        if 'sensor2' in topic:
            if measurement['measure'] == 'tmp':
                tmpKtchn = measurement['value']*9/5+32
                print("kitchen: ", tmpKtchn)
        elif 'sensor3' in topic:
            if measurement['measure'] == 'tmp':
                tmpBdrm = measurement['value']*9/5+32
                print("bedroom: ", tmpBdrm)
    except Exception as e:
        print("error unpacking measurement", e)
        return
    
# start mqtt client
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        # print("\nMQTT connect success")
        pass
    else:
        print(f"\nMQTT connect fail with code {rc}")

client = mqtt.Client() 
client.on_connect = on_connect
client.on_message = new_measurement
client.username_pw_set(username='solar', password='1947nw')
client.connect("127.0.0.1", 1883, 60) 

client.subscribe('home/sensor2/tmp')
client.subscribe("home/sensor3/tmp")
client.subscribe('stat/SP104/RESULT')

current_time = time.localtime()

### get current temps
try:
    startTime = time.time()
    # tmpBdrm can occasionally be slightly negative at night
    while (tmpBdrm < 0.0 or tmpKtchn < 0.0) and time.time() - startTime < 120:
       client.loop()
       time.sleep(.2)
    if (time.time()-startTime) >= 120:
        print("\n*** timeout waiting for temperature data ***\n")
        sys.exit(-1)

except Exception as e:
    print("Failure getting temps", e)

rc = client.publish('cmnd/SP104/Power')

startTime = time.time()
while not heaterStateValid and time.time() - startTime < 120:
    client.loop()
    time.sleep(.2)
if (time.time()-startTime) >= 120:
    print("\n*** timeout waiting for heater state ***\n")
else:
    print("heaterState:", heaterState, current_time.tm_hour)
    if (((current_time.tm_hour > 2 and current_time.tm_hour < 6)
         or (current_time.tm_hour > 19 and current_time.tm_hour < 22))
        and tmpBdrm < 67.4):
        start_heating()
    else:
        stop_heating()
            
