# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:29:37 2019

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
start_time = None
#start_time = datetime.datetime(2018, 5, 1)
#start_time = datetime.datetime.utcnow() - datetime.timedelta(days=10)

#--- Stop
stop_time = None
#stop_time = datetime.datetime(2019, 5, 1)
#stop_time = datetime.datetime.utcnow()


# %% Database Paths ===========================================================
db_paths = [
    #--- comb_generator -------------------------------------------------------
    # Data
    'comb_generator/IM_bias',
    # Devices
    'comb_generator/device_IM_bias',
    'comb_generator/device_PDU_12V',
    # States
    'comb_generator/state_12V_supply',
    'comb_generator/state_IM_bias',
    'comb_generator/control',

    #--- cw_laser -------------------------------------------------------------
    # Data
    'cw_laser/dac_limits',
    'cw_laser/dac_output',
    'cw_laser/freq_err',
    # States
    'cw_laser/state_frequency',

    #--- filter_cavity --------------------------------------------------------
    # Data
    'filter_cavity/DAQ_Vout_vs_reflect',
    'filter_cavity/DAQ_error_signal',
    'filter_cavity/HV_output',
    'filter_cavity/PID_output',
    'filter_cavity/PID_output_limits',
    'filter_cavity/heater_temperature',
    # Devices
    'filter_cavity/device_DAQ_Vout_vs_reflect',
    'filter_cavity/device_HV',
    'filter_cavity/device_PID',
    # States
    'filter_cavity/state',
    'filter_cavity/control',
    ]


# %% EOM Comb - IM Bias =======================================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'comb_generator/IM_bias')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['V']])
finally:
    mongo_client.close()

data = np.array(data).T

# Plot
fig = plt.figure("EOM Comb - IM Bias")
plt.clf()

ax0 = plt.subplot2grid((1,1), (0,0))

ax0.plot(data[0], data[1], '.', markersize=1)
ax0.set_title("IM Bias")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.grid()

fig.autofmt_xdate()
plt.tight_layout()


# %% EOM Comb - fCW PLL =======================================================
data = [[], [], []]
try:
    mongo_client = MongoDB.MongoClient()
    db_fCW_err = MongoDB.DatabaseRead(mongo_client,
                                      'cw_laser/freq_err')
    db_fCW_out = MongoDB.DatabaseRead(mongo_client,
                                      'cw_laser/dac_output')
    db_fCW_lim = MongoDB.DatabaseRead(mongo_client,
                                      'cw_laser/dac_limits')
    cursor = db_fCW_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['Hz'],
             ])
    cursor = db_fCW_out.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['V'],
             ])
    cursor = db_fCW_lim.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['min_V'],
             doc['max_V'],
             ])
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T,
        np.array(data[2]).T,]
n_0 = len(data[0][0])
n_1 = len(data[1][0])
n_1 = len(data[2][0])

# Plot
fig_0 = plt.figure("EOM Comb - fCW PLL")
plt.clf()

gs0 = gridspec.GridSpec(2, 1)
gs00 = gridspec.GridSpecFromSubplotSpec(3, 5, subplot_spec=gs0[0,0], wspace=0, hspace=0)
gs10 = gridspec.GridSpecFromSubplotSpec(1, 5, subplot_spec=gs0[1,0], wspace=0, hspace=0)

ax0 = plt.subplot(gs00[1:2+1,0:-1])
ax1 = plt.subplot(gs00[1:2+1,4:], sharey=ax0)
ax2 = plt.subplot(gs00[0,0:-1], sharex=ax0)

ax3 = plt.subplot(gs10[:,0:-1], sharex=ax0)

# f0
n_f0_avg = int(n_0/100)
f0_y = data[0][1].astype(np.float)
f0_y_order = f0_y.argsort()
f0_y_order_r = f0_y_order.argsort()
f0_y_diff = np.append(0, np.diff(f0_y[f0_y_order]))
f0_y_diff = hf.fftconvolve(f0_y_diff, 1/n_f0_avg*np.array([1]*n_f0_avg), mode="same")
f0_z = 1/f0_y_diff[f0_y_order_r]
f0_z_order = f0_z.argsort()[::1]

ax0.scatter(data[0][0][f0_z_order], data[0][1][f0_z_order], c=f0_z[f0_z_order], edgecolor='', cmap=plt.cm.Blues_r, s=1, vmax=np.nanmax(f0_z), vmin=np.nanmin(f0_z))
ax2.scatter(data[0][0], np.abs(data[0][1]), s=1, c=plt.cm.Blues_r(0), edgecolor='')

ax3.fill_between(data[2][0], data[2][1].astype(np.float), data[2][2].astype(np.float), alpha=.25)
ax3.plot(data[1][0], data[1][1].astype(np.float), '.', markersize=1)

ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax0.autoscale(axis='x', tight=True)
f0_std = np.sqrt(np.median((data[0][1] - np.median(data[0][1]))**2))
ax0.set_ylim([-10*f0_std, 10*f0_std])

ax2.set_title(r"In-Loop f$_{CW}$ Error")
ax2.set_yscale("log")
ax2.yaxis.set_major_locator(ticker.LogLocator())
ax2.yaxis.get_major_locator().set_params(numticks=3)
ax2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2.set_ylim([ax0.get_ylim()[1], ax2.get_ylim()[1]])
ax2.autoscale(axis='x', tight=True)

ax1.hist(data[0][1].astype(np.float), bins=10000, density=True, orientation="horizontal", range=(-1000*f0_std, 1000*f0_std))

for label in ax0.xaxis.get_ticklabels():
    label.set_visible(False)

for label in ax1.xaxis.get_ticklabels():
    label.set_visible(False)
ax1.yaxis.tick_right()
for label in ax1.yaxis.get_ticklabels():
    label.set_visible(False)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)

ax3.set_title(r"f$_{CW}$ Servo Output")
ax3.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax3.autoscale(axis='x', tight=True)
for label in ax3.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

fig_0.tight_layout()


# %% EOM Comb - Flt. Cav. Lock ================================================
data = [[], [], []]
try:
    mongo_client = MongoDB.MongoClient()
    db_err = MongoDB.DatabaseRead(mongo_client,
                                  'filter_cavity/DAQ_error_signal')
    db_out = MongoDB.DatabaseRead(mongo_client,
                                  'filter_cavity/PID_output')
    db_lim = MongoDB.DatabaseRead(mongo_client,
                                  'filter_cavity/PID_output_limits')
    cursor = db_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['V'],
             ])
    cursor = db_out.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['V'],
             ])
    cursor = db_lim.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['min'],
             doc['max'],
             ])
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T,
        np.array(data[2]).T,]
n_0 = len(data[0][0])
n_1 = len(data[1][0])
n_1 = len(data[2][0])

# %lot
fig_0 = plt.figure("EOM Comb - Flt. Cav. Lock")
plt.clf()

ax0 = plt.subplot2grid((2,1), (0,0))
ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

ax0.plot(data[0][0], data[0][1], '.', markersize=1)

ax1.fill_between(data[2][0], data[2][1].astype(np.float), data[2][2].astype(np.float), alpha=.25, step='post')
ax1.plot(data[1][0], data[1][1], '.', markersize=1)

ax0.set_title(r"Filter Cavity Reflection Signal")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.autoscale(axis='x', tight=True)

ax1.set_title(r"Filter Cavity Servo Output")
ax1.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax1.autoscale(axis='x', tight=True)

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% EOM Comb - Slow Flt. Cav. Feedback =======================================
data = [[], []]
try:
    mongo_client = MongoDB.MongoClient()
    db_hv = MongoDB.DatabaseRead(mongo_client,
                                  'filter_cavity/HV_output')
    db_T = MongoDB.DatabaseRead(mongo_client,
                                 'filter_cavity/heater_temperature')
    cursor = db_hv.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['V'],
             ])
    cursor = db_T.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        if 'set_V' in doc:
            data[1].append(
                [doc['_timestamp'],
                 doc['set_V']/100e-6,
                 doc['act_V']/100e-6,
                 ])
        else:
            data[1].append(
                [doc['_timestamp'],
                 doc['V_set']/100e-6,
                 doc['V_act']/100e-6,
                 ])
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T,
        ]
n_0 = len(data[0][0])
n_1 = len(data[1][0])

# Plot
fig_0 = plt.figure("EOM Comb - Slow Flt. Cav. Feedback")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

ax0.plot(data[0][0], data[0][1], '.', markersize=1)
ax1.plot(data[1][0], data[1][1], '.', markersize=1, label='Set')
ax1.plot(data[1][0], data[1][2], '.', markersize=1, label='Act.')

ax0.set_title(r"Filter Cavity Piezo Voltage")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.autoscale(axis='x', tight=True)

ax1.set_title(r"Heater Temperature")
ax1.yaxis.set_major_formatter(ticker.EngFormatter('$\Omega$'))
ax1.autoscale(axis='x', tight=True)
ax1.legend()

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% EOM Comb - Flt. Cav. Lock Search =========================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                                  'filter_cavity/DAQ_Vout_vs_reflect')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['V_out'],
             doc['V_ref'],
             ])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig_0 = plt.figure("EOM Comb - Flt. Cav. Lock Search")
plt.clf()
ax0 = plt.subplot2grid((4,1),(0,0), rowspan=3)
ax1 = plt.subplot2grid((4,1),(3,0))

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], '-')
    ax1.plot(data[0, idx], 0, 'o')

ax0.set_title(r"Filter Cavity Lock Point Search")
ax0.set_xlabel(r"Servo Voltage")
ax0.set_ylabel(r"Reflection Signal")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.xaxis.set_major_formatter(ticker.EngFormatter('V'))

for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)
ax1.yaxis.set_ticks([])

fig_0.tight_layout()

