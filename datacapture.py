#!/usr/bin/env python

'''
This is a simple script that captures data from sensors and send it to the ecostatus server.
'''

import json
import requests
from time import sleep

def send_data(dictdata, sourcename, full_address):
    dictdata["type"] = "data"
    dictdata["source"] = sourcename

    req = requests.post(full_address, json=dictdata)
    return (req.status_code, req.reason)

def fake_get_data():
    return {"temp": 20, "dust": 0.4} 

def mainloop(sourcename, full_address):
    d = get_data()
    try:
        send_data(d, sourcename, full_address)
    except:
        print("Unseccessful POST")
        
def maintest():
    global get_data
    get_data = fake_get_data
    while True:
        mainloop("testclient", "http://127.0.0.1:8080/")
        sleep(1)
    
if __name__=="__main__":
     maintest()
