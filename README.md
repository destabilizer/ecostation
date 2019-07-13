## Ecostation

This is the script that collects sensor data and gps coordinates and sends it to the server.
It's divided into simple functions that organising threads, and the main function is managing them.

```python
def main(device_name, com_port, sampling_period, pindict,
 server_address, server_port,
 gps_address,   gps_port,
 mongo_address,   mongo_port,
 delay, use_local_db, send_wait,
 gps_timeout_to_reconnect, gps_reconnect_wait): ...
```

* device_name: the name that will identify this client, for example "lattepanda"
* com_port: the port on which arduino is connected
* sampling_period: sampling period for pyfirmata2, 100 (ms) recommended
* pindict: dictionary with pin mapping, where key:value pair is data type:(pin type, pin number). See example
* server_address: address of server
* server_port: 
* gps_address: address of server with gps coordinates
* gps_port:
* mongo_address: address of mongodb server
* mongo_port: 
* delay: times to wait between data collecting, in ms
* use_local_db: set True if you want to save data locally for safity, False otherwise
* send_wait: (ms) sending timeout. If data hadn't send in this time, it will be lost until you set use_local_db
* gps_timeout_to_reconnect: (ms) if gps server is unavailable more than this time, it will try to reconnect
* gps_reconnect_wait: (ms) how many time wait for reconnecting to gps server

This function manages routines what collects data from gps server and pins, saves (or not) them locally and sending
it to server. It's working cycle looks like this:

0. Fix time.
1. Initialize threads that collecting data from pins.
2. Initialize threads that collecting gps. If gps is reconnecting, wait.
3. START ALL THREADS. Data is collecting synchronously.
4. Wait delay.
5. Let's have a look on threads. Is something is tempting -- killing it. If gps hadn't collected, starting
gps reconnection.
6. Starting sending data to the server and saving it locally.

Example run (from `start.py`):
```python
device_name = "lattepanda1"
com_port = 'COM4'
sampling_period = 100
pindict = {"co": (0, "a"), "sound": (1, "a"), "light": (2, "a")} 
server_address = "192.168.8.69"
server_port = 8080
gps_address = "192.168.8.110"
gps_port = 8080
delay = 100
use_local_db = False
mongo_address = None
mongo_port = None
send_wait = 4000
gps_timeout_to_reconnect = 2000
gps_reconnect_wait = 3000

main(device_name, com_port, sampling_period, pindict,
     server_address, server_port,
     gps_address,       gps_port,
     mongo_address,   mongo_port,
     delay, use_local_db, send_wait,
     gps_timeout_to_reconnect, gps_reconnect_wait)
```
