# -*- coding: utf-8 -*-
"""
Created on Thu Jul 26 16:09:31 2018

@author: cdf1
"""

# spectral_shaper ---------------------------------------------------------
    # Data ----------------------------------
'spectral_shaper/DW',
'spectral_shaper/mask',
'spectral_shaper/spectrum',
    # Devices -------------------------------
'spectral_shaper/device_OSA',
    # States --------------------------------
'spectral_shaper/state_SLM',
'spectral_shaper/state_optimizer',
'spectral_shaper/control',




# %% Modules
from analysis import helper_functions as hf

import datetime
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.dates import MonthLocator



from Drivers.Database import MongoDB

# %% Start/Stop Time
#--- Start
start_time = None
#start_time = datetime.datetime(2018, 5, 1)
#start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=4.5)
#start_time = datetime.datetime.utcnow() - datetime.timedelta(days=2)

#--- Stop
stop_time = None
#stop_time = datetime.datetime(2019, 5, 1)
#stop_time = datetime.datetime.utcnow()


# %% Constants

lens_loss = {'LMH-50X-1064':.39, 'M-60x':1.25, 'LMH-20x-1064':0.03}


# %% Data
header = []

mongo_client = MongoDB.MongoClient()
spc_data = {}
try:
    # Mask Data -----------------------------------------------------
    spc_data['mask'] = []
    database = 'spectral_shaper/mask'
    db = MongoDB.DatabaseRead(mongo_client, database)
    cursor = db.read_record(start_time, stop_time)
    for doc in cursor:
        spc_data['mask'].append({'mask':'top' in doc['path'], 'time':doc['_timestamp']})
    spc_data['mask'] = pd.DataFrame(spc_data['mask'])
    # Spectrum Data -------------------------------------------------
    spc_data['x'] = []
    spc_data['y'] = []
    spc_data['y_std'] = []
    database = 'spectral_shaper/spectrum'
    db = MongoDB.DatabaseRead(mongo_client, database)
    cursor = db.read_record(start_time, stop_time)
    for doc in cursor:
        spc_data['x'].append(doc['data']['x'] if isinstance(doc['data']['x'],list) else [np.nan])
        spc_data['y'].append(doc['data']['y'] if isinstance(doc['data']['y'],list) else [np.nan])
        spc_data['y_std'].append(doc['data']['y_std'] if isinstance(doc['data']['y_std'],list) else [np.nan])
        header.append({'time':doc['_timestamp']})
    spc_data['x'] = pd.DataFrame(spc_data['x']).transpose(copy=True) # each column is a OSA trace
    spc_data['y'] = pd.DataFrame(spc_data['y']).apply(hf.dBm_to_W, result_type='broadcast').transpose(copy=True) # linear scale, each column is a OSA trace
    spc_data['y_std'] = pd.DataFrame(spc_data['y_std']).transpose(copy=True) # keep in dB, each column is a OSA trace
    # Dispersive Wave -----------------------------------------------
    spc_data['DW'] = []
    database = 'spectral_shaper/DW'
    db = MongoDB.DatabaseRead(mongo_client, database)
    cursor = db.read_record(start_time, stop_time)
    for doc in cursor:
        spc_data['DW'].append({'dBm':doc['dBm'], 'std':(doc['std'] if "std" in doc else doc["dBm_std"]), 'time':doc['_timestamp']})
    spc_data['DW'] = pd.DataFrame(spc_data['DW'])
finally:
    mongo_client.close()


# Shared Parameters
for info in header:
    info['repetition_rate'] = 30e9

# Convert Header to DataFrame
header = pd.DataFrame(header)
header = header.sort_values(by='time')

header['mask'] = np.nan
for mask_ind in spc_data['mask'].index:
    mask = spc_data['mask'].loc[mask_ind, 'mask']
    mask_start_time = spc_data['mask'].loc[mask_ind, 'time']
    mask_end_time = next(iter(spc_data['mask'].loc[mask_ind+1:, 'time']), header['time'].iloc[-1])
    mask_index = header.loc[((header['time'] > mask_start_time) & (header['time'] <= mask_end_time))].index[1:]
    header.loc[mask_index, 'mask'] = mask
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 6, 15, 3, 23, 30)) & (header['time'] <= datetime.datetime(2018, 6, 15, 12, 16, 50)))].index
header.loc[mask_index, 'mask'] = np.nan
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 6, 19, 18, 30, 13)) & (header['time'] <= datetime.datetime(2018, 6, 20, 0, 2, 30)))].index
header.loc[mask_index, 'mask'] = np.nan
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 7, 3, 16, 56, 50)) & (header['time'] <= datetime.datetime(2018, 7, 4, 0, 10, 12)))].index
header.loc[mask_index, 'mask'] = np.nan
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 11, 28, 18, 30, 0)) & (header['time'] <= datetime.datetime(2018, 11, 28, 23, 40, 0)))].index
header.loc[mask_index, 'mask'] = np.nan
mask_index = header.loc[((header['time'] > datetime.datetime(2019, 1, 8, 16, 45, 0)) & (header['time'] <= datetime.datetime(2019, 1, 8, 23, 45, 0)))].index
header.loc[mask_index, 'mask'] = np.nan

# %% Preliminary Plots
fig, ax0 = hf.plot_setup(0, len(header.index))

#for spectrum in trace:
#    plt.plot(spectrum['data']['x'], spectrum['data']['y'])
#ylim = plt.ylim()
#plt.ylim((ylim[-1]-100, ylim[-1]))
idxs = header['time'][header['mask']==0].sort_values().index
ax0.plot(spc_data['x'].loc[:,idxs], spc_data['y'].loc[:,idxs].apply(hf.dB, result_type='broadcast'))
#ylim = plt.ylim()
#plt.ylim((ylim[-1]-80, ylim[-1]))

ax1 = hf.complementary_x_ticks(ax0, hf.nm_to_THz, nbins=7)

# %% Normalize
def nantrapz(y, x=None, axis=0):
    return np.asarray(np.trapz(np.ma.masked_invalid(y), x=None if x is None else np.ma.masked_invalid(x), axis=axis))

def normalize(x, y, norm, jacobian=1):
    return (y*jacobian).mul(norm/np.abs(nantrapz(y*jacobian, x, axis=0)), axis='columns')

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
    header.loc[:,'output_power'] = np.trapz(spc_data['y'], spc_data['x'], axis=0)
else:
    for idx in derive_output_power.index[derive_output_power]:
        header.loc[idx, 'output_power'] = np.trapz(spc_data['y'].loc[:,idx], spc_data['x'].loc[:,idx])

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
spc_data['x_nm'] = spc_data['x']
spc_data['x_THz'] = hf.nm_to_THz(spc_data['x_nm'])
spc_data['x_mode'] = spc_data['x_THz']*1e12/header['repetition_rate'] # THz * (1e12 Hz)/THz * mode/rep rate(Hz)
# Power -------------------------------------------------------------
# Power/nm
spc_data['y_P/nm'] = spc_data['y'] # P/nm
# Power/THz
spc_data['y_P/THz'] = normalize(spc_data['x_THz'], spc_data['y'], output_power, jacobian=hf.constants.c_nm_ps/spc_data['x_THz']**2) # P/THz = P/nm * c/fr**2
# Power/mode
spc_data['y_P/mode'] = spc_data['y_P/THz'].mul(header['repetition_rate']*1e-12, axis='columns')  # P/mode = P/THz * THz/(1e12 Hz) * rep rate(Hz)/mode
# Energy ------------------------------------------------------------
# Energy/nm
spc_data['y_E/nm'] = spc_data['y_P/nm'].div(header['repetition_rate'], axis='columns') # E/(nm*pulse) = (power/nm)/rep_rate(pulses/s)
# Energy/THz
spc_data['y_E/THz'] = spc_data['y_P/THz'].div(header['repetition_rate'], axis='columns') # E/(nm*pulse) = (power/THz)/rep_rate(pulses/s)
# Energy/mode
spc_data['y_E/mode'] = spc_data['y_P/mode'].div(header['repetition_rate'], axis='columns') # E/(mode*pulse) = (power/mode)*rep_rate(pulses/s)
# Photons per pulse -------------------------------------------------
# Photons/nm
spc_data['y_Ph/nm'] = spc_data['y_E/nm']/(hf.constants.h*hf.constants.c/(spc_data['x_nm']*1e-9)) # N/(nm*pulse) = E/(nm*pulse)/(h c / wl)
# Photons/THz
spc_data['y_Ph/THz'] = spc_data['y_E/THz']/(hf.constants.h*spc_data['x_THz']*1e12) # N/(THz*pulse) = E/(THz*pulse)/(h fr)
# Photons/mode
spc_data['y_Ph/mode'] = spc_data['y_E/mode']/(hf.constants.h*spc_data['x_THz']*1e12) # N/(mode*pulse) = E/(mode*pulse)/(h fr)
# Photons flux ------------------------------------------------------
# Photons/mode/s
spc_data['y_Ph/mode/s'] = spc_data['y_Ph/mode'].mul(header['repetition_rate'], axis='columns') # N/s = N/(mode*pulse) * rep_rate(pulses/s)


# %% Preliminary Plots
fig, ax0 = hf.plot_setup("All Spectra", len(header.index), size=(6.4*1.5, 4.8))

idxs = header['time'][header['mask']==0].sort_values().index

ax0.plot(spc_data['x_THz'].loc[:,idxs]*1e12, spc_data['y_Ph/mode/s'].loc[:,idxs].apply(hf.dB, result_type='broadcast'))


#for idx in header['time'][header['mask']==0].sort_values().index:
#    # Per nm
##    ax0.plot(spc_data['x_nm'].loc[idx]*1e12, spc_data['y_P/nm'].apply(dB, result_type='broadcast'))
##    ax0.plot(spc_data['x_nm'].loc[idx]*1e12, spc_data['y_E/nm'].apply(dB, result_type='broadcast'))
##    ax0.plot(spc_data['x_nm'].loc[idx]*1e12, spc_data['y_Ph/nm'].apply(dB, result_type='broadcast'))
#    # Per THz
##    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_P/THz'].apply(dB, result_type='broadcast'))
##    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_E/THz'].apply(dB, result_type='broadcast'))
##    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_Ph/THz'].apply(dB, result_type='broadcast'))
#    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_Ph/mode/s'].apply(dB, result_type='broadcast'))
#    # Per Mode
##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_P/mode'].apply(dB, result_type='broadcast'))
##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_E/mode'].apply(dB, result_type='broadcast'))
##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_Ph/mode'].apply(dB, result_type='broadcast'))
##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_Ph/mode/s'].apply(dB, result_type='broadcast'))
#    # Flux

#ylim = plt.ylim()
#plt.ylim((ylim[-1]-100, ylim[-1]))
ax0.xaxis.set_major_formatter(ticker.EngFormatter(unit='Hz'))

ax1 = hf.complementary_x_ticks(ax0, hf.m_to_Hz, formatter=ticker.EngFormatter(unit='m'))
plt.tight_layout()

# %% Output Power
fig, ax0 = hf.plot_setup("Output Power", 1, size=(6.4*1.5, 4.8))
ax0.plot(header['time'][header['mask']==0], header['output_power'][header['mask']==0], '.')
ax0.yaxis.set_major_formatter(ticker.EngFormatter(unit='W'))
plt.tight_layout()


# %% Uptime Plot

#--- Calculate
hpf_psb = (spc_data['x_nm'][0] >= 810) & (spc_data['x_nm'][0] <= 1280)
hpf_psb = hpf_psb.index[hpf_psb]

flt_idxs = header['time'][header['mask']==0].sort_values().index

# Integrated Power
norm_power = np.trapz(
    spc_data['y_Ph/mode/s'].loc[hpf_psb, :],
    spc_data['x_mode'].loc[hpf_psb, :],
    axis=0)
norm_power /= np.nanmean(norm_power[flt_idxs])

# Downtime Locations
time_delta = -header['time'].diff(periods=-1)
t_thr = np.array(int(1e9 * 1e4), dtype="timedelta64[ns]")
t_dwt = time_delta.index[time_delta > t_thr]
t_dwt = t_dwt.delete([2,6,7,8,9,10,11])
t_dwt_dt = time_delta.loc[t_dwt]

p_dwt_idxs = np.flatnonzero(norm_power < 0.25)
p_dwt = np.append(0, 1 + np.flatnonzero(np.diff(p_dwt_idxs) > 10))
p_dwt = np.delete(p_dwt, [0])
p_dwt_dt = header['time'].loc[p_dwt_idxs[np.append(p_dwt[1:]-1, -1)]].values - header['time'].loc[p_dwt_idxs[p_dwt]]
p_dwt = p_dwt_idxs[p_dwt]

total_downtime = t_dwt_dt.sum() + p_dwt_dt.sum()
total_time = header['time'].max() - header['time'].min()
print(total_time)
print(total_downtime)
print(total_downtime/total_time)
print(p_dwt_dt.sum())
print(p_dwt_dt.sum()/total_time)


# 2D Spectral Amplitudes
spc_db_diff = spc_data['y_Ph/mode/s'].loc[hpf_psb,flt_idxs].apply(hf.dB, result_type='broadcast')
spc_db_diff = spc_db_diff.sub(spc_db_diff.mean(axis='columns'), axis='index')
spc_db_diff = 10**(spc_db_diff/10)

for dwt_idx in t_dwt:
    spc_db_diff.loc[:, dwt_idx] *= np.NaN

#--- Plot
fig = plt.figure("Spectral Uptime", constrained_layout=True)
fig.clf()
gs = fig.add_gridspec(nrows=20, ncols=20)
ax0 = fig.add_subplot(gs[:9, :-1])
ax1 = fig.add_subplot(gs[9:-1, :-1], sharex=ax0)
ax2 = fig.add_subplot(gs[9:-1, -1])
ax3 = fig.add_subplot(gs[-1, :-1], sharex=ax0)

ax0.plot(header['time'].loc[flt_idxs], norm_power[flt_idxs], '.', markersize=1)
ax0.set_ylabel("Integrated Power")
ax0.set_ylim(bottom=0)
ax0.grid(True, alpha=0.25)

ax3.errorbar(header['time'].loc[t_dwt], np.zeros_like(t_dwt), xerr=[np.zeros_like(t_dwt_dt), t_dwt_dt], fmt='.')
ax3.errorbar(header['time'].loc[p_dwt], np.zeros_like(p_dwt), xerr=[np.zeros_like(p_dwt_dt), p_dwt_dt], fmt='.')

pcolor_cmap = plt.cm.nipy_spectral
pcolor_cmap.set_bad(color='k')
im = ax1.pcolormesh(
    header['time'].loc[flt_idxs],
    1e-3*spc_data['x_nm'].loc[hpf_psb,flt_idxs].mean(axis='columns'),
    spc_db_diff,
    cmap=pcolor_cmap,
    norm=plt.matplotlib.colors.LogNorm(),
    vmin=1/3, vmax=3)
ax1.set_ylabel(r"Wavelength ($\mu$m)")

tck_fmt = ticker.FormatStrFormatter("%.1g")
cbar = fig.colorbar(im, cax=ax2, ticks=[1/3, 0.5, 1, 2, 3], format=tck_fmt)
minorticks = np.arange(.4, 3, .1)
cbar.ax.yaxis.set_ticks(minorticks, minor=True)
cbar.ax.yaxis.set_minor_formatter(ticker.NullFormatter())
cbar.set_label(r"Power / Avg Power")

for label in ax0.xaxis.get_ticklabels():
    label.set_ha('right')
    label.set_rotation(20)
ax1.xaxis.tick_bottom()
for label in ax1.xaxis.get_ticklabels():
    label.set_visible(False)
ax3.xaxis.tick_top()
for label in ax3.xaxis.get_ticklabels():
    label.set_visible(False)
ax3.yaxis.set_ticks([])


# %% All Traces

fig = plt.figure("All Traces")
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
ax0 = plt.subplot2grid((2,1), (0,0))
ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

flat = header['time'][header['mask']==0].sort_values().index
#flat = header['time'][header['mask']==0][header['time']<utc_tz.localize(datetime.datetime(2018, 7, 24))].sort_values().index
#flat = header['time'][header['mask']==0][header['time']>utc_tz.localize(datetime.datetime(2018, 7, 24))].sort_values().index

ax0.plot(spc_data['x_nm'].loc[:,flat], spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast'), color=[31/255, 119/255, 180/255], markersize=1, alpha=0.01)
ax0.plot(spc_data['x_nm'].loc[:,flat].mean(axis='columns'), spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').mean(axis='columns'), color='0', markersize=0.5, alpha=1)

ax1.plot(spc_data['x_nm'].loc[:,flat], spc_data['y_std'].loc[:,flat], color=[31/255, 119/255, 180/255], markersize=1, alpha=0.01)
ax1.plot(spc_data['x_nm'].loc[:,flat].mean(axis='columns'), spc_data['y_std'].loc[:,flat].mean(axis='columns'), color=[31/255, 119/255, 180/255], markersize=1, alpha=1, label='1000s Avg')
ax1.plot(spc_data['x_nm'].loc[:,flat].mean(axis='columns'), spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').std(axis='columns'), color='0', markersize=1, alpha=1, label='Total Avg')

ax1.legend()

ax0.set_ylabel('Amplitude (dBm/nm)')
ax0.grid(b=True)
ax1.set_ylabel('Standard Deviation (dB/nm)')
ax1.set_xlabel('Wavelength (nm)')
ax1.grid(b=True)

plt.tight_layout()
#plt.savefig('long_spectrum.png', dpi=600, transparent=True)

#avg_flat = copy.deepcopy(np.array([data_list[0], data_avg]))

# %% Flat 2D Diff
flat = header['time'][header['mask']==0].sort_values().index

fig = plt.figure("Flat 2D Diff")
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
plt.pcolormesh(header['time'].loc[flat],
               spc_data['x_nm'].loc[:,flat].mean(axis='columns'),
               spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').sub(spc_data['y_P/nm'].loc[:,flat].apply(hf.dB).mean(axis='columns'), axis='index'),
#               hf.gaus_filt(
#                       spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').sub(spc_data['y_P/nm'].loc[:,flat].apply(hf.dB).mean(axis='columns'), axis='index'),
#                       (10, 1),
#                       ),
               cmap=plt.cm.nipy_spectral)#plt.cm.seismic)
plt.clim(-4,4)
plt.ylabel("Wavelength (nm)")
c_bar = plt.colorbar()
c_bar.set_label(r"$\Delta$dB")
fig.autofmt_xdate()
#plt.xlim([736810.5475672083, 736970.9387923519])
#plt.gca().xaxis.set_major_locator(MonthLocator())
#plt.ylim(800, 1300)
plt.tight_layout()


# %% Flat 2D Diff Abs
flat = header['time'][header['mask']==0].sort_values().index

fig = plt.figure("Abs Flat 2D Diff")
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
plt.pcolormesh(header['time'].loc[flat],
               spc_data['x_nm'].loc[:,flat].mean(axis='columns'),
               (spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').sub(spc_data['y_P/nm'].loc[:,flat].apply(hf.dB).mean(axis='columns'), axis='index')).apply(np.abs, result_type='broadcast'),
               cmap=plt.cm.nipy_spectral)
plt.clim(0,4)
plt.ylabel("Wavelength (nm)")
c_bar = plt.colorbar()
c_bar.set_label(r"|$\Delta$dB|")
fig.autofmt_xdate()
#plt.ylim(800, 1300)
#plt.xlim([736810.5475672083, 736970.9387923519])
#plt.gca().xaxis.set_major_locator(MonthLocator())
plt.tight_layout()

# %% Std Dev
flat = header['time'][header['mask']==0].sort_values().index

fig = plt.figure("Flat Std Dev")
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
plt.pcolormesh(header['time'].loc[flat],
               spc_data['x_nm'].loc[:,flat].mean(axis='columns'),
               spc_data['y_std'].loc[:,flat],
               cmap=plt.cm.nipy_spectral)
plt.clim(0,1)
plt.ylabel("Wavelength (nm)")
c_bar = plt.colorbar()
c_bar.set_label(r"dB std")
fig.autofmt_xdate()
#plt.ylim(800, 1300)
#plt.gca().xaxis.set_major_locator(MonthLocator())
plt.tight_layout()

# %% Plot DW
plt.figure("DW")
plt.clf()
fig = plt.gcf()
ax0 = plt.subplot2grid((2,1), (0,0))
ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

ax0.plot(spc_data['DW'].loc[:,'time'], spc_data['DW'].loc[:,'dBm'], '.',  markersize=3)
ax0.set_ylabel('DW Amplitude (dBm/nm)')

ax1.plot(spc_data['DW'].loc[:,'time'], spc_data['DW'].loc[:,'std'], '.',  markersize=3)
ax1.set_ylabel('Std Dev (dB/nm)')

#ax0.axhline(-43.5, linestyle='--', linewidth=1, alpha=0.5, xmax=.39)
#ax0.axhline(-47.5, linestyle='--', linewidth=1, alpha=0.5, xmax=.39)

#ax0.axhline(-44.5, linestyle='--', linewidth=1, alpha=0.5, xmin=.39)
#ax0.axhline(-46.5, linestyle='--', linewidth=1, alpha=0.5, xmin=.39)

#first_of_the_month = [datetime.date(2018, 5, 1), datetime.date(2018, 6, 1), datetime.date(2018, 7, 1), datetime.date(2018, 8, 1), datetime.date(2018, 9, 1)]
#ax0.set_xticks(first_of_the_month)
#ax0.set_xticklabels(first_of_the_month)
#ax0.set_xlim([spc_data['DW'].loc[:,'time'].min(), spc_data['DW'].loc[:,'time'].max()])

fig.autofmt_xdate()
#ax1.xaxis.set_major_locator(MonthLocator())

plt.tight_layout()
#plt.savefig('long_DW.png', dpi=600, transparent=True)

