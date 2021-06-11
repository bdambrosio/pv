import time as utime
import json
import socket
import time
import paho.mqtt.client as mqtt
import json
import sqlite3
import sys

db = sqlite3.connect('pv.db')
hourly_total = {}
hourly_count = {}
last_db_update_time = {}

def update_db(topic, value):
    global hourly_total, hourly_count, last_db_update_time, db

    if not topic in hourly_total.keys():
        hourly_total[topic] = 0.0 # start new accumulator
        hourly_count[topic] = 0
        last_db_update_time[topic] = time.time() - 1 # -1 because this measurement not in last update
    
    hourly_total[topic] += value
    hourly_count[topic] += 1
    int_time = int(time.time())
    if int_time - last_db_update_time[topic] > 3600: # more than 1 hr
        try:
            hour_value = hourly_total[topic]/hourly_count[topic]
            new_row="INSERT INTO "+"'"+topic[3:]+"'"+" ('time', 'value') VALUES ({0}, {1:6.2f})".format(int_time, hour_value)
            print(new_row)
            cursor=db.cursor()
            rc=cursor.execute(new_row)
            db.commit()
            cursor.close()
        except:
            print ("Error updating db")
        #note we reset regardless of db update success, so that eventual success will have one hr total
        hourly_total[topic] = 0.0
        hourly_count[topic] = 0
        last_db_update_time[topic] = int_time

#setup to publish to mosquitto broker
def new_msg():
    print ("new msg")
    
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT connect success")
    else:
        print(f"MQTT connect fail with code {rc}")

def on_publish(client,userdata,result):             #create function for callback
    #print("data published ", result)
    pass

client = mqtt.Client() 
client.on_connect = on_connect
client.on_message = new_msg
client.on_publish = on_publish
client.username_pw_set(username='mosq', password='1947nw')
client.connect("127.0.0.1", 1883, 60) 

battery_input_scale = {'v_scale':398.8, 'v_offset':0.0,'i_scale':1400.0, 'ioffset':0.1}
battery_output_scale = {'v_scale':398.8, 'v_offset':0.0,'i_scale':1425.0, 'ioffset':0.0}
battery_test_scale = {'v_scale':398.8, 'v_offset':0.0,'i_scale':1425.0, 'ioffset':0.0}
out_sensor_ipaddr =  '192.168.1.148'
input_sensor_ipaddr = '192.168.1.103'
test_sensor_ipaddr =  '192.168.1.nnn'

def process_sensor(ipaddr, scale):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((ipaddr, 1884)) 
            #temp hack
            if '103' in ipaddr:
                print("sending to ", ipaddr)
                s.sendall(bytearray(json.dumps(scale), 'utf8'))
                print("sent", bytearray(json.dumps(scale), 'utf8'))
        except OSError:
            print ('Socket connect failed! Loop up and try socket again')
            utime.sleep( 5.0)
            return
        
        try:
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
                if 'voltage' in item and '148' in ipaddr:
                    scaled_value = scale['voltage']*value
                elif 'current' in item and '148' in ipaddr:
                    scaled_value = scale['current']*value
                try:
                    rc = client.publish(data['units'], scaled_value)
                except:
                    print("error posting measurement, skipping")
                update_db(data['units'], scaled_value)
            except:
                print ("error processing ", item)

while True:
    # print("checking connection")
    utime.sleep(5)
    # try openning connection to pv monitor hardware
    if len(sys.argv) < 1 or sys.argv[1] != 'test':
        process_sensor(output_sensor_ipaddr, battery_output_scale)
        process_sensor(input_sensor_ipaddr, battery_input_scale)
    else:
        print("processing test sensor")
        process_sensor(test_sensor_ipaddr, battery_output_scale)
        

