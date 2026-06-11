/from labjack import ljm
from time import sleep
import math

# Open the LabJack T7
handle = ljm.openS("T7", "ANY", "ANY")

# --- Configuration for Thermocouple 1: AIN0 (differential, AIN0+ / AIN1-) ---
# --- Configuration for Thermocouple 2: AIN2 (differential, AIN2+ / AIN3-) ---

# Set up AIN0 in differential mode (negative channel = AIN1 = channel 1)
ljm.eWriteName(handle, "AIN0_NEGATIVE_CH", 1)       # AIN1 as negative channel
ljm.eWriteName(handle, "AIN0_RANGE", 0.1)            # ±0.1V range for thermocouple signals
ljm.eWriteName(handle, "AIN0_RESOLUTION_INDEX", 4)   # Higher resolution (1-12, higher = slower but more accurate)
ljm.eWriteName(handle, "AIN0_SETTLING_US", 0)        # Default settling time

# Set up AIN2 in differential mode (negative channel = AIN3 = channel 3)
ljm.eWriteName(handle, "AIN2_NEGATIVE_CH", 3)        # AIN3 as negative channel
ljm.eWriteName(handle, "AIN2_RANGE", 0.1)            # ±0.1V range for thermocouple signals
ljm.eWriteName(handle, "AIN2_RESOLUTION_INDEX", 4)
ljm.eWriteName(handle, "AIN2_SETTLING_US", 0)

def mv_to_celsius_k_type(mv):
    """
    Simple K-type thermocouple approximation using the Seebeck coefficient.
    For more accuracy, use a full NIST polynomial or a dedicated library.
    K-type Seebeck coefficient ~41 µV/°C
 """
    seebeck_uv_per_c = 41.0  # µV per °C (approximate)
    voltage_uv = mv * 1000.0
    return voltage_uv / seebeck_uv_per_c

def read_thermocouples(handle):
    """Read both thermocouples and return temperatures in Celsius."""
    
    # Read the cold junction temperature (internal T7 temperature sensor)
    cold_junction_c = ljm.eReadName(handle, "TEMPERATURE_DEVICE_K") - 273.15

    # Read differential voltages (in Volts)
    voltage_ch0 = ljm.eReadName(handle, "AIN0")  # Thermocouple 1
    voltage_ch2 = ljm.eReadName(handle, "AIN2")  # Thermocouple 2

    # Convert to millivolts
    mv_ch0 = voltage_ch0 * 1000.0
    mv_ch2 = voltage_ch2 * 1000.0

    # Convert millivolt reading to temperature delta, then add cold junction
    temp_ch0 = mv_to_celsius_k_type(mv_ch0) + cold_junction_c
    temp_ch2 = mv_to_celsius_k_type(mv_ch2) + cold_junction_c

    return temp_ch0, temp_ch2, cold_junction_c

# --- Main loop ---
try:
    print("Reading K-type thermocouples in differential mode...")
    print(f"{'TC1 (°C)':<15} {'TC2 (°C)':<15} {'Cold Junction (°C)'}")
    print("-" * 50)

    for _ in range(10):  # Read 10 times; replace with a while loop for continuous reading
        tc1, tc2, cj = read_thermocouples(handle)
        print(f"{tc1:<15.2f} {tc2:<15.2f} {cj:.2f}")
        ljm.eReadName(handle, "AIN0")  # Small delay via read
        sleep(1)

finally:
    ljm.close(handle)
    print("Device closed.")