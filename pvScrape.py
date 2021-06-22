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
        last_db_update_time[topic] = time.time() - 3601 # because this measurement not in last update
    
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

battery_input_scale = {'v_scale':398.8, 'v_offset':0.0,'i_scale':111.0, 'i_offset':0.01}
battery_input_prefix = 'pv.battery.input.'
battery_input_ipaddr = '192.168.1.110'

battery_output_scale = {'v_scale':398.8, 'v_offset':0.0,'i_scale':950.0, 'i_offset':0.0}
battery_output_prefix ='pv.battery.output.'
battery_output_ipaddr =  '192.168.1.148'

battery_test_scale = {'v_scale':398.8, 'v_offset':0.0,'i_scale':1425.0, 'i_offset':0.0}
battery_test_prefix = 'pv.battery.test.'
battery_test_ipaddr =  '192.168.1.110'

def process_sensor(ipaddr, prefix, scale):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            print("connecting to ", ipaddr)
            s.settimeout(2)
            s.connect((ipaddr, 1884)) 
            s.sendall(bytearray(json.dumps(scale), 'utf8'))
        except OSError:
            print ('Socket connect failed! Loop up and try socket again')
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
                elif 'current' in item:
                    label=prefix+'current'
                print(label, value)
                try:
                    rc = client.publish(label, value)
                except:
                    print("error posting measurement, skipping")
                update_db(label, value)
            except:
                print ("error processing ", label)

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
        

