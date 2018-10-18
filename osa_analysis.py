# -*- coding: utf-8 -*-
"""
Created on Thu Jul 26 16:09:31 2018

@author: cdf1
"""

# %% Modules
import os
import fnmatch
import json

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.dates import MonthLocator
from cycler import cycler

from scipy.ndimage.filters import gaussian_filter, median_filter

from Drivers.Database import MongoDB

import datetime
import pytz
central_tz = pytz.timezone('US/Central')
utc_tz = pytz.utc

utc_to_ct_conv = lambda dt: (utc_tz.localize(dt.replace(tzinfo=None))).astimezone(central_tz)
ct_to_utc_conv = lambda dt: (central_tz.localize(dt.replace(tzinfo=None))).astimezone(utc_tz)

# %% Constants

c = 299792458 #m/s
c_nm_ps = c*1e-3 # nm/ps, or nm THz
h = 6.62607e-34 #J s

lens_loss = {'LMH-50X-1064':.39, 'M-60x':1.25, 'LMH-20x-1064':0.03}

import matplotlib as mpl
mpl.rcParams['savefig.dpi'] = 200


# %% Functions

def med_filt(array, filt_size, num=1):
    for itteration in range(num):
        array = median_filter(array, filt_size)
    return array

def gaus_filt(array, filt_size, num=1):
    for itteration in range(num):
        array = gaussian_filter(array, filt_size)
    return array

import math
def format_eng(num, unit='', places=None, sep=''):
    """ A port from matplotlib.ticker.EngFormatter
    Formats a number in engineering notation, appending a letter
    representing the power of 1000 of the original number.
    Some examples:

    >>> format_eng(0)       # for self.places = 0
    '0'

    >>> format_eng(1000000) # for self.places = 1
    '1.0 M'

    >>> format_eng("-1e-6") # for self.places = 2
    u'-1.00 \N{GREEK SMALL LETTER MU}'

    `num` may be a numeric value or a string that can be converted
    to a numeric value with ``float(num)``.
    """
    # The SI engineering prefixes
    ENG_PREFIXES = {
        -24: "y",
        -21: "z",
        -18: "a",
        -15: "f",
        -12: "p",
         -9: "n",
         -6: "\N{GREEK SMALL LETTER MU}",
         -3: "m",
          0: "",
          3: "k",
          6: "M",
          9: "G",
         12: "T",
         15: "P",
         18: "E",
         21: "Z",
         24: "Y"
    }
    
    dnum = float(num)
    sign = 1
    fmt = "g" if places is None else ".{:d}g".format(places)

    if dnum < 0:
        sign = -1
        dnum = -dnum

    if dnum != 0:
        pow10 = int(math.floor(math.log10(dnum) / 3) * 3)
    else:
        pow10 = 0
        # Force dnum to zero, to avoid inconsistencies like
        # format_eng(-0) = "0" and format_eng(0.0) = "0"
        # but format_eng(-0.0) = "-0.0"
        dnum = 0.0

    pow10 = np.clip(pow10, min(ENG_PREFIXES), max(ENG_PREFIXES))

    mant = sign * dnum / (10.0 ** pow10)
    # Taking care of the cases like 999.9..., which
    # may be rounded to 1000 instead of 1 k.  Beware
    # of the corner case of values that are beyond
    # the range of SI prefixes (i.e. > 'Y').
    _fmant = float("{mant:{fmt}}".format(mant=mant, fmt=fmt))
    if _fmant >= 1000 and pow10 != max(ENG_PREFIXES):
        mant /= 1000
        pow10 += 3

    prefix = ENG_PREFIXES[int(pow10)]

    formatted = "{mant:{fmt}}{sep}{prefix}{unit}".format(
        mant=mant, sep=sep, prefix=prefix, unit=unit, fmt=fmt)

    return formatted

def nm_to_THz(x):
    return c_nm_ps/x # nm to THz

def m_to_Hz(x):
    return c/x # m to Hz

def dB(x):
    return 10.*np.log10(x)

def dBm_to_W(x):
    return 1e-3*10**(x/10)

# Plotting Helpers ------------------------------------------------------------
def plot_setup(fig_ind, count, start=0, stop=.95, size=None, dpi=None, tight=True, clear=True, r_color=False):
    plt.figure(fig_ind, clear=clear)
    fig = plt.gcf()
    ax = plt.gca()
    # Color Cyler
    if r_color:
        colormap = plt.cm.nipy_spectral_r
        r_start = 1-stop
        r_stop = 1-start
        start = r_start
        stop = r_stop
    else:
        colormap = plt.cm.nipy_spectral
    ax.set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(start, stop, count)]))
    # Size in Inches
    if not(size is None):
        fig.set_size_inches(size)
    # DPI
    if not(dpi is None):
        fig.set_dpi(dpi)
    # Tight Layout
    fig.set_tight_layout(tight)
    return (fig, ax)

def nonlinear_formatter(__call__, transform, inverse_transform=None):
    '''A decorator for "matplotlib.ticker.Formatter.__call__" method.    
    '''
    if inverse_transform is None:
        inverse_transform = transform
    def wrapper(x, pos=None):
        x = transform(x)
        return __call__(x, pos=pos)
    return wrapper

def nonlinear_locator(tick_values, transform, inverse_transform=None):
    '''A decorator for "matplotlib.ticker.Locator.tick_values" method.
    '''
    if inverse_transform is None:
        inverse_transform = transform
    def wrapper(vmin, vmax):
        vlims = transform(np.array([vmin, vmax]))
        vlims.sort()
        return inverse_transform(tick_values(vlims[0], vlims[1]))
    return wrapper

def patch_call(instance, func):
    '''Overrides the "__call__" method of "instance" with "func".
    https://stackoverflow.com/a/38541437
    '''
    class _(type(instance)):
        def __call__(self, *arg, **kwarg):
           return func(*arg, **kwarg)
    instance.__class__ = _

def complementary_x_ticks(old_axis, transform, inverse_transform=None, formatter=None, locator=None, nbins=None):
    '''A convenience function that generates a new x axis with major tick marks
    on complementary units. Best called after the original plot has been
    finalized. Returns the new axes object.
    
    old_axis:
        a matplotlib axes object (plt.gca())
    transform(x):
        The transform function
    inverse_transform(x):
        The inverse of the conversion function:
            inverse_transform(transform(x)) == x.
        If None, it is assumed that conv_func is its own inverse:
            transform(transform(x)) == x
    formator:
        A "matplotlib.ticker.Formatter" object
    locator:
        A "matplotlib.ticker.Locator" object
    '''
# Inverse Function
    if (inverse_transform is None):
        inverse_transform = transform
# New Axis
    new_axis = old_axis.twiny()
# Formatter
    if formatter is None:
        formatter = new_axis.xaxis.get_major_formatter()
    patch_call(formatter, nonlinear_formatter(formatter.__call__, transform, inverse_transform=inverse_transform))
    new_axis.xaxis.set_major_formatter(formatter)
# Locator
    if (locator is None):
        locator = new_axis.xaxis.get_major_locator()
    locator.tick_values = nonlinear_locator(locator.tick_values, transform, inverse_transform=inverse_transform)
    new_axis.xaxis.set_major_locator(locator)
# Limits
    old_xlim = old_axis.get_xlim()
    new_axis.set_xlim(old_xlim)
# Number of Bins
    if not(nbins is None):
        new_axis.locator_params(axis='x', nbins=nbins)
    return new_axis


# %% Data
header = []

start_time = ct_to_utc_conv(datetime.datetime(2018, 5, 1, 0, 0))
stop_time = utc_tz.localize(datetime.datetime.utcnow())
#start_time = stop_time - datetime.timedelta(days=2*7)

mongo_client = MongoDB.MongoClient()
data = {}
try:
    # Mask Data -----------------------------------------------------
    data['mask'] = []
    database = 'spectral_shaper/mask'
    db = MongoDB.DatabaseRead(mongo_client, database)
    cursor = db.read_record(start_time, stop_time)
    for doc in cursor:
        data['mask'].append({'mask':'top' in doc['path'], 'time':doc['_timestamp']})
    data['mask'] = pd.DataFrame(data['mask'])
    # Spectrum Data -------------------------------------------------
    data['x'] = []
    data['y'] = []
    data['y_std'] = []
    database = 'spectral_shaper/spectrum'
    db = MongoDB.DatabaseRead(mongo_client, database)
    cursor = db.read_record(start_time, stop_time)
    for doc in cursor:
        data['x'].append(doc['data']['x'] if isinstance(doc['data']['x'],list) else [np.nan])
        data['y'].append(doc['data']['y'] if isinstance(doc['data']['y'],list) else [np.nan])
        data['y_std'].append(doc['data']['y_std'] if isinstance(doc['data']['y_std'],list) else [np.nan])
        header.append({'time':doc['_timestamp']})
    data['x'] = pd.DataFrame(data['x']).transpose(copy=True) # each column is a OSA trace
    data['y'] = pd.DataFrame(data['y']).apply(dBm_to_W, result_type='broadcast').transpose(copy=True) # linear scale, each column is a OSA trace
    data['y_std'] = pd.DataFrame(data['y_std']).transpose(copy=True) # keep in dB, each column is a OSA trace
    # Dispersive Wave -----------------------------------------------
    data['DW'] = []
    database = 'spectral_shaper/DW'
    db = MongoDB.DatabaseRead(mongo_client, database)
    cursor = db.read_record(start_time, stop_time)
    for doc in cursor:
        data['DW'].append({'dBm':doc['dBm'], 'std':doc['std'], 'time':doc['_timestamp']})
    data['DW'] = pd.DataFrame(data['DW'])
finally:
    mongo_client.close()


# Shared Parameters
for info in header:
    info['repetition_rate'] = 30e9

# Convert Header to DataFrame
header = pd.DataFrame(header)
header = header.sort_values(by='time')

header['mask'] = np.nan
for mask_ind in data['mask'].index:
    mask = data['mask'].loc[mask_ind, 'mask']
    mask_start_time = data['mask'].loc[mask_ind, 'time']
    mask_end_time = next(iter(data['mask'].loc[mask_ind+1:, 'time']), header['time'].iloc[-1])
    mask_index = header.loc[((header['time'] > mask_start_time) & (header['time'] <= mask_end_time))].index[1:]
    header.loc[mask_index, 'mask'] = mask
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 6, 15, 3, 23, 30)) & (header['time'] <= datetime.datetime(2018, 6, 15, 12, 16, 50)))].index
header.loc[mask_index, 'mask'] = np.nan
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 6, 19, 18, 30, 13)) & (header['time'] <= datetime.datetime(2018, 6, 20, 0, 2, 30)))].index
header.loc[mask_index, 'mask'] = np.nan
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 7, 3, 16, 56, 50)) & (header['time'] <= datetime.datetime(2018, 7, 4, 0, 10, 12)))].index
header.loc[mask_index, 'mask'] = np.nan


# %% Preliminary Plots
fig, ax0 = plot_setup(0, len(header.index))

#for spectrum in trace:
#    plt.plot(spectrum['data']['x'], spectrum['data']['y'])
#ylim = plt.ylim()
#plt.ylim((ylim[-1]-100, ylim[-1]))
idxs = header['time'][header['mask']==0].sort_values().index
ax0.plot(data['x'].loc[:,idxs], data['y'].loc[:,idxs].apply(dB, result_type='broadcast'))
#ylim = plt.ylim()
#plt.ylim((ylim[-1]-80, ylim[-1]))

ax1 = complementary_x_ticks(ax0, nm_to_THz, nbins=7)

# %% Normalize
def normalize(x, y, norm, jacobian=1):
    return (y*jacobian).mul(norm/np.abs(np.trapz(y, x, axis=0)), axis='columns')

# Fill in missing values
if not('input_power' in header):
    header['input_power'] = np.nan
if not('output_power' in header):
    header['output_power'] = np.nan
if not('repetition_rate' in header):
    header['repetition_rate'] = np.nan
if not('input_coupling' in header):
    header['input_coupling'] = np.nan
if not('output_coupling' in header):
    header['output_coupling'] = np.nan

derive_output_power = header['output_power'].isna()
if derive_output_power.all():
    header.loc[:,'output_power'] = np.trapz(data['y'], data['x'], axis=0)
else:
    for idx in derive_output_power.index[derive_output_power]:
        header.loc[idx, 'output_power'] = np.trapz(data['y'].loc[:,idx], data['x'].loc[:,idx])

# Add loss to input coupling
lens_loss_data = header['input_coupling'].isin(lens_loss)
header['adj_input_power'] = np.nan
for idx in lens_loss_data.index[lens_loss_data]:
    header.loc[idx,'adj_input_power'] = header.loc[idx,'input_power']*10.**(-lens_loss[header.loc[idx,'input_coupling']]/10.)

# Remove loss from output coupling
lens_loss_data = header['output_coupling'].isin(lens_loss)
header['adj_output_power'] = np.nan
for idx in lens_loss_data.index[lens_loss_data]:
    header.loc[idx,'adj_output_power'] = header.loc[idx,'output_power']*10.**(lens_loss[header.loc[idx,'output_coupling']]/10.)

# Pulse Energy
header['input_energy'] = header['input_power']/header['repetition_rate']
header['adj_input_energy'] = header['adj_input_power']/header['repetition_rate']
header['output_energy'] = header['output_power']/header['repetition_rate']
header['adj_output_energy'] = header['adj_output_power']/header['repetition_rate']

# Coupling Efficiency
header['coupling_efficiency'] = header['output_power']/header['input_power']
header['adj_coupling_efficiency'] = header['adj_output_power']/header['adj_input_power']

# Normalize Spectral Data
output_power = header['adj_output_power'].where(header['adj_output_power'].notna(), other=header['output_power'])
output_energy = header['adj_output_energy'].where(header['adj_output_energy'].notna(), other=header['output_energy'])
## Frequency Axis
data['x_nm'] = data['x']
data['x_THz'] = nm_to_THz(data['x_nm'])
data['x_mode'] = data['x_THz']*1e12/header['repetition_rate'] # THz * (1e12 Hz)/THz * mode/rep rate(Hz)
# Power -------------------------------------------------------------
# Power/nm
data['y_P/nm'] = data['y'] # P/nm
# Power/THz
data['y_P/THz'] = normalize(data['x_THz'], data['y'], output_power, jacobian=c_nm_ps/data['x_THz']**2) # P/THz = P/nm * c/fr**2
# Power/mode
data['y_P/mode'] = data['y_P/THz'].mul(header['repetition_rate']*1e-12, axis='columns')  # P/mode = P/THz * THz/(1e12 Hz) * rep rate(Hz)/mode
# Energy ------------------------------------------------------------
# Energy/nm
data['y_E/nm'] = data['y_P/nm'].div(header['repetition_rate'], axis='columns') # E/(nm*pulse) = (power/nm)/rep_rate(pulses/s)
# Energy/THz
data['y_E/THz'] = data['y_P/THz'].div(header['repetition_rate'], axis='columns') # E/(nm*pulse) = (power/THz)/rep_rate(pulses/s)
# Energy/mode
data['y_E/mode'] = data['y_P/mode'].div(header['repetition_rate'], axis='columns') # E/(mode*pulse) = (power/mode)*rep_rate(pulses/s)
# Photons per pulse -------------------------------------------------
# Photons/nm
data['y_Ph/nm'] = data['y_E/nm']/(h*c/(data['x_nm']*1e-9)) # N/(nm*pulse) = E/(nm*pulse)/(h c / wl)
# Photons/THz
data['y_Ph/THz'] = data['y_E/THz']/(h*data['x_THz']*1e12) # N/(THz*pulse) = E/(THz*pulse)/(h fr)
# Photons/mode
data['y_Ph/mode'] = data['y_E/mode']/(h*data['x_THz']*1e12) # N/(mode*pulse) = E/(mode*pulse)/(h fr)
# Photons flux ------------------------------------------------------
# Photons/mode/s
data['y_Ph/mode/s'] = data['y_Ph/mode'].mul(header['repetition_rate'], axis='columns') # N/s = N/(mode*pulse) * rep_rate(pulses/s)


# %% Preliminary Plots
fig, ax0 = plot_setup(1, len(header.index), size=(6.4*1.5, 4.8))

idxs = header['time'][header['mask']==0].sort_values().index

ax0.plot(data['x_THz'].loc[:,idxs]*1e12, data['y_Ph/mode/s'].loc[:,idxs].apply(dB, result_type='broadcast'))


#for idx in header['time'][header['mask']==0].sort_values().index:
#    # Per nm
##    ax0.plot(data['x_nm'].loc[idx]*1e12, data['y_P/nm'].apply(dB, result_type='broadcast'))
##    ax0.plot(data['x_nm'].loc[idx]*1e12, data['y_E/nm'].apply(dB, result_type='broadcast'))
##    ax0.plot(data['x_nm'].loc[idx]*1e12, data['y_Ph/nm'].apply(dB, result_type='broadcast'))
#    # Per THz
##    ax0.plot(data['x_THz']*1e12, data['y_P/THz'].apply(dB, result_type='broadcast'))
##    ax0.plot(data['x_THz']*1e12, data['y_E/THz'].apply(dB, result_type='broadcast'))
##    ax0.plot(data['x_THz']*1e12, data['y_Ph/THz'].apply(dB, result_type='broadcast'))
#    ax0.plot(data['x_THz']*1e12, data['y_Ph/mode/s'].apply(dB, result_type='broadcast'))
#    # Per Mode
##    ax0.plot(data['x_mode']*1e12, data['y_P/mode'].apply(dB, result_type='broadcast'))
##    ax0.plot(data['x_mode']*1e12, data['y_E/mode'].apply(dB, result_type='broadcast'))
##    ax0.plot(data['x_mode']*1e12, data['y_Ph/mode'].apply(dB, result_type='broadcast'))
##    ax0.plot(data['x_mode']*1e12, data['y_Ph/mode/s'].apply(dB, result_type='broadcast'))
#    # Flux
    
#ylim = plt.ylim()
#plt.ylim((ylim[-1]-100, ylim[-1]))
ax0.xaxis.set_major_formatter(ticker.EngFormatter(unit='Hz'))

ax1 = complementary_x_ticks(ax0, m_to_Hz, formatter=ticker.EngFormatter(unit='m'))
plt.tight_layout()

# %% Output Power
fig, ax0 = plot_setup(1, 1, size=(6.4*1.5, 4.8))
ax0.plot(header['time'][header['mask']==0], header['output_power'][header['mask']==0], '.')
ax0.yaxis.set_major_formatter(ticker.EngFormatter(unit='W'))
plt.tight_layout()

# %% All Traces

fig = plt.figure(2)
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
ax0 = plt.subplot2grid((2,1), (0,0))
ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

flat = header['time'][header['mask']==0].sort_values().index
#flat = header['time'][header['mask']==0][header['time']<utc_tz.localize(datetime.datetime(2018, 7, 24))].sort_values().index
#flat = header['time'][header['mask']==0][header['time']>utc_tz.localize(datetime.datetime(2018, 7, 24))].sort_values().index

ax0.plot(data['x_nm'].loc[:,flat], data['y_P/nm'].loc[:,flat].apply(dB, result_type='broadcast'), color=[31/255, 119/255, 180/255], markersize=1, alpha=0.01)
ax0.plot(data['x_nm'].loc[:,flat].mean(axis='columns'), data['y_P/nm'].loc[:,flat].apply(dB, result_type='broadcast').mean(axis='columns'), color='0', markersize=0.5, alpha=1)

ax1.plot(data['x_nm'].loc[:,flat], data['y_std'].loc[:,flat], color=[31/255, 119/255, 180/255], markersize=1, alpha=0.01)
ax1.plot(data['x_nm'].loc[:,flat].mean(axis='columns'), data['y_std'].loc[:,flat].mean(axis='columns'), color=[31/255, 119/255, 180/255], markersize=1, alpha=1, label='1000s Avg')
ax1.plot(data['x_nm'].loc[:,flat].mean(axis='columns'), data['y_P/nm'].loc[:,flat].apply(dB, result_type='broadcast').std(axis='columns'), color='0', markersize=1, alpha=1, label='Total Avg')

ax1.legend()

ax0.set_ylabel('Amplitude (dBm/nm)')
ax0.grid(b=True)
ax1.set_ylabel('Standard Deviation (dB/nm)')
ax1.set_xlabel('Wavelength (nm)')
ax1.grid(b=True)

plt.tight_layout()
plt.savefig('long_spectrum.png', dpi=600, transparent=True)

#avg_flat = copy.deepcopy(np.array([data_list[0], data_avg]))

# %% Flat 2D Diff
flat = header['time'][header['mask']==0].sort_values().index

fig = plt.figure(3)
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
plt.pcolormesh(header['time'].loc[flat], data['x_nm'].loc[:,flat].mean(axis='columns'), data['y_P/nm'].loc[:,flat].apply(dB, result_type='broadcast').sub(data['y_P/nm'].loc[:,flat].apply(dB, result_type='broadcast').mean(axis='columns'), axis='index'), cmap='cividis')
plt.clim(-2,2)
c_bar = plt.colorbar()
fig.autofmt_xdate()
#plt.gca().xaxis.set_major_locator(MonthLocator())
plt.tight_layout()

# %%
flat = header['time'][header['mask']==0].sort_values().index

fig = plt.figure(4)
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
plt.pcolormesh(header['time'].loc[flat], data['x_nm'].loc[:,flat].mean(axis='columns'), data['y_std'].loc[:,flat], cmap='cividis')
plt.clim(0,1)
c_bar = plt.colorbar()
fig.autofmt_xdate()
#plt.gca().xaxis.set_major_locator(MonthLocator())
plt.tight_layout()

# %% Plot DW
plt.figure(5)
plt.clf()
fig = plt.gcf()
ax0 = plt.subplot2grid((2,1), (0,0))
ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

ax0.plot(data['DW'].loc[:,'time'], data['DW'].loc[:,'dBm'], '.',  markersize=3)
ax0.set_ylabel('DW Amplitude (dBm/nm)')

ax1.plot(data['DW'].loc[:,'time'], data['DW'].loc[:,'std'], '.',  markersize=3)
ax1.set_ylabel('Std Dev (dB/nm)')

ax0.axhline(-43.5, linestyle='--', linewidth=1, alpha=0.5, xmax=.39)
ax0.axhline(-47.5, linestyle='--', linewidth=1, alpha=0.5, xmax=.39)

ax0.axhline(-44.5, linestyle='--', linewidth=1, alpha=0.5, xmin=.39)
ax0.axhline(-46.5, linestyle='--', linewidth=1, alpha=0.5, xmin=.39)

#first_of_the_month = [datetime.date(2018, 5, 1), datetime.date(2018, 6, 1), datetime.date(2018, 7, 1), datetime.date(2018, 8, 1), datetime.date(2018, 9, 1)]
#ax0.set_xticks(first_of_the_month)
#ax0.set_xticklabels(first_of_the_month)
#ax0.set_xlim([data['DW'].loc[:,'time'].min(), data['DW'].loc[:,'time'].max()])

fig.autofmt_xdate()
ax1.xaxis.set_major_locator(MonthLocator())

plt.tight_layout()
plt.savefig('long_DW.png', dpi=600, transparent=True)

