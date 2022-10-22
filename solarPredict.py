import requests
import json
import time
import paho.mqtt.client as mqtt
import threading
import math
import sys

w = None
iIn = -1.0; iOut = -1.0; vIn = -1.0; vOut = -1.0
sleepDischargeRate = .075 # Wh/hr
dayDischargeRate = .07 # Wh/hr above overnight discharge rate
#solar_capture_factor = {0:1.0, 1:1.0, 2:0.9, 3:0.8, 4:0.7, 5:0.6, 6:0.6}
# new factors since estimate computation now includes cloud cover
solar_capture_factor = {0:1.0, 1:1.0, 2:0.95, 3:0.9, 4:0.85, 5:0.8, 6:0.8}

pvChargerStateValid = False
pvChargerOn = False

def start_charging():
    global pvChargerState, pvChargerStateValid
    try:
        rc = client.publish('cmnd/SP101/Power', 'ON')
        print("starting charging", rc)
        pvChargerState = True
        pvChargerStateValid = True
    except:
        print ("error starting charging")

def stop_charging():
    global pvChargerState, pvChargerStateValid
    try:
        rc = client.publish('cmnd/SP101/Power', 'OFF')
        print('stopping charging', rc)
        pvChargerState = False
        pvChargerStateValid = True
    except:
        print ("error stopping charging")

def new_measurement(client, userdata, msg):
    global iIn, iOut, vIn, vOut, pvChargerState, pvChargerStateValid
    topic = msg.topic
    measurement = json.loads(msg.payload)
    if 'SP101' in topic:
        pvChargerState = (measurement["POWER"] == 'ON')
        pvChargerStateValid = True
        return
    print(topic, measurement)
    if 'output' in topic:
        if 'current' in topic:
            iOut = measurement
        elif 'voltage' in topic:
            vOut = measurement
    elif 'input' in topic:
        if 'current' in topic:
            iIn = measurement
        elif 'voltage' in topic:
            vIn = measurement

def vCorrection(vEst, iIn, iOut):
    if (iIn - iOut) >=0:
        vEst = vEst - (max(0.0,53.5-vEst)*(iIn-iOut)*.15) - (iIn-iOut)*.06   # voltage drop per amp - calibrated when net charge
    else:
        vEst = vEst + (iOut-iIn)*.09   # voltage drop per amp - calibrated when net disCharge
    return vEst
    
# start mqtt client
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("\nMQTT connect success")
    else:
        print(f"\nMQTT connect fail with code {rc}")

#print("New MQQT session being set up")
# init mqtt values to -1 so we know when we have all
vOut = -1.0; vIn = -1.0; iIn = -1.0; iOut = -1.0
client = mqtt.Client() 
client.on_connect = on_connect
client.on_message = new_measurement
client.username_pw_set(username='solar', password='1947nw')
client.connect("127.0.0.1", 1883, 60) 

client.subscribe('pv/battery/output/voltage')
client.subscribe("pv/battery/output/current")
client.subscribe('pv/battery/input/voltage')
client.subscribe("pv/battery/input/current")
client.subscribe('stat/SP101/RESULT')

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
    expJoules = wJSON['days'][0]['solarenergy'] * 2.8   # energy in MJoules/m^2 * m^2 of my panels
    expJoules2 = wJSON['days'][0]['solarradiation'] * .21  #second estimate from radiation figure
    print(expJoules, expJoules2)
    # problems with solarenergy data on 10/23
    if expJoules > 25 and expJoules2 > 5 and expJoules2 < 25:
        expJoules = expJoules2
    elif expJoules < 25 and expJoules2 > 5 and expJoules2 < 23:
        expJoules = (expJoules + expJoules2)/2.0
    solarKwh = expJoules/3.6                               # 1MJoule = 3.6 Kwh
    cloudCover = wJSON['days'][0]['cloudcover']
    # batteryKwh = solarKwh * (1.0-cloudCover/100) * .18    # solar energy seems to include cloud cover
    batteryKwh = solarKwh * .18     # 20% efficiency panels/solarcharger/batteries - may need to derate in winter.
    month = current_time.tm_mon
    if month <= 6:
        month = month - 1
    month = abs(month-6)
    cf = solar_capture_factor[month]
    batteryKwhAdj = batteryKwh * cf
    solarDayLeft = 1.0-max(0.0, min((current_time.tm_hour+(current_time.tm_min/60.0)/6.0-10), 6)/6.0)
    print("\nsolarDayLeft:{:.0f}%".format(solarDayLeft*100))
    batteryKwhAdj2 = batteryKwhAdj*solarDayLeft
    print("cost ", wJSON['queryCost'], 'solar radiation', wJSON['days'][0]['solarradiation'], 'energy', wJSON['days'][0]['solarenergy'], "mJoules: ", "{:.1f}".format(expJoules), "solarKwh: {:.1f}".format(solarKwh),
         "pvKwhAvailable:", "{:.1f}".format(batteryKwhAdj2))
    startTime = time.time()
    #mqtt_thread = threading.Thread(target=MQTT_Msgs)
    #mqtt_thread.start()
    # iIn can occasionally be slightly negative at night
    while (vOut < 0.0 or vIn < 0.0 or iOut < -.5 or iIn < - 0.9) and time.time() - startTime < 120:
       client.loop()
       time.sleep(.2)
    if (time.time()-startTime) >= 120:
        print("\n*** timeout waiting for pv sensor data ***\n")
        sys.exit(-1)


    # goal is to be at full chg by 4pm (end of solar),
    # turning on charger early enough that we can turn it off before 3pm peak rates
    # = soc800am - 1600wh (8:00-16:00 shop draw) + (exp charge from solar) + (charge from charger)

    #Below estimates net i=0 voltage based on net current draw/chg
    # vOut swings less with iIn, so weight that more heavily...
    vEst = (vIn/2+vOut)/1.5
    vEst = vCorrection(vEst, iIn, iOut) # voltage drop per amp - calibrated when net charge
    soc = 0
    #soc800am = ((vEst-51.2)*25 + 20)/100 # obsolete linear approximation
    if vEst > 51.2 and vEst <= 52.0:
        soc = .2+.2*((vEst-51.2)/0.8)
    elif vEst > 52.0 and vEst <= 52.4:
        soc = 0.4 + .2*((vEst - 52.0)/.4)
    elif vEst > 52.4 and vEst <= 53.8:
        soc = 0.6 + .2*((vEst - 52.4)/1.2)
    elif vEst > 53.8 and vEst <= 54.3: 
        soc = 0.8 + .1*((vEst - 53.8)/.5)

    if vEst > 54.4:
        soc = .95
    elif vEst < 51.2:
        soc = .1

    print("\nPV vIn: {:.2f}V".format(vIn), "vOut: {:.2f}V".format(vOut),"iIn: {:.2f}A".format(iIn), "iOut: {:.2f}A".format(iOut), "vEst: {:.2f}V".format(vEst), "SOC: {:.0f}%".format(soc*100))
    # sleepDischargeRage W till 8am, dayDischargeRate 8am - 8pm (but only count till 3pm, rates rise)
    expDraw = 0.0
    if current_time.tm_hour < 15:
        expDraw = (15-current_time.tm_hour)*sleepDischargeRate \
        + max(0.0, (15 - max(current_time.tm_hour,8))*dayDischargeRate)
    # print("exp draw hr", current_time.tm_hour, (15-current_time.tm_hour)*sleepDischargeRate, max(0.0, (15 - max(current_time.tm_hour,8))*dayDischargeRate))

    # target is 90% SOC
    yKwh = ((3.1 - soc*3.2) + expDraw   # charge needed to get to 90% now + additional drain till 3pm
            - batteryKwhAdj2)            # expected from solar

    bKwhNow = soc*3.2
    bKwh8am = bKwhNow
    # estimate for 8am tomorrow - can we make it from here with no charger?
    hr = current_time.tm_hour
    if hr < 8: # add drain till 8am
        bKwhNow =- (8-current_time.tm_hour)*sleepDischargeRate

    bKwh8am = 0.0
    if hr < 16: # now add daytime drain till 4pm plus remaining charge from solar 
        bKwh4pm = min(3.2, bKwhNow + batteryKwhAdj2 - (8-(max(0, hr-8)))*dayDischargeRate)
        bKwh8am = bKwh4pm - 4*dayDischargeRate - 12*sleepDischargeRate
    else:
        bKwh8am = bKwhNow - max(0.0, 12-(hr-8))*dayDischargeRate - max(0.0, 12-(hr-20))*sleepDischargeRate
    
    print("  deficit now: {:.2f}".format(3.2-soc*3.2), "expected draw: {:.2f}".format(expDraw), "solarCharge today: {:.1f}".format(batteryKwhAdj), "solarCharge remaining: {:.1f}".format(batteryKwhAdj2))

    if abs(iOut - iIn) > 2.0:
        print("  ***hi charge or discharge rate, net: {:.1f}, estimate unreliable***".format( abs(iOut-iIn)))
    print("  battery projected 8am (no chrger, just solar) Kwh: {:.2f}".format(bKwh8am),"SOC: {:.0f}%".format(bKwh8am/3.2*100.0))
    if yKwh < 0.0:
        chargerStartHour = 99
    else:
        chargerStartHour = math.floor(14-yKwh*5)  # start charger so we're done by 2pm
    #print("expected draw till 16:00: {:.1f}".format(max(0.0, expDraw+dayDischargeRate)), 'total chg needed (yKwh): {:.2f}'.format(yKwh))
    print("  SOC: {:.0f}%".format(soc*100), "solar shortfall: {:.2f}Kwh".format(yKwh), "chg needed: {:.2f}".format(yKwh), "start Charger: {:2d}:00".format(chargerStartHour))


    rc = client.publish('cmnd/SP101/Power')

    startTime = time.time()
    while not pvChargerStateValid and time.time() - startTime < 120:
       client.loop()
       time.sleep(.2)
    if (time.time()-startTime) >= 120:
        print("\n*** timeout waiting for pv charger state ***\n")
    else:
        # print("pvChargerState:", pvChargerState, current_time.tm_hour, chargerStartHour)
        if (current_time.tm_hour < 15 and (chargerStartHour <= current_time.tm_hour or yKwh > 1.0)) or soc<.3:
            start_charging()
        elif current_time.tm_hour > 15 or chargerStartHour > current_time.tm_hour+1 or soc> .8:
            stop_charging()
            
