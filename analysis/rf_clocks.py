# -*- coding: utf-8 -*-
"""
Created on Thu May 16 08:19:32 2019

@author: cdf1
"""
# %% Imports ==================================================================
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib import gridspec

from Drivers.Database import MongoDB

from analysis import helper_functions as hf

import datetime

# %% Start/Stop Time
#--- Start
#start_time = None
start_time = datetime.datetime(2018, 5, 1)
#start_time = datetime.datetime.utcnow() - datetime.timedelta(days=3)

#--- Stop
stop_time = None
#stop_time = datetime.datetime(2019, 5, 1)
#stop_time = datetime.datetime.utcnow()


# %% Database Paths ===========================================================
db_paths = [
    # rf_oscillators ----------------------------------------------------------
    # Data
    'rf_oscillators/100MHz_phase_lock',
    'rf_oscillators/1GHz_phase_lock',
    'rf_oscillators/Rb_OCXO_control',
    'rf_oscillators/Rb_detected_signals',
    'rf_oscillators/Rb_frequency_offset',
    'rf_oscillators/Rb_magnetic_read',
    'rf_oscillators/Rb_status',
    'rf_oscillators/Rb_time_tag',
    # Devices
    'rf_oscillators/device_Rb_clock',
    # States
    'rf_oscillators/state_PLOs',
    'rf_oscillators/state_Rb_clock',
    'rf_oscillators/control',
    ]
# More rf_oscillators
for idx in range(20):
    db_paths.append('rf_oscillators/Rb_adc_{:}'.format(idx))
for idx in range(8):
    db_paths.append('rf_oscillators/Rb_dac_{:}'.format(idx))
"""
DAC----------------------------------------------------------------------------
Port    Function
0       Controls the amplitude of the RF to multiplier in resonance cell
1       Controls the analog portion (0 to 99 ns) of the delay for the 1pps output
2       Controls the drain voltage for the discharge lamp’s FET oscillator
3       Controls the temperature of the discharge lamp
4       Controls the temperature of the 10 MHz SC-cut crystal
5       Controls the temperature of the resonance cell
6       Controls the amplitude of the 10 MHz oscillator
7       Controls the peak deviation for the RF phase modulation

12-bit ADC ports --------------------------------------------------------------
Port    Returned voltage
0       Spare (J204)
1       +24V(heater supply) divided by 10.
2       +24V(electronics supply) divided by 10
3       Drain voltage to lamp FET divided by 10
4       Gate voltage to lamp FET divided by 10
5       Crystal heater control voltage
6       Resonance cell heater control voltage
7       Discharge lamp heater control voltage
8       Amplified ac photosignal
9       Photocell’s I/V converter voltage divided by 4
10      Case temperature (10 mV/°C)
11      Crystal thermistors
12      Cell thermistors
13      Lamp thermistors
14      Frequency calibration pot / external calibration voltage
15      Analog ground

8-bit microcontroller’s ADC ports ---------------------------------------------
Port    Returned voltage
16      Varactor voltage for 22.48 MHz VCXO (inside RF synthesizer) / 4
17      Varactor voltage for 360 MHz VCO (output of RF synthesizer) / 4
18      Gain control voltage for amplifier which drives frequency multiplier / 4
19      RF synthesizer’s lock indicator voltage (nominally 4.8 V when locked)
"""


# %% PLO - Phase Locks ========================================================
data = [[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_100MHz = MongoDB.DatabaseRead(mongo_client,
        'rf_oscillators/100MHz_phase_lock')
    db_1GHz = MongoDB.DatabaseRead(mongo_client,
        'rf_oscillators/1GHz_phase_lock')
    cursor = db_100MHz.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['bit'],
             doc['flips']])
    cursor = db_1GHz.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['bit'],
             doc['flips'],
             ])
finally:
    mongo_client.close()

n = []
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    n.append(len(data[idx][0]))

# Plot
fig_0 = plt.figure("PLO - Phase Locks")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

ax0.plot(data[0][0], data[0][1], '.-', markersize=1, label='lock', drawstyle='steps-post')
ax0.plot(data[0][0], data[0][2], '.', markersize=1, label='flips')
ax1.plot(data[1][0], data[1][1], '.-', markersize=1, label='lock', drawstyle='steps-post')
ax1.plot(data[1][0], data[1][2], '.', markersize=1, label='flips')

ax0.set_title("100MHz PLO")
ax0.legend()
ax0.set_yticks([-1, 0, 1])
ax0.autoscale(axis='x', tight=True)

ax1.set_title("1GHz PLO")
ax1.legend()
ax1.set_yticks([-1, 0, 1])

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% Rb Clock - Rb Frequency Control ==========================================
data = [[],[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_frq_offset = MongoDB.DatabaseRead(mongo_client,
        'rf_oscillators/Rb_frequency_offset')
    db_mag_rd = MongoDB.DatabaseRead(mongo_client,
        'rf_oscillators/Rb_magnetic_read')
    db_gps_tt = MongoDB.DatabaseRead(mongo_client,
        'rf_oscillators/Rb_time_tag')
    cursor = db_frq_offset.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['1e-12'],
             ])
    cursor = db_mag_rd.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['DAC'],
             ])
    cursor = db_gps_tt.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['ns'],
             ])
finally:
    mongo_client.close()

n = []
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    n.append(len(data[idx][0]))

# Plot
fig_0 = plt.figure("Rb Clock - Rb Frequency Control")
fig_0.set_size_inches([6.4 , 4.78*1.25], forward=True)
plt.clf()
ax0 = plt.subplot2grid((3,1),(0,0))
ax1 = plt.subplot2grid((3,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((3,1),(2,0), sharex=ax0)

ax0.plot(data[2][0], data[2][1]*1e-9, '.', markersize=1)
ax1.plot(data[0][0], 10e6*data[0][1]*1e-12, '.', markersize=1)
ax2.plot(data[1][0], data[1][1], '.', markersize=1)

ax0.set_title("GPS Time Tag")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('s'))
ax0.autoscale(axis='x', tight=True)
ax0.grid(True, alpha=.25)

ax1.set_title("Frequency Offset")
ax1.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax1.grid(True, alpha=.25)

ax2.set_title("Magnetic Control")
ax2.set_ylabel('DAC (arb. units)')
ax2.grid(True, alpha=.25)

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% Rb Clock - OCXO to Rb FLL ================================================
data = [[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_det_sgn = MongoDB.DatabaseRead(mongo_client,
        'rf_oscillators/Rb_detected_signals')
    db_OCXO_ctrl = MongoDB.DatabaseRead(mongo_client,
        'rf_oscillators/Rb_OCXO_control')
    cursor = db_det_sgn.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['mod'],
             doc['2mod'],
             ])
    cursor = db_OCXO_ctrl.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['high'],
             doc['low']])
finally:
    mongo_client.close()

n = []
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    n.append(len(data[idx][0]))

# Plot
fig_0 = plt.figure("Rb Clock - OCXO to Rb FLL")
fig_0.set_size_inches([6.4 , 4.78*1.25], forward=True)
plt.clf()
ax0 = plt.subplot2grid((3,1),(0,0))
ax1 = plt.subplot2grid((3,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((3,1),(2,0), sharex=ax0)

ax0.plot(data[0][0], data[0][1], '.', markersize=1)
ax1.plot(data[1][0], data[1][1], '.', markersize=1, label='MSBs')
ax1.plot(data[1][0], data[1][2], '.', markersize=1, label='LSBs')
ax2.plot(data[0][0], data[0][2], '.', markersize=1)

ax0.set_title(r"Frequency Error Signal")
ax0.set_ylabel('(arb. units)')
ax0.autoscale(axis='x', tight=True)
ax0.grid(True, alpha=.25)

ax1.set_title(r"OCXO Control")
ax1.set_ylabel('(arb. units)')
ax1.grid(True, alpha=.25)

ax2.set_title(r"RMS Amplitude at 2$\omega$")
ax2.set_ylabel('(arb. units)')
ax2.grid(True, alpha=.25)

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% Rb Clock - Misc. ADCs and DACs ===========================================
"""
DAC----------------------------------------------------------------------------
Port    Function
0       Controls the amplitude of the RF to multiplier in resonance cell
1       Controls the analog portion (0 to 99 ns) of the delay for the 1pps output
2       Controls the drain voltage for the discharge lamp’s FET oscillator
3       Controls the temperature of the discharge lamp
4       Controls the temperature of the 10 MHz SC-cut crystal
5       Controls the temperature of the resonance cell
6       Controls the amplitude of the 10 MHz oscillator
7       Controls the peak deviation for the RF phase modulation

12-bit ADC ports --------------------------------------------------------------
Port    Returned voltage
0       Spare (J204)
1       +24V(heater supply) divided by 10.
2       +24V(electronics supply) divided by 10
3       Drain voltage to lamp FET divided by 10
4       Gate voltage to lamp FET divided by 10
5       Crystal heater control voltage
6       Resonance cell heater control voltage
7       Discharge lamp heater control voltage
8       Amplified ac photosignal
9       Photocell’s I/V converter voltage divided by 4
10      Case temperature (10 mV/°C)
11      Crystal thermistors
12      Cell thermistors
13      Lamp thermistors
14      Frequency calibration pot / external calibration voltage
15      Analog ground

8-bit microcontroller’s ADC ports ---------------------------------------------
Port    Returned voltage
16      Varactor voltage for 22.48 MHz VCXO (inside RF synthesizer) / 4
17      Varactor voltage for 360 MHz VCO (output of RF synthesizer) / 4
18      Gain control voltage for amplifier which drives frequency multiplier / 4
19      RF synthesizer’s lock indicator voltage (nominally 4.8 V when locked)
"""
data_adc = []
db_adc = []
data_dac = []
db_dac = []
try:
    mongo_client = MongoDB.MongoClient()
    for idx in range(20):
        db_adc.append(MongoDB.DatabaseRead(mongo_client,
            'rf_oscillators/Rb_adc_{:}'.format(idx)))
        cursor = db_adc[idx].read_record(start=start_time, stop=stop_time)
        data_adc.append([])
        for doc in cursor:
            data_adc[idx].append(
                [doc['_timestamp'],
                 doc['V'],
                 ])
    for idx in range(8):
        db_dac.append(MongoDB.DatabaseRead(mongo_client,
            'rf_oscillators/Rb_dac_{:}'.format(idx)))
        cursor = db_dac[idx].read_record(start=start_time, stop=stop_time)
        data_dac.append([])
        for doc in cursor:
            data_dac[idx].append(
                [doc['_timestamp'],
                 doc['DAC'],
                 ])
finally:
    mongo_client.close()

n_adc = []
for idx in range(len(data_adc)):
    data_adc[idx] = list(zip(*data_adc[idx]))
    for idx2 in range(len(data_adc[idx])):
        data_adc[idx][idx2] = np.array(data_adc[idx][idx2])
    n_adc.append(len(data_adc[idx][0]))
n_dac = []
for idx in range(len(data_dac)):
    data_dac[idx] = list(zip(*data_dac[idx]))
    for idx2 in range(len(data_dac[idx])):
        data_dac[idx][idx2] = np.array(data_dac[idx][idx2])
    n_dac.append(len(data_dac[idx][0]))

# Plot Temperature Control
fig_0 = plt.figure("Rb Clock - Temperature Control")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

ax1_c = ax1.twinx()

ax0.plot(data_adc[11][0], data_adc[11][1]/10e-3, '.', markersize=1, label='Crystal')
ax0.plot(data_adc[12][0], data_adc[12][1]/10e-3, '.', markersize=1, label='Cell')
ax0.plot(data_adc[13][0], data_adc[13][1]/10e-3, '.', markersize=1, label='Lamp')
ax0.plot(data_adc[10][0], data_adc[10][1]/10e-3, '.', markersize=1, label='Case')

ax1.plot(data_dac[4][0], data_dac[4][1], '--', markersize=1, label='Crystal')
ax1.plot(data_dac[5][0], data_dac[5][1], '--', markersize=1, label='Cell')
ax1.plot(data_dac[3][0], data_dac[3][1], '--', markersize=1, label='Lamp')

ax1_c.plot(data_adc[5][0], data_adc[5][1], '.', markersize=1, label='Crystal')
ax1_c.plot(data_adc[6][0], data_adc[6][1], '.', markersize=1, label='Cell')
ax1_c.plot(data_adc[7][0], data_adc[7][1], '.', markersize=1, label='Lamp')

ax0.set_title(r"Temperature Reading")
ax0.set_ylabel('Temperature')
ax0.yaxis.set_major_formatter(ticker.EngFormatter('C'))
ax0.legend(markerscale=10)
ax0.autoscale(axis='x', tight=True)

ax0.grid(True, alpha=0.25)
ax1.set_title(r"Heater Control")
ax1.set_ylabel('Setpoint (arb. units)')
ax1.legend(loc=6, title='Setpoint')

ax1_c.set_ylabel('Actual (arb. units)')
ax1_c.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax1_c.legend(loc=7, title='Actual', markerscale=10)
ax1.grid(True, alpha=0.25)

fig_0.autofmt_xdate()
fig_0.tight_layout()

# Plot Frequency Control
fig_0 = plt.figure("Rb Clock - Frequency Control")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

ax0.plot(data_adc[16][0], data_adc[16][1], '.', markersize=1, label='Varactor 22.5MHz')
ax0.plot(data_adc[17][0], data_adc[17][1], '.', markersize=1, label='Varactor 360MHz')
ax0.plot(data_adc[19][0], data_adc[19][1], '.', markersize=1, label='Lock Indicator')
ax0.plot(data_adc[14][0], data_adc[14][1], '.', markersize=1, label='Freq. Calibration')

ax1.plot(data_dac[7][0], data_dac[7][1], '.', markersize=1, label='Peak RF Deviation')
ax1.plot(data_dac[1][0], data_dac[1][1], '.', markersize=1, label='1pps Output Delay')

ax0.set_title(r"Misc. ADC")
ax0.legend(markerscale=10)
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.autoscale(axis='x', tight=True)
ax0.grid(True, alpha=0.25)

ax1.set_title(r"Misc. DAC")
ax1.set_ylabel('(arb. units)')
ax1.legend(markerscale=10)
ax1.grid(True, alpha=0.25)

fig_0.autofmt_xdate()
fig_0.tight_layout()

# Plot Lamp Control
fig_0 = plt.figure("Rb Clock - Lamp Control")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)
ax1_c = ax1.twinx()

ax0.plot(data_adc[8][0], data_adc[8][1], '.', markersize=1, label='AC Photosignal')
ax0.plot(data_adc[9][0], data_adc[9][1], '.', markersize=1, label='I to V Converter')

ax1.plot(data_dac[2][0], data_dac[2][1], '--', markersize=1, label='Drain V Control')
ax1_c.plot(data_adc[3][0], data_adc[3][1]*10, '.', markersize=1, label='Drain Voltage')
ax1_c.plot(data_adc[4][0], data_adc[4][1]*10, '.', markersize=1, label='Gate Voltage')

ax0.set_title(r"Photosignal")
ax0.legend(markerscale=10)
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.autoscale(axis='x', tight=True)
ax0.grid(True, alpha=0.25)

ax1.set_title(r"Lamp Current Control")
ax1.set_ylabel('(arb. units)')
ax1.legend(loc=6, markerscale=10)
ax1_c.legend(loc=7, markerscale=10)
ax1_c.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax1.grid(True, alpha=0.25)

fig_0.autofmt_xdate()
fig_0.tight_layout()

# Plot Power
fig_0 = plt.figure("Rb Clock - Power")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)
ax1_c = ax1.twinx()

ax0.plot(data_adc[0][0], data_adc[0][1], '.', markersize=1, label='Spare')
ax0.plot(data_adc[1][0], data_adc[1][1]*10, '.', markersize=1, label='Heater Supply')
ax0.plot(data_adc[2][0], data_adc[2][1]*10, '.', markersize=1, label='Electrical Supply')
ax0.plot(data_adc[15][0], data_adc[15][1], '.', markersize=1, label='Ground')

ax1.plot(data_dac[0][0], data_dac[0][1], '.', markersize=1, label='RF Mult. Ampl.')
ax1.plot(data_dac[6][0], data_dac[6][1], '.', markersize=1, label='10MHz Ampl.')
ax1_c.plot(data_adc[18][0][0], np.nan)
ax1_c.plot(data_adc[18][0][0], np.nan)
ax1_c.plot(data_adc[18][0], data_adc[18][1], '.', markersize=1, label='Freq. Mult. Gain')

ax0.set_title(r"Electrical Power")
ax0.legend(markerscale=10)
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.autoscale(axis='x', tight=True)
ax0.grid(True, alpha=0.25)

ax1.set_title(r"RF Power")
ax1.set_ylabel('(arb. units)')
ax1.legend(loc=6, markerscale=10)
ax1_c.legend(loc=7, markerscale=10)
ax1_c.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax1.grid(True, alpha=0.25)

fig_0.autofmt_xdate()
fig_0.tight_layout()