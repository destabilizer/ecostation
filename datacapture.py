#!/usr/bin/env python

'''
This is a simple script that captures data from sensors and send it to the ecostatus server.
'''

import json
import requests
import time
import socket

def connect_gps(address, port):
    global gpsclient
    gpsclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gpsclient.connect((address, port))

def get_raw_gps():
    gpsclient.send(b'GET')
    answer = bytes()
    c = b''
    while c != b"\n":
        c = gpsclient.recv(1)
        answer += c
    return answer

def send_data(dictdata, sourcename, full_address):
    dictdata["type"] = "data"
    dictdata["source"] = sourcename

    req = requests.post(full_address, json=dictdata)
    return (req.status_code, req.reason)

def fake_get_data():
    return {"temp": 20, "dust": 0.4}

def get_data():
    value_light = board.analog[2].read()
    value_sound = board.analog[1].read()
    value_co = board.analog[0].read()
    llh_gps = requests.get('https://192.128.8.110') #ip rover
    #parsing into value_gps
    return {"light": value_light, "sound": value_sound, "co": value_co}

def mainloop(sourcename, full_address):
    d = get_data()
    print(d)
    try:
        print("starting sending data")
        ans = send_data(d, sourcename, full_address)
        print(ans)
    except:
        print("Unseccessful POST")

        
def maintest():
    global get_data
    get_data = fake_get_data
    while True:
        mainloop("testclient", "http://127.0.0.1:8080/")
        sleep(1)

def main():
    from pyfirmata2 import Arduino

    global board

    board = Arduino('COM4')
    board.samplingOn(100)

    board.analog[2].enable_reporting()
    board.analog[1].enable_reporting()
    board.analog[0].enable_reporting()

    while True:
        mainloop("lattepanda1", "http://192.168.8.69:8080/") #ip server
        print("ok")
        time.sleep(2)
    
if __name__=="__main__":
     main()
