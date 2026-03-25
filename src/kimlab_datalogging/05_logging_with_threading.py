import sys
from labjack import ljm
import labjack_utils as lu
from datetime import datetime
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
import threading
import queue
# from iblg_mpl_stylesheet.iblg_mpl_stylsheet import iblg_mpl_style
# plt.style.use(default_stylsheet)


def set_time_interval_between_readings(interval_handle, seconds_between_readings):
    microseconds_between_readings = int(seconds_between_readings*10**6)
    ljm.startInterval(interval_handle, microseconds_between_readings)
    return

def create_axes(temp_unit, flow_unit):
    fig, ax = plt.subplots(nrows=2, sharex=True)
    plt.title('Thermocouple Temperature Over Time')
    ax[1].set_xlabel('Time')
    ax[0].set_ylabel(f'Temperature ({temp_unit})')
    ax[1].set_ylabel(f'Flow rate ({flow_unit})')
    ax[1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    return fig, ax


def read_and_log_thermocouples(
        thermocouple_channels=[0],
        flow_channels=[2],
        tc_type: str = 'k',
        temp_unit: str = 'C',
        flow_unit: str = 'mL/min',
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
        abc, label = lu.get_read_ABC(channel_name)
        abcs.append(abc)
        labels.append(label)
        
    abcs_flattened = [i for row in abcs for i in row]
    labels_flattened = [i for row in labels for i in row]
    labels_flattened.append('time')
    labels_flattened.append('dt')
    labels_flattened.append('message')

    times = []
    thermocouple_temps = {cn: [] for cn in channel_names}
    all_data = []
    time_format = "%Y/%m/%d, %H:%M:%S.%f"

    start_time = datetime.now()
    save_time_format = "%Y_%m_%d_%H_%M_%S"
    formatted_start_time = datetime.strftime(start_time, save_time_format)

    fig, ax = create_axes(temp_unit, flow_unit)
    
    lines = {channel_name: ax[0].plot([], [], '.', label=f'Thermocouple {channel_name}')[0] for channel_name in plot_channel_names}
    thermocouple_index = [3*i for i in range(len(thermocouple_channels))]

    def animate(i):
        current_time = datetime.now()
        formatted_time = datetime.strftime(current_time, time_format)
        dt = (current_time - start_time).total_seconds()
        
        data_in = ljm.eReadNames(handle, len(abcs_flattened), abcs_flattened)
        # print("Data read from LabJack:", data_in)  # Debugging line
        
        temperatures = [data_in[idx] for idx in thermocouple_index]
        # print("Temperatures:", temperatures)  # Debugging line
        
        message = ""
        if message_queue and not message_queue.empty():
            message = message_queue.get()

        data_entry = data_in + [formatted_time, dt, message]
        all_data.append(data_entry)
        
        times.append(mdates.date2num(current_time))

        for j, temp in enumerate(temperatures):
            thermocouple_temps[channel_names[j]].append(temp)
            
        # print("Thermocouple temperatures:", thermocouple_temps)  # Debugging line

        for channel_name in plot_channel_names:
            lines[channel_name].set_data(times, thermocouple_temps[channel_name])

        [axis.relim() for axis in ax]
        [axis.autoscale_view() for axis in ax]
        [axis.legend() for axis in ax]

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

def input_thread(message_queue):
    while True:
        message = input("Enter message to log: ")
        message_queue.put(message)

def main():
    # help(ljm.constants)
    now = datetime.now()
    now = datetime.strftime(now, '%Y_%m_%d_%H_%M_%S')

    st = Path(__file__).parent / 'liveplotting_data' / now
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
                               exclude_channels_from_plot=[])
    

    return

if __name__ == '__main__':
    main()