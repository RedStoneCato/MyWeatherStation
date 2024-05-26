import os
import glob
import time
import sys
import datetime
import board
import busio
import http.client
import urllib

#import urllib.request as urllib2
import adafruit_ads1x15.ads1015 as ADS
import RPi.GPIO as GPIO

from adafruit_bme280 import basic as adafruit_bme280
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL,board.SDA)
bme = adafruit_bme280.Adafruit_BME280_I2C(i2c)
ads = ADS.ADS1015(i2c)
ads.gain = 1

interval = 15  #Time between loops in seconds
windTick = 0   #Used to count the number of times the wind speed is triggered
rainTick = 0   #Used to count the number of times the rain input is triggered 

key = "56J8MRNIQ6RJVWFZ"

#Set GPIO pins to use BCM pin numbers for windspeed
GPIO.setmode(GPIO.BCM)

#Set digital pin 17 to an input and enable the pullup for windspeed
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Set digital pin 23 to an input and enable the pullup for rain measurement
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Event to detect wind (4 ticks per revolution) for windspeed
GPIO.add_event_detect(17, GPIO.BOTH)
def windtrig(self):
        global windTick
        windTick += 1

GPIO.add_event_callback(17, windtrig)

#Event to detect rainfall tick
GPIO.add_event_detect(23, GPIO.FALLING)
def raintrig(self):
        global rainTick
        rainTick += 1

GPIO.add_event_callback(23, raintrig)

#Initiate the DS18B20 temperature sensor
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

#Set up location of the sensor in the system
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def read_temp_raw(): #a function thatgrabs the raw temperature data from the sensor
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines

def read_temp(): #a function that checks that the connection was good and strips out the temperature
        lines = read_temp_raw()
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos !=-1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string)/1000.0
            temp_f = temp_c * 9.0/5.0 + 32
            return temp_c

while True: #infinite loop
    time.sleep(interval)

    #Pull temp from DS18B20
    tempin = read_temp() 
    values = [datetime.datetime.now(), tempin]

    #Pull temp from BME280
    case_temp = bme.temperature

    #Pull pressure from BME280 and convert to kPa
    pressure_pa = bme.pressure
    pressure = pressure_pa/10

    #Pull humidity from BME280
    humidity = bme.humidity

    #Calculate wind direction based on ADC reading
    chan = AnalogIn(ads, ADS.P0)
    val = chan.value
    windDir = "Not Connected"
    windDeg = 999

    if 20000 <= val <= 20500:
        windDir = "N"
        windDeg = 0

    if 10000 <= val <= 10500:
        windDir = "NNE"
        windDeg = 22.5

    if 11500 <= val <= 12000:
        windDir = "NE"
        windDeg = 45

    if 2000 <= val <= 2250:
        windDir = "ENE"
        windDeg = 67.5

    if 2300 <= val <= 2500:
        windDir = "E"
        windDeg = 90

    if 1500 <= val <= 1950:
        windDir = "ESE"
        windDeg = 112.5

    if 4500 <= val <= 4900:
        windDir = "SE"
        windDeg = 135

    if 3000 <= val <= 3500:
        windDir = "SSE"
        windDeg = 157.5

    if 7000 <= val <= 7500:
        windDir = "S"
        windDeg = 180

    if 6000 <= val <= 6500:
        windDir = "SSW"
        windDeg = 202.5

    if 16000 <= val <= 16500:
        windDir = "SW"
        windDeg = 225

    if 15000 <= val <= 15500:
        windDir = "WSW"
        windDeg = 247.5

    if 24000 <= val <= 24500:
        windDir = "W"
        windDeg = 270

    if 21000 <= val <= 21500:
        windDir = "WNW"
        windDeg = 292.5

    if 22500 <= val <= 23000:
        windDir = "NW"
        windDeg = 315

    if 17500 <= val <= 18500:
        windDir = "NNW"
        windDeg = 337.5

    #Calculate average windspeed over the last 15 seconds
    windSpeed = (windTick * 1.2) / interval
    windTick = 0

    #Calculate accumulated rainfall over the last 15 seconds
    rainFall = rainTick * 0.2794
    rainTick = 0
    
    #Calculate Windchill Value
    windChillCalc = 13.12 + 0.6215 * tempin - 11.37 * windSpeed ** 0.16 + 0.3965 * tempin * windSpeed ** 0.16
    windChill = windChillCalc

    #Print the results
    ##    print('Temperature: ',case_temp)
    ##    print('Humidity: ',humidity, '%')
    ##    print('Pressure: ',pressure, 'kPa')
    ##    print('Probe Temperature: ', tempin)
    ##    print('Wind Dir: ' , windDir, ' (', windDeg, ')')
    ##    print('Wind Speed: ' , windSpeed, 'KPH')
    ##    print('Rainfall: ' , rainFall, 'mm')
    ##    print('')
    ##    #g = urllib2.urlopen(baseURL + "&field1=%s" % (tempin))

    params = urllib.parse.urlencode({'field1' : tempin, 'field2' : humidity, 'field3' : pressure, 'field4' : windSpeed, 'field5' : windDeg, 'field6' : rainFall, 'field7' : windDir, 'field8' : windChill, 'key':key})

    #Configure header / connection address
    headers = {"Content-typZZe": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = http.client.HTTPConnection("api.thingspeak.com:80")

    #Try to connect to ThingSpeak and send Data
    try:
        conn.request("POST", "/update", params, headers)
        response = conn.getresponse()   
        print(response.status, response.reason)
        data = response.read()
        conn.close()

    #Catch the exception if the connection fails
    except:
        print( "connection failed")
    
