# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:25:58 2019

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
start_time = datetime.datetime.utcnow() - datetime.timedelta(days=10)

#--- Stop
stop_time = None
#stop_time = datetime.datetime(2019, 5, 1)
#stop_time = datetime.datetime.utcnow()

# %% Database Paths ===========================================================
db_paths = [
    # rf_oscillators ----------------------------------------------------------
    # Data
    'rf_oscillators/Rb_time_tag',
    'rf_oscillators/100MHz_phase_lock',
    'rf_oscillators/1GHz_phase_lock',
    'rf_oscillators/Rb_detected_signals',

    # mll_fR ------------------------------------------------------------------
    # Data
    'mll_fR/DAQ_error_signal', # should be related to freq error (V is prop to phase)

    # mll_f0 ------------------------------------------------------------------
    # Data
    'mll_f0/freq_err',

    # cw_laser ----------------------------------------------------------------
    # Data
    'cw_laser/freq_err',
]


# %% Rb Clock - GPS Stability =================================================
data = [[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_err = MongoDB.DatabaseRead(mongo_client,
                                      'rf_oscillators/Rb_time_tag')
    cursor = db_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['ns']*1e-9,
             doc['std']*1e-9,
             ])
finally:
    mongo_client.close()
n = []
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    n.append(len(data[idx][0]))

fGPS_td = np.fromiter((td.total_seconds() for td in np.diff(data[0][0])), np.float, n[0]-1)
fGPS_err = np.diff(data[0][1])/(fGPS_td)*10e6
fGPS_mask = np.logical_not(np.ma.masked_invalid(fGPS_err).mask)
fGPS_err = fGPS_err[fGPS_mask]
data[0][0] = data[0][0][1:][fGPS_mask]
data[0][1] = fGPS_err
n[0] = len(fGPS_err)

# %% Plot
fig_0 = plt.figure("Rb Clock - GPS Stability")
fig_0.set_size_inches([6.4 , 4.78*1.25], forward=True)
plt.clf()

gs0 = gridspec.GridSpec(7, 1)
gs00 = gridspec.GridSpecFromSubplotSpec(5, 10, subplot_spec=gs0[:3+1,0], wspace=0, hspace=0)
gs10 = gridspec.GridSpecFromSubplotSpec(1, 10, subplot_spec=gs0[4:,0], wspace=0, hspace=0)

ax0 = plt.subplot(gs00[1:3+1,0:-1])
ax1 = plt.subplot(gs00[1:3+1,-1], sharey=ax0)
ax2 = plt.subplot(gs00[0,0:-1], sharex=ax0)
ax2_2 = plt.subplot(gs00[4,0:-1], sharex=ax0)

ax3 = plt.subplot(gs10[:,0:-1])

# f
f_std = np.sqrt(np.median((data[0][1] - np.median(data[0][1]))**2))

n_f_avg = int(n[0]/10)
f_y = data[0][1].astype(np.float)
f_y_order = f_y.argsort()
f_y_order_r = f_y_order.argsort()
f_y_diff = np.append(0, np.diff(f_y[f_y_order]))
f_y_diff = hf.fftconvolve(f_y_diff, 1/n_f_avg*np.array([1]*n_f_avg), mode="same")
f_z = 1/f_y_diff[f_y_order_r]
f_z_order = f_z.argsort()[::1]

#amps, bins = np.histogram(data[0][1], bins=75, range=(-10*f_std, 10*f_std))
#bins = (bins[:-1] + bins[1:])/1
#f_z = np.interp(data[0][1], bins, amps)**2
#f_z_order = f_z.argsort()[::1]

ax0.scatter(data[0][0][f_z_order], data[0][1][f_z_order], c=f_z[f_z_order], edgecolor='', cmap=plt.cm.Blues_r, s=1, vmax=np.nanmax(f_z), vmin=np.nanmin(f_z))

ax1.hist(data[0][1].astype(np.float), bins=10000, density=True, orientation="horizontal", range=(-1000*f_std, 1000*f_std))

test_time = np.fromiter((dt.timestamp() for dt in data[0][0]), np.float, len(data[0][0]))
# Raw Adev
adev = hf.adev.tot_dev_fft(test_time, data[0][1], sampling=1000)
ax3.loglog(adev[0], adev[1], '.', markersize=1, label="Raw")
# Deglitched Adev
x, y = hf.adev.deglitch(test_time, data[0][1])
adev_dg = hf.adev.tot_dev_fft(x, y, sampling=1000)
ax3.loglog(adev_dg[0], adev_dg[1], '.', markersize=1, label="Deglitched")

ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax0.autoscale(axis='x', tight=True)
ax0.set_xlim((np.min(data[0][0]), np.max(data[0][0])))
ax0.set_ylim([-10*f_std, 10*f_std])

out_high = (data[0][1] >= 10*f_std)
out_low = (data[0][1] <= -10*f_std)

ax2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')
ax2_2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')

ax2.set_title(r"In-Loop GPS Error")
ax2.set_ylim(bottom = ax0.get_ylim()[1], top=100*ax2.get_ylim()[0])
ax2.set_yscale("symlog", linthreshy=10*f_std)
ax2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2.yaxis.get_major_locator().set_params(numticks=int(4))
ax2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2.yaxis.set_minor_formatter(ticker.NullFormatter())

ax2_2.set_yscale("symlog", linthreshy=10*f_std)
ax2_2.set_ylim(top = ax0.get_ylim()[0], bottom=100*ax2_2.get_ylim()[0])
ax2_2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2_2.yaxis.get_major_locator().set_params(numticks=4)
ax2_2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2_2.yaxis.set_minor_formatter(ticker.NullFormatter())

symmetric_limit = np.max(np.abs([ax2.get_ylim()[1], ax2_2.get_ylim()[0]]))
ax2.set_ylim(top = symmetric_limit)
ax2_2.set_ylim(bottom = -symmetric_limit)

for label in ax0.xaxis.get_ticklabels():
    label.set_visible(False)

ax1.set_xticks([])
ax1.yaxis.tick_right()
for label in ax1.yaxis.get_ticklabels():
    label.set_visible(False)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
for label in ax2_2.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax3.set_title(r"GPS Allan Deviation")
ax3.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax3.set_xlabel("seconds")
ax3.grid()
ax3.legend(markerscale=5)
fig_0.tight_layout()


# %% Aux. Comb - fR Stability =================================================
data = [[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_err = MongoDB.DatabaseRead(mongo_client,
                                      'mll_fR/DAQ_error_signal')
    cursor = db_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['V']/(0.4*np.sqrt(2)),
             doc['std']/(0.4*np.sqrt(2)),
             ])
finally:
    mongo_client.close()
n = []
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    n.append(len(data[idx][0]))

fR_td = np.fromiter((td.total_seconds() for td in np.diff(data[0][0])), np.float, n[0]-1)
fR_err = np.diff(data[0][1])/(fR_td*(2*np.pi))
fR_mask = np.logical_not(np.ma.masked_invalid(fR_err).mask)
fR_err = fR_err[fR_mask]
data[0][0] = data[0][0][1:][fR_mask]
data[0][1] = fR_err
n[0] = len(fR_err)

# Plot
fig_0 = plt.figure("Aux. Comb - fR Stability")
fig_0.set_size_inches([6.4 , 4.78*1.25], forward=True)
plt.clf()

gs0 = gridspec.GridSpec(7, 1)
gs00 = gridspec.GridSpecFromSubplotSpec(5, 10, subplot_spec=gs0[:3+1,0], wspace=0, hspace=0)
gs10 = gridspec.GridSpecFromSubplotSpec(1, 10, subplot_spec=gs0[4:,0], wspace=0, hspace=0)

ax0 = plt.subplot(gs00[1:3+1,0:-1])
ax1 = plt.subplot(gs00[1:3+1,-1], sharey=ax0)
ax2 = plt.subplot(gs00[0,0:-1], sharex=ax0)
ax2_2 = plt.subplot(gs00[4,0:-1], sharex=ax0)

ax3 = plt.subplot(gs10[:,0:-1])

# f
n_f_avg = int(n[0]/100)
f_y = data[0][1].astype(np.float)
f_y_order = f_y.argsort()
f_y_order_r = f_y_order.argsort()
f_y_diff = np.append(0, np.diff(f_y[f_y_order]))
f_y_diff = hf.fftconvolve(f_y_diff, 1/n_f_avg*np.array([1]*n_f_avg), mode="same")
f_z = 1/f_y_diff[f_y_order_r]
f_z_order = f_z.argsort()[::1]

ax0.scatter(data[0][0][f_z_order], data[0][1][f_z_order], c=f_z[f_z_order], edgecolor='', cmap=plt.cm.Blues_r, s=1, vmax=np.nanmax(f_z), vmin=np.nanmin(f_z))

test_time = np.fromiter((dt.timestamp() for dt in data[0][0]), np.float, len(data[0][0]))
# Raw Adev
adev = hf.adev.tot_dev_fft(test_time, data[0][1], sampling=1000)
ax3.loglog(adev[0], adev[1], '.', markersize=1, label="Raw")
# Deglitched Adev
x, y = hf.adev.deglitch(test_time, data[0][1])
adev_dg = hf.adev.tot_dev_fft(x, y, sampling=1000)
ax3.loglog(adev_dg[0], adev_dg[1], '.', markersize=1, label="Deglitched")

ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax0.autoscale(axis='x', tight=True)
ax0.set_xlim((np.min(data[0][0]), np.max(data[0][0])))
f_std = np.sqrt(np.median((data[0][1] - np.median(data[0][1]))**2))
ax0.set_ylim([-10*f_std, 10*f_std])

out_high = (data[0][1] >= 10*f_std)
out_low = (data[0][1] <= -10*f_std)

ax2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')
ax2_2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')

ax2.set_title(r"In-Loop f$_{R}$ Error")
ax2.set_yscale("symlog", linthreshy=10*f_std)
ax2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2.yaxis.get_major_locator().set_params(numticks=4)
ax2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2.set_ylim(bottom = ax0.get_ylim()[1])

ax2_2.set_yscale("symlog", linthreshy=10*f_std)
ax2_2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2_2.yaxis.get_major_locator().set_params(numticks=4)
ax2_2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2_2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2_2.set_ylim(top = ax0.get_ylim()[0])

symmetric_limit = np.max(np.abs([ax2.get_ylim()[1], ax2_2.get_ylim()[0]]))
ax2.set_ylim(top = symmetric_limit)
ax2_2.set_ylim(bottom = -symmetric_limit)

ax1.hist(data[0][1].astype(np.float), bins=10000, density=True, orientation="horizontal", range=(-1000*f_std, 1000*f_std))

for label in ax0.xaxis.get_ticklabels():
    label.set_visible(False)

ax1.set_xticks([])
ax1.yaxis.tick_right()
for label in ax1.yaxis.get_ticklabels():
    label.set_visible(False)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
for label in ax2_2.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax3.set_title(r"f$_{R}$ Allan Deviation")
ax3.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax3.set_xlabel("seconds")
ax3.grid()
ax3.legend(markerscale=5)
fig_0.tight_layout()


# %% Aux. Comb - f0 Stability =================================================
data = [[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_err = MongoDB.DatabaseRead(mongo_client,
                                      'mll_f0/freq_err')
    cursor = db_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['Hz'],
             doc['std'],
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
fig_0 = plt.figure("Aux. Comb - f0 Stability")
fig_0.set_size_inches([6.4 , 4.78*1.25], forward=True)
plt.clf()

gs0 = gridspec.GridSpec(7, 1)
gs00 = gridspec.GridSpecFromSubplotSpec(5, 10, subplot_spec=gs0[:3+1,0], wspace=0, hspace=0)
gs10 = gridspec.GridSpecFromSubplotSpec(1, 10, subplot_spec=gs0[4:,0], wspace=0, hspace=0)

ax0 = plt.subplot(gs00[1:3+1,0:-1])
ax1 = plt.subplot(gs00[1:3+1,-1], sharey=ax0)
ax2 = plt.subplot(gs00[0,0:-1], sharex=ax0)
ax2_2 = plt.subplot(gs00[4,0:-1], sharex=ax0)

ax3 = plt.subplot(gs10[:,0:-1])

# f
n_f_avg = int(n[0]/100)
f_y = data[0][1].astype(np.float)
f_y_order = f_y.argsort()
f_y_order_r = f_y_order.argsort()
f_y_diff = np.append(0, np.diff(f_y[f_y_order]))
f_y_diff = hf.fftconvolve(f_y_diff, 1/n_f_avg*np.array([1]*n_f_avg), mode="same")
f_z = 1/f_y_diff[f_y_order_r]
f_z_order = f_z.argsort()[::1]

ax0.scatter(data[0][0][f_z_order], data[0][1][f_z_order], c=f_z[f_z_order], edgecolor='', cmap=plt.cm.Blues_r, s=1, vmax=np.nanmax(f_z), vmin=np.nanmin(f_z))

test_time = np.fromiter((dt.timestamp() for dt in data[0][0]), np.float, len(data[0][0]))
# Raw Adev
adev = hf.adev.tot_dev_fft(test_time, data[0][1], sampling=1000)
ax3.loglog(adev[0], adev[1], '.', markersize=1, label="Raw")
# Deglitched Adev
x, y = hf.adev.deglitch(test_time, data[0][1])
adev_dg = hf.adev.tot_dev_fft(x, y, sampling=1000)
ax3.loglog(adev_dg[0], adev_dg[1], '.', markersize=1, label="Deglitched")

ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax0.autoscale(axis='x', tight=True)
ax0.set_xlim((np.min(data[0][0]), np.max(data[0][0])))
f_std = np.sqrt(np.median((data[0][1] - np.median(data[0][1]))**2))
ax0.set_ylim([-10*f_std, 10*f_std])

out_high = (data[0][1] >= 10*f_std)
out_low = (data[0][1] <= -10*f_std)

ax2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')
ax2_2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')

ax2.set_title(r"In-Loop f$_{0}$ Error")
ax2.set_yscale("symlog", linthreshy=10*f_std)
ax2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2.yaxis.get_major_locator().set_params(numticks=3.5)
ax2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2.set_ylim(bottom = ax0.get_ylim()[1])

ax2_2.set_yscale("symlog", linthreshy=10*f_std)
ax2_2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2_2.yaxis.get_major_locator().set_params(numticks=3.5)
ax2_2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2_2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2_2.set_ylim(top = ax0.get_ylim()[0])

symmetric_limit = np.max(np.abs([ax2.get_ylim()[1], ax2_2.get_ylim()[0]]))
ax2.set_ylim(top = symmetric_limit)
ax2_2.set_ylim(bottom = -symmetric_limit)

ax1.hist(data[0][1].astype(np.float), bins=10000, density=True, orientation="horizontal", range=(-1000*f_std, 1000*f_std))

for label in ax0.xaxis.get_ticklabels():
    label.set_visible(False)

ax1.set_xticks([])
ax1.yaxis.tick_right()
for label in ax1.yaxis.get_ticklabels():
    label.set_visible(False)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
for label in ax2_2.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax3.set_title(r"f$_{0}$ Allan Deviation")
ax3.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax3.set_xlabel("seconds")
ax3.grid()
ax3.legend(markerscale=5)
fig_0.tight_layout()


# %% EOM Comb - fCW Stability =================================================
data = [[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_err = MongoDB.DatabaseRead(mongo_client,
                                      'cw_laser/freq_err')
    cursor = db_err.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['Hz'],
             doc['std'],
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
fig_0 = plt.figure("EOM Comb - fCW Stability")
fig_0.set_size_inches([6.4 , 4.78*1.25], forward=True)
plt.clf()

gs0 = gridspec.GridSpec(7, 1)
gs00 = gridspec.GridSpecFromSubplotSpec(5, 10, subplot_spec=gs0[:3+1,0], wspace=0, hspace=0)
gs10 = gridspec.GridSpecFromSubplotSpec(1, 10, subplot_spec=gs0[4:,0], wspace=0, hspace=0)

ax0 = plt.subplot(gs00[1:3+1,0:-1])
ax1 = plt.subplot(gs00[1:3+1,-1], sharey=ax0)
ax2 = plt.subplot(gs00[0,0:-1], sharex=ax0)
ax2_2 = plt.subplot(gs00[4,0:-1], sharex=ax0)

ax3 = plt.subplot(gs10[:,0:-1])

# f
n_f_avg = int(n[0]/100)
f_y = data[0][1].astype(np.float)
f_y_order = f_y.argsort()
f_y_order_r = f_y_order.argsort()
f_y_diff = np.append(0, np.diff(f_y[f_y_order]))
f_y_diff = hf.fftconvolve(f_y_diff, 1/n_f_avg*np.array([1]*n_f_avg), mode="same")
f_z = 1/f_y_diff[f_y_order_r]
f_z_order = f_z.argsort()[::1]

ax0.scatter(data[0][0][f_z_order], data[0][1][f_z_order], c=f_z[f_z_order], edgecolor='', cmap=plt.cm.Blues_r, s=1, vmax=np.nanmax(f_z), vmin=np.nanmin(f_z))

test_time = np.fromiter((dt.timestamp() for dt in data[0][0]), np.float, len(data[0][0]))
# Raw Adev
adev = hf.adev.tot_dev_fft(test_time, data[0][1], sampling=1000)
ax3.loglog(adev[0], adev[1], '.', markersize=1, label="Raw")
# Deglitched Adev
x, y = hf.adev.deglitch(test_time, data[0][1])
adev_dg = hf.adev.tot_dev_fft(x, y, sampling=1000)
ax3.loglog(adev_dg[0], adev_dg[1], '.', markersize=1, label="Deglitched")

ax0.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax0.autoscale(axis='x', tight=True)
ax0.set_xlim((np.min(data[0][0]), np.max(data[0][0])))
f_std = np.sqrt(np.median((data[0][1] - np.median(data[0][1]))**2))
ax0.set_ylim([-10*f_std, 10*f_std])

out_high = (data[0][1] >= 10*f_std)
out_low = (data[0][1] <= -10*f_std)

ax2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')
ax2_2.scatter(data[0][0], data[0][1], s=1, c=plt.cm.Blues_r(0), edgecolor='')

ax2.set_title(r"In-Loop f$_{CW}$ Error")
ax2.set_yscale("symlog", linthreshy=10*f_std)
ax2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2.yaxis.get_major_locator().set_params(numticks=3.5)
ax2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2.set_ylim(bottom = ax0.get_ylim()[1])

ax2_2.set_yscale("symlog", linthreshy=10*f_std)
ax2_2.yaxis.set_major_locator(ticker.SymmetricalLogLocator(linthresh=10*f_std, base=10))
ax2_2.yaxis.get_major_locator().set_params(numticks=3.5)
ax2_2.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax2_2.yaxis.set_minor_formatter(ticker.NullFormatter())
ax2_2.set_ylim(top = ax0.get_ylim()[0])

symmetric_limit = np.max(np.abs([ax2.get_ylim()[1], ax2_2.get_ylim()[0]]))
ax2.set_ylim(top = symmetric_limit)
ax2_2.set_ylim(bottom = -symmetric_limit)

ax1.hist(data[0][1].astype(np.float), bins=10000, density=True, orientation="horizontal", range=(-1000*f_std, 1000*f_std))

for label in ax0.xaxis.get_ticklabels():
    label.set_visible(False)

ax1.set_xticks([])
ax1.yaxis.tick_right()
for label in ax1.yaxis.get_ticklabels():
    label.set_visible(False)

ax2.xaxis.tick_top()
for label in ax2.xaxis.get_ticklabels():
    label.set_visible(False)
for label in ax2_2.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(30)

ax3.set_title(r"f$_{CW}$ Allan Deviation")
ax3.yaxis.set_major_formatter(ticker.EngFormatter('Hz'))
ax3.set_xlabel("seconds")
ax3.grid()
ax3.legend(markerscale=5)
fig_0.tight_layout()

