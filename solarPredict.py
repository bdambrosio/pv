import requests
import json
import time
import paho.mqtt.client as mqtt
import threading
import math
import sys

w = None
iIn = -1.0; iOut = -1.0; vIn = -1.0; vOut = -1.0
#solar_capture_factor = {0:1.0, 1:1.0, 2:0.9, 3:0.8, 4:0.7, 5:0.6, 6:0.6}
# new factors since estimate computation now includes cloud cover
solar_capture_factor = {0:1.0, 1:1.0, 2:0.95, 3:0.9, 4:0.85, 5:0.8, 6:0.8}
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
        pass
        #print("\nMQTT connect success")
    else:
        print(f"\nMQTT connect fail with code {rc}")

#print("New MQQT session being set up")
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

if len(sys.argv) == 3:
    str_date = str(current_time.tm_year)+"-" + sys.argv[1] +"-" + sys.argv[2]

print (str_date+":"+str(current_time.tm_hour))

try:
    w = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/94708/"+str_date+"/?unitGroup=us&key=NS8CY2VL7AEGA6LJCJ83G9EYB&contentType=json&include=current")
    #w = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/94044/"+str_date+"/?unitGroup=us&key=NS8CY2VL7AEGA6LJCJ83G9EYB&contentType=json&include=current")
except:
    print("problem w requests.get")

if w is not None:
    #print("status: ", w.status_code)
    wJSON = w.json()
    #print(wJSON)
    expJoules = (wJSON['days'][0]['solarenergy'] * 28/10)   # energy in MJoules/m^2 * m^2 of my panels
    solarKwh = expJoules/3.6                                # 1MJoule = 3.6 Kwh
    cloudCover = wJSON['days'][0]['cloudcover']
    # batteryKwh = solarKwh * (1.0-cloudCover/100) * .18     # 20% efficiency panels/solarcharger/batteries - may need to derate in winter.
    batteryKwh = solarKwh * .18     # 20% efficiency panels/solarcharger/batteries - may need to derate in winter.
    month = current_time.tm_mon
    if month <= 6:
        month = month - 1
    month = abs(month-6)
    cf = solar_capture_factor[month]
    batteryKwhAdj = batteryKwh * cf
    print("cost ", wJSON['queryCost'], 'solar radiation', wJSON['days'][0]['solarradiation'], 'energy', wJSON['days'][0]['solarenergy'], "mJoules: ", "{:.1f}".format(expJoules), "solarKwh: {:.1f}".format(solarKwh),
         "batteryKwh:", "{:.1f}".format(batteryKwh))
    print("capture factor: {:.1f}".format(cf), "solarKwh Adjusted: {:.1f}".format(batteryKwhAdj))
    startTime = time.time()
    vOut = -1.0; vIn = -1.0
    #mqtt_thread = threading.Thread(target=MQTT_Msgs)
    #mqtt_thread.start()
    while (vOut < 0.0 or iIn < -.9 or iOut < 0.0) and time.time() - startTime < 120:
       client.loop()
       time.sleep(.2)
    print("PV vIn: {:.2f}V".format(vIn), "vOut: {:.2f}V".format(vOut),
          "iIn: {:.2f}A".format(iIn), "iOut: {:.2f}A".format(iOut))
    
    # goal is to be at full chg by 4pm (end of solar),
    # turning on charger early enough that we can turn it off before 3pm peak rates
    # = soc800am - 1600wh (8:00-16:00 shop draw) + (exp charge from solar) + (charge from charger)
    #Below estimates net i=0 voltage based on net current draw/chg
    vOut = vOut + (iOut-iIn)*.075   # voltage drop per amp - calibrated when net draw
    soc = 0
    #soc800am = ((vOut-51.2)*25 + 20)/100 # obsolete linear approximation
    if vOut > 51.2 and vOut < 52.0:
        soc = .2+.2*((vOut-51.2)/0.8)
    elif vOut > 52.0 and vOut < 52.4:
        soc = 0.4 + .2*((vOut - 52.0)/.4)
    elif vOut > 52.4 and vOut < 54.0:
        soc = 0.6 + .35*((vOut - 52.4)/1.8)

    if vOut > 53.9:
        soc = .95
    elif vOut < 51.2:
        soc = .1

    # 100 W till 8am, 175W till 8pm (but only count till 3pm, rates rise)
    expDraw = 0.0
    if current_time.tm_hour < 15:
        expDraw = (15-current_time.tm_hour)*0.075  + max(0.0, ((15 - max(current_time.tm_hour,8))*0.1))
    
    yKwh = ((3.2 - soc*3.2) + expDraw   # charge needed to get to 100% now + additional drain till 3pm
            - batteryKwhAdj)            # expected from solar
    print("yKwh elements: {:.2f}".format(3.2-soc*3.2), "expDraw: {:.2f}".format(expDraw), "bKwhAdj: {:.2f}".format(batteryKwhAdj))
    if yKwh < 0.0:
        chargerStartHour = -1
    else:
        chargerStartHour = math.floor(15-yKwh*5)
    print("now {:2d}".format(current_time.tm_hour), "expected draw till 16:00: {:.1f}".format(max(0.0,(16-current_time.tm_hour)*.16)), 'total chg needed (yKwh): {:.2f}'.format(yKwh))
    print("adj vOut: {:.2f}V".format(vOut), "SOC: {:.0f}%".format(soc*100), "solar shortfall: {:.1f}Kwh".format(yKwh),
          "start Charger: {:2d}:00".format(chargerStartHour))
    if abs(iOut - iIn) > 2.0:
        print("hi charge or discharge rate: {:.1f}, estimate unreliable".format( abs(iOut-iIn)))
