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
start_time = central_tz.localize(datetime.datetime(2018, 5, 1, 0, 0))
stop_time = central_tz.localize(datetime.datetime.now())
#start_time = stop_time - datetime.timedelta(days=2*7)
DBs = {
    # ambience ----------------------------------------------------------------
    'ambience/box_temperature_0':{
            'start':start_time,
            'stop':stop_time,
            'keys':{
                    'V':lambda v: v*100,
                    'std':lambda v: v*100}},
    'ambience/box_temperature_1':{
            'start':start_time,
            'stop':stop_time,
            'keys':{
                    'V':lambda v: v*100,
                    'std':lambda v: v*100}},
    'ambience/rack_temperature_0':{
            'start':start_time,
            'stop':stop_time,
            'keys':{
                    'V':lambda v: v*100,
                    'std':lambda v: v*100}},
#    # broadening_stage --------------------------------------------------------
    'broadening_stage/device_rotation_mount':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                    'position':lambda p: p}},
#    # comb_generator ----------------------------------------------------------
    'comb_generator/IM_bias':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                   'V':lambda v: v,
                   'std':lambda v: v}},
    # cw_laser ----------------------------------------------------------------
#    'cw_laser/dac_limits':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'min_V':lambda v: v,
#                    'max_V':lambda v: v,
#                    'min_std':lambda v: v,
#                    'max_std':lambda v: v}},
    'cw_laser/dac_output':{
            'start':start_time, 'stop':stop_time,
            'keys':{
                    'V':lambda v: v,
                    'std':lambda v: v}},
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
#    'spectral_shaper/DW_vs_IM_bias':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'V':lambda v: v,
#                    'dBm':lambda dw: dw}},
#    'spectral_shaper/DW_vs_waveplate_angle':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'deg':lambda d: d,
#                    'dBm':lambda dw: dw}},
#    'spectral_shaper/mask':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'path':lambda p: 'top' in p}},
#    'spectral_shaper/spectrum':{
#            'start':start_time, 'stop':stop_time,
#            'keys':{
#                    'data':lambda d: {'x':d['x'], 'y':d['y'], 'y_std':d['y_std']}}},
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
        data_temp = list(zip(data[database]['V'][1],data[database]['dBm'][1], data[database]['dBm'][0]))
        plt.figure()
        plt.title(database)
        ax1 = plt.subplot2grid((4,1),(0,0), rowspan=3)
        ax2 = plt.subplot2grid((4,1),(3,0))
        colormap = plt.cm.spectral
        ax1.set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(0, 0.95, len(data_temp))]))
        ax2.set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(0, 0.95, len(data_temp))]))
        for ind2, data_list in enumerate(data_temp):
            ax1.plot(data_list[0], data_list[1], '.', markersize=10)#, label=data[database]['deg'][0][ind2])
            ax2.plot(data_list[2], 0, '.', markersize=10)
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
    elif database == 'spectral_shaper/DW_vs_waveplate_angle':
        data_temp = list(zip(data[database]['deg'][1],data[database]['dBm'][1],data[database]['dBm'][0]))
        plt.figure()
        plt.title(database)
        ax1 = plt.subplot2grid((4,1),(0,0), rowspan=3)
        ax2 = plt.subplot2grid((4,1),(3,0))
        colormap = plt.cm.spectral
        ax1.set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(0, 0.95, len(data_temp))]))
        ax2.set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(0, 0.95, len(data_temp))]))
        for ind2, data_list in enumerate(data_temp):
            ax1.plot(data_list[0], data_list[1], '.', markersize=10)#, label=data[database]['deg'][0][ind2])
            ax2.plot(data_list[2], 0, '.', markersize=10)
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
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
                axarr[0].plot(data_list[0], data_list[1], markersize=1)#, label=data[database]['data'][0][ind3])
            except:
                axarr[0].plot(data_list[0], np.array(data_list[0])*np.nan, '.', markersize=1)#, label=data[database]['data'][0][ind3])
            try:
                len(data_list[0])==len(data_list[2])
                axarr[1].plot(data_list[0], data_list[2], markersize=1)#, label=data[database]['data'][0][ind3])
            except:
                axarr[1].plot(data_list[0], np.array(data_list[0])*np.nan, '.', markersize=1)#, label=data[database]['data'][0][ind3])
        axarr[0].set_title(database+':y')
        axarr[0].grid(b=True)
        axarr[1].set_title(database+':y_std')
        axarr[1].grid(b=True)
            #2D plot
        plt.figure()
        
        specs_2D = []
        y_data = []
        for ind3, data_list in enumerate(data_temp):
            try:
                len(data_list[0])==len(data_list[1])
                specs_2D.append(np.array([data_list[0], data_list[1]]))
                y_data.append(data_list[3])
            except:
                pass
        plt_specs_2D = np.flipud(np.vstack(list(zip(*specs_2D))[1]))
        wvl_samp = np.mean(list(zip(*specs_2D))[0],axis=0)
#        names = np.flipud(zip(*file_data)[1])
#        y_data = np.linspace(0,1,count+1)
#        y_diff = np.mean(np.ediff1d(y_data))
#        y_ticks = np.arange(y_diff/2., 1+y_diff/2, y_diff)
        plt.pcolormesh(wvl_samp, y_data, plt_specs_2D, cmap='nipy_spectral')
        c_map = plt.get_cmap('nipy_spectral')
        c_map.set_bad(color='k', alpha = 1)
        c_bar = plt.colorbar()
        c_bar.set_label('Amplitude (dBm/nm)')
        plt.axis("tight")
#        plt.yticks(y_ticks[cmap_select], names[cmap_select])
        plt.xlabel('Wavelength (nm)')
#        plt.title(sub_name+': '+group_ident)
        plt.tight_layout()
    elif database == 'broadening_stage/device_rotation_mount':
        f, axarr = plt.subplots(2, sharex=True)
        f.autofmt_xdate()
        axe = axarr[0]
        key = 'position'
        axe.plot(data[database][key][0], data[database][key][1],
             '.',  markersize=1, label=database+':'+key)
        axe.legend()
        axe.grid(b=True)
        axe = axarr[1]
        axe.plot(data[database][key][0], 1-np.cos(np.pi/180*2*(52-np.array(data[database][key][1])))**2,
             '.',  markersize=1, label='transmission')
        axe.legend()
        axe.grid(b=True)
    else: # sAll other data
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

#data_temp = copy.deepcopy([[spectrum['x'], spectrum['y'], spectrum['y_std'], data['spectral_shaper/spectrum']['data'][0][idx].timestamp()] for idx,spectrum in enumerate(data['spectral_shaper/spectrum']['data'][1])])
#data_temp = np.array(data_temp)
#np.save(r'C:\Users\National Institute\Pictures\Plots 18-07-02\spectral-shaper_spectrum', data_temp)
#
#data_temp = copy.deepcopy(data['spectral_shaper/mask']['path'])
#data_temp[0] = [dt.timestamp() for dt in data_temp[0]]
#data_temp = np.array(data_temp)
#np.save(r'C:\Users\National Institute\Pictures\Plots 18-07-02\spectral-shaper_mask', data_temp)
#
#data_temp = copy.deepcopy(data['spectral_shaper/DW'])
#data_temp['dBm'][0] = [dt.timestamp() for dt in data_temp['dBm'][0]]
#data_temp['std'][0] = [dt.timestamp() for dt in data_temp['std'][0]]
#data_temp = np.array([data_temp['dBm'], data_temp['std']])
#np.save(r'C:\Users\National Institute\Pictures\Plots 18-07-02\spectral-shaper_DW', data_temp)

