import requests
import json
import time
import datetime
from dateutil.parser import parse
import math
import sys

try:
    w = requests.get("https://api.solcast.com.au/rooftop_sites/ef90-5ab9-3b1e-8602/forecasts?format=json",
                     cookies={'_fbp':'fb.2.1666712018017.665241469',
                              '_lfa':'LF1.1.29c86318a58dab47.1666712018225',
                              '_gid':'GA1.3.796218654.1666711753',
                              'intercom-id-r2l1t14h':'76b6cbb8-6315-4cbb-8ee9-35eeb7fed015',
                              'ss-id':'JbbkNuAKQCLhPBPDFzC3',
                              'ss-pid':'yCtjbW7JtoBPBDjahUSV',
                              'ss-opt':'temp',
                              'X-UAId':'34305',
                              '_hjSessionUser_1767543':'eyJpZCI6IjhlNDU2NmVhLWYxNDUtNWFjOS04ODEwLTk4NTVhNWY2NmQ3YiIsImNyZWF0ZWQiOjE2NjY3MTIwMTgwODUsImV4aXN0aW5nIjp0cnVlfQ=='})
    
    #w = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/94044/"+str_date+"/?unitGroup=us&key=NS8CY2VL7AEGA6LJCJ83G9EYB&contentType=json&include=current")
except Exception as e:
    print("problem w requests.get", e)

current_time = time.localtime()
if w is not None:
    #print("status: ", w.status_code)
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

    
