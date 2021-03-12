import time
import Adafruit_DHT
from src import bmp280
from src import bh1750
from src import ADS1x15

GAIN = 2/3
DHT11_SENSOR = Adafruit_DHT.DHT11
DHT11_PIN = 14

DHT22_SENSOR = Adafruit_DHT.DHT22
DHT22_PIN = 15


bmp = bmp280.BMP280(0x76)
adc = ADS1x15.ADS1115()

print("| {0:>6} | {1:>6} | {2:>6} | {3:>6} | {4:>6} | {5:>6} | {6:>6} | {7:>6} | {8:>6} |".format("TEM11", "TEM22", "HUM11", "HUM22", "GAS", "RAIN", "LIGHT", "BMP", "BMPADJ"))

while True:
    light = bh1750.readLight() + 1.6
    humidity1, temperature1 = Adafruit_DHT.read_retry(DHT11_SENSOR, DHT11_PIN, delay_seconds=0)
    humidity2, temperature2 = Adafruit_DHT.read_retry(DHT22_SENSOR, DHT22_PIN, delay_seconds=0)
    pressure = round(bmp.get_pressure(), 2)
    values = [0]*4
    for i in range(4):
        values[i] = adc.read_adc(i, gain=GAIN)
    print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} | {4:>6} | {5:>6} | {6:>6} | {7:>6} | {8:>6} |'.format(round(temperature1, 1), round(temperature2, 1), round(humidity1, 1), round(humidity2, 1), values[0], values[1], light, pressure, pressure-727))
    time.sleep(1)
