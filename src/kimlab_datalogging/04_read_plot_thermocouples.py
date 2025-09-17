"""
Demonstrates thermocouple configuration and measurement using the thermocouple
AIN_EF (T7/T8 only).

Relevant Documentation:

Thermocouple App-Note:
    https://labjack.com/support/app-notes/thermocouples

LJM Library:
    LJM Library Installer:
        https://labjack.com/support/software/installers/ljm
    LJM Users Guide:
        https://labjack.com/support/software/api/ljm
    Opening and Closing:
        https://labjack.com/support/software/api/ljm/function-reference/opening-and-closing
    Single Value Functions (such as eWriteName and eReadName):
        https://labjack.com/support/software/api/ljm/function-reference/single-value-functions
    Multiple Value Functions (such as eReadNames):
        https://labjack.com/support/software/api/ljm/function-reference/multiple-value-functions
    Timing Functions (such as StartInterval, WaitForNextInterval and
    CleanInterval):
        https://labjack.com/support/software/api/ljm/function-reference/timing-functions

T-Series and I/O:
    Modbus Map:
        https://labjack.com/support/software/api/modbus/modbus-map
    Analog Inputs:
        https://labjack.com/support/datasheets/t-series/ain
    Thermocouple AIN_EF (T7/T8 only):
        https://labjack.com/support/datasheets/t-series/ain/extended-features/thermocouple
"""
import sys
from labjack import ljm
from datetime import datetime
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation

def get_labjack_handle(arg1='ANY', arg2='ANY', arg3='ANY'):
    handle = ljm.openS("ANY", "ANY", "ANY")
    info = ljm.getHandleInfo(handle)
    print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
          "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
          (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
    device_type = info[0]
    return handle, device_type

def create_analog_channel(channel):
    return "AIN{}".format(channel)

def set_tc_index(tc_type: str) -> int:
    tc_type = tc_type.lower()
    ef_indices = {
        'e': 20,
        'j': 21,
        'k': 22,
        'r': 23,
        't': 24,
        's': 25,
        'n': 27,
        'b': 28,
        'c': 30
    }
    return ef_indices[tc_type]

def get_temp_unit_index(T_unit_name='K'):
    T_unit_name = T_unit_name.lower()
    temp_unit_index = {'k': 0, 'c': 1, 'f': 2}
    return temp_unit_index[T_unit_name]

def get_channel_value_register(handle, device_type, channel_name):
    if device_type == ljm.constants.dtT7:
        neg_channel_value = ljm.constants.GND
        neg_channel_register = "%s_NEGATIVE_CH" % channel_name
        ljm.eWriteName(handle, neg_channel_register, neg_channel_value)
    elif device_type == ljm.constants.dtT4:
        print("\nThe T4 does not support the thermocouple AIN_EF. See our InAmp thermocouple example.")
        exit(0)
    return neg_channel_value, neg_channel_register

def get_cjc_address(device_type, channel):
    if device_type == ljm.constants.dtT8:
        cjc_address = 600 + 2 * channel
    else:
        cjc_address = 60052
    return cjc_address

def set_cjc_slope_offset(tc_type):
    if tc_type.lower() == 'k':
        cjc_slope, cjc_offset = 1.0, 0.0
        return cjc_slope, cjc_offset
    else:
        print('Since thermocouple is not type K, I don\'t know what cjc slope and offset to set')
        return

def set_resolution_index_registers(handle, channel_names, channels):
    for channel_name, channel in zip(channel_names, channels):
        resolution_index_register = "{}_RESOLUTION_INDEX".format(channel_name)
        ljm.eWriteName(handle, resolution_index_register, channel)
    return

def configure_ain_ef_registers(handle, channel_names, tc_index, temp_unit_index, cjc_addresses, cjc_slope, cjc_offset):
    aNames = []
    aValues = []
    for channel_name, cjc_address in zip(channel_names, cjc_addresses):
        indexRegister = "%s_EF_INDEX" % channel_name
        aNames.append(indexRegister)
        aValues.append(tc_index)

        configA = "%s_EF_CONFIG_A" % channel_name
        aNames.append(configA)
        aValues.append(temp_unit_index)

        configB = "%s_EF_CONFIG_B" % channel_name
        aNames.append(configB)
        aValues.append(cjc_address)

        configD = "%s_EF_CONFIG_D" % channel_name
        aNames.append(configD)
        aValues.append(cjc_slope)

        configE = "%s_EF_CONFIG_E" % channel_name
        aNames.append(configE)
        aValues.append(cjc_offset)

        ljm.eWriteNames(handle, len(aNames), aNames, aValues)
    return

def get_read_ABC(channel_name):
    readA = "%s_EF_READ_A" % channel_name
    readB = "%s_EF_READ_B" % channel_name
    readC = "%s_EF_READ_C" % channel_name
    abcs = [readA, readB, readC]

    labels = ['T_thermocouple', 'V_thermocouple', 'T_cold_junction']
    labels = [i + '_{}'.format(channel_name) for i in labels]
    return abcs, labels

def set_time_interval_between_readings(interval_handle, seconds_between_readings):
    microseconds_between_readings = int(seconds_between_readings*10**6)
    ljm.startInterval(interval_handle, microseconds_between_readings)
    return

def read_and_log_thermocouples(
        channels=[0],
        tc_type: str = 'k',
        temp_unit: str = 'C',
        seconds_between_readings: float = 1.0,
        print_output_flag: bool = True,
        save_to: bool | Path = False
        ):
    
    handle, device_type = get_labjack_handle()
    tc_index = set_tc_index(tc_type)
    cjc_slope, cjc_offset = set_cjc_slope_offset(tc_type)

    temp_unit_index = get_temp_unit_index(temp_unit)

    channel_names = [create_analog_channel(channel) for channel in channels]

    neg_channel_values = []
    neg_channel_registers = []
    for channel_name in channel_names:
        ncv, ncr = get_channel_value_register(handle, device_type, channel_name)
        neg_channel_values.append(ncv)
        neg_channel_registers.append(ncr)
    
    cjc_addresses = []
    for channel in channels:
        cjc_addresses.append(get_cjc_address(device_type, channel))

    set_resolution_index_registers(handle, channel_names, channels)
    configure_ain_ef_registers(handle, channel_names, tc_index, temp_unit_index, cjc_addresses, cjc_slope, cjc_offset)
    interval_handle = 1
    set_time_interval_between_readings(interval_handle, seconds_between_readings)

    abcs, labels = [], []
    for channel_name in channel_names:
        abc, label = get_read_ABC(channel_name)
        abcs.append(abc)
        labels.append(label)
        
    abcs_flattened = [i for row in abcs for i in row]
    labels_flattened = [i for row in labels for i in row]

    labels_flattened.append('time')
    labels_flattened.append('dt')

    times, thermocouple_temps = [], {cn: [] for cn in channel_names}
    all_data = []
    time_format = "%Y/%m/%d, %H:%M:%S.%f"

    start_time = datetime.now()
    save_time_format = "%Y_%m_%d_%H_%M_%S"
    formatted_start_time = datetime.strftime(start_time, save_time_format)

    fig, ax = plt.subplots()
    plt.title('Thermocouple Temperature Over Time')
    plt.xlabel('Time')
    plt.ylabel(f'Temperature ({temp_unit})')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

    lines = {channel_name: ax.plot([], [], label=f'Thermocouple {channel_name}')[0] for channel_name in channel_names}
    thermocouple_index = [3*i for i in range(len(channels))]

    def animate(i):
        current_time = datetime.now()
        formatted_time = datetime.strftime(current_time, time_format)
        dt = (current_time - start_time).total_seconds()
        
        data_in = ljm.eReadNames(handle, len(abcs_flattened), abcs_flattened)

        temperatures = [data_in[i] for i in thermocouple_index]
        
        data_entry = data_in + [formatted_time, dt]
        all_data.append(data_entry)
        
        times.append(mdates.date2num(current_time))

        for j, temp in enumerate(temperatures):
            thermocouple_temps[channel_names[j]].append(temp)

        for channel_name in channel_names:
            lines[channel_name].set_data(times, thermocouple_temps[channel_name])

        ax.relim()
        ax.autoscale_view()
        plt.legend()

        if print_output_flag:
            print(data_entry)

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

def main():
    now = datetime.now()
    now = datetime.strftime(now, '%Y_%m_%d_%H_%M_%S')

    st = Path(__file__).parent / 'liveplotting_data' / now
    st = st.with_suffix('.csv')
    read_and_log_thermocouples([0, 2], seconds_between_readings=1, save_to=st, print_output_flag=False)
    
    return

if __name__ == '__main__':
    main()