# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:11:55 2019

@author: cdf1
"""
# %% Imports ==================================================================
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker

from Drivers.Database import MongoDB

from analysis import helper_functions as hf

import datetime

# %% Start/Stop Time
#--- Start
# start_time = None
# start_time = datetime.datetime(2018, 5, 1)
start_time = datetime.datetime.utcnow() - datetime.timedelta(weeks=4*4)
# start_time = datetime.datetime.utcnow() - datetime.timedelta(days=7)
# start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

#--- Stop
stop_time = None
# stop_time = datetime.datetime(2018, 5, 1)
#stop_time = datetime.datetime.utcnow()


# %% Database Paths ===========================================================
db_paths = [
    #--- mll_f0 ---------------------------------------------------------------
    # Data
    'mll_f0/dac_limits',
    'mll_f0/dac_output',
    'mll_f0/freq_err',
    # States
    'mll_f0/state',

    #--- mll_fR ---------------------------------------------------------------
    # Data
    'mll_fR/DAQ_Vout_vs_freq',
    'mll_fR/DAQ_error_signal',
    'mll_fR/HV_output',
    'mll_fR/PID_output',
    'mll_fR/PID_output_limits',
    'mll_fR/TEC_current',
    'mll_fR/TEC_event_status',
    'mll_fR/TEC_temperature',
    # Devices
    'mll_fR/device_DAQ_Vout_vs_freq',
    'mll_fR/device_HV',
    'mll_fR/device_PID',
    'mll_fR/device_TEC',
    # States
    'mll_fR/state',
    'mll_fR/control',
    ]


# %% Aux. Comb - f0 PLL =======================================================
data = [[], [], []]
try:
    mongo_client = MongoDB.MongoClient()
    db_f0_err = MongoDB.DatabaseRead(mongo_client,
                                  'mll_f0/freq_err')
    db_f0_out = MongoDB.DatabaseRead(mongo_client,
                                  'mll_f0/dac_output')
    db_f0_lim = MongoDB.DatabaseRead(mongo_client,
                                 'mll_f0/dac_limits')
    cursor = db_f0_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['Hz'],
             ])
    cursor = db_f0_out.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['V'],
             ])
    cursor = db_f0_lim.read_record(start=start_time, stop=stop_time)
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
fig_0 = plt.figure("Aux-Comb f0-PLL")
plt.clf()

gs0 = plt.matplotlib.gridspec.GridSpec(2, 1)
gs00 = plt.matplotlib.gridspec.GridSpecFromSubplotSpec(3, 10, subplot_spec=gs0[0,0], wspace=0, hspace=0)
gs10 = plt.matplotlib.gridspec.GridSpecFromSubplotSpec(1, 10, subplot_spec=gs0[1,0], wspace=0, hspace=0)

ax0 = plt.subplot(gs00[1:2+1,0:-1])
ax1 = plt.subplot(gs00[1:2+1,-1], sharey=ax0)
ax2 = plt.subplot(gs00[0,0:-1], sharex=ax0)

ax3 = plt.subplot(gs10[:,0:-1], sharex=ax0)

# f0
std_cutoff = 10
f0_y = data[0][1].astype(float)
f0_std = hf.mad_std(f0_y)
print("{:.2g} fraction outside {:} std".format(np.count_nonzero(np.abs(f0_y) > f0_std*std_cutoff)/f0_y.size, std_cutoff))

x_bins = hf.utc_ts_to_dt(hf.bins(hf.utc_dt_to_ts(data[0][0]), n=500))
y_bins = np.linspace(-std_cutoff*f0_std, std_cutoff*f0_std, 100)
ax0.hist2d(data[0][0], f0_y, bins=[x_bins, y_bins], cmap=plt.cm.Blues_r, norm=plt.matplotlib.colors.LogNorm())

ax2.semilogy(data[0][0], np.abs(f0_y), alpha=0)
y_bins = np.unique([
    np.linspace(0, std_cutoff*f0_std, 50),
    np.geomspace(std_cutoff*f0_std, ax2.get_ylim()[1], 50)])
ax2.hist2d(data[0][0], np.abs(f0_y), bins=[x_bins, y_bins], cmap=plt.cm.Blues_r, norm=plt.matplotlib.colors.LogNorm())

ax3.fill_between(data[2][0], data[2][1].astype(float), data[2][2].astype(float), alpha=.25, step='post')
ax3.plot(data[1][0], data[1][1].astype(float), '.', markersize=1)

ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax0.set_ylim([-std_cutoff*f0_std, std_cutoff*f0_std])

ax2.set_title(r"In-Loop f$_0$ Error")
ax2.set_yscale("log")
ax2.yaxis.set_major_locator(ticker.LogLocator())
ax2.yaxis.get_major_locator().set_params(numticks=3)
ax2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2.set_ylim(bottom=ax0.get_ylim()[1])
ax2.autoscale(axis='x', tight=True)


ax1.hist(f0_y, bins=100, density=True, orientation="horizontal", range=(-std_cutoff*f0_std, std_cutoff*f0_std))

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

ax3.set_title(r"f$_0$ Servo Output")
ax3.yaxis.set_major_formatter(ticker.EngFormatter('V'))
for label in ax3.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax0.grid(True, alpha=0.25)
ax1.grid(True, alpha=0.25)
ax2.grid(True, alpha=0.25)
ax3.grid(True, alpha=0.25)
ax0.set_xlim((data[0][0].min(), data[0][0].max()))
fig_0.tight_layout()
plt.draw()

# %% Aux. Comb - fR PLL =======================================================
data = [[], [], []]
try:
    mongo_client = MongoDB.MongoClient()
    db_fR_err = MongoDB.DatabaseRead(mongo_client,
                                  'mll_fR/DAQ_error_signal')
    db_fR_out = MongoDB.DatabaseRead(mongo_client,
                                  'mll_fR/PID_output')
    db_fR_lim = MongoDB.DatabaseRead(mongo_client,
                                 'mll_fR/PID_output_limits')
    cursor = db_fR_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['V']/(0.4*np.sqrt(2)), #.125 instead?
             ])
    cursor = db_fR_out.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['V'],
             ])
    cursor = db_fR_lim.read_record(start=start_time, stop=stop_time)
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
        np.array(data[2]).T,
        ]
n_0 = len(data[0][0])
n_1 = len(data[1][0])
n_2 = len(data[1][0])

# Plot
fig_0 = plt.figure("Aux-Comb fR-PLL")
plt.clf()

gs0 = plt.matplotlib.gridspec.GridSpec(2, 1)
gs00 = plt.matplotlib.gridspec.GridSpecFromSubplotSpec(3, 10, subplot_spec=gs0[0,0], wspace=0, hspace=0)
gs10 = plt.matplotlib.gridspec.GridSpecFromSubplotSpec(1, 10, subplot_spec=gs0[1,0], wspace=0, hspace=0)

ax0 = plt.subplot(gs00[1:2+1,0:-1])
ax1 = plt.subplot(gs00[1:2+1,-1], sharey=ax0)
ax2 = plt.subplot(gs00[0,0:-1], sharex=ax0)

ax3 = plt.subplot(gs10[:,0:-1], sharex=ax0)

# fR
fR_td = np.fromiter((td.total_seconds() for td in np.diff(data[0][0])), float, n_0-1)
fR_err = np.diff(data[0][1].astype(float))/(fR_td*(2*np.pi)).astype(float)
fR_mask = np.logical_not(np.ma.masked_invalid(fR_err).mask)
fR_err = fR_err[fR_mask]
fR_dt = data[0][0][1:][fR_mask]

std_cutoff = 10
fR_y = fR_err
fR_std = hf.mad_std(fR_y)
print("{:.2g} fraction outside {:} std".format(np.count_nonzero(np.abs(fR_y) > fR_std*std_cutoff)/fR_y.size, std_cutoff))

x_bins = hf.utc_ts_to_dt(hf.bins(hf.utc_dt_to_ts(fR_dt), n=500))
y_bins = np.linspace(-std_cutoff*fR_std, std_cutoff*fR_std, 100)
ax0.hist2d(fR_dt, fR_y, bins=[x_bins, y_bins], cmap=plt.cm.Blues_r, norm=plt.matplotlib.colors.LogNorm())

ax2.semilogy(fR_dt, np.abs(fR_y), alpha=0)
y_bins = np.unique([
    np.linspace(0, std_cutoff*fR_std, 50),
    np.geomspace(std_cutoff*fR_std, ax2.get_ylim()[1], 50)])
ax2.hist2d(fR_dt, np.abs(fR_y), bins=[x_bins, y_bins], cmap=plt.cm.Blues_r, norm=plt.matplotlib.colors.LogNorm())

if len(data[2]):
    ax3.fill_between(data[2][0], data[2][1].astype(float), data[2][2].astype(float), alpha=.25, step='post')
ax3.plot(data[1][0], data[1][1], '.', markersize=1)

ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
fR_std = hf.mad_std(fR_err)
ax0.set_ylim([-std_cutoff*fR_std, std_cutoff*fR_std])

ax2.set_title(r"In-Loop f$_R$ Error")
ax2.set_yscale("log")
ax2.yaxis.set_major_locator(ticker.LogLocator())
ax2.yaxis.get_major_locator().set_params(numticks=3)
ax2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2.set_ylim([ax0.get_ylim()[1], ax2.get_ylim()[1]])

ax1.hist(fR_err, bins=100, density=True, orientation="horizontal", range=(-std_cutoff*fR_std, std_cutoff*fR_std))

for label in ax0.xaxis.get_ticklabels():
    label.set_visible(False)

ax1.xaxis.set_ticklabels([])
ax1.yaxis.tick_right()
for label in ax1.yaxis.get_ticklabels():
    label.set_visible(False)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)

ax3.set_title(r"f$_R$ Servo Output")
ax3.yaxis.set_major_formatter(ticker.EngFormatter('V'))

for label in ax3.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax0.grid(True, alpha=0.25)
ax1.grid(True, alpha=0.25)
ax2.grid(True, alpha=0.25)
ax3.grid(True, alpha=0.25)
ax0.set_xlim((data[0][0].min(), data[0][0].max()))
fig_0.tight_layout()
plt.draw()


# %% Aux. Comb - Slow fR Feedback =============================================
data = [[], [], []]
try:
    mongo_client = MongoDB.MongoClient()
    db_hv = MongoDB.DatabaseRead(mongo_client,
                                  'mll_fR/HV_output')
    db_I = MongoDB.DatabaseRead(mongo_client,
                                 'mll_fR/TEC_current')
    db_T = MongoDB.DatabaseRead(mongo_client,
                                  'mll_fR/TEC_temperature')
    cursor = db_hv.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['V'],
             ])
    cursor = db_I.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['A'],
             ])
    cursor = db_T.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['kOhm']*1e3,
             ])
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T,
        np.array(data[2]).T,
        ]
n_0 = len(data[0][0])
n_1 = len(data[1][0])
n_2 = len(data[2][0])

# Plot
fig_0 = plt.figure("Aux-Comb Slow-fR-Feedback")
fig_0.set_size_inches([6.4 , 4.78*1.25])
plt.clf()
ax0 = plt.subplot2grid((3,1),(0,0))
ax1 = plt.subplot2grid((3,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((3,1),(2,0), sharex=ax0)

ax0.plot(data[0][0], data[0][1], '.', markersize=1)
ax1.plot(data[1][0], data[1][1], '.', markersize=1)
ax2.plot(data[2][0], data[2][1], '.', markersize=1)

ax0.set_title(r"f$_R$ Piezo Voltage")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('V'))


ax1.set_title(r"TEC Current")
ax1.yaxis.set_major_formatter(ticker.EngFormatter('A'))

ax2.set_title(r"Thermistor Resistance")
ax2.yaxis.set_major_formatter(ticker.EngFormatter(r'$\Omega$'))

ax0.autoscale(axis='x', tight=True)
ax0.grid(True, alpha=0.25)
ax1.grid(True, alpha=0.25)
ax2.grid(True, alpha=0.25)

fig_0.autofmt_xdate()
fig_0.tight_layout()
plt.draw()


# %% Aux. Comb - fR Lock Search ===============================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                                  'mll_fR/DAQ_Vout_vs_freq')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['Hz'],
             doc['V'],
             ])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# Plot
fig_0 = plt.figure("Aux. Comb - fR Lock Search")
plt.clf()
ax0 = plt.subplot2grid((4,1),(0,0), rowspan=3)
ax1 = plt.subplot2grid((4,1),(3,0))

colormap = plt.cm.nipy_spectral
ax0.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))
ax1.set_prop_cycle(color=colormap(np.linspace(0, 0.99, n)))

for idx in range(n):
    ax0.plot(data[2, idx], data[1, idx], '-')
    ax1.plot(data[0, idx], 0, 'o')

ax0.set_title(r"f$_R$ Lock Point Search")
ax0.set_xlabel(r"Servo Voltage")
ax0.set_ylabel(r"Frequency Error")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax0.xaxis.set_major_formatter(ticker.EngFormatter('V'))

for label in ax1.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)
ax1.yaxis.set_ticks([])

fig_0.tight_layout()
