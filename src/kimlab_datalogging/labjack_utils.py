from labjack import ljm

def get_temp_unit_index(T_unit_name='K'):
    T_unit_name = T_unit_name.lower()
    temp_unit_index = {'k': 0, 'c': 1, 'f': 2}
    return temp_unit_index[T_unit_name]

def get_labjack_handle(arg1='ANY', arg2='ANY', arg3='ANY'):
    handle = ljm.openS("ANY", "ANY", "ANY")
    info = ljm.getHandleInfo(handle)
    print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
          "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
          (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
    device_type = info[0]
    return handle, device_type

def set_resolution_index_registers(handle, channel_names, thermocouple_channels):
    for channel_name, channel in zip(channel_names, thermocouple_channels):
        resolution_index_register = "{}_RESOLUTION_INDEX".format(channel_name)
        ljm.eWriteName(handle, resolution_index_register, channel)
    return


def create_analog_channel(channel: int) -> str:
    return "AIN{}".format(channel)

def set_cjc_slope_offset(tc_type):
    if tc_type.lower() == 'k':
        cjc_slope, cjc_offset = 1.0, 0.0
        return cjc_slope, cjc_offset
    else:
        print('Since thermocouple is not type K, I don\'t know what cjc slope and offset to set')
        return
    
def get_channel_value_register(handle, device_type, channel_name):
    if device_type == ljm.constants.dtT7:
        neg_channel_value = ljm.constants.GND
        neg_channel_register = "%s_NEGATIVE_CH" % channel_name
        ljm.eWriteName(handle, neg_channel_register, neg_channel_value)
    elif device_type == ljm.constants.dtT4:
        print("\nThe T4 does not support the thermocouple AIN_EF. See our InAmp thermocouple example.")
        exit(0)
    return neg_channel_value, neg_channel_register

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

def get_read_ABC(channel_name):
    readA = "%s_EF_READ_A" % channel_name
    readB = "%s_EF_READ_B" % channel_name
    readC = "%s_EF_READ_C" % channel_name
    abcs = [readA, readB, readC]

    labels = ['T_thermocouple', 'V_thermocouple', 'T_cold_junction']
    labels = [i + '_{}'.format(channel_name) for i in labels]
    return abcs, labels

def get_cjc_address(device_type, channel):
    if device_type == ljm.constants.dtT8:
        cjc_address = 600 + 2 * channel
    else:
        cjc_address = 60052
    return cjc_address

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