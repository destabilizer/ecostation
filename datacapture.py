#!/usr/bin/env python

'''
This is a simple script that captures data from sensors and send it to the ecostatus server.
'''

import json
import requests
import time
import socket
from threading import Thread

def connect_gps(address, port):
    gpsclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gpsclient.connect((address, port))
    return gpsclient

def get_raw_gps(gpsclient):
    gpsclient.send(b'GET')
    answer = bytes()
    c = b''
    while c != b"\n":
        c = gpsclient.recv(1)
        answer += c
    return answer

def convert_gps(bytes_gps_data):
    return str(bytes_gps_data)

def get_gps(address, port):
    c = connect_gps(address, port)
    r = get_raw_gps(c)
    return convert_gps(r)

def write_data_from_gps(address, port, datadict):
    write_data(get_gps, (address, port), datadict, "gps")

def process_gps(address, port, datadict):
    p = Thread(target=write_data_from_gps, args=(address, port, datadict))
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

def process_pins(board, pindict, datadict):
    process_stack = []
    for dataname, pi in pindict:
        p = Thread(target=write_data_from_pin, args=(board, *pi, datadict, dataname))
        process_stack.append(p)
    return process_stack

def apply_process_stack(process_stack):
    for p in process_stack:
        p.start()
    for p in process_stack:
        p.join()

def join_process_stack(process_stack):
    for d, p in process_stack:
        p.join()

def send_data(dictdata, sourcename, full_address):
    dictdata["type"] = "data"
    dictdata["source"] = sourcename
    req = requests.post(full_address, json=dictdata)
    return (req.status_code, req.reason)


def testloop():
    data = {"temp": 20, "dust": 0.4}
    while True:
        mainloop("testclient", "http://127.0.0.1:8080/")
        sleep(1)

def test():
    ...

def mainloop(sourcename, board, pindict, full_address, gps_address, gps_port):
    data = {}
    process_stack = process_pins(board, pindict, data)
    pgps = process_gps(gps_address, gps_port, data)
    process_stack.append(pgps)
    apply_process_stack(process_stack)
    print("Collected data: ", data)
    try:
        print("starting sending data")
        ans = send_data(data, sourcename, full_address)
        print(ans)
    except:
        print("Unseccessful POST") 

def main(device_name, board, pindict, server_address, server_port, gps_address, gps_port, delay):
    init_pins(board, pindict)
    time.sleep(1)
    full_address = "http://" + str(server_address) + ":" + str(server_port) + "/"
    while True:
        mainloop(device_name, board, pindict, full_address, gps_address, gps_port) #ip server
        time.sleep(delay)
    
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
    delay = 2
    
    main(device_name, board, pindict, server_address, server_port, gps_address, gps_port, delay)
