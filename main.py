import time
import datetime
import json
import jwt
import time
import Adafruit_DHT
import urllib.request, urllib.error
import configparser
from src import bmp280
from src import bh1750
from src import ADS1x15
from tendo import singleton
from gpiozero import CPUTemperature
from pushbullet import Pushbullet
import paho.mqtt.client as mqtt

me = singleton.SingleInstance() # will sys.exit(-1) if another instance of this program is already running

parser = configparser.ConfigParser()
parser.read('/home/pi/Project/IoT-WeatherForecast/config/config.ini')
api = parser['pushbullet']['api']
pb = Pushbullet(api)

# Constants that shouldn't need to be changed
token_life = 60 #lifetime of the JWT token (minutes)
# end of constants

GAIN = 2/3
DHT11_SENSOR = Adafruit_DHT.DHT11
DHT11_PIN = 14

DHT22_SENSOR = Adafruit_DHT.DHT22
DHT22_PIN = 15


bmp = bmp280.BMP280(0x76)
adc = ADS1x15.ADS1115()

def getSensorData():
    light = bh1750.readLight()
    hum11, temp11 = Adafruit_DHT.read_retry(DHT11_SENSOR, DHT11_PIN, delay_seconds=0)
    hum22, temp22 = Adafruit_DHT.read_retry(DHT22_SENSOR, DHT22_PIN, delay_seconds=0)
    pressure = round(bmp.get_pressure(), 2)
    cputemp = CPUTemperature().temperature
    values = [0]*2
    for i in range(2):
        values[i] = adc.read_adc(i, gain=GAIN)
    return round(temp22, 2), round(hum22, 2), pressure, light, values[0], values[1], temp11, hum11, cputemp

def create_jwt(cur_time, projectID, privateKeyFilepath, algorithmType):
  token = {
      'iat': cur_time,
      'exp': cur_time + datetime.timedelta(minutes=token_life),
      'aud': projectID
  }

  with open(privateKeyFilepath, 'r') as f:
    private_key = f.read()

  return jwt.encode(token, private_key, algorithm=algorithmType) # Assuming RSA, but also supports ECC

def error_str(rc):
    return '{}: {}'.format(rc, mqtt.error_string(rc))

def on_connect(unusued_client, unused_userdata, unused_flags, rc):
    print('on_connect', error_str(rc))

def on_publish(unused_client, unused_userdata, unused_mid):
    print('on_publish')

def createJSON(timestamp, temp, hum, press, light, airq, rain, in_temp, in_hum, cputemp):
    data = {
	'timestamp' :timestamp,
	'temp' : temp,
	'hum' : hum,
	'press' : press,
    'light' : light,
    'airq' : airq,
    'rain' : rain,
    'in_temp' : in_temp,
    'in_hum' : in_hum,
    'cputemp' : cputemp
    }

    json_str = json.dumps(data)
    return json_str

def wait_for_connection():
    while True:
        try:
            check = urllib.request('8.8.8.8', timeout=1)
        except urllib.error.URLError:
            pass

def main():
    project_id = "single-cirrus-307302"
    gcp_location = "asia-east1"
    registry_id = "raspberry"
    device_id = "raspberrypi"
    root_cert_filepath = "/home/pi/.ssh/roots.pem"
    ssl_private_key_filepath = "/home/pi/.ssh/ec_private.pem"
    ssl_algorithm = "ES256"
    googleMQTTURL = "mqtt.googleapis.com"
    googleMQTTPort = 8883

    _CLIENT_ID = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(project_id, gcp_location, registry_id, device_id)
    _MQTT_TOPIC = '/devices/{}/events'.format(device_id)
	
    pb.push_note("IoTWeather", "Device is Running")
    print ("Ready. Waiting for signal.")
    
    while True:

        client = mqtt.Client(client_id=_CLIENT_ID)
        cur_time = datetime.datetime.utcnow()
        # authorization is handled purely with JWT, no user/pass, so username can be whatever
        client.username_pw_set(
            username='unused',
            password=create_jwt(cur_time, project_id, ssl_private_key_filepath, ssl_algorithm))

        client.on_connect = on_connect
        client.on_publish = on_publish

        client.tls_set(ca_certs=root_cert_filepath) # Replace this with 3rd party cert if that was used when creating registry
        client.connect(googleMQTTURL, googleMQTTPort)

        jwt_refresh = time.time() + ((token_life - 1) * 60) #set a refresh time for one minute before the JWT expires

        client.loop_start()

        while time.time() < jwt_refresh: # as long as the JWT isn't ready to expire, otherwise break this loop so the JWT gets refreshed
        # Continuously monitor for heart beat signals being received
            try:
                currentTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                temp, hum, press, light, airq, rain, in_temp, in_hum, cputemp = getSensorData()

                payload = createJSON(currentTime, temp, hum, press, light, airq, rain, in_temp, in_hum, cputemp)
                client.publish(_MQTT_TOPIC, payload, qos=1)
                # print("{}\n".format(payload))
                # time.sleep(0.5)
            except Exception as e:
                pb.push_note("IoTWeather - ERROR", "Connection error")
                pb.push_note("IoTWeather - ERROR", e)
                print("There was an error")
                print(e)
            time.sleep(20)    
        client.loop_stop()

if __name__ == '__main__':
	main()
