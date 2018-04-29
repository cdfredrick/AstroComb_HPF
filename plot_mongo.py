# -*- coding: utf-8 -*-
"""
Created on Wed Mar 21 11:46:06 2018

@author: National Institute
"""

# %% Modules

import matplotlib.pyplot as plt
import datetime
import numpy as np

from Drivers.Database import MongoDB

import pytz
central_tz = pytz.timezone('US/Central')
utc_tz = pytz.utc

# %% Choose data
#start_time = central_tz.localize(datetime.datetime(2018, 3, 19, 14))
#stop_time = central_tz.localize(datetime.datetime(2018, 3, 22, 6))
start_time = central_tz.localize(datetime.datetime(2018, 4, 21, 14, 40))
stop_time = central_tz.localize(datetime.datetime.now())
DBs = {
#        'filter_cavity/HV_output':{
#        'start':start_time,
#        'stop':stop_time,
#        'keys':{
#                '_timestamp':lambda dt: utc_tz.localize(dt).astimezone(central_tz),
#                'V':lambda v: v}}
        'ambience/box_temperature_0':{
                'start':start_time,
                'stop':stop_time,
                'keys':{
                        '_timestamp':lambda dt: utc_tz.localize(dt).astimezone(central_tz),
                        'V':lambda v: v*100,
                        'std':lambda v: v*100}},
        'ambience/box_temperature_1':{
                'start':start_time,
                'stop':stop_time,
                'keys':{
                        '_timestamp':lambda dt: utc_tz.localize(dt).astimezone(central_tz),
                        'V':lambda v: v*100,
                        'std':lambda v: v*100}}
#        'ambience/rack_temperature_0':{
#                'start':start_time,
#                'stop':stop_time,
#                'keys':{
#                        '_timestamp':lambda dt: utc_tz.localize(dt).astimezone(central_tz),
#                        'V':lambda v: v*100,
#                        'std':lambda v: v*100}}
}


# %% Connect to database and pull results

mongo_client = MongoDB.MongoClient()
data = {}
try:
    for database in DBs:
        data[database] = {}
        start = DBs[database]['start'].astimezone(utc_tz)
        stop = DBs[database]['stop'].astimezone(utc_tz)
        keys = DBs[database]['keys']
        for key in keys:
            data[database][key] = []
        db = MongoDB.DatabaseRead(mongo_client, database)
        cursor = db.read_record(start, stop)
        for doc in cursor:
            for key in keys:
                data[database][key].append(keys[key](doc[key]))
finally:
    mongo_client.close()

# %% Plot Data

plt.clf()
for database in DBs:
    db = database
    plt.plot(data[db]['_timestamp'], data[db]['V'], label=db)
plt.legend()

# %% 
#start = 0
#stop = -1
#db = 'ambience/rack_temperature_0'
#freqs = np.fft.rfftfreq(len(data[db]['_timestamp'][start:stop]), d=np.mean(np.diff(data[db]['_timestamp'][start:stop])).total_seconds())
#amps = np.fft.rfft((data[db]['V'][start:stop]-np.mean(data[db]['V'][start:stop]))*np.hanning(len(data[db]['V'][start:stop])))
#
#plt.clf()
#plt.plot(freqs*60*60, np.abs(amps)**2)
