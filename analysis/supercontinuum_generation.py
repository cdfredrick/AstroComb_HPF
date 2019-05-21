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
start_time = None
#start_time = datetime.datetime(2018, 5, 1)
#start_time = datetime.datetime.utcnow() - datetime.timedelta(days=10)

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
def deg_to_pwr(deg):
    return np.sin(np.pi/180 * 2*(58 - deg))**2

data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'broadening_stage/rot_stg_position')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        if doc['deg'] > 0:
            data.append(
                [doc['_timestamp'],
                 doc['deg']])
finally:
    mongo_client.close()


data = np.array(data).T

# Plot
fig = plt.figure("Brd.Stg. - Rotation Stage Position")
plt.clf()

ax0 = plt.subplot2grid((2,1), (0,0))
ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

ax0.plot(data[0], data[1], '.', markersize=1)
ax0.set_ylabel("Angle (deg)")
ax0.set_title("Position")
ax0.grid()

ax1.plot(data[0], deg_to_pwr(data[1].astype(np.float)), '.', markersize=1)
ax1.set_title("Transmission")
ax1.set_ylabel("Power (arb. unit)")
ax1.grid()

fig.autofmt_xdate()
plt.tight_layout()


# %% Brd.Stg. - NanoTrack In ==================================================
data = [[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_tia = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_in_TIA')
    db_ntp = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_in_position')
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
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T]
n_0 = len(data[0][0])
n_1 = len(data[1][0])

# Plot
fig_0 = plt.figure("Brd.Stg. - NanoTrack In")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

colormap = plt.cm.nipy_spectral
#ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n_0)))
#ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n_1)))

#ax0.errorbar(data[0][0], data[0][1], yerr=np.array(data[0][2])*2, fmt='.')
ax0.plot(data[0][0], data[0][1], '.', markersize=1)

#ax1.errorbar(data[1][0], data[1][1], yerr=np.array(data[1][3])*2, fmt='.', label='x')
#ax1.errorbar(data[1][0], data[1][2], yerr=np.array(data[1][4])*2, fmt='.', label='y')
ax1.plot(data[1][0], data[1][1], '.', label='x', markersize=1)
ax1.plot(data[1][0], data[1][2], '.', label='y', markersize=1)

ax1.legend()

ax0.set_title("NT-In TIA Reading")
ax0.set_ylabel("TIA Current")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))

ax1.set_title("NT-In Position")
ax1.set_ylabel("arb. units")

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% Brd.Stg. - NanoTrack Out =================================================
data = [[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_tia = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_out_TIA')
    db_ntp = MongoDB.DatabaseRead(mongo_client,
                                  'broadening_stage/nanotrack_out_position')
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
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T]
n_0 = len(data[0][0])
n_1 = len(data[1][0])

# Plot
fig_0 = plt.figure("Brd.Stg. - NanoTrack Out")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

colormap = plt.cm.nipy_spectral
#ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n_0)))
#ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n_1)))

#ax0.errorbar(data[0][0], data[0][1], yerr=np.array(data[0][2])*2, fmt='.')
ax0.plot(data[0][0], data[0][1], '.', markersize=1)

#ax1.errorbar(data[1][0], data[1][1], yerr=np.array(data[1][3])*2, fmt='.', label='x')
#ax1.errorbar(data[1][0], data[1][2], yerr=np.array(data[1][4])*2, fmt='.', label='y')
ax1.plot(data[1][0], data[1][1], '.', label='x', markersize=1)
ax1.plot(data[1][0], data[1][2], '.', label='y', markersize=1)

ax1.legend()

ax0.set_title("NT-Out TIA Reading")
ax0.set_ylabel("TIA Current")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))

ax1.set_title("NT-Out Position")
ax1.set_ylabel("arb. units")

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% Brd.Stg. - 2nd Stage Input Optimizer =====================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'broadening_stage/2nd_stage_z_in_optimizer')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['V'],
             doc['A'],
             doc['model']])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig = plt.figure("Brd.Stg. - 2nd Stage Input Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
    ax2.plot(data[0, idx], 0, 'o')

ax0.set_title("2nd Stage Input Optimization")
ax0.set_ylabel("TIA Current")
ax0.set_xlabel("HV Output")
ax0.xaxis.set_major_formatter(ticker.EngFormatter('V'))
ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))

ax1.set_title("Optimum Voltage")
ax1.set_ylabel("Voltage")
for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
ax2.yaxis.set_ticks([])

plt.tight_layout()


# %% Brd.Stg. - 2nd Stage Output Optimizer ====================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'broadening_stage/2nd_stage_z_out_optimizer')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['V'],
             doc['A'],
             doc['model']])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig = plt.figure("Brd.Stg. - 2nd Stage Output Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
    ax2.plot(data[0, idx], 0, 'o')

ax0.set_title("2nd Stage Output Optimization")
ax0.set_ylabel("TIA Current")
ax0.set_xlabel("Voltage")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('A'))

ax1.set_title("Optimum Voltage")
ax1.set_ylabel("Voltage")
for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
ax2.yaxis.set_ticks([])

plt.tight_layout()


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
fig = plt.figure("Spc.Shp. - 2nd Stage Input Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
    ax2.plot(data[0, idx], 0, 'o')

ax0.set_title("2nd Stage Input Optimization")
ax0.set_ylabel("Max DW Power")
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
fig = plt.figure("Spc.Shp. - 2nd Stage Output Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
    ax1.plot(data[0, idx], data[3, idx]['opt x'][0], 'o')
    ax2.plot(data[0, idx], 0, 'o')

ax0.set_title("2nd Stage Output Optimization")
ax0.set_ylabel("Max DW Power")
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

plt.tight_layout()


# %% Spc.Shp. - DW Setpoint Optimizer =========================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                              'spectral_shaper/DW_bulk_vs_waveplate_angle')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['deg'],
             doc['bulk_dBm'],
             doc['DW_dBm'],
             doc.get('bulk_model', None),
             doc.get('DW_model', None)])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig_0 = plt.figure("Spc.Shp. - DW Setpoint Optimizer")
fig_0.set_size_inches(6.4 , 8.38)
plt.clf()
ax0 = plt.subplot2grid((9,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((9,1),(2,0), rowspan=2)
#ax2 = plt.subplot2grid((9,1),(4,0), sharex=ax1)

#fig_1 = plt.figure("Spc.Shp. - DW Setpoint Optimizer:DW")
ax3 = plt.subplot2grid((9,1),(4,0), rowspan=2, sharex=ax0)
ax4 = plt.subplot2grid((9,1),(6,0), rowspan=2, sharex=ax1)
ax5 = plt.subplot2grid((9,1),(8,0), sharex=ax4)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
#ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax3.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax4.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax5.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

for idx in range(n):
    ax0.plot(data[1, idx], data[2, idx], 'o')
#    ax2.plot(data[0, idx], 0, 'o')
    ax3.plot(data[1, idx], data[3, idx], 'o')
    ax5.plot(data[0, idx], 0, 'o')
    if data[4, idx] is not None:
        ax1.plot(data[0, idx], data[4, idx]['opt x'][0], 'o')
    else:
        ax1.plot(data[0, idx], np.nan, 'o')
    if data[5, idx] is not None:
        y = data[5, idx]['diagnostics']['optimum y']
        y_err = data[5, idx]['diagnostics']['optimum y std']
        ax4.errorbar(data[0, idx], y, yerr=y_err*2, fmt='.')
    else:
        ax4.errorbar(data[0, idx], np.nan, yerr=None, fmt='.')

ax0.set_title("Bulk Optimization")
ax0.set_ylabel("dBm")
ax0.set_xlabel("deg")

ax1.set_title("Optimum Angle")
ax1.set_ylabel("deg")

ax3.set_title("DW vs Angle")
ax3.set_ylabel("dBm")
ax3.set_xlabel("deg")

ax4.set_title("Optimum DW Amplitude")
ax4.set_ylabel("dBm")

for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

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
fig_0 = plt.figure("Spc.Shp. - IM Bias Optimizer")
plt.clf()
ax0 = plt.subplot2grid((5,1),(0,0), rowspan=2)
ax1 = plt.subplot2grid((5,1),(2,0), rowspan=2)
ax2 = plt.subplot2grid((5,1),(4,0), sharex=ax1)

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

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

# Plot
fig_0 = plt.figure("Spc.Shp. - Optical Phase Optimizer")
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
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))
#ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.95, 6)))
ax2.set_prop_cycle(color=colormap(np.linspace(0, 0.95, n)))

coefs = []
for idx in range(n):
    if data[5, idx] is None:
        coefs.append([0,0] + data[3, idx]['opt x'])
    else:
        coefs.append([0,0] + data[4, idx])
    freqs = np.array(data[1, idx]['freq'])
    poly_fit = np.polynomial.Legendre(coefs[idx], domain=data[2, idx])
    ax0.plot(hf.nm_to_THz(freqs), poly_fit(freqs))
    ax2.plot(data[0, idx], 0, 'o')

for idx_2 in range(6):
    ax1.plot(data[0], [coefs[idx][idx_2+2] for idx in range(n)], '--o', label=idx_2+2)

ax0.set_title("Optimum Phase")
ax0.set_ylabel("Phase (rad.)")
ax0.set_xlabel("Wavelength (nm)")
ax0.set_xlim([1058, 1070])
ax0.set_ylim([-14, 14])
ax0_sp.set_ylim([-30, 10])

ax1.set_title("Optimum Coefficients")
ax1.set_ylabel("arb. units")
ax1.legend(ncol=2)

for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
ax2.yaxis.set_ticks([])

fig_0.tight_layout()

