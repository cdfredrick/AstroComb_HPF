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
#start_time = datetime.datetime(2019, 5, 15, 18) # strict initialization valid
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


# %% Uptime Calculator ========================================================
def uptime(time, compliant, initialized, actual_state, desired_state,
           stop_time=None, prioritize_desire=False,
           strict_initialization=False):
    '''

    Parameters
    ----------
    strict_initialization : bool
        set to True to force strict initialization

    Notes
    -----
    Strict initialization is only completely valid for UTC times greater than
    2019-05-15 18:00 (new uptime bookeeping implemented on 2019-05-15 around
    12pm MT).
    '''
    # Copy Input Arrays
    time = np.copy(time)
    compliant = np.copy(compliant).astype(np.bool)
    initialized = np.copy(initialized).astype(np.bool)
    actual_state = np.copy(actual_state)
    desired_state = np.copy(desired_state)

    # Stop Time
    if stop_time is None:
        stop_time = datetime.datetime.utcnow()

    # Calculate Time Delta
    time_delta = np.diff(np.append(time, stop_time))

    # Prioritize Desired State
    if prioritize_desire:
        compliant = np.logical_and(compliant,
                                   np.equal(desired_state, actual_state))

    # Check Initialization Condition
    compliant = compliant[::-1]
    initialized = initialized[::-1]
    for idx in range(1, len(time)):
        if (compliant[idx]) and (not initialized[idx]) and (not compliant[idx-1]):
            compliant[idx] = False
            if ((time[idx] > datetime.datetime(2019, 5, 15, 18)) or strict_initialization) and (idx+1 < len(time)):
                compliant[idx+1] = False
    compliant = compliant[::-1]
    initialized = initialized[::-1]

    # Result Container
    result = {"total":{},
              "state":{}}
    # Total Uptime
    uptime = np.nonzero(compliant)[0]
    downtime = np.nonzero(np.logical_not(compliant))[0]
    uptime_gap = np.nonzero(np.not_equal(np.abs(np.diff(uptime)), 1))[0]
    downtime_gap = np.nonzero(np.not_equal(np.abs(np.diff(downtime)), 1))[0]
    if len(uptime):
        uptime_start = np.append(uptime[0], uptime[uptime_gap+1])
        uptime_stop = np.append(uptime[uptime_gap], uptime[-1])
    else:
        uptime_start = np.array([], dtype=np.int)
        uptime_stop = np.array([], dtype=np.int)
    if len(downtime):
        downtime_start = np.append(downtime[0], downtime[downtime_gap+1])
        downtime_stop = np.append(downtime[downtime_gap], downtime[-1])
    else:
        downtime_start = np.array([], dtype=np.int)
        downtime_stop = np.array([], dtype=np.int)
    uptime_idx = np.array([uptime_start, uptime_stop]).T
    downtime_idx = np.array([downtime_start, downtime_stop]).T
    uptime_time_delta = np.array([np.sum(time_delta[idx[0]:idx[1]+1]) for idx in uptime_idx])
    downtime_time_delta = np.array([np.sum(time_delta[idx[0]:idx[1]+1]) for idx in downtime_idx])
    result["total"]["uptime"] = {
        "start":time[uptime_start],
        "stop":time[uptime_start]+uptime_time_delta,
        "delta":np.fromiter((td.total_seconds() for td in uptime_time_delta), np.float, len(uptime_time_delta)),
        "time":np.sum(uptime_time_delta).total_seconds() if len(uptime_time_delta) else 0.}
    result["total"]["downtime"] = {
        "start":time[downtime_start],
        "stop":time[downtime_start]+downtime_time_delta,
        "delta":np.fromiter((td.total_seconds() for td in downtime_time_delta), np.float, len(downtime_time_delta)),
        "time":np.sum(downtime_time_delta).total_seconds() if len(downtime_time_delta) else 0.}
    result["total"]["time"] = np.sum(time_delta).total_seconds() if len(time_delta) else 0.

    # Uptime by State
    states = np.unique([actual_state, desired_state])
    for state in states:
        result["state"][state] = {}
        # Find state records
        if prioritize_desire:
            is_state = (desired_state == state)
        else:
            is_state = (actual_state == state)
        # Uptime
        uptime = np.nonzero(np.logical_and(is_state, compliant))[0]
        downtime = np.nonzero(np.logical_and(is_state, np.logical_not(compliant)))[0]
        uptime_gap = np.nonzero(np.not_equal(np.diff(uptime), 1))[0]
        downtime_gap = np.nonzero(np.not_equal(np.diff(downtime), 1))[0]
        if len(uptime):
            uptime_start = np.append(uptime[0], uptime[uptime_gap+1])
            uptime_stop = np.append(uptime[uptime_gap], uptime[-1])
        else:
            uptime_start = np.array([], dtype=np.int)
            uptime_stop = np.array([], dtype=np.int)
        if len(downtime):
            downtime_start = np.append(downtime[0], downtime[downtime_gap+1])
            downtime_stop = np.append(downtime[downtime_gap], downtime[-1])
        else:
            downtime_start = np.array([], dtype=np.int)
            downtime_stop = np.array([], dtype=np.int)
        uptime_idx = np.array([uptime_start, uptime_stop]).T
        downtime_idx = np.array([downtime_start, downtime_stop]).T
        uptime_time_delta = np.array([np.sum(time_delta[idx[0]:idx[1]+1]) for idx in uptime_idx])
        downtime_time_delta = np.array([np.sum(time_delta[idx[0]:idx[1]+1]) for idx in downtime_idx])
        result["state"][state]["uptime"] = {
            "start":time[uptime_start],
            "stop":time[uptime_start]+uptime_time_delta,
            "delta":np.fromiter((td.total_seconds() for td in uptime_time_delta), np.float, len(uptime_time_delta)),
            "time":np.sum(uptime_time_delta).total_seconds() if len(uptime_time_delta) else 0.}
        result["state"][state]["downtime"] = {
            "start":time[downtime_start],
            "stop":time[downtime_start]+downtime_time_delta,
            "delta":np.fromiter((td.total_seconds() for td in downtime_time_delta), np.float, len(downtime_time_delta)),
            "time":np.sum(downtime_time_delta).total_seconds() if len(downtime_time_delta) else 0.}
        result["state"][state]["time"] = np.sum(time_delta[is_state]).total_seconds() if len(time_delta[is_state]) else 0.
    return result

# %% RF Osc. - State ==========================================================
data = [[],[]]
ut_data = [[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_PLO = MongoDB.DatabaseRead(mongo_client,
                                 'rf_oscillators/state_PLOs')
    db_Rb = MongoDB.DatabaseRead(mongo_client,
                                 'rf_oscillators/state_Rb_clock')
    cursor = db_PLO.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
    cursor = db_Rb.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
finally:
    mongo_client.close()
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    ut_data[idx] = uptime(*data[idx])

# Plot
fig_0 = plt.figure("RF Osc. - State")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

n_0d = len(ut_data[0]['total']['downtime']['start'])
line_x0 = np.array(
    [ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['stop'],
     ut_data[0]['total']['downtime']['stop']]).T.flatten().tolist()
line_y0 = np.array(
    [np.nan * np.ones(n_0d),
     0 * np.ones(n_0d),
     0 * np.ones(n_0d),
     np.nan * np.ones(n_0d)]).T.flatten().tolist()

n_0u = len(ut_data[0]['total']['uptime']['start'])
line_x0.extend(np.array(
    [ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['stop'],
     ut_data[0]['total']['uptime']['stop']]).T.flatten().tolist())
line_y0.extend(np.array(
    [np.nan * np.ones(n_0u),
     1 * np.ones(n_0u),
     1 * np.ones(n_0u),
     np.nan * np.ones(n_0u)]).T.flatten().tolist())

n_1d = len(ut_data[1]['total']['downtime']['start'])
line_x1 = np.array(
    [ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['stop'],
     ut_data[1]['total']['downtime']['stop']]).T.flatten().tolist()
line_y1 = np.array(
    [np.nan * np.ones(n_1d),
     0 * np.ones(n_1d),
     0 * np.ones(n_1d),
     np.nan * np.ones(n_1d)]).T.flatten().tolist()

n_1u = len(ut_data[1]['total']['uptime']['start'])
line_x1.extend(np.array(
    [ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['stop'],
     ut_data[1]['total']['uptime']['stop']]).T.flatten().tolist())
line_y1.extend(np.array(
    [np.nan * np.ones(n_1u),
     1 * np.ones(n_1u),
     1 * np.ones(n_1u),
     np.nan * np.ones(n_1u)]).T.flatten().tolist())

ax0.plot(line_x0, line_y0, '.-', markersize=2)
ax1.plot(line_x1, line_y1, '.-', markersize=2)

ax0.set_title(r"PLOs State ({:.2g}% downtime)".format(100 * ut_data[0]['total']['downtime']['time']/ut_data[0]['total']['time']))
ax0.set_yticks([0,1])

ax1.set_title(r"Rb Clock State ({:.2g}% downtime)".format(100 * ut_data[1]['total']['downtime']['time']/ut_data[1]['total']['time']))
ax1.set_yticks([0,1])

fig_0.autofmt_xdate()
fig_0.tight_layout()


# %% Aux. Comb - State ========================================================
data = [[],[]]
ut_data = [[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_f0 = MongoDB.DatabaseRead(mongo_client,
                                 'mll_f0/state')
    db_fR = MongoDB.DatabaseRead(mongo_client,
                                 'mll_fR/state')
    cursor = db_f0.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
    cursor = db_fR.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
finally:
    mongo_client.close()
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    ut_data[idx] = uptime(*data[idx])

# Plot
fig_0 = plt.figure("Aux. Comb - State")
plt.clf()
ax0 = plt.subplot2grid((2,1),(0,0))
ax1 = plt.subplot2grid((2,1),(1,0), sharex=ax0)

n_0d = len(ut_data[0]['total']['downtime']['start'])
line_x0 = np.array(
    [ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['stop'],
     ut_data[0]['total']['downtime']['stop']]).T.flatten().tolist()
line_y0 = np.array(
    [np.nan * np.ones(n_0d),
     0 * np.ones(n_0d),
     0 * np.ones(n_0d),
     np.nan * np.ones(n_0d)]).T.flatten().tolist()

n_0u = len(ut_data[0]['total']['uptime']['start'])
line_x0.extend(np.array(
    [ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['stop'],
     ut_data[0]['total']['uptime']['stop']]).T.flatten().tolist())
line_y0.extend(np.array(
    [np.nan * np.ones(n_0u),
     1 * np.ones(n_0u),
     1 * np.ones(n_0u),
     np.nan * np.ones(n_0u)]).T.flatten().tolist())

n_1d = len(ut_data[1]['total']['downtime']['start'])
line_x1 = np.array(
    [ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['stop'],
     ut_data[1]['total']['downtime']['stop']]).T.flatten().tolist()
line_y1 = np.array(
    [np.nan * np.ones(n_1d),
     0 * np.ones(n_1d),
     0 * np.ones(n_1d),
     np.nan * np.ones(n_1d)]).T.flatten().tolist()

n_1u = len(ut_data[1]['total']['uptime']['start'])
line_x1.extend(np.array(
    [ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['stop'],
     ut_data[1]['total']['uptime']['stop']]).T.flatten().tolist())
line_y1.extend(np.array(
    [np.nan * np.ones(n_1u),
     1 * np.ones(n_1u),
     1 * np.ones(n_1u),
     np.nan * np.ones(n_1u)]).T.flatten().tolist())

ax0.plot(line_x0, line_y0, '.-', markersize=2)
ax1.plot(line_x1, line_y1, '.-', markersize=2)

ax0.set_title(r"$f_0$ State ({:.2g}% downtime)".format(100 * ut_data[0]['total']['downtime']['time']/ut_data[0]['total']['time']))
ax0.set_yticks([0,1])

ax1.set_title(r"$f_R$ State ({:.2g}% downtime)".format(100 * ut_data[1]['total']['downtime']['time']/ut_data[1]['total']['time']))
ax1.set_yticks([0,1])

fig_0.autofmt_xdate()
fig_0.tight_layout()

# %% EOM Comb - State =========================================================
data = [[],[],[],[]]
ut_data = [[],[],[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_CG_12V = MongoDB.DatabaseRead(mongo_client,
        'comb_generator/state_12V_supply')
    db_CG_IM = MongoDB.DatabaseRead(mongo_client,
        'comb_generator/state_IM_bias')
    db_CW = MongoDB.DatabaseRead(mongo_client,
        'cw_laser/state_frequency')
    db_flt_cav = MongoDB.DatabaseRead(mongo_client,
        'filter_cavity/state')
    cursor = db_CG_12V.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
    cursor = db_CG_IM.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
    cursor = db_CW.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
    cursor = db_flt_cav.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[3].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
finally:
    mongo_client.close()
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    ut_data[idx] = uptime(*data[idx])

# Plot
fig_0 = plt.figure("EOM Comb - State")
plt.clf()
ax0 = plt.subplot2grid((4,1),(0,0))
ax1 = plt.subplot2grid((4,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((4,1),(2,0), sharex=ax0)
ax3 = plt.subplot2grid((4,1),(3,0), sharex=ax0)


n_0d = len(ut_data[0]['total']['downtime']['start'])
line_x0 = np.array(
    [ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['stop'],
     ut_data[0]['total']['downtime']['stop']]).T.flatten().tolist()
line_y0 = np.array(
    [np.nan * np.ones(n_0d),
     0 * np.ones(n_0d),
     0 * np.ones(n_0d),
     np.nan * np.ones(n_0d)]).T.flatten().tolist()
n_0u = len(ut_data[0]['total']['uptime']['start'])
line_x0.extend(np.array(
    [ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['stop'],
     ut_data[0]['total']['uptime']['stop']]).T.flatten().tolist())
line_y0.extend(np.array(
    [np.nan * np.ones(n_0u),
     1 * np.ones(n_0u),
     1 * np.ones(n_0u),
     np.nan * np.ones(n_0u)]).T.flatten().tolist())

n_1d = len(ut_data[1]['total']['downtime']['start'])
line_x1 = np.array(
    [ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['stop'],
     ut_data[1]['total']['downtime']['stop']]).T.flatten().tolist()
line_y1 = np.array(
    [np.nan * np.ones(n_1d),
     0 * np.ones(n_1d),
     0 * np.ones(n_1d),
     np.nan * np.ones(n_1d)]).T.flatten().tolist()
n_1u = len(ut_data[1]['total']['uptime']['start'])
line_x1.extend(np.array(
    [ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['stop'],
     ut_data[1]['total']['uptime']['stop']]).T.flatten().tolist())
line_y1.extend(np.array(
    [np.nan * np.ones(n_1u),
     1 * np.ones(n_1u),
     1 * np.ones(n_1u),
     np.nan * np.ones(n_1u)]).T.flatten().tolist())

n_2d = len(ut_data[2]['total']['downtime']['start'])
line_x2 = np.array(
    [ut_data[2]['total']['downtime']['start'],
     ut_data[2]['total']['downtime']['start'],
     ut_data[2]['total']['downtime']['stop'],
     ut_data[2]['total']['downtime']['stop']]).T.flatten().tolist()
line_y2 = np.array(
    [np.nan * np.ones(n_2d),
     0 * np.ones(n_2d),
     0 * np.ones(n_2d),
     np.nan * np.ones(n_2d)]).T.flatten().tolist()
n_2u = len(ut_data[2]['total']['uptime']['start'])
line_x2.extend(np.array(
    [ut_data[2]['total']['uptime']['start'],
     ut_data[2]['total']['uptime']['start'],
     ut_data[2]['total']['uptime']['stop'],
     ut_data[2]['total']['uptime']['stop']]).T.flatten().tolist())
line_y2.extend(np.array(
    [np.nan * np.ones(n_2u),
     1 * np.ones(n_2u),
     1 * np.ones(n_2u),
     np.nan * np.ones(n_2u)]).T.flatten().tolist())

n_3d = len(ut_data[3]['total']['downtime']['start'])
line_x3 = np.array(
    [ut_data[3]['total']['downtime']['start'],
     ut_data[3]['total']['downtime']['start'],
     ut_data[3]['total']['downtime']['stop'],
     ut_data[3]['total']['downtime']['stop']]).T.flatten().tolist()
line_y3 = np.array(
    [np.nan * np.ones(n_3d),
     0 * np.ones(n_3d),
     0 * np.ones(n_3d),
     np.nan * np.ones(n_3d)]).T.flatten().tolist()
n_3u = len(ut_data[3]['total']['uptime']['start'])
line_x3.extend(np.array(
    [ut_data[3]['total']['uptime']['start'],
     ut_data[3]['total']['uptime']['start'],
     ut_data[3]['total']['uptime']['stop'],
     ut_data[3]['total']['uptime']['stop']]).T.flatten().tolist())
line_y3.extend(np.array(
    [np.nan * np.ones(n_3u),
     1 * np.ones(n_3u),
     1 * np.ones(n_3u),
     np.nan * np.ones(n_3u)]).T.flatten().tolist())

ax0.plot(line_x0, line_y0, '.-', markersize=2)
ax1.plot(line_x1, line_y1, '.-', markersize=2)
ax2.plot(line_x2, line_y2, '.-', markersize=2)
ax3.plot(line_x3, line_y3, '.-', markersize=2)

ax0.set_title(r"12V State ({:.2g}% downtime)".format(100 * ut_data[0]['total']['downtime']['time']/ut_data[0]['total']['time']))
ax0.set_yticks([0,1])

ax1.set_title(r"IM Bias State ({:.2g}% downtime)".format(100 * ut_data[1]['total']['downtime']['time']/ut_data[1]['total']['time']))
ax1.set_yticks([0,1])

ax2.set_title(r"$f_{CW}$ State"+" ({:.2g}% downtime)".format(100 * ut_data[2]['total']['downtime']['time']/ut_data[2]['total']['time']))
ax2.set_yticks([0,1])

ax3.set_title(r"Flt. Cav. State ({:.2g}% downtime)".format(100 * ut_data[3]['total']['downtime']['time']/ut_data[3]['total']['time']))
ax3.set_yticks([0,1])

fig_0.autofmt_xdate()
fig_0.tight_layout()

# %% SCG - State ==============================================================
data = [[],[],[]]
ut_data = [[],[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_BS_2ndStg = MongoDB.DatabaseRead(mongo_client,
        'broadening_stage/state_2nd_stage')
    db_SS_SLM = MongoDB.DatabaseRead(mongo_client,
        'spectral_shaper/state_SLM')
    db_SS_Opt = MongoDB.DatabaseRead(mongo_client,
        'spectral_shaper/state_optimizer')
    cursor = db_BS_2ndStg.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
    cursor = db_SS_SLM.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
    cursor = db_SS_Opt.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['compliance'],
             doc['initialized'],
             doc['state'],
             doc['desired_state'],
             ])
finally:
    mongo_client.close()
for idx in range(len(data)):
    data[idx] = list(zip(*data[idx]))
    for idx2 in range(len(data[idx])):
        data[idx][idx2] = np.array(data[idx][idx2])
    ut_data[idx] = uptime(*data[idx])#, strict_initialization=True if idx==1 else False)

# Plot
fig_0 = plt.figure("SC Gen. - State")
plt.clf()
ax0 = plt.subplot2grid((3,1),(0,0))
ax1 = plt.subplot2grid((3,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((3,1),(2,0), sharex=ax0)

n_0d = len(ut_data[0]['total']['downtime']['start'])
line_x0 = np.array(
    [ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['start'],
     ut_data[0]['total']['downtime']['stop'],
     ut_data[0]['total']['downtime']['stop']]).T.flatten().tolist()
line_y0 = np.array(
    [np.nan * np.ones(n_0d),
     0 * np.ones(n_0d),
     0 * np.ones(n_0d),
     np.nan * np.ones(n_0d)]).T.flatten().tolist()
n_0u = len(ut_data[0]['total']['uptime']['start'])
line_x0.extend(np.array(
    [ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['start'],
     ut_data[0]['total']['uptime']['stop'],
     ut_data[0]['total']['uptime']['stop']]).T.flatten().tolist())
line_y0.extend(np.array(
    [np.nan * np.ones(n_0u),
     1 * np.ones(n_0u),
     1 * np.ones(n_0u),
     np.nan * np.ones(n_0u)]).T.flatten().tolist())

n_1d = len(ut_data[1]['total']['downtime']['start'])
line_x1 = np.array(
    [ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['start'],
     ut_data[1]['total']['downtime']['stop'],
     ut_data[1]['total']['downtime']['stop']]).T.flatten().tolist()
line_y1 = np.array(
    [np.nan * np.ones(n_1d),
     0 * np.ones(n_1d),
     0 * np.ones(n_1d),
     np.nan * np.ones(n_1d)]).T.flatten().tolist()
n_1u = len(ut_data[1]['total']['uptime']['start'])
line_x1.extend(np.array(
    [ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['start'],
     ut_data[1]['total']['uptime']['stop'],
     ut_data[1]['total']['uptime']['stop']]).T.flatten().tolist())
line_y1.extend(np.array(
    [np.nan * np.ones(n_1u),
     1 * np.ones(n_1u),
     1 * np.ones(n_1u),
     np.nan * np.ones(n_1u)]).T.flatten().tolist())

n_2d = len(ut_data[2]['total']['downtime']['start'])
line_x2 = np.array(
    [ut_data[2]['total']['downtime']['start'],
     ut_data[2]['total']['downtime']['start'],
     ut_data[2]['total']['downtime']['stop'],
     ut_data[2]['total']['downtime']['stop']]).T.flatten().tolist()
line_y2 = np.array(
    [np.nan * np.ones(n_2d),
     0 * np.ones(n_2d),
     0 * np.ones(n_2d),
     np.nan * np.ones(n_2d)]).T.flatten().tolist()
n_2u = len(ut_data[2]['total']['uptime']['start'])
line_x2.extend(np.array(
    [ut_data[2]['total']['uptime']['start'],
     ut_data[2]['total']['uptime']['start'],
     ut_data[2]['total']['uptime']['stop'],
     ut_data[2]['total']['uptime']['stop']]).T.flatten().tolist())
line_y2.extend(np.array(
    [np.nan * np.ones(n_2u),
     1 * np.ones(n_2u),
     1 * np.ones(n_2u),
     np.nan * np.ones(n_2u)]).T.flatten().tolist())

ax0.plot(line_x0, line_y0, '.-', markersize=2)
ax1.plot(line_x1, line_y1, '.-', markersize=2)
ax2.plot(line_x2, line_y2, '.-', markersize=2)

ax0.set_title(r"Brd.Stg. 2nd Stage State ({:.2g}% downtime)".format(100 * ut_data[0]['total']['downtime']['time']/ut_data[0]['total']['time']))
ax0.set_yticks([0,1])

ax1.set_title(r"Spc.Shp. SLM State ({:.2g}% downtime)".format(100 * ut_data[1]['total']['downtime']['time']/ut_data[1]['total']['time']))
ax1.set_yticks([0,1])

ax2.set_title(r"Spc.Shp. Optimizer State"+" ({:.2g}% downtime)".format(100 * ut_data[2]['total']['downtime']['time']/ut_data[2]['total']['time']))
ax2.set_yticks([0,1])

fig_0.autofmt_xdate()
fig_0.tight_layout()
