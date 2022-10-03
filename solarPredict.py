import requests
import json
import time
import paho.mqtt.client as mqtt
import threading
import math
w = None
iIn = -1.0; iOut = -1.0; vIn = -1.0; vOut = -1.0
def new_measurement(client, userdata, msg):
    global iIn, iOut, vIn, vOut
    topic = msg.topic
    measurement = json.loads(msg.payload)
    # print(topic, measurement)
    if 'output' in topic:
        if 'current' in topic:
            iOut = measurement
        elif 'voltage' in topic:
            vOut = measurement
    elif 'input' in topic:
        if 'current' in topic:
            iIn = measurement
        else:
            vIn = measurement

    
# start mqtt client
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT connect success")
    else:
        print(f"MQTT connect fail with code {rc}")

print("New MQQT session being set up")
client = mqtt.Client() 
client.on_connect = on_connect
client.on_message = new_measurement
client.username_pw_set(username='solar', password='1947nw')
client.connect("192.168.1.101", 1883, 60) 

client.subscribe('pv/battery/output/voltage')
client.subscribe("pv/battery/output/current")
client.subscribe('pv/battery/input/voltage')
client.subscribe("pv/battery/input/current")

current_time = time.localtime()
str_date = str(current_time.tm_year)+"-"+str(current_time.tm_mon)+"-"+str(current_time.tm_mday)

print (str_date+":"+str(current_time.tm_hour))

try:
    w = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/94708/"+str_date+"/?unitGroup=us&key=NS8CY2VL7AEGA6LJCJ83G9EYB&contentType=json&include=current")
except:
    print("problem w requests.get")

if w is not None:
    #print("status: ", w.status_code)
    wJSON = w.json()
    expJoules = (wJSON['days'][0]['solarenergy'] * 28/10)   # energy in MJoules/m^2 * m^2 of my panels
    solarKwh = expJoules/3.6                                # 1MJoule = 3.6 Kwh
    batteryKwh = solarKwh * .18     # 20% efficiency panels/solarcharger/batteries - may need to derate in winter.
    print("cost ", wJSON['queryCost'], 'solar radiation', wJSON['days'][0]['solarradiation'], 'energy', wJSON['days'][0]['solarenergy'], "mJoules: ", "{:.1f}".format(expJoules), "solarKwh: ", "{:.1f}".format(solarKwh),
         "batteryKwh:", "{:.1f}".format(batteryKwh))

    startTime = time.time()
    vOut = -1.0; vIn = -1.0
    #mqtt_thread = threading.Thread(target=MQTT_Msgs)
    #mqtt_thread.start()
    while (vOut < 0.0 or iIn < -.9 or iOut < 0.0) and time.time() - startTime < 120:
       client.loop()
       time.sleep(.2)
    print("vIn: ",vIn, "vOut: ",vOut, "iIn: ", iIn, "iOut: ", iOut)

    #3000 (~ 90% charge wh) 
    #   = soc800am - 1600wh (800-1600 usage from above) + x (exp charge from solar) + y (charge from charger)
    vOut = vOut + (iOut-iIn)*.1     # .1 volt drop per amp - need to recalibrate when new 25Ah cells arrive
    soc800am = ((vOut-51.0)*25 + 15)/100
    if vOut > 53.9:
        soc800am = .9
    elif vOut < 51.0:
        soc800am = .1
    yKwh = 3.2 - soc800am*3.2 + 1.6 - batteryKwh
    if yKwh < 0.0:
        chargerStartTime = -1
    else:
        chargerStartTime = math.floor(1500-yKwh*500)
    print("adj vOut: {:.2f}V".format(vOut), "SOC: {:.0f}%".format(soc800am*100), "solar shortfall: {:.1f}Kwh".format(yKwh),
          "start Charger: ", chargerStartTime)
    if abs(iOut - iIn) < 2.0:
        print("hi charge or discharge rate, estimate unreliable")
