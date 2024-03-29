import time as utime
import json
import socket
import time
import paho.mqtt.client as mqtt
import json
from influxdb import InfluxDBClient
import sys
from time import ctime
from datetime import datetime
from datetime import timedelta
import pytz
import math

intvl_total = {}
intvl_count = {}
last_db_update_time = {}

ptz = pytz.timezone('America/Los_Angeles')
utc = pytz.timezone('UTC')
now = utc.localize(datetime.utcnow())
Time = str(now.astimezone(ptz))[:-13]

db = InfluxDBClient(host='localhost', port=8086)
db.switch_database('pv')

json_measurement =  {
    "measurement": "voltage",
    "tags": {
        "sys": "pv",
        "subsys": "Battery",
        "subsys2": 'input'
    },
    "fields": {
        "value": 127,
        "units": 'C'
    }
}

charging = True
def start_charging():
    global charging
    try:
        rc = client.publish('cmnd/SP101/Power', 'ON')
        print("starting charging", rc)
        charging = True
    except:
        print ("error starting charging")

def stop_charging():
    global charging
    try:
        rc = client.publish('cmnd/SP101/Power', 'OFF')
        print('stopping charging', rc)
        charging = False
    except:
        print ("error stopping charging")
    
json_measurements = [json_measurement]
last_battery_Iin = 0
last_battery_Iin_time = utc.localize(datetime.utcnow())

def update_db(topic, value):
    global intvl_total, intvl_count, last_db_update_time, db, last_battery_Iin, last_battery_Iin_time, charging

    if not topic in intvl_total.keys():
        intvl_total[topic] = 0.0 # start new accumulator
        intvl_count[topic] = 0
        last_db_update_time[topic] = time.time() - 601 # because this measurement not in last update
        print (topic, intvl_total.keys())
    intvl_total[topic] += value
    intvl_count[topic] += 1
    int_time = int(time.time())
    now = utc.localize(datetime.utcnow())
    Time = str(now.astimezone(ptz))[:-13]
    tags = topic.split('/')
    measure = tags[3]

    try:
        # charger control
        if measure == 'current' and tags[1] == 'battery' and tags[2] == 'input':
            #print("recording battery input current", value)
            last_battery_Iin == value
            last_battery_Iin_time = now
        
        #print("measure", measure, tags[1], tags[2], value, now - last_battery_Iin_time,
        #      timedelta(minutes=20), last_battery_Iin)

        # emergency rule to turn on ac charger if battery voltage low
        # and no input current. reason for timedelta is to make sure
        # battery in sensor is actually reporting.
        if ((measure == 'voltage' and tags[1] == 'battery' and tags[2] == 'output' and value > 10.0 and value < 48)
            and (now-last_battery_Iin_time < timedelta(minutes=20))
            and last_battery_Iin < 3):
            start_charging()
        #elif (measure == 'voltage' and value > 53.99) and charging:
        #    stop_charging()
    except:
        print("error in charger rule execution")

    # update database
    if int_time - last_db_update_time[topic] > 600: # more than 10 min
        try:
            hour_value = intvl_total[topic]/intvl_count[topic]
            
            json_measurement['measurement'] = measure
            json_measurement['fields']['value'] = hour_value
            json_measurement['fields']['units'] = 'C'
            json_measurement['tags']['sys'] = tags[0]
            json_measurement['tags']['subsys'] = tags[1]
            json_measurement['tags']['subsys2'] = tags[2]
            #print (json_measurement)
            db.write_points(json_measurements)
        except:
            print ("Error updating db")
        #note we reset regardless of db update success, so that eventual success will have one hr total
        intvl_total[topic] = 0.0
        intvl_count[topic] = 0
        last_db_update_time[topic] = int_time

#setup to publish to mosquitto broker
def new_msg():
    print ("new msg")
    
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT connect success")
    else:
        print(f"MQTT connect fail with code {rc}")

def on_disconnect(client, userdata, rc):
    print ("disconnect", rc)
    client.reconnect()

def on_publish(client,userdata,result):             #create function for callback
    #print("data published ", result)
    pass

client = mqtt.Client() 
client.on_connect = on_connect
client.on_message = new_msg
client.on_publish = on_publish
client.on_disconnect = on_disconnect
client.username_pw_set(username='mosq', password='1947nw')
client.connect("192.168.1.101", 1883, 60) 

# note - input now running on ina219 sensor
battery_input_scale = {'v_scale':0.0001978, 'v_offset':0.0,'i_scale':0.26, 'i_offset':-0.01}
battery_input_prefix = 'pv/battery/input/'
battery_input_ipaddr =  '192.168.1.164'

battery_output_scale = {'v_scale':0.00472, 'v_offset':0.0,'i_scale':0.012, 'i_offset':0}
#battery_output_scale = {'v_scale':0.00626, 'v_offset':0.0,'i_scale':0.01016, 'i_offset':0}
battery_output_prefix ='pv/battery/output/'
battery_output_ipaddr =  '192.168.1.172'

battery_test_scale = {'v_scale':0.000198, 'v_offset':0.0,'i_scale':0.0047, 'i_offset':0}
battery_test_prefix = 'pv/battery/test/'
battery_test_ipaddr =  '192.168.1.164'

def process_sensor(ipaddr, prefix, scale):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            #print("connecting to ", ipaddr)
            s.settimeout(2)
            s.connect((ipaddr, 1884)) 
            s.sendall(bytearray(json.dumps(scale), 'utf8'))
        except OSError:
            print ('Socket connect failed! Loop up and try socket again', ipaddr)
            utime.sleep( 2.0)
            return
        
        try:
            s.settimeout(2)
            msg=s.recv(1024)
        except OSError:
            print ('Socket timeout, loop and try recv() again')
            utime.sleep( 5.0)
            return
        
         # print ('received', str(msg, 'utf8'))
        try:
            measurements = json.loads(str(msg, 'utf8'))
        except:
            print("json parse failure: ",ipaddr)
            return
        
        scaled_value = 0.0
        for item,data in measurements.items():
            try:
                value = data['value']
                scaled_value = value
                label = prefix
                if 'voltage' in item:
                    label=prefix+'voltage'
                    scaled_value = (value-scale['v_offset'])*scale['v_scale']
                    print(label, value, scaled_value)
                elif 'current' in item:
                    label=prefix+'current'
                    scaled_value = (value-scale['i_offset'])*scale['i_scale']
                    print(label, value, scaled_value)
                try:
                    rc = client.publish(label, scaled_value)
                except:
                    print("error posting measurement, skipping", label, scaled_value)
                update_db(label, scaled_value)
            except:
                print ("error processing ", ipaddr, item, data)

while True:
    # print("checking connection")
    utime.sleep(5)
    # try openning connection to pv monitor hardware
    if len(sys.argv) < 2:
        process_sensor(battery_input_ipaddr, battery_input_prefix, battery_input_scale)
        process_sensor(battery_output_ipaddr, battery_output_prefix, battery_output_scale)
    elif  sys.argv[1] == 'test':
        print("processing test sensor")
        process_sensor(sys.argv[2], battery_test_prefix, battery_test_scale)
