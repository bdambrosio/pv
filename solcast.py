import requests
import json
import time
import datetime
from dateutil.parser import parse
import math
import sys

try:
    w = requests.get("https://api.solcast.com.au/rooftop_sites/ef90-5ab9-3b1e-8602/forecasts?format=json&api_key=ZvnsFTgK4EuxWU37gP4dLH8ZxNoTPcla")
except Exception as e:
    print("problem w requests.get", e)

current_time = time.localtime()
if w is not None:
    #print("status: ", w.status_code)
    #print(w)
    try:
        solcast_json = w.json()
        with open('/home/pi/Documents/mpProjects/pv/solcast.json', 'w') as outfile:
            json.dump(solcast_json, outfile)
        num_forecasts = 0
        total_forecast = 0.0
        for i in range(len(solcast_json['forecasts'])):
            forecast = solcast_json['forecasts'][i]
            pv_estimate = forecast["pv_estimate"]
            period_end = forecast["period_end"]
            
            #forecast_date = datetime.datetime.strptime(period_end, '%Y-%m-%dT%H:%M:%S.%fZ')
            forecast_date = parse(period_end)
            forecast_day = forecast_date.date().day
            forecast_hour = forecast_date.time().hour
            if forecast_day == current_time.tm_mday:
                total_forecast += pv_estimate
                num_forecasts += 1
                print(pv_estimate)

        total_remaining_pv_kwh = 0.0
        if num_forecasts > 0:
            # each forecast is for 30 min, and prediction is for 3Kw of panels
            total_remaining_pv_kwh = (total_forecast/2)*.7/3.0   
        print (total_forecast, num_forecasts, total_remaining_pv_kwh)
    except Exception as e:
        print("failure getting or processing solcast forecasts", e)

    
