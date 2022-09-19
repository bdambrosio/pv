import requests
import json
import time

w = None

"""
try:
    w = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/94708/2022-06-15/?unitGroup=us&key=NS8CY2VL7AEGA6LJCJ83G9EYB&contentType=json&include=current")
except:
    print("problem w requests.get")

if w is not None:
   #print("status: ", w.status_code)
   wJSON = w.json()
   print('Historical: 09-15-22')
   print(wJSON['queryCost'], 'solar radiation', wJSON['days'][0]['solarradiation'], 'energy', wJSON['days'][0]['solarenergy'])
   print()
   #print('solarradiation', wJSON['currentConditions']['solarradiation'])
   expJoules = (wJSON['days'][0]['solarenergy'] * 28/10)   # energy in MJoules/m^2 * m^2 of my panels
   solarKwh = expJoules/3.6                                  # 1MJoule = 3.6 Kwh
   batteryKwh = solarKwh * .2                                # 20% efficiency panels/solarcharger/batteries ?
   print("mJoules: ", "{:.1f}".format(expJoules), "solarKwh: ", "{:.1f}".format(solarKwh),
         "batteryKwh:", "{:.1f}".format(batteryKwh))
   
"""
#example conversion of UTC to local
current_time = time.localtime()
str_date = str(current_time.tm_year)+"-"+str(current_time.tm_mon)+"-"+str(current_time.tm_mday)
print (str_date)

try:
    w = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/94708/"+str_date+"/?unitGroup=us&key=NS8CY2VL7AEGA6LJCJ83G9EYB&contentType=json&include=current")
except:
    print("problem w requests.get")

if w is not None:
   #print("status: ", w.status_code)
   wJSON = w.json()
   expJoules = (wJSON['days'][0]['solarenergy'] * 28/10)   # energy in MJoules/m^2 * m^2 of my panels
   solarKwh = expJoules/3.6                                  # 1MJoule = 3.6 Kwh
   batteryKwh = solarKwh * .2                                # 20% efficiency panels/solarcharger/batteries ?
   print("cost ", wJSON['queryCost'], 'solar radiation', wJSON['days'][0]['solarradiation'], 'energy', wJSON['days'][0]['solarenergy'], "mJoules: ", "{:.1f}".format(expJoules), "solarKwh: ", "{:.1f}".format(solarKwh),
         "batteryKwh:", "{:.1f}".format(batteryKwh))
   

