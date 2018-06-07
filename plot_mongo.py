# -*- coding: utf-8 -*-
"""
Created on Wed Mar 21 11:46:06 2018

@author: National Institute
"""

# %% Modules

import matplotlib.pyplot as plt
import datetime
import numpy as np
import copy

from Drivers.Database import MongoDB

import pytz
central_tz = pytz.timezone('US/Central')
utc_tz = pytz.utc

from cycler import cycler
def plot_setup(count, fig_ind=None, start=0, stop=.95):
    if fig_ind == None:
        plt.figure()
    else:
        plt.figure(fig_ind)
    plt.clf()
    colormap = plt.cm.spectral
    #plt.gca().set_color_cycle([colormap(i) for i in np.linspace(start, stop, count)])
    plt.gca().set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(start, stop, count)]))

# %% Choose data
ct_conv = lambda dt: utc_tz.localize(dt).astimezone(central_tz)
#start_time = central_tz.localize(datetime.datetime(2018, 3, 19, 14))
#stop_time = central_tz.localize(datetime.datetime(2018, 3, 22, 6))
#start_time = central_tz.localize(datetime.datetime(2018, 4, 21, 14, 40))
start_time = central_tz.localize(datetime.datetime(2018, 4, 21, 20, 0))
stop_time = central_tz.localize(datetime.datetime.now())
DBs = {
    # ambience ----------------------------------------------------------------
#    'ambience/box_temperature_0':{
#            'start':start_time,
#            'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v*100,
#                    'std':lambda v: v*100}},
#    'ambience/box_temperature_1':{
#            'start':start_time,
#            'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v*100,
#                    'std':lambda v: v*100}},
#    'ambience/rack_temperature_0':{
#            'start':start_time,
#            'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v*100,
#                    'std':lambda v: v*100}},
    # broadening_stage --------------------------------------------------------
#    'broadening_stage/device_rotation_mount':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'position':lambda p: p}},
    # comb_generator ----------------------------------------------------------
#    'comb_generator/IM_bias':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                   'V':lambda v: v,
#                   'std':lambda v: v}},
    # cw_laser ----------------------------------------------------------------
#    'cw_laser/dac_limits':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'min_V':lambda v: v,
#                    'max_V':lambda v: v,
#                    'min_std':lambda v: v,
#                    'max_std':lambda v: v}},
#    'cw_laser/dac_output':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    'cw_laser/freq_err':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'Hz':lambda f: f,
#                    'std':lambda f: f}},
    # filter_cavity -----------------------------------------------------------
#    'filter_cavity/DAQ_Vout_vs_reflect':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V_out':lambda v: v,
#                    'V_ref':lambda v: v}},
#    'filter_cavity/DAQ_error_signal':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    'filter_cavity/HV_output':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    'filter_cavity/PID_output':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    'filter_cavity/PID_output_limits':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'min':lambda v: v,
#                    'max':lambda v: v}},
#    'filter_cavity/heater_temperature':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'set_V':lambda v: v,
#                    'set_std':lambda v: v,
#                    'act_V':lambda v: v,
#                    'act_std':lambda v: v}},
    # mll_f0 ------------------------------------------------------------------
#    'mll_f0/dac_limits':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'min_V':lambda v: v,
#                    'min_std':lambda v: v,
#                    'max_V':lambda v: v,
#                    'max_std':lambda v: v}},
#    'mll_f0/dac_output':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    'mll_f0/freq_err':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'Hz':lambda f: f,
#                    'std':lambda f: f}},
    # mll_fR ------------------------------------------------------------------
#    'mll_fR/DAQ_Vout_vs_freq':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'Hz':lambda f: f}},
#    'mll_fR/DAQ_error_signal':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    'mll_fR/HV_output':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    'mll_fR/PID_output':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'std':lambda v: v}},
#    #'mll_fR/PID_output_limits':{
#    #        'start':start_time, 'stop':stop_time,
#    #        'keys':{
#    #                'min':lambda v: v,
#    #                'max':lambda v: v}},
#    'mll_fR/TEC_current':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'A':lambda a: a,
#                    'std':lambda a: a}},
#    'mll_fR/TEC_temperature':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'kOhm':lambda o: o,
#                    'std':lambda o: o}},
    # rf_oscillators ----------------------------------------------------------
#    'rf_oscillators/100MHz_phase_lock':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'bit':lambda b: b,
#                    'flips':lambda b: b}},
#    'rf_oscillators/1GHz_phase_lock':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'bit':lambda b: b,
#                    'flips':lambda b: b}},
#    'rf_oscillators/Rb_OCXO_control':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'high':lambda n: n,
#                    'high_std':lambda n: n,
#                    'low':lambda n: n,
#                    'low_std':lambda n: n}},
#    'rf_oscillators/Rb_detected_signals':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'mod':lambda v: v,
#                    'mod_std':lambda v: v,
#                    '2mod':lambda v: v,
#                    '2mod_std':lambda v: v}},
#    'rf_oscillators/Rb_frequency_offset':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    '1e-12':lambda n: n}},
#    'rf_oscillators/Rb_magnetic_read':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'DAC':lambda n: n}},
#    'rf_oscillators/Rb_time_tag':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'ns':lambda s: s,
#                    'std':lambda s: s}},
    # spectral_shaper ---------------------------------------------------------
    'spectral_shaper/DW':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                    'dBm':lambda dw: dw,
                    'std':lambda dw: dw}},
    'spectral_shaper/DW_vs_IM_bias':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                    'V':lambda v: v,
                    'dBm':lambda dw: dw}},
    'spectral_shaper/DW_vs_waveplate_angle':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                    'deg':lambda d: d,
                    'dBm':lambda dw: dw}},
    'spectral_shaper/mask':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                    'path':lambda p: 'top' in p}},
    'spectral_shaper/spectrum':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                    'data':lambda d: {'x':d['x'], 'y':d['y'], 'y_std':d['y_std']}}},
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
            data[database][key] = [[],[]]
        db = MongoDB.DatabaseRead(mongo_client, database)
        cursor = db.read_record(start, stop)
        for doc in cursor:
            for key in keys:
                if key in doc:
                    data[database][key][0].append(ct_conv(doc['_timestamp']))
                    data[database][key][1].append(keys[key](doc[key]))
finally:
    mongo_client.close()

# %% Plot Data
plt.close('all')
for ind, database in enumerate(DBs):
    keys = DBs[database]['keys']
    if database == 'filter_cavity/DAQ_Vout_vs_reflect':
        data_temp = list(zip(data[database]['V_out'][1],data[database]['V_ref'][1]))
        plot_setup(len(data_temp))
        for ind2, data_list in enumerate(data_temp):
            plt.plot(data_list[0], data_list[1], '.', markersize=1)#, label=data[database]['V_out'][0][ind2])
        plt.title(database)
        #plt.legend()
    elif database == 'mll_fR/DAQ_Vout_vs_freq':
        data_temp = list(zip(data[database]['V'][1],data[database]['Hz'][1]))
        plot_setup(len(data_temp))
        for ind2, data_list in enumerate(data_temp):
            plt.plot(data_list[0], data_list[1], '.', markersize=1)#, label=data[database]['V'][0][ind2])
        plt.title(database)
        #plt.legend()
    elif database == 'spectral_shaper/DW_vs_IM_bias':
        data_temp = list(zip(data[database]['V'][1],data[database]['dBm'][1]))
        plot_setup(len(data_temp))
        for ind2, data_list in enumerate(data_temp):
            plt.plot(data_list[0], data_list[1], '.', markersize=1)#, label=data[database]['V'][0][ind2])
        plt.title(database)
        #plt.legend()
    elif database == 'spectral_shaper/DW_vs_waveplate_angle':
        data_temp = list(zip(data[database]['deg'][1],data[database]['dBm'][1]))
        plot_setup(len(data_temp))
        for ind2, data_list in enumerate(data_temp):
            plt.plot(data_list[0], data_list[1], '.', markersize=1)#, label=data[database]['deg'][0][ind2])
        plt.title(database)
        #plt.legend()
    elif database == 'spectral_shaper/spectrum':
        data_temp = [[spectrum['x'], spectrum['y'], spectrum['y_std'], data[database]['data'][0][idx]] for idx,spectrum in enumerate(data[database]['data'][1])]
        [next( (data_temp.pop(idx) for idx, value in enumerate(data_temp) if value[3] >= switch_time), None) for switch_time in data['spectral_shaper/mask']['path'][0]]
        f, axarr = plt.subplots(2, sharex=True)
        colormap = plt.cm.spectral
        axarr[0].set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(0, 0.95, len(data_temp))]))
        axarr[1].set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(0, 0.95, len(data_temp))]))
        for ind3, data_list in enumerate(data_temp):
            try:
                len(data_list[0])==len(data_list[1])
                axarr[0].plot(data_list[0], data_list[1], '.', markersize=1)#, label=data[database]['data'][0][ind3])
            except:
                axarr[0].plot(data_list[0], np.array(data_list[0])*np.nan, '.', markersize=1)#, label=data[database]['data'][0][ind3])
            try:
                len(data_list[0])==len(data_list[2])
                axarr[1].plot(data_list[0], data_list[2], '.', markersize=1)#, label=data[database]['data'][0][ind3])
            except:
                axarr[1].plot(data_list[0], np.array(data_list[0])*np.nan, '.', markersize=1)#, label=data[database]['data'][0][ind3])
        axarr[0].set_title(database+':y')
        axarr[0].grid(b=True)
        axarr[1].set_title(database+':y_std')
        axarr[1].grid(b=True)
    else:
        f, axarr = plt.subplots(len(keys), sharex=True)
        f.autofmt_xdate()
        for ind2, key in enumerate(keys):
            if len(keys) == 1:
                axe = axarr
            else:
                axe = axarr[ind2]
            axe.plot(data[database][key][0], data[database][key][1],
                 '.',  markersize=1, label=database+':'+key)
            #axe.plot(data[database][key][0], data[database][key][1],
            #     'gray',  markersize=1, label=database+':'+key)
            axe.legend()
            axe.grid(b=True)

# %% Save
#data_temp = copy.deepcopy(data['rf_oscillators/Rb_time_tag']['ns'])
#data_temp[0] = [dt.timestamp() for dt in data_temp[0]]
#data_temp = np.array(data_temp)
#np.save(r'C:\Users\National Institute\Pictures\Plots 18-06-06\rf-oscillators_Rb-time-tag', data_temp)

#data_temp = copy.deepcopy([[spectrum['x'], spectrum['y'], spectrum['y_std'], data[database]['data'][0][idx].timestamp()] for idx,spectrum in enumerate(data[database]['data'][1])])
#data_temp = np.array(data_temp)
#np.save(r'C:\Users\National Institute\Pictures\Plots 18-06-06\spectral-shaper_spectrum', data_temp)

#data_temp = copy.deepcopy(data['spectral_shaper/mask']['path'])
#data_temp[0] = [dt.timestamp() for dt in data_temp[0]]
#data_temp = np.array(data_temp)
#np.save(r'C:\Users\National Institute\Pictures\Plots 18-06-06\spectral-shapers_mask', data_temp)

# %% 
#start = 0
#stop = -1
#db = 'ambience/rack_temperature_0'
#freqs = np.fft.rfftfreq(len(data[db]['_timestamp'][start:stop]), d=np.mean(np.diff(data[db]['_timestamp'][start:stop])).total_seconds())
#amps = np.fft.rfft((data[db]['V'][start:stop]-np.mean(data[db]['V'][start:stop]))*np.hanning(len(data[db]['V'][start:stop])))
#
#plt.clf()
#plt.plot(freqs*60*60, np.abs(amps)**2)
