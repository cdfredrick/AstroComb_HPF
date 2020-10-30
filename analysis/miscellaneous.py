# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:25:09 2019

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
#start_time = datetime.datetime(2018, 5, 1)
# start_time = datetime.datetime(2020, 5, 1)
# start_time = datetime.datetime.utcnow() - datetime.timedelta(days=21)
start_time = datetime.datetime.utcnow() - datetime.timedelta(weeks=2)

#--- Stop
stop_time = None
#stop_time = datetime.datetime(2019, 5, 1)
#stop_time = datetime.datetime.utcnow()


# %% Database Paths ===========================================================
db_paths = [
    #--- ambience -------------------------------------------------------------
    # Data
    'ambience/box_temperature_0',
    'ambience/box_temperature_1',
    'ambience/rack_temperature_0',

    #--- monitor_DAQ ----------------------------------------------------------
    # Devices
    'monitor_DAQ/device_DAQ_analog_in',
    'monitor_DAQ/device_DAQ_digital_in',
    # States
    'monitor_DAQ/state_analog',
    'monitor_DAQ/state_digital',
    'monitor_DAQ/control',
    ]


# %% Env. - Temperature =======================================================
data = [[],[],[]]
try:
    mongo_client = MongoDB.MongoClient()
    db_cp = MongoDB.DatabaseRead(mongo_client,
                                  'ambience/box_temperature_0')
    db_box = MongoDB.DatabaseRead(mongo_client,
                                  'ambience/box_temperature_1')
    db_rack = MongoDB.DatabaseRead(mongo_client,
                                  'ambience/rack_temperature_0')
    cursor = db_cp.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[0].append(
            [doc['_timestamp'],
             doc['V']*100,
             ])
    cursor = db_box.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[1].append(
            [doc['_timestamp'],
             doc['V']*100,
             ])
    cursor = db_rack.read_record(start=start_time, stop=stop_time)
    for doc in cursor:
        data[2].append(
            [doc['_timestamp'],
             doc['V']*100,
             ])
finally:
    mongo_client.close()
data = [np.array(data[0]).T,
        np.array(data[1]).T,
        np.array(data[2]).T]
n_0 = len(data[0][0])
n_1 = len(data[1][0])
n_2 = len(data[2][0])

# Plot
fig_0 = plt.figure("Env. - Temperature")
fig_0.set_size_inches([6.4 , 4.78*1.25], forward=True)
plt.clf()
ax0 = plt.subplot2grid((3,1),(0,0))
ax1 = plt.subplot2grid((3,1),(1,0), sharex=ax0)
ax2 = plt.subplot2grid((3,1),(2,0), sharex=ax0)

ax0.plot(data[0][0], data[0][1], '.', markersize=1)
ax1.plot(data[1][0], data[1][1], '.', markersize=1)
ax2.plot(data[2][0], data[2][1], '.', markersize=1)

ax0.set_title("Cold Plate")
ax0.set_ylabel("Temperature")
ax0.yaxis.set_major_formatter(ticker.EngFormatter('C'))

ax1.set_title("Box")
ax1.set_ylabel("Temperature")
ax1.yaxis.set_major_formatter(ticker.EngFormatter('C'))

ax2.set_title("Rack")
ax2.set_ylabel("Temperature")
ax2.yaxis.set_major_formatter(ticker.EngFormatter('C'))

fig_0.autofmt_xdate()
ax0.autoscale(axis='x', tight=True)
ax0.grid(True, alpha=.25)
ax1.grid(True, alpha=.25)
ax2.grid(True, alpha=.25)
fig_0.tight_layout()