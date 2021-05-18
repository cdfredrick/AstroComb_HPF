# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:13:10 2019

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
# start_time = datetime.datetime(2018, 5, 1)
# start_time = datetime.datetime(2019, 9, 1)
# start_time = datetime.datetime(2020, 5, 1)
#start_time = datetime.datetime.utcnow() - datetime.timedelta(days=14)
start_time = datetime.datetime.utcnow() - datetime.timedelta(weeks=4*3)
# start_time = datetime.datetime.utcnow() - datetime.timedelta(days=4)

#--- Stop
stop_time = None
#stop_time = datetime.datetime(2019, 5, 1)
#stop_time = datetime.datetime.utcnow()


# %% Database Paths ===========================================================
db_paths = [
    #--- broadening_stage -----------------------------------------------------
    # Data
    'broadening_stage/2nd_stage_z_in_optimizer',
    'broadening_stage/2nd_stage_z_out_optimizer',
    'broadening_stage/nanotrack_in_TIA',
    'broadening_stage/nanotrack_in_position',
    'broadening_stage/nanotrack_in_status',
    'broadening_stage/nanotrack_out_TIA',
    'broadening_stage/nanotrack_out_position',
    'broadening_stage/nanotrack_out_status',
    'broadening_stage/piezo_x_in_HV_output',
    'broadening_stage/piezo_x_out_HV_output',
    'broadening_stage/piezo_y_in_HV_output',
    'broadening_stage/piezo_y_out_HV_output',
    'broadening_stage/piezo_z_in_HV_output',
    'broadening_stage/piezo_z_out_HV_output',
    'broadening_stage/rot_stg_position',
    'broadening_stage/rot_stg_status',
    'broadening_stage/rot_stg_velocity',
    # Devices
    'broadening_stage/device_nanotrack_in',
    'broadening_stage/device_nanotrack_out',
    'broadening_stage/device_piezo_x_in',
    'broadening_stage/device_piezo_x_out',
    'broadening_stage/device_piezo_y_in',
    'broadening_stage/device_piezo_y_out',
    'broadening_stage/device_piezo_z_in',
    'broadening_stage/device_piezo_z_out',
    'broadening_stage/device_rotation_mount',
    # States
    'broadening_stage/state_2nd_stage',
    'broadening_stage/control',

    #--- spectral_shaper ------------------------------------------------------
    # Data
    'spectral_shaper/2nd_stage_z_in_optimizer',
    'spectral_shaper/2nd_stage_z_out_optimizer',
    'spectral_shaper/DW_bulk_vs_waveplate_angle',
    'spectral_shaper/DW_vs_IM_bias',
    'spectral_shaper/DW_vs_waveplate_angle',
    'spectral_shaper/optical_phase_optimizer',
    # Devices
    'spectral_shaper/device_IM_bias',
    'spectral_shaper/device_OSA',
    'spectral_shaper/device_piezo_z_in',
    'spectral_shaper/device_piezo_z_out',
    'spectral_shaper/device_rotation_mount',
    'spectral_shaper/device_waveshaper',
    ]

# %% Brd.Stg. - Rotation Stage Position =======================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'broadening_stage/rot_stg_position')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        if doc['deg'] > 0:
            if doc['_timestamp'] < datetime.datetime(2020, 1, 10, 18):
                pwr = np.sin(2*(58 - doc['deg']) * np.pi/180)**2
            elif doc['_timestamp'] < datetime.datetime(2020, 10, 27, 20):
                continue
            else:
                pwr = np.cos(2*(60 - doc['deg']) * np.pi/180)**2
            data.append(
                [doc['_timestamp'],
                 doc['deg'],
                 pwr])
finally:
    mongo_client.close()


data = np.array(data).T

# Plot
fig = plt.figure("Brd-Stg Rotation-Stage-Position")
plt.clf()

ax0 = plt.subplot2grid((2,1), (0,0))
ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

ax0.plot(data[0], data[1], '.', markersize=1)
ax0.set_ylabel("Angle (deg)")
ax0.set_title("Position")
ax0.grid(True, alpha=0.25)

ax1.plot(data[0], data[2], '.', markersize=1)
ax1.set_title("Transmission")
ax1.set_ylabel("Power (arb. unit)")
ax1.grid(True, alpha=0.25)

fig.autofmt_xdate()
ax0.autoscale(axis='x', tight=True)
plt.tight_layout()


# %% Brd.Stg. - NanoTrack In ==================================================
data = [[],[],[],[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_tia = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_in_TIA')
    db_ntp = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_in_position')
    db_HV_x = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/piezo_x_in_HV_output')
    db_HV_y = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/piezo_y_in_HV_output')
    db_HV_z = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/piezo_z_in_HV_output')
    cursor = db_tia.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['A'],
             doc['A_std'],
             ])
    cursor = db_ntp.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['x'],
             doc['y'],
             doc['x_std'],
             doc['y_std'],
             ])
    cursor = db_HV_x.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['V'],
             doc['std'],
             ])
    cursor = db_HV_y.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[3].append(
            [doc['_timestamp'],
             doc['V'],
             doc['std'],
             ])
    cursor = db_HV_z.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[4].append(
            [doc['_timestamp'],
             doc['V'],
             doc['std'],
             ])
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T,
        np.array(data[2]).T,
        np.array(data[3]).T,
        np.array(data[4]).T]
n_0 = len(data[0][0])
n_1 = len(data[1][0])
n_2 = len(data[2][0])
n_3 = len(data[3][0])
n_4 = len(data[4][0])


# Plot
fig_0 = plt.figure("Brd-Stg NanoTrack-In")
fig_0.set_size_inches([6.4 , 4.78*1.25])
plt.clf()
ax0 = plt.subplot2grid((3,1),(0,0))
ax1 = plt.subplot2grid((3,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((3,1),(2,0), sharex=ax0)

#ax0.errorbar(data[0][0], data[0][1], yerr=np.array(data[0][2])*2, fmt='.')
ax0.plot(data[0][0], data[0][1], '.', markersize=1)
ax0.set_title("NT-In TIA Reading")
ax0.set_ylabel("TIA Current")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))

#ax1.errorbar(data[1][0], data[1][1], yerr=np.array(data[1][3])*2, fmt='.', label='x')
#ax1.errorbar(data[1][0], data[1][2], yerr=np.array(data[1][4])*2, fmt='.', label='y')
ax1.plot(data[1][0], data[1][1], '.', label='x', markersize=1)
ax1.plot(data[1][0], data[1][2], '.', label='y', markersize=1)
ax1.legend(loc=2, markerscale=10)
ax1.set_title("NT-In Position")
ax1.set_ylabel("arb. units")

ax2.plot(data[2][0], data[2][1], '.', label='x', markersize=1)
ax2.plot(data[3][0], data[3][1], '.', label='y', markersize=1)
ax2.plot(data[4][0], data[4][1], '.', label='z', markersize=1)
ax2.legend(loc=2, markerscale=10)
ax2.set_title("Piezo-In")
ax2.set_ylabel("HV Output")
ax2.yaxis.set_major_formatter(ticker.EngFormatter('V'))


fig_0.autofmt_xdate()
ax0.grid(True, alpha=0.25)
ax1.grid(True, alpha=0.25)
ax2.grid(True, alpha=0.25)
ax0.autoscale(axis='x', tight=True)
fig_0.tight_layout()


# %% Brd.Stg. - NanoTrack Out =================================================
data = [[],[],[],[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_tia = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_out_TIA')
    db_ntp = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_out_position')
    db_HV_x = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/piezo_x_out_HV_output')
    db_HV_y = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/piezo_y_out_HV_output')
    db_HV_z = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/piezo_z_out_HV_output')
    cursor = db_tia.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['A'],
             doc['A_std'],
             ])
    cursor = db_ntp.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['x'],
             doc['y'],
             doc['x_std'],
             doc['y_std'],
             ])
    cursor = db_HV_x.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['V'],
             doc['std'],
             ])
    cursor = db_HV_y.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[3].append(
            [doc['_timestamp'],
             doc['V'],
             doc['std'],
             ])
    cursor = db_HV_z.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[4].append(
            [doc['_timestamp'],
             doc['V'],
             doc['std'],
             ])
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T,
        np.array(data[2]).T,
        np.array(data[3]).T,
        np.array(data[4]).T]
n_0 = len(data[0][0])
n_1 = len(data[1][0])
n_2 = len(data[2][0])
n_3 = len(data[3][0])
n_4 = len(data[4][0])

# Plot
fig_0 = plt.figure("Brd-Stg NanoTrack-Out")
fig_0.set_size_inches([6.4 , 4.78*1.25])
plt.clf()
ax0 = plt.subplot2grid((3,1),(0,0))
ax1 = plt.subplot2grid((3,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((3,1),(2,0), sharex=ax0)

#ax0.errorbar(data[0][0], data[0][1], yerr=np.array(data[0][2])*2, fmt='.')
ax0.plot(data[0][0], data[0][1], '.', markersize=1)
ax0.set_title("NT-Out TIA Reading")
ax0.set_ylabel("TIA Current")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))

#ax1.errorbar(data[1][0], data[1][1], yerr=np.array(data[1][3])*2, fmt='.', label='x')
#ax1.errorbar(data[1][0], data[1][2], yerr=np.array(data[1][4])*2, fmt='.', label='y')
ax1.plot(data[1][0], data[1][1], '.', label='x', markersize=1)
ax1.plot(data[1][0], data[1][2], '.', label='y', markersize=1)
ax1.legend(markerscale=10)
ax1.set_title("NT-Out Position")
ax1.set_ylabel("arb. units")

ax2.plot(data[2][0], data[2][1], '.', label='x', markersize=1)
ax2.plot(data[3][0], data[3][1], '.', label='y', markersize=1)
ax2.plot(data[4][0], data[4][1], '.', label='z', markersize=1)
ax2.legend(markerscale=10)
ax2.set_title("Piezo-Out")
ax2.set_ylabel("HV Output")
ax2.yaxis.set_major_formatter(ticker.EngFormatter('V'))


fig_0.autofmt_xdate()
ax0.grid(True, alpha=0.25)
ax1.grid(True, alpha=0.25)
ax2.grid(True, alpha=0.25)
ax0.autoscale(axis='x', tight=True)
fig_0.tight_layout()


# %% Brd.Stg. - 2nd Stage Input Optimizer =====================================
#data = []
#try:
#    mongo_client = MongoDB.MongoClient()
#    db = MongoDB.DatabaseRead(mongo_client,
#                              'broadening_stage/2nd_stage_z_in_optimizer')
#    cursor = db.read_record(start=start_time, stop=stop_time)
#    for doc in cursor:
#        data.append(
#            [doc['_timestamp'],
#             doc['V'],
#             doc['A'],
#             doc['model']])
#finally:
#    mongo_client.close()
#data = np.array(data).T
#n = len(data[0])
#
## Plot
#fig = plt.figure("Brd.Stg. - 2nd Stage Input Optimizer")
#plt.clf()
#ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
#ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
#ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)
#
#colormap = plt.cm.nipy_spectral
#ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#
#for idx in range(n):
#    ax0.plot(data[1, idx], data[2, idx], 'o')
#    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
#    ax2.plot(data[0, idx], 0, 'o')
#
#ax0.set_title("2nd Stage Input Optimization")
#ax0.set_ylabel("TIA Current")
#ax0.set_xlabel("HV Output")
#ax0.xaxis.set_major_formatter(ticker.EngFormatter('V'))
#ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))
#
#ax1.set_title("Optimum Voltage")
#ax1.set_ylabel("Voltage")
#for label in ax1.xaxis.get_ticklabels():
#    label.set_ha('right')
#    label.set_rotation(30)
#
#ax2.xaxis.tick_top()
#for label in ax2.xaxis.get_ticklabels():
#    label.set_visible(False)
#ax2.yaxis.set_ticks([])
#
#plt.tight_layout()


# %% Brd.Stg. - 2nd Stage Output Optimizer ====================================
#data = []
#try:
#    mongo_client = MongoDB.MongoClient()
#    db = MongoDB.DatabaseRead(mongo_client,
#                              'broadening_stage/2nd_stage_z_out_optimizer')
#    cursor = db.read_record(start=start_time, stop=stop_time)
#    for doc in cursor:
#        data.append(
#            [doc['_timestamp'],
#             doc['V'],
#             doc['A'],
#             doc['model']])
#finally:
#    mongo_client.close()
#data = np.array(data).T
#n = len(data[0])
#
## Plot
#fig = plt.figure("Brd.Stg. - 2nd Stage Output Optimizer")
#plt.clf()
#ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
#ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
#ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)
#
#colormap = plt.cm.nipy_spectral
#ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#
#for idx in range(n):
#    ax0.plot(data[1, idx], data[2, idx], 'o')
#    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
#    ax2.plot(data[0, idx], 0, 'o')
#
#ax0.set_title("2nd Stage Output Optimization")
#ax0.set_ylabel("TIA Current")
#ax0.set_xlabel("Voltage")
#ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))
#
#ax1.set_title("Optimum Voltage")
#ax1.set_ylabel("Voltage")
#for label in ax1.xaxis.get_ticklabels():
#    label.set_ha('right')
#    label.set_rotation(30)
#
#ax2.xaxis.tick_top()
#for label in ax2.xaxis.get_ticklabels():
#    label.set_visible(False)
#ax2.yaxis.set_ticks([])
#
#plt.tight_layout()


# %% Spc.Shp. - 2nd Stage Input Optimizer =====================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'spectral_shaper/2nd_stage_z_in_optimizer')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['V'],
             doc['dBm'],
             doc['model']])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig = plt.figure("Spc-Shp 2nd-Stage-Input-Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
    ax2.plot(data[0, idx], 0, 'o')

ax0.set_title("2nd Stage Input Optimization")
ax0.set_ylabel("Max DW Power")
ax0.set_xlabel("Voltage")
ax0.autoscale(axis="x", tight=True)
ax0.grid(True, alpha=0.25)

ax1.set_title("Optimum Voltage")
ax1.set_ylabel("Voltage")
for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
ax2.yaxis.set_ticks([])

ax1.autoscale(axis="x", tight=True)
ax1.grid(True, alpha=0.25)

plt.tight_layout()


# %% Spc.Shp. - 2nd Stage Output Optimizer ====================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'spectral_shaper/2nd_stage_z_out_optimizer')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['V'],
             doc['dBm'],
             doc['model']])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig = plt.figure("Spc-Shp 2nd-Stage-Output-Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
    ax2.plot(data[0, idx], 0, 'o')

ax0.set_title("2nd Stage Output Optimization")
ax0.set_ylabel("Max DW Power")
ax0.set_xlabel("Voltage")
ax0.autoscale(axis="x", tight=True)
ax0.grid(True, alpha=0.25)

ax1.set_title("Optimum Voltage")
ax1.set_ylabel("Voltage")
for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
ax2.yaxis.set_ticks([])

ax1.autoscale(axis="x", tight=True)
ax1.grid(True, alpha=0.25)

plt.tight_layout()


# %% Spc.Shp. - DW Setpoint Optimizer =========================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'spectral_shaper/DW_bulk_vs_waveplate_angle')
    db_nwp = MongoDB.DatabaseRead(mongo_client,
                              'spectral_shaper/DW_bulk_vs_piezo_in_voltage')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        measure = "Angle"
        unit = "deg"
        data.append(
            [doc['_timestamp'],
             doc['deg'],
             doc['bulk_dBm'],
             doc['DW_dBm'],
             doc.get('bulk_model', None),
             doc.get('DW_model', None)])
    cursor = db_nwp.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        measure = "Voltage"
        unit = "V"
        data.append(
            [doc['_timestamp'],
             doc['V'],
             doc['bulk_dBm'],
             doc['DW_dBm'],
             doc.get('bulk_model', None),
             doc.get('DW_model', None)])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig_0 = plt.figure("Spc-Shp DW-Setpoint-Optimizer")
fig_0.set_size_inches(6.4 , 8.9)
plt.clf()
ax0 = plt.subplot2grid((9,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((9,1),(2,0), rowspan=2, sharex=ax0)
#ax2 = plt.subplot2grid((9,1),(4,0), sharex=ax1)

#fig_1 = plt.figure("Spc.Shp. - DW Setpoint Optimizer:DW")
ax3 = plt.subplot2grid((9,1),(4,0), rowspan=2)
ax4 = plt.subplot2grid((9,1),(6,0), rowspan=2, sharex=ax3)
ax5 = plt.subplot2grid((9,1),(8,0), sharex=ax3)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax3.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax4.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax5.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
#    ax2.plot(data[0, idx], 0, 'o')
    ax1.plot(data[1, idx], data[3, idx], 'o')
    ax5.plot(data[0, idx], 0, 'o')
    if data[4, idx] is not None:
        ax3.plot(data[0, idx], data[4, idx]['opt x'][0], 'o')
    else:
        ax3.plot(data[0, idx], np.nan, 'o')
    if data[5, idx] is not None:
        y = data[5, idx]['diagnostics']['optimum y']
        y_err = data[5, idx]['diagnostics']['optimum y std']
        ax4.errorbar(data[0, idx], y, yerr=y_err*2, fmt='.')
    else:
        ax4.errorbar(data[0, idx], np.nan, yerr=None, fmt='.')

ax0.set_title("Bulk Optimization")
ax0.set_ylabel("dBm")
ax0.set_xlabel("{:}".format(unit))
ax0.autoscale(axis="x", tight=True)
ax0.grid(True, alpha=0.25)

ax1.set_title("DW vs {:}".format(measure))
ax1.set_ylabel("dBm")
ax1.set_xlabel("{:}".format(unit))
ax1.grid(True, alpha=0.25)

ax3.set_title("Optimum {:}".format(measure))
ax3.set_ylabel("{:}".format(unit))
ax3.autoscale(axis="x", tight=True)
ax3.grid(True, alpha=0.25)

ax4.set_title("Optimum DW Amplitude")
ax4.set_ylabel("dBm")
ax4.grid(True, alpha=0.25)

for label in ax3.xaxis.get_ticklabels():
    label.set_visible(False)

#ax2.xaxis.tick_top()
#for label in ax2.xaxis.get_ticklabels():
#    label.set_visible(False)
#ax2.yaxis.set_ticks([])

for label in ax4.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax5.xaxis.tick_top()
for label in ax5.xaxis.get_ticklabels():
    label.set_visible(False)
ax5.yaxis.set_ticks([])

fig_0.tight_layout()
#fig_1.tight_layout()


# %% Spc.Shp. - IM Bias Optimizer =============================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'spectral_shaper/DW_vs_IM_bias')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['V'],
             doc['dBm'],
             doc.get('model', None)])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig_0 = plt.figure("Spc-Shp IM-Bias-Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
    ax2.plot(data[0, idx], 0, 'o')
    if data[3, idx] is not None:
        ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
    else:
        ax1.plot(data[0, idx], np.nan, 'o')

ax0.set_title("IM Bias Optimization")
ax0.set_ylabel("dBm")
ax0.set_xlabel("Voltage")

ax1.set_title("Optimum Voltage")
ax1.set_ylabel("Voltage")


for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
ax2.yaxis.set_ticks([])

ax0.autoscale(axis="x", tight=True)
ax0.grid(True, alpha=0.25)
ax1.autoscale(axis="x", tight=True)
ax1.grid(True, alpha=0.25)


fig_0.tight_layout()


# %% Spc.Shp. - Optical Phase Optimizer =======================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'spectral_shaper/optical_phase_optimizer')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['filter profile'],
             doc['domain'],
             doc.get('model', None),
             doc.get('coefs', None),
             doc.get('orders', None),
             ])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

#--- Total Phase
fig_0 = plt.figure("Spc-Shp Optical-Phase-Optimizer")
fig_0.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax0_sp = plt.twinx(ax0)
ax0_sp.set_zorder(ax0.get_zorder()-1)
ax0.patch.set_visible(False)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

spectrum = np.genfromtxt('analysis/W0048_EO.CSV', skip_header=30, delimiter=',').T
ax0_sp.plot(spectrum[0], spectrum[1]+20, color="0.75")
ax0_sp.set_ylabel("dB")

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
#ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, 6)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))

coefs = []
for idx in range(n):
    if data[5, idx] is None:
        coefs.append([0,0] + data[3, idx]['opt x'])
    else:
        coefs.append([0,0] + data[4, idx])
    freqs = np.array(data[1, idx]['freq'])
    if data[0, idx] > datetime.datetime(2020, 6, 4, 17, 30):
        poly_fit = np.polynomial.Polynomial(coefs[idx], domain=data[2, idx])
    else:
        poly_fit = np.polynomial.Legendre(coefs[idx], domain=data[2, idx])
        # Switch to Polynomial
        poly_fit2 = np.polynomial.Polynomial.fit(freqs, poly_fit(freqs), len(coefs[idx]), domain=data[2, idx])
        poly_fit = np.polynomial.Polynomial([0,0] + poly_fit2.coef.tolist()[2:], domain=data[2, idx])
        coefs[idx] = poly_fit.coef.tolist()
    ax0.plot(hf.nm_to_THz(freqs), poly_fit(freqs))
    # ax0.plot(hf.nm_to_THz(freqs), poly_fit.deriv(2)(freqs))
    ax2.plot(data[0, idx], 0, 'o')

    # Change coefficients to Taylor Series (phi[w] == phi[w0] + dphi/dw w + 0.5 d2phi/dw2 w**2 + ...)
    coefs[idx] = [1/(2*np.pi)**m * poly_fit.deriv(m)(hf.constants.c/1064e-9 * 1e-12) for m in range(8)]

for idx_2 in range(6):
    ax1.plot(data[0], [coefs[idx][idx_2+2] for idx in range(n)], '--.', label=idx_2+2, markersize=5, zorder=-idx_2)

ax0.set_title("Optimum Phase")
ax0.set_ylabel("Phase (rad.)")
ax0.set_xlabel("Wavelength (nm)")
ax0.set_xlim([1058, 1070])
ax0.set_ylim([-14, 14])
ax0_sp.set_ylim([-30, 10])

ax1.set_title("Optimum Coefficients")
ax1.set_ylabel("arb. units")
ax1.legend(loc="lower left", ncol=2, markerscale=2, columnspacing=1)


for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
ax2.yaxis.set_ticks([])

ax0.grid(True, alpha=0.25)
ax1.autoscale(axis="x", tight=True)
ax1.grid(True, alpha=0.25)

fig_0.tight_layout()

#%%
#--- Individual Orders
fig_1 = plt.figure("Spc.Shp. - Optical Phase Optimizer - Ind")
fig_1.clf()
ax3_2 = plt.subplot2grid((13,1),(0,0), rowspan=2)
ax3_3 = plt.subplot2grid((13,1),(2,0), rowspan=2)
ax3_4 = plt.subplot2grid((13,1),(4,0), rowspan=2)
ax3_5 = plt.subplot2grid((13,1),(6,0), rowspan=2)
ax3_6 = plt.subplot2grid((13,1),(8,0), rowspan=2)
ax3_7 = plt.subplot2grid((13,1),(10,0), rowspan=2)
ax4 = plt.subplot2grid((13,1),(12,0))

ax3_2.set_prop_cycle(color=colormap(np.linspace(0, .99, n)))
ax3_3.set_prop_cycle(color=colormap(np.linspace(0, .99, n)))
ax3_4.set_prop_cycle(color=colormap(np.linspace(0, .99, n)))
ax3_5.set_prop_cycle(color=colormap(np.linspace(0, .99, n)))
ax3_6.set_prop_cycle(color=colormap(np.linspace(0, .99, n)))
ax3_7.set_prop_cycle(color=colormap(np.linspace(0, .99, n)))
ax4.set_prop_cycle(color=colormap(np.linspace(0, 1, n)))

# for idx, order in enumerate(data[5]):
for idx, order in enumerate([data[5][-1]]):
    if order is not None:
        if '2' in order:
            ax3_2.plot(order['2']['coefs'], order['2']['dBm'], 'o')
        else:
            ax3_2.plot([],[], '.')
        if '3' in order:
            ax3_3.plot(order['3']['coefs'], order['3']['dBm'], 'o')
        else:
            ax3_3.plot([],[], '.')
        if '4' in order:
            ax3_4.plot(order['4']['coefs'], order['4']['dBm'], 'o')
        else:
            ax3_4.plot([],[], '.')
        if '5' in order:
            ax3_5.plot(order['5']['coefs'], order['5']['dBm'], 'o')
        else:
            ax3_5.plot([],[], '.')
        if '6' in order:
            ax3_6.plot(order['6']['coefs'], order['6']['dBm'], 'o')
        else:
            ax3_6.plot([],[], '.')
        if '7' in order:
            ax3_7.plot(order['7']['coefs'], order['7']['dBm'], 'o')
        else:
            ax3_7.plot([],[], '.')
        ax4.plot(data[0, idx], 0, 'o')

ax3_2.grid(True, alpha=.25)
ax3_3.grid(True, alpha=.25)
ax3_4.grid(True, alpha=.25)
ax3_5.grid(True, alpha=.25)
ax3_6.grid(True, alpha=.25)
ax3_7.grid(True, alpha=.25)

ax3_2.set_ylabel("2nd Order")
ax3_3.set_ylabel("3rd Order")
ax3_4.set_ylabel("4th Order")
ax3_5.set_ylabel("5th Order")
ax3_6.set_ylabel("6th Order")
ax3_7.set_ylabel("7th Order")

ax4.autoscale(axis="x", tight=True)
for label in ax4.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)
ax4.yaxis.set_ticks([])

fig_1.tight_layout()
