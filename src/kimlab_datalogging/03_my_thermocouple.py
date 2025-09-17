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

def get_labjack_handle(arg1='ANY', arg2='ANY', arg3='ANY'):
    # Open first found LabJack
    handle = ljm.openS("ANY", "ANY", "ANY")  # Any device, Any connection, Any identifier
    #handle = ljm.openS("T8", "ANY", "ANY")  # T8 device, Any connection, Any identifier
    #handle = ljm.openS("T7", "ANY", "ANY")  # T7 device, Any connection, Any identifier
    #handle = ljm.open(ljm.constants.dtANY, ljm.constants.ctANY, "ANY")  # Any device, Any connection, Any identifier

    info = ljm.getHandleInfo(handle)
    print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
          "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
          (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
    device_type = info[0]
    return handle, device_type

def create_analog_channel(channel):
    return "AIN{}".format(channel)

def set_tc_index(tc_type:str) -> int:
    # Thermocouple AIN_EF indices:
    # 20=type E
    # 21=type J
    # 22=type K
    # 23=type R
    # 24=type T
    # 25=type S
    # 27=type N
    # 28=type B
    # 30=type C
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
    # # Temperature reading units (0=K, 1=C, 2=F)

    T_unit_name = T_unit_name.lower()
    temp_unit_index = {'k':0, 'c':1, 'f':2}
    return temp_unit_index[T_unit_name]

def get_channel_value_register(handle, device_type, channel_name):
    # Set up any negative channel configurations required. The T8 inputs are
    # isolated and therefore do not require any negative channel configuration.
    if device_type == ljm.constants.dtT7:
        # There are only certain valid differential channel pairs. For AIN0-13
        # the valid pairs are an even numbered AIN and next odd AIN. For
        # example, AIN0-AIN1, AIN2-AIN3. To take a differential reading between
        # AIN0 and AIN1, set AIN0_NEGATIVE_CH to 1.

        # Set up a single ended measurement
        neg_channel_value = ljm.constants.GND
        neg_channel_register = "%s_NEGATIVE_CH" % channel_name
        ljm.eWriteName(handle, neg_channel_register, neg_channel_value)
    elif device_type == ljm.constants.dtT4:
        print("\nThe T4 does not support the thermocouple AIN_EF. See our InAmp thermocouple example.")
        exit(0)
    return neg_channel_value, neg_channel_register

def get_cjc_address(device_type, channel):
    # The CJC configurations should be set up such that:
    # tempK = reading * cjc_slope + cjc_offset
    # Where 'tempK' is the CJC reading in Kelvin and 'reading' is the value
    # read from the register at cjc_address.
    if device_type == ljm.constants.dtT8:
        # Use TEMPERATURE# for the T8 for CJC. Since the thermocouple is
        # connected to AIN0, we are using TEMPERATURE0 for the CJC.
        cjc_address = 600 + 2*channel
    else:
        # Use TEMPERATURE_DEVICE_K for the T7 for CJC
        cjc_address = 60052
    return cjc_address

def set_cjc_slope_offset(tc_type):
    # CJC slope when using TEMPERATURE_DEVICE_K
    # cjc_slope = 1.0
    # CJC offset when using TEMPERATURE_DEVICE_K
    # cjc_offset = 0.0

    if tc_type.lower() == 'k':
        cjc_slope, cjc_offset = 1.0, 0.0
        return cjc_slope, cjc_offset
    else:
        print('Since thermocouple is not type K, I don\'t know what cjc slope and offset to set')
        return

def set_resolution_index_registers(handle, channel_names, channels):
    # Set the resolution index to the default setting.
    # Default setting has different meanings depending on the device.
    # See Labjack's AIN documentation (linked above) for more information.
    for channel_name, channel in zip(channel_names, channels):
        resolution_index_register = "{}_RESOLUTION_INDEX".format(channel_name)
        ljm.eWriteName(handle, resolution_index_register, channel)
    return

def configure_ain_ef_registers(handle, channel_names, tc_index, temp_unit_index, cjc_addresses, cjc_slope, cjc_offset):
    # Configure all of the necessary thermocouple AIN_EF registers
    aNames = []
    aValues = []
    for channel_name, cjc_address in zip(channel_names, cjc_addresses):
        # For setting up the AIN#_EF_INDEX (thermocouple type)
        indexRegister = "%s_EF_INDEX" % channel_name
        aNames.append(indexRegister)
        aValues.append(tc_index)

        # For setting up the AIN#_EF_CONFIG_A (temperature units)
        configA = "%s_EF_CONFIG_A" % channel_name
        aNames.append(configA)
        aValues.append(temp_unit_index)

        # For setting up the AIN#_EF_CONFIG_B (CJC address)
        configB = "%s_EF_CONFIG_B" % channel_name
        aNames.append(configB)
        aValues.append(cjc_address)

        # For setting up the AIN#_EF_CONFIG_D (CJC slope)
        configD = "%s_EF_CONFIG_D" % channel_name
        aNames.append(configD)
        aValues.append(cjc_slope)

        # For setting up the AIN#_EF_CONFIG_E (CJC offset)
        configE = "%s_EF_CONFIG_E" % channel_name
        aNames.append(configE)
        aValues.append(cjc_offset)

        # Write all of the AIN_EF settings
        ljm.eWriteNames(handle, len(aNames), aNames, aValues)
    return

def get_read_ABC(channel_name):
    # AIN#_EF_READ_A returns the thermocouple temperature reading
    readA = "%s_EF_READ_A" % channel_name

    # AIN#_EF_READ_B returns the thermocouple voltage reading
    readB = "%s_EF_READ_B" % channel_name

    # AIN#_EF_READ_C returns the thermocouple CJC temperature reading
    readC = "%s_EF_READ_C" % channel_name
    abcs = [readA, readB, readC]

    labels = ['T_thermocouple', 'V_thermocouple', 'T_cold_junction']
    labels = [i + '_{}'.format(channel_name) for i in labels]
    return abcs, labels

def set_time_interval_between_readings(interval_handle, seconds_between_readings):
        # Delay between readings (in microseconds)
    microseconds_between_readings = int(seconds_between_readings*10**6)
    ljm.startInterval(interval_handle, microseconds_between_readings)
    return



def read_and_log_thermocouple(channels=[0], 
                              tc_type: str = 'k', temp_unit: str = 'C', 
                              num_iterations: int = 10, 
                              seconds_between_readings: float = 1.0, 
                              print_output_flag: bool = True,
                              save_to: bool | Path = False):
    """ 
    Reads the temperature of a single thermocouple num_iteration times. Save to file save_to.
    Confirmed to work with a thermocouple in AIN0 and grounded to GND.
    
    Arguments:
    channel, list of ints
    The AIN numbers of where your thermocouple is attached to the labjack.

    tc_type: str, default 'k'
    The type of your thermocouple. # as of 2025/08/08, only K type thermocouples are implemented

    temp_unit: str, default 'C'
    The unit you wish to use. Possible units are 'C', 'K', or 'F'.
    
    num_iterations: int, default 10
    Number of readings

    seconds_between_readings: float, default 1.0
    Number of seconds to wait between readings.

    save_to: bool | Path, default False
    If False, no file is saved.
    If a Path to a directory is passed (including a non-existing directory), the file is saved to that directory with a filename that is the starting
    time of measurement.
    If a Path to a file is passed, the file is saved to that location.

    """
    handle, device_type = get_labjack_handle() # only done once, on startup
    tc_index = set_tc_index(tc_type) # currently, all thermocouples must be of same type, so this is only done once.
    cjc_slope, cjc_offset = set_cjc_slope_offset(tc_type)

    temp_unit_index = get_temp_unit_index(temp_unit)

    # Take a measurement of a thermocouple connected to AIN0
    # channel_name = create_analog_channel(channel)
    channel_names = [create_analog_channel(channel) for channel in channels]


    # neg_channel_value, neg_channel_register = get_channel_value_register(handle, device_type, channel_name)

    neg_channel_values = []
    neg_channel_registers = []
    for channel_name in channel_names:
        ncv, ncr = get_channel_value_register(handle, device_type, channel_name)
        neg_channel_values.append(ncv)
        neg_channel_registers.append(ncr)
    
    cjc_addresses = []
    # cjc_address = get_cjc_address(device_type, channel)
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

    abcs_flattened, labels_flattened = [], [] # To-do: rewrite with list comprehension.
    for row in abcs:
        for i in row:
            abcs_flattened.append(i)
    for row in labels:
        for i in row:
            labels_flattened.append(i)
    labels_flattened.append('time')
    labels_flattened.append('dt')
    print('abcs flattened',abcs_flattened)
    print("\nReading thermocouples {} temperature {} times...\n".format(channel_names,num_iterations))

    times, delta_times, thermocouple_temps, thermocouple_voltages, cold_junction_temps = [], [], [], [], [] 
    time_format = "%Y/%m/%d, %H:%M:%S.%f"

    start_time = datetime.now()
    save_time_format = "%Y_%m_%d_%H_%M_%S"
    formatted_start_time = datetime.strftime(start_time, save_time_format)


    data = []
    for i in range(num_iterations):
        try:
            current_time = datetime.now()
            formatted_time = datetime.strftime(current_time, time_format)
            times.append(formatted_time)
            dt = current_time - start_time
            dt = dt.total_seconds()
            delta_times.append(dt)


            # Read the thermocouple temperature
            data_in = ljm.eReadNames(handle, len(abcs_flattened), abcs_flattened)
            data_in.append(formatted_time)
            data_in.append(dt)

            data.append(data_in)

            # thermocouple_temps.append(thermocouple_temp)
            # thermocouple_voltages.append(thermocouple_volts)
            # cold_junction_temps.append(cold_junction_temp)

            if print_output_flag:
                print(data_in)
        
            ljm.waitForNextInterval(interval_handle)

        except Exception:
            print(sys.exc_info()[1])
            break

    data = pd.DataFrame(data, columns=labels_flattened)
    print(data)

    data['T unit'] = temp_unit

    if save_to is False:
        pass
    elif save_to.is_dir(): # if only a directory is provided, save it to that directory with the time as the file name.
        save_to.mkdir(exist_ok=True)
        save_to = save_to / formatted_start_time
        save_to = save_to.with_suffix('.csv')
        data.to_csv(save_to)
    else: # if the save to is a file, save to the given filename
        save_to.parent.mkdir(exist_ok=True)
        data.to_csv(save_to, index=False)


  # Close handles
    ljm.cleanInterval(interval_handle)
    ljm.close(handle)
    print("Done!")
    return

def main():
    st = Path(__file__).parent / 'data2.csv'
    read_and_log_thermocouple([0,2], num_iterations=5, seconds_between_readings=1, save_to=st)
    
    return

if __name__ == '__main__':
    main()