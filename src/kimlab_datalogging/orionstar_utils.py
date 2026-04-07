import serial
from pathlib import Path
import time
from datetime import datetime
import re

def get_reading_from_versastar(ser, meas_type='DO', command=b"GETMEAS\r\n"):
    
    meas_type = meas_type.lower()
    if meas_type == 'ph':
        search_phrase = 'PH'
    elif meas_type == 'do':
        search_phrase = 'DO'

    ser.write(command)
    now = datetime.now()

    # print(f'{now}: >>> {command.decode('utf-8').strip()}')
    reading = None

    while ser.in_waiting > 0:

        now = datetime.now()
        response = ser.read_all().decode('utf-8').strip()
        # print(f'{now}\nResponse: {response}')

        if meas_type == 'do' or meas_type == 'rdo':
            reading = get_DO_from_versastar_string(response, search_phrase=search_phrase, verbose_flag=True)
        elif meas_type == 'ph':
            reading = get_pH_from_versastar_string(response, search_phrase=search_phrase)


        # ph  = get_pH_from_versastar_string(response)
        # DO = get_DO_from_versastar_string(response)
        # print(f'{now}\npH={ph}. Response: {response}')
    return reading

def get_pH_from_versastar_string(response, search_phrase):
    reading = response.split(search_phrase)[1].split(',')[0]
    reading = float(reading)
    return reading

def get_DO_from_versastar_string(reading: str, search_phrase: str, verbose_flag=False) -> float:
    reading = reading.split(',')
    DO_index = [idx for idx, s in enumerate(reading) if search_phrase in s][0] + 1
    DO = float(reading[DO_index])
    DO_unit = reading[DO_index + 1]
    DO_pct = float(reading[DO_index + 2])
    
    T_string = 'C (ATC)'
    T_index = [idx for idx, s in enumerate(reading) if T_string in s][0] - 1
    T = float(reading[T_index])
    
    p_string = 'mmHg'
    p_index = [idx for idx, s in enumerate(reading) if p_string in s][0] - 1
    p = float(reading[p_index])

    if verbose_flag:
        # print('DO: {:2.3f} {} ({:2.2f}%)'.format(DO, DO_unit, DO_pct))
        # print('T: {:2.1f} {}'.format(T, T_string))
        # print('T: {:3.1f} {}'.format(p, p_string))

        return DO, DO_unit, DO_pct, T, T_string, p, p_string
    else:
       return DO

def read_for_n_seconds(ser: serial.Serial, n_seconds: int, readings_per_second=1):
    now = datetime.now()
    print(f'{now}: Start')
    command = b"GETMEAS\r\n"
    n_readings = int(n_seconds * readings_per_second)
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
        read_for_n_seconds(ser, 2, readings_per_second=1)
        # get_ph_measurement_from_orionstar(ser)
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