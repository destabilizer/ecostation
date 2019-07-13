#!/usr/bin/env python

"""
This is a simple script that captures data from sensors and send it to the ecostatus server.
"""


from pyfirmata2 import Arduino
import requests
import time
import socket
from collections import deque
from kthread import KThread

board = None
gpsclient = None
gps_stat = None
sendthread = None


# == GPS actions ==


def connect_gps(address, port, timeout):
    global gpsclient
    gpsclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gpsclient.connect((address, port))
    gpsclient.settimeout(timeout)


def init_gps(address, port, timeout, gps_times_to_reconnect):
    connect_gps(address, port, timeout)
    init_gps_stat(gps_times_to_reconnect)
    for i in range(gps_times_to_reconnect):
        get_raw_gps()


def reconnect_gps(address, port, timeout):
    global gpsclient
    gpsclient.close()
    connect_gps(address, port, timeout)


def init_gps_stat(size):
    global gps_stat
    gps_stat = deque(size*[False], size)


def sum_gps_stat():
    global gps_stat
    for b in gps_stat:
        if b == False: break
    else:
        return True


def get_raw_gps():
    gpsclient.send(b'GET') # probably this is not needed at all
    try:
        b = gpsclient.recv(4096)
        gps_stat.append('False')
    except socket.timeout:
        gps_stat.append('True')
        raise socket.timeout
    return b


def convert_gps(bytes_gps_data):
    gps = str(bytes_gps_data.split(b'\n')[-2])
    list_gps = gps.split('   ')
    datadict = dict()
    datadict["gps_timestamp"] = list_gps[0][2:]
    datadict["latitude"] = list_gps[1]
    datadict["longitude"] = list_gps[2]
    datadict["height"] = list_gps[3]
    return datadict


def get_gps():
    r = get_raw_gps()
    return convert_gps(r)


def write_data_from_gps(datadict):
    datadict.update(get_gps())
    datadict["gps_collected"] = True


# == Board actions ==


def init_board(com_port, sampling_period):
    global board
    board = Arduino(com_port)
    board.samplingOn(sampling_period)


def init_pins(board, pindict):
    for n, t in pindict.values():
        if t == "a":
            board.analog[n].enable_reporting()
        elif t == "d":
            board.digital[n].enable_reporting()
        else:
            pass


def _init_pins(board, pindict):
    init_pins(board, pindict)
    time.sleep(1)


def get_data_from_pin(board, pin_number, pin_type):
    if pin_type == "a":
        return board.analog[pin_number].read()
    elif pin_type == "d":
        return board.digital[pin_number].read()


def write_data_from_pin(board, pin_number, pin_type, datadict, dataname):
    write_data(get_data_from_pin, (board, pin_number, pin_type), datadict, dataname)
    datadict[dataname+"_collected"] = True


# == Threading routines ==


def process_init_gps(address, port, timeout, gps_times_to_reconnect):
    t = KThread(target=init_gps, args=(address, port, timeout, gps_times_to_reconnect))
    return t


def process_reconnect_gps(address, port, timeout):
    t = KThread(target=reconnect_gps, args=(address, port, timeout))
    return t
    

def process_init_board(com_port, sampling_period):
    t = KThread(target=init_board, args=(com_port, sampling_period))
    return t


def process_gps(datadict):
    t = KThread(target=write_data_from_gps, args=(datadict,))
    t.setName('gps')
    return t


def process_init_pins(board, pindict):
    p = KThread(target=_init_pins, args=(board, pindict))
    return p


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


def finish_thread(kthr, dont_kill=False):
    if not dont_kill and kthr.isAlive():
        kthr.terminate()
        print("Thread", kthr.getName(), "is killed!")
    else:
        kthr.join()
        print("Thread", kthr.getName(), "is finished")


def finish_process_stack(process_stack, exceptions=[], dont_kill=[]):
    for p in process_stack:
        if p.getName() in exceptions: continue
        finish_thread(p, dont_kill=(p.getName() in dont_kill))


# == Data processing ==


def write_data(func, args, datadict, dataname):
    r = func(*args)
    datadict[dataname] = r


def new_data(data, pindict):
    mil = int(time.time()*1000)%1000
    ts = time.gmtime()
    hts = time.strftime("%Y/%m/%d %H:%M:%S", ts)
    data["timestamp"] = hts + "." + str(mil)
    for k in pindict.keys():
        data[k+"_collected"]=False
    data["gps_collected"]=False


def init_local_db(mongo_adress, mongo_port):
    from pymongo import MongoClient
    global local_db
    ts = time.gmtime()
    hts = time.strftime("ts%Y-%m-%d_%H-%M-%S", ts)
    local_db = MongoClient()[hts]


def insert_local_db(data):
    global local_db
    local_db.insert_one(data)


def send_data(dictdata, sourcename, full_address):
    dictdata["type"] = "data"
    dictdata["source"] = sourcename
    req = requests.post(full_address, json=dictdata)
    return (req.status_code, req.reason)


# == Sending routines ==


send_deque = None


def init_send_deque(size):
    global send_deque
    send_deque = deque(size*[None], size)


def start_new_send_thread(data, device_name, full_address):
    global send_deque
    sendthread = KThread(target=send_data, args=(data, device_name, full_address))
    sendthread.setName("data_send")
    send_deque.append(sendthread)
    print("Starting sending data...")
    sendthread.start()


def finish_last_send_thread():
    global send_deque
    ls = send_deque[0]
    if ls: finish_thread(ls)


# == GPS reconnection routine ==


is_reconnecting_gps = False
reconnecting_step = 0
rgps = None


def start_gps_reconnection(gps_address, gps_port, gps_timeout):
    global is_reconnecting_gps
    global reconnecting_step
    global rgps
    is_reconnecting_gps = True
    reconnecting_step = 0
    rgps =  process_reconnect_gps(gps_address, gps_port, gps_timeout)
    rgps.start()


def set_gps_reconnection():
    global is_reconnecting_gps
    is_reconnecting_gps = True


def kill_gps_reconnection_and_start_new(gps_address, gps_port, gps_timeout):
    global rgps
    rgps.terminate()
    start_gps_reconnection(gps_address, gps_port, gps_timeout)


def add_gps_reconnection_step():
    global reconnecting_step
    reconnecting_step += 1


def finish_gps_reconnection():
    global rgps
    global is_reconnecting_gps
    rgps.join()
    is_reconnecting_gps = False


#def test():
#    data = {"temp": 20, "dust": 0.4}
#    while True:
#        mainloop("testclient", "http://127.0.0.1:8080/")
#        sleep(1)

# == Main routine ==

def main(device_name, com_port, sampling_period, pindict,
         server_address, server_port,
         gps_address,       gps_port,
         mongo_address,   mongo_port,
         delay, use_local_db, send_wait,
         gps_timeout_to_reconnect, gps_reconnect_wait):

    global board
    
    gps_times_to_reconnect = (gps_timeout_to_reconnect + delay - 1) // delay
    send_times_to_try = (send_wait + delay - 1) // delay
    delay /= 1000
    send_wait /= 1000
    gps_reconnect_wait /= 1000
    gps_timeout = delay*0.99
    t_gps = process_init_gps(gps_address, gps_port,
                             gps_timeout, gps_times_to_reconnect) # Initialization
    t_board = process_init_board(com_port, sampling_period)
    t_gps.start()
    t_board.start()
    t_board.join()
    t_pins = process_init_pins(board, pindict)
    t_pins.start()
    t_pins.join()
    t_gps.join()

    init_gps_stat(gps_times_to_reconnect)
    init_send_deque(send_times_to_try)
    if use_local_db: init_local_db(mongo_address, mongo_port)     # Using local db
    
    full_server_address = "http://" + str(server_address) + ":" + str(server_port) + "/"
    data = {}
    
    while True:                                                    # mainloop
        new_data(data, pindict)
        
        process_stack = []
        add_pins = lambda: process_stack.extend(process_pins(board, pindict, data)) # add pins thread
        # add_send = lambda: process_stack.append(sendthread)         # add data_send thread to stack
        add_gps  = lambda: process_stack.append(process_gps(data))  # add gps thread to stack

        add_pins()
        # if sendthread: add_send()
        if is_reconnecting_gps:
            if rgps.isAlive() and reconnecting_step >= gps_reconnect_wait:
                kill_gps_reconnection_and_start_new(gps_address, gps_port, gps_timeout)
            elif rgps.isAlive() and reconnecting_step < gps_reconnect_wait:
                add_gps_reconnection_step()
            else:
                finish_gps_reconnection()
                add_gps()
        elif sum_gps_stat():
            add_gps()
        else:
            start_gps_reconnection(gps_address, gps_port, gps_timeout)

        start_process_stack(process_stack)
        time.sleep(delay)                      # <= constant delay for catching data
        finish_process_stack(process_stack)    # <= maybe exceptions=["send_data"] 
        finish_last_send_thread()              # for giving more time to send data

        cdata = data.copy()
        print("Collected data: ", cdata)
        start_new_send_thread(cdata, device_name, full_server_address) # sending collected data
        if use_local_db: insert_local_db(cdata)
