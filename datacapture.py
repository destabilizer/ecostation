#!/usr/bin/env python

'''
This is a simple script that captures data from datchiki and send it to the ecostatus server.
'''

import json
import urllib2
from time import sleep

def send_data(dictdata, sourcename, address, port):
    dictdata["type"] = "data"
    dictdata["source"] = sourcename
    
    req = urllib2.Request(str(address)+":"+str(port))
    req.add_header('Content-Type', 'application/json')

    response = urllib2.urlopen(req, json.dumps(dictdata))
    return response

def get_data():
    return {"temp": 20, "dust": 0.4}

def mainloop(sourcename, address, port):
    d = get_data()
    send_data(d, sourcename, address, port)

def maintest():
    while True:
        mainloop("testclient", "127.0.0.1", 8080)
        sleep(1)
    
if __name__=="__main__":
     maintest()
