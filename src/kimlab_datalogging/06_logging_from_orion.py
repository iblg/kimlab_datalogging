import serial
from pathlib import Path
import time
from datetime import datetime
import re

def extract_pH_from_versastar_string(reading: str):
    """
    VERSA STAR,V01687,2.73,03-03-26,1:00:58 PM,Ch-1,-----,5,-----,VA02961,PH,5.340,pH,54.0,m>,22.5,C (ATC),97.9,%,100

    """
    ph = reading.split('PH,')[1].split(',')[0]
    ph = float(ph)

    return ph

def read_for_n_seconds(ser: serial.Serial, n_seconds: int, readings_per_second=1):
    now = datetime.now()
    print(f'{now}: Start')
    command = b"GETMEAS\r\n"
    n_readings = n_seconds * readings_per_second
    t_interval = 1/readings_per_second
    print(f'Will read for {n_seconds} seconds')
    print(f'Will take {readings_per_second} readings per second')
    print(f'Will wait {t_interval} seconds between measurements')
    print(f'Will take {n_readings} total.')

    for i in range(n_readings):
        time.sleep(t_interval)

        now = datetime.now()

        ser.write(command)
        print(f'{now}: >>> {command.decode('utf-8').strip()}')
        # print(20*'*')
        while ser.in_waiting > 0:
            now = datetime.now()
            response = ser.read_all().decode('utf-8').strip()
            ph  = extract_pH_from_versastar_string(response)
            print(f'{now}\npH={ph}. Response: {response}')
            


    return

def main():
    """
    Note: make sure to enter Setup > pH (or whatever probe you are using) > Mode > Continuous
    and set it back to auto when ytou are done, for the best interests of other users.
    """
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=9600,  # Check meter manual for 38400 if 9600 fails
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=0.1
        )
        read_for_n_seconds(ser, 5, readings_per_second=1)

        # time.sleep(2)  # Allow time for connection to stabilize

        # ser.reset_input_buffer()  # Clear junk from input buffer

        # # Trying different command formats
        # # command = b"*IDN?\r"  # Adjust EOL characters if necessary

        # #### THIS WORKS!!!
        # command = b"GETMEAS\r\n"  # Adjust EOL characters if necessary

        # ser.write(command)
        # print(f"Sent command: {command}")

        # time.sleep(5)  # Increase wait time for response

        # while ser.in_waiting > 0:
        #     response = ser.read_all().decode('utf-8').strip()
        #     print(f"Meter Response: {response}")

        # if ser.in_waiting == 0:
        #     print("No data received")

        # ser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()