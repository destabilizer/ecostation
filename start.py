from datacapture import main

if __name__=="__main__":
    device_name = "lattepanda1"
    com_port = 'COM4'
    sampling_period = 100
    pindict = {"co": (0, "a"), "sound": (1, "a"), "light": (2, "a")} 
    server_address = "192.168.8.69"
    server_port = 8080
    gps_address = "192.168.8.110"
    gps_port = 8080
    delay = 1
    use_local_db = False
    mongo_address = None
    mongo_port = None
    gps_times_to_reconnect = 4
    gps_reconnect_wait = 4
    
    main(device_name, com_port, sampling_period, pindict,
         server_address, server_port,
         gps_address        gps_port,
         mongo_address,   mongo_port
         delay, use_local_db,
         gps_times_to_reconnect, gps_reconnect_wait)
