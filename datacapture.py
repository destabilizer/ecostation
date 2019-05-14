#!/usr/bin/env python

'''
This is a simple script that captures data from sensors and send it to the ecostatus server.
'''

import json
import requests
import time
import socket
from kthread import KThread

gpsclient = None
sendthread = None

def connect_gps(address, port):
    global gpsclient
    gpsclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gpsclient.connect((address, port))
    return gpsclient

def get_raw_gps():
    gpsclient.send(b'GET')
    b = gpsclient.recv(4096)
    return b

def convert_gps(bytes_gps_data):
    gps = str(bytes_gps_data.split(b'\n')[-2])
    list_gps = gps.split('   ')
    datadict = {}
    datadict["gps_timestamp"] = list_gps[0][2:]
    datadict["latitude"] = list_gps[1]
    datadict["longitude"] = list_gps[2]
    datadict["height"] = list_gps[3]
    return datadict

def get_gps(address, port):
    r = get_raw_gps()
    return convert_gps(r)

def write_data_from_gps(address, port, datadict):
    datadict.update(get_gps(address, port))
    datadict["gps_collected"] = True

def process_gps(address, port, datadict):
    p = KThread(target=write_data_from_gps, args=(address, port, datadict))
    p.setName("gps")
    return p
    
def init_pins(board, pindict):
    for n, t in pindict.values():
        if t == "a":
            board.analog[n].enable_reporting()
        elif t == "d":
            board.digital[n].enable_reporting()
        else:
            pass

def get_data_from_pin(board, pin_number, pin_type):
    if pin_type == "a":
        return board.analog[pin_number].read()
    elif pin_type == "d":
        return board.digital[pin_number].read()

def write_data(func, args, datadict, dataname):
    r = func(*args)
    datadict[dataname] = r

def write_data_from_pin(board, pin_number, pin_type, datadict, dataname):
    write_data(get_data_from_pin, (board, pin_number, pin_type), datadict, dataname)
    datadict[dataname+"_collected"] = True

def process_pins(board, pindict, datadict):
    process_stack = []
    for dataname, pi in pindict.items():
        p = KThread(target=write_data_from_pin, args=(board, *pi, datadict, dataname))
        p.setName(dataname)
        process_stack.append(p)
    return process_stack

def start_process_stack(process_stack):
    for p in process_stack:
        print(p.getName())
        p.start()
        print("Started!")

def join_process_stack(process_stack):
    for d, p in process_stack:
        p.join()

def send_data(dictdata, sourcename, full_address):
    dictdata["type"] = "data"
    dictdata["source"] = sourcename
    req = requests.post(full_address, json=dictdata)
    return (req.status_code, req.reason)

def finish_thread(kthr):
    if kthr.isAlive():
        kthr.terminate()
        print("Thread", kthr.getName(), "is killed!")
    else:
        kthr.join()
        print("Thread", kthr.getName(), "is finished")

def new_send_thread(data, device_name, full_address):
    global sendthread
    sendthread = KThread(target=send_data, args=(data, device_name, full_address))
    sendthread.setName("data_send")

def start_send_thread():
    global sendthread
    sendthread.start()

def finish_send_thread():
    finish_thread(sendthread)

def finish_process_stack(process_stack):
    for p in process_stack:
        finish_thread(p)

def new_data(data, pindict):
    data["timestamp"] = str(int(time.time()))
    for k in pindict.keys():
        data[k+"_collected"]=False
    data["gps_collected"]=False

def create_local_db(mongo_adress, mongo_port):
    from pymongo import MongoClient
    global local_db
    local_db = MongoClient()[str(int(time.time()))]

def isert_local_db(data):
    local_db.insert_one(data)
    
#def test():
#    data = {"temp": 20, "dust": 0.4}
#    while True:
#        mainloop("testclient", "http://127.0.0.1:8080/")
#        sleep(1)

def main(device_name, board, pindict,
         server_address, server_port,
         gps_address,       gps_port,
         mongo_address,   mongo_port
         delay, use_local_db):

    init_pins(board, pindict)
    connect_gps(gps_address, gps_port)
    time.sleep(1)
    if use_local_db: create_local_db(mongo_adress, mongo_port)
    full_address = "http://" + str(server_address) +\
                       + ":" + str(server_port) + "/"
    data = {}
    new_send_thread(data, device_name, full_address)
    while True:
        print("starting sending data")
        start_send_thread()
        
        new_data(data, pindict)
        process_stack = process_pins(board, pindict, data)
        pgps = process_gps(gps_address, gps_port, data)
        process_stack.append(pgps)
        
        start_process_stack(process_stack)
        time.sleep(delay) # constant delay for catching data
        finish_process_stack(process_stack)
        finish_send_thread()

        cdata = data.copy()
        print("Collected data: ", cdata)
        new_send_thread(cdata, device_name, full_address)
        if use_local_db: insert_local_db(cdata)
            
    
if __name__=="__main__":
    from pyfirmata2 import Arduino
    
    board = Arduino('COM4')
    board.samplingOn(100)
    
    device_name = "lattepanda1"
    pindict = {"co": (0, "a"), "sound": (1, "a"), "light": (2, "a")} 
    server_address = "192.168.8.69"
    server_port = 8080
    gps_address = "192.168.8.110"
    gps_port = 8080
    delay = 1
    use_local_db = False
    mongo_address = None
    mongo_port = None
    
    main(device_name, board, pindict,
         server_address, server_port,
         gps_address        gps_port,
         mongo_address,   mongo_port
         delay, use_local_db)
