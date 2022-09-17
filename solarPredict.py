import requests
import json

w = None
try:
    w = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/94708/2022-09-15T10:00:00/?unitGroup=us&key=NS8CY2VL7AEGA6LJCJ83G9EYB&contentType=json&include=current")
except:
    print("problem w requests.get")

if w is not None:
   print("status: ", w.status_code)
   wJSON = w.json()
   print(wJSON)
   

