from labjack import ljm
import labjack_utils as lu
from datetime import datetime
import pandas as pd
from pathlib import Path
import shutil
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
import threading
import queue
import serial
import numpy as np
from orionstar_utils import get_reading_from_versastar


def set_time_interval_between_readings(interval_handle, seconds_between_readings):
    microseconds_between_readings = int(seconds_between_readings*10**6)
    ljm.startInterval(interval_handle, microseconds_between_readings)
    return

def create_axes(temp_unit, flow_unit, DO_unit):
    fig, ax = plt.subplots(nrows=3, sharex=True)
    # plt.title('Thermocouple Temperature Over Time')
    ax[-1].set_xlabel('Time')
    ax[0].set_ylabel(f'Temperature ({temp_unit})')
    ax[1].set_ylabel(f'Weight ({flow_unit})')
    ax[2].set_ylabel(f'DO ({DO_unit})') #### CURRENTLY ASSUMES IN MG/L
    ax[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    return fig, ax


def copy_to_onedrive(path_to_file: Path, target_dir: Path) -> None:
    # print(filename)
    filename = path_to_file.name
    shutil.copy2(path_to_file, target_dir)

    return


def read_weight(ser):
    while ser.in_waiting > 0:

        weight = ser.read_all()
    
        if b'-' in weight:
            A = -1
            weight = weight.split(b'-')[1]
        else:
            A = 1
        

        # weight = weight.strip(b' g \r\n')
        weight = weight.split(b' g  \r\n')[0]


        if weight == b'':
            return None
        else:
            weight = float(weight)    
            weight = A * weight
            return weight



def read_and_log_thermocouples(
        thermocouple_channels=[0],
        flow_channels=[3],
        tc_type: str = 'k',
        temp_unit: str = 'C',
        flow_unit: str = 'g',
        DO_unit: str = 'mg/L',
        seconds_between_readings: float = 1.0,
        print_output_flag: bool = True,
        save_to: bool | Path = False,
        message_queue=None,
        exclude_channels_from_plot=[],
        ):
    

    
    handle, device_type = lu.get_labjack_handle()
    tc_index = lu.set_tc_index(tc_type)
    cjc_slope, cjc_offset = lu.set_cjc_slope_offset(tc_type) # currently only implemented for K-type thermocouples
    temp_unit_index = lu.get_temp_unit_index(temp_unit)

    channel_names = [lu.create_analog_channel(channel) for channel in thermocouple_channels]
    plot_channel_names = [name for name in channel_names if name not in exclude_channels_from_plot]

    neg_channel_values = []
    neg_channel_registers = []
    for channel_name in channel_names:
        ncv, ncr = lu.get_channel_value_register(handle, device_type, channel_name)
        neg_channel_values.append(ncv)
        neg_channel_registers.append(ncr)
    
    cjc_addresses = [lu.get_cjc_address(device_type, channel) for channel in thermocouple_channels]

    lu.set_resolution_index_registers(handle, channel_names, thermocouple_channels)
    lu.configure_ain_ef_registers(handle, channel_names, tc_index, temp_unit_index, cjc_addresses, cjc_slope, cjc_offset)
    interval_handle = 1
    set_time_interval_between_readings(interval_handle, seconds_between_readings)

    abcs, labels = [], []
    for channel_name in channel_names:
        
        print(f'Channel name: {channel_name}')
        abc, label = lu.get_read_ABC(channel_name)
        abcs.append(abc)
        labels.append(label)
        ljm.eWriteName(handle, f'{channel_name}_RANGE', 0.1)
        ljm.eWriteName(handle, f'{channel_name}_RESOLUTION_INDEX', 12)
        ljm.eWriteName(handle, f'{channel_name}_SETTLING_US', 0)
        if channel_name == 'AIN0':
            ljm.eWriteName(handle, f'{channel_name}_NEGATIVE_CH', 1)
        elif channel_name == 'AIN2':
            ljm.eWriteName(handle, f'{channel_name}_NEGATIVE_CH', 3)
        else:
            print('No negative channel')

    scale = serial.Serial(port='/dev/ttyUSB0',
                          baudrate=9600,
                          parity=serial.PARITY_NONE,
                          bytesize=8,
                          timeout=0.1

                          )
    # scale.write(b'CONTINUOUS')


    # to find COM Ports in Windows: /c/Windows/System32/mode.com # to be run in terminal
    # to find COM ports in linux: sudo dmesg | grep tty
    orionstar = serial.Serial(
            # port='COM6',
            port = '/dev/ttyUSB1',
            baudrate=9600,  # Check meter manual for 38400 if 9600 fails
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=0.1
        )
    orionstar_prompt = b"GETMEAS\r\n"

    abcs_flattened = [i for row in abcs for i in row]
    labels_flattened = [i for row in labels for i in row]
    labels_flattened.append('time')
    labels_flattened.append('dt')
    labels_flattened.append('message')
    labels_flattened.append('DO')
    labels_flattened.append('flow rate voltage')

    times = []
    thermocouple_temps = {cn: [] for cn in channel_names}
    all_data = []
    time_format = "%Y/%m/%d, %H:%M:%S.%f"

    start_time = datetime.now()
    save_time_format = "%Y_%m_%d_%H_%M_%S"
    formatted_start_time = datetime.strftime(start_time, save_time_format)

    data_df = pd.DataFrame()

    # prep_to_save
    if save_to is False:
        pass
    elif save_to.is_dir():
        save_to.mkdir(exist_ok=True)
        save_to = save_to / (formatted_start_time + '.csv')
        data_df.to_csv(save_to, index=False)
    else:
        save_to.parent.mkdir(exist_ok=True)
        data_df.to_csv(save_to, index=False)

    fig, ax = create_axes(temp_unit, flow_unit, DO_unit)
    
    lines = {channel_name: ax[0].plot([], [], '.', label=f'Thermocouple {channel_name}')[0] for channel_name in plot_channel_names}
    # lines['pH'] = ax[2].plot([],[], '.', label='pH')[0]
    lines['DO'] = ax[2].plot([],[], '.', label='DO')[0]
    lines['flow_rate'] = ax[1].plot([],[], '.', label='flow rate', alpha=0.4)[0]
    lines['flow_rate_smoothed'] = ax[1].plot([],[], '.', label='flow rate')[0]

    thermocouple_index = [3*i for i in range(len(thermocouple_channels))]
    # flowmeter_index = -2 # to avoid problems, the flowmeter should be attached to the labjack at the highest analog input position

    pH_list = []
    weight_list = []
    DO_list = []

    counterDIO = 0

    # ljm.eWriteName(handle, "DIO%d_EF_ENABLE" % counterDIO, 0)  # Enable the DIO#_EF Mode.
    # ljm.eWriteName(handle, "DIO%d_EF_INDEX" % counterDIO,  8)  # Set DIO#_EF_INDEX to 8 for Interrupt Counter.
    # ljm.eWriteName(handle, "DAC1_FREQUENCY_OUT_ENABLE",  1)    # Enable 10 Hz square wave on DAC1.
    # ljm.eWriteName(handle, "DIO%d_EF_ENABLE" % counterDIO, 1)  # Enable the DIO#_EF Mode.
    def animate(i):
        current_time = datetime.now()
        formatted_time = datetime.strftime(current_time, time_format)
        dt = (current_time - start_time).total_seconds()
        

        data_in = ljm.eReadNames(handle, len(abcs_flattened), abcs_flattened)
        # flow_rate_voltage = ljm.eReadName(handle, 'ain3')
        # flow_rate = convert_volts_to_flow(float(flow_rate_voltage))
        temperatures = [data_in[idx] for idx in thermocouple_index]
        DO = get_reading_from_versastar(orionstar, meas_type='DO', command=orionstar_prompt)
        try:
            DO_list.append(DO[0])
        except TypeError as te:
            DO_list.append(DO)
        # pH_list.append(pH)
        # weight_list.append(flow_rate)p
        # flow_rate_voltage = ljm.eReadName(handle, 'FIO0')
        # numRisingEdges = ljm.eReadName(handle, "DIO%d_EF_READ_A_AND_RESET" % counterDIO)
        # flow_rate_voltage = numRisingEdges

        # weight_list.append(flow_rate_voltage)
        weight = read_weight(scale)

        if weight is None:
            weight_list.append(None)
            pass
        else:
            weight_list.append(weight)
        # weight_list.append(0) # temporary, while flow meter is down
        # flow_rate_voltage = 0 # temporary
        
        message = ""
        if message_queue and not message_queue.empty():
            message = message_queue.get()

        data_entry = data_in + [formatted_time, dt, message, DO, weight]
        all_data.append(data_entry)
        
        times.append(mdates.date2num(current_time))

        for j, temp in enumerate(temperatures):
            thermocouple_temps[channel_names[j]].append(temp)
            
        # print("Thermocouple temperatures:", thermocouple_temps)  # Debugging line

        for channel_name in plot_channel_names:
            lines[channel_name].set_data(times, thermocouple_temps[channel_name])

        lines['DO'].set_data(times, DO_list)
        lines['flow_rate'].set_data(times, weight_list)

        for idx, axis in enumerate(ax):
            # print(f'Relimming axis {idx}')
            axis.relim()

        # [axis.relim() for axis in ax]
        [axis.autoscale_view() for axis in ax]
        [axis.legend() for axis in ax]

        if print_output_flag:
            print(data_entry)

        data_df = pd.DataFrame(all_data, columns=labels_flattened)
        data_df.to_csv(save_to, index=False)


    ani = FuncAnimation(fig, animate, interval=seconds_between_readings * 1000, save_count=3)
    plt.show()

    data_df = pd.DataFrame(all_data, columns=labels_flattened)
    data_df['T unit'] = temp_unit

    if save_to is False:
        pass
    elif save_to.is_dir():
        save_to.mkdir(exist_ok=True)
        save_to = save_to / (formatted_start_time + '.csv')
        data_df.to_csv(save_to, index=False)
    else:
        save_to.parent.mkdir(exist_ok=True)
        data_df.to_csv(save_to, index=False)

    ljm.cleanInterval(interval_handle)
    ljm.close(handle)
    print("Done!")
    return

def input_thread(message_queue):
    while True:
        now = datetime.now()
        now = datetime.strftime(now, '%H:%M:%S')
        message = input(f"Enter message to log: ")
        message_queue.put(message)
        print(f'\nTime: {now}, logged message \n{message}')

def main():
    # help(ljm.constants)
    now = datetime.now()
    now = datetime.strftime(now, '%Y_%m_%d_%H_%M_%S')

    st = Path.home() / 'Documents' / 'datalogging'
    st = st / now

    print(f'Saving to {st}')
    st = st.with_suffix('.csv')

    message_queue = queue.Queue()
    input_thread_instance = threading.Thread(target=input_thread, args=(message_queue,))
    input_thread_instance.daemon = True
    input_thread_instance.start()

    read_and_log_thermocouples(thermocouple_channels=[0, 2], 
                               flow_channels=[3],
                               seconds_between_readings=1, 
                               save_to=st, print_output_flag=False, 
                               message_queue=message_queue, 
                               exclude_channels_from_plot=[3])
    
    # COMMENTED OUT FOR LINUX CPU
    # target_dir = Path().home() /'OneDrive - Yale University' / 'kimlab' / 'vuv' / 'datalogging'

    # copy_to_onedrive(st, target_dir=target_dir)

    return


if __name__ == '__main__':
    main()