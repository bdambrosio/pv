# pv
misc. software to monitor my off-grid PV

# Includes:
- pvMonitorSocket.py - simple micropython Wemos D1 voltage/current sensor. 
  - ADS1115 ADC, since ESP8266/32 ADC is so bad 
  - SSD1315 128*64 local display (optional)
  - TCP socket to accept data request. 
    Data request can include json parameters (scale, offset) for both voltage and current.
    This allows changing parameters without having to access remote sensors.
- pvScrape.py - simple python3 script to poll sensors and (less often) update Sqllite db.
  pvScrape also publishes data to local Mosquitto MQTT broker
- pvDisplayMQTT - simple micropython display that subscribes to and displays MQTT messages about sensor values
  SSD1306 128*64 display

## License
[MIT](https://choosealicense.com/licenses/mit/)  
