# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 11:29:37 2019

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
    # broadening_stage --------------------------------------------------------
    # States
    'broadening_stage/state_2nd_stage',
    
    # comb_generator ----------------------------------------------------------
    # States
    'comb_generator/state_12V_supply',
    'comb_generator/state_IM_bias',
    
    # cw_laser ----------------------------------------------------------------
    # States
    'cw_laser/state_frequency',
    
    # filter_cavity -----------------------------------------------------------
    # States
    'filter_cavity/state',
    
    # mll_f0 ------------------------------------------------------------------
    # States
    'mll_f0/state',
    
    # mll_fR ------------------------------------------------------------------
    # States
    'mll_fR/state',
    
    # monitor_DAQ -------------------------------------------------------------
    # States
    'monitor_DAQ/state_analog',
    'monitor_DAQ/state_digital',
    
    # rf_oscillators ----------------------------------------------------------
    # States
    'rf_oscillators/state_PLOs',
    'rf_oscillators/state_Rb_clock',
    
    # spectral_shaper ---------------------------------------------------------
    # States
    'spectral_shaper/state_SLM',
    'spectral_shaper/state_optimizer',
    ]
logs = [
    # broadening_stage --------------------------
    'broadening_stage',
    # comb_generator ----------------------------
    'comb_generator',
    # cw_laser ----------------------------------
    # filter_cavity -----------------------------
    'filter_cavity',
    # mll_f0 ------------------------------------
    # mll_fR ------------------------------------
    'mll_fR',
    # monitor_DAQ -------------------------------
    'monitor_DAQ',
    # rf_oscillators ----------------------------
    'rf_oscillators',
    # spectral_shaper ---------------------------
    'spectral_shaper',
    ]

# %% Uptime
def uptime(time, compliant, initialized, actual_state, desired_state,
           stop_time=None, prioritize_desire=False):
    # Copy Input Arrays
    time = np.copy(time)
    compliant = np.copy(compliant).astype(np.bool)
    initialized = np.copy(initialized).astype(np.bool)
    actual_state = np.copy(actual_state)
    desired_state = np.copy(desired_state)
    
    # Prioritize Desired State
    if prioritize_desire:
        compliant = np.logical_and(compliant,
                                   np.equal(desired_state, actual_state))
        
    # Stop Time
    if stop_time is None:
        stop_time = datetime.datetime.utcnow()
        
    # Check Initialization Condition
    compliant = compliant[::-1]
    initialized = initialized[::-1]
    for idx in range(1, len(time)):
        if (compliant[idx]) and (not initialized[idx]) and (not compliant[idx-1]):
            compliant[idx] = False
    compliant = compliant[::-1]
    initialized = initialized[::-1]
    
    # Calculate Change
    comp_change = np.append(True, np.not_equal(compliant[:-1], compliant[1:]))
    act_state_change = np.append(True, np.not_equal(actual_state[:-1], actual_state[1:]))
    #dsr_state_change = np.append(True, np.not_equal(desired_state[:-1], desired_state[1:]))
    time_delta = np.fromiter((td.total_seconds() for td in np.diff(np.append(time, stop_time))), np.float, len(time))

    # Result Container
    result = {"total":{},
              "state":{}}    
    # Total Uptime
    uptime = np.logical_and(comp_change, compliant)
    downtime = np.logical_and(comp_change, np.logical_not(compliant))
    uptime_start = np.nonzero(uptime)[0]
    downtime_start = np.nonzero(downtime)[0]
    uptime_stop = np.copy(downtime_start)
    downtime_stop = np.copy(uptime_start)
    up_last = np.max(uptime_start) > np.max(downtime_start)
    if len(uptime_start) and len(downtime_start):
        up_last = np.max(uptime_start) > np.max(downtime_start)
    elif len(uptime_start):
        up_last = True
        down_last = False
    elif len(downtime_start):
        up_last = False
        down_last = True
    else:
        up_last = False
        down_last = False
    if up_last:
        uptime_stop = uptime_stop[1:]
        uptime_stop = np.append(uptime_stop, None)
    elif down_last:
        downtime_stop = downtime_stop[1:]
        downtime_stop = np.append(downtime_stop, None)
    uptime_idx = list(zip(uptime_start.tolist(), uptime_stop.tolist()))
    downtime_idx = list(zip(downtime_start.tolist(), downtime_stop.tolist()))
    uptime_time_delta = np.fromiter((np.sum(time_delta[idxs[0]:idxs[-1]]) for idxs in uptime_idx), np.float, len(time[uptime]))
    downtime_time_delta = np.fromiter((np.sum(time_delta[idxs[0]:idxs[-1]]) for idxs in downtime_idx), np.float, len(time[downtime]))
    result["total"]["uptime"] = {
        "timestamp":time[uptime],
        "delta":uptime_time_delta,
        "total":np.sum(uptime_time_delta)}
    result["total"]["downtime"] = {
        "timestamp":time[downtime],
        "delta":downtime_time_delta,
        "total":np.sum(downtime_time_delta)}
    result["total"]["totaltime"] = np.sum(time_delta)
    
    # Uptime by State
    states = np.unique([actual_state, desired_state])
    for state in states:
        result["state"][state] = {}
        # Find state records
        if prioritize_desire:
            is_state = (desired_state == state)
        else:
            is_state = (actual_state == state)
        # Find Compliance
        uptime = np.logical_and(
            np.logical_or(comp_change, act_state_change),
            np.logical_and(is_state, compliant))
        downtime = np.logical_and(
            np.logical_or(comp_change, act_state_change),
            np.logical_and(is_state, np.logical_not(compliant)))
        uptime_start = np.nonzero(uptime)[0]
        downtime_start = np.nonzero(downtime)[0]
        uptime_stop = np.copy(downtime_start)
        downtime_stop = np.copy(uptime_start)
        if len(uptime_start) and len(downtime_start):
            up_last = np.max(uptime_start) > np.max(downtime_start)
        elif len(uptime_start):
            up_last = True
            down_last = False
        elif len(downtime_start):
            up_last = False
            down_last = True
        else:
            up_last = False
            down_last = False
        if up_last:
            uptime_stop = uptime_stop[1:]
            uptime_stop = np.append(uptime_stop, None)
        elif down_last:
            downtime_stop = downtime_stop[1:]
            downtime_stop = np.append(downtime_stop, None)
        uptime_idx = list(zip(uptime_start.tolist(), uptime_stop.tolist()))
        downtime_idx = list(zip(downtime_start.tolist(), downtime_stop.tolist()))
        uptime_time_delta = np.fromiter((np.sum(is_state[idxs[0]:idxs[-1]] * time_delta[idxs[0]:idxs[-1]]) for idxs in uptime_idx), np.float, len(time[uptime]))
        downtime_time_delta = np.fromiter((np.sum(is_state[idxs[0]:idxs[-1]] * time_delta[idxs[0]:idxs[-1]]) for idxs in downtime_idx), np.float, len(time[downtime]))
        result["state"][state]["uptime"] = {
            "timestamp":time[uptime],
            "delta":uptime_time_delta,
            "total":np.sum(uptime_time_delta)}
        result["state"][state]["downtime"] = {
            "timestamp":time[downtime],
            "delta":downtime_time_delta,
            "total":np.sum(downtime_time_delta)}
        result["state"][state]["totaltime"] = np.sum(time_delta[is_state])
    return result

test = uptime(data[0], data[1], data[2], data[3], data[4])
# %% EOM Comb - CW Laser ======================================================
data = []
try:
    mongo_client = MongoDB.MongoClient()
    db = MongoDB.DatabaseRead(mongo_client,
                                  'mll_fR/state')
    cursor = db.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data.append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
finally:
    mongo_client.close()
data = np.array(data).T
n = len(data[0])

# %%
test = uptime(data[0], data[1], data[2], data[3], data[4])

# %%
fig_0 = plt.figure("TEST")
plt.clf()
plt.hist(ut_data[1], bins=100)


# %%
# Plot
fig_0 = plt.figure("Aux. Comb - fR Freq. State")
plt.clf()
plt.plot(np.append(data[0], datetime.datetime.utcnow()),
         np.append(data[1].astype(np.float), data[1][-1]),
         drawstyle='steps-post')
plt.plot(data[0],
         data[1].astype(np.float),
         'o')
plt.plot(data[0],
         data[2].astype(np.float),
         '.')
# %%

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





