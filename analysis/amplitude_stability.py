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
import colorcet

from Drivers.Database import MongoDB

# %% Constants

lens_loss = {'LMH-50X-1064':.39, 'M-60x':1.25, 'LMH-20x-1064':0.03}
utc = datetime.timezone.utc

# %%
plt.rcParams['savefig.dpi'] = 600
plt.rcParams['savefig.bbox'] = 'tight'

# %% Start/Stop Time
#--- Start
start_time = None
# start_time = datetime.datetime(2018, 5, 1)
# start_time = datetime.datetime(2018, 10, 20)
# start_time = datetime.datetime(2020, 3, 1)
# start_time = datetime.datetime.utcnow() - datetime.timedelta(days=2)
# start_time = datetime.datetime.utcnow() - datetime.timedelta(weeks=2)

#--- Stop
stop_time = None
#stop_time = datetime.datetime(2019, 5, 1)
#stop_time = datetime.datetime.utcnow()


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
    spc_data['y'] = hf.dBm_to_W(pd.DataFrame(spc_data['y'])).transpose(copy=True) # linear scale, each column is a OSA trace
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

# %% SLM Masks
header['mask'] = np.nan # initialize masks
for mask_ind in spc_data['mask'].index:
    mask = spc_data['mask'].loc[mask_ind, 'mask']
    mask_start_time = spc_data['mask'].loc[mask_ind, 'time']
    mask_end_time = next(iter(spc_data['mask'].loc[mask_ind+1:, 'time']), header['time'].iloc[-1])
    mask_index = header.loc[((header['time'] > mask_start_time) & (header['time'] <= mask_end_time))].index[1:]
    header.loc[mask_index, 'mask'] = mask # set known masks

#---- Mask Failures (but OK spectral generation)
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 6, 15, 3, 23, 30, tzinfo=utc)) & (header['time'] <= datetime.datetime(2018, 6, 15, 12, 16, 50, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # seconds=32000
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 6, 19, 18, 30, 13, tzinfo=utc)) & (header['time'] <= datetime.datetime(2018, 6, 20, 0, 2, 30, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # seconds=19937
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 7, 3, 16, 56, 50, tzinfo=utc)) & (header['time'] <= datetime.datetime(2018, 7, 4, 0, 10, 12, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # seconds=26002
mask_index = header.loc[((header['time'] > datetime.datetime(2018, 11, 28, 18, 30, 0, tzinfo=utc)) & (header['time'] <= datetime.datetime(2018, 11, 28, 23, 40, 0, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # seconds=18600
mask_index = header.loc[((header['time'] > datetime.datetime(2019, 1, 8, 16, 45, 0, tzinfo=utc)) & (header['time'] <= datetime.datetime(2019, 1, 8, 23, 45, 0, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # seconds=25200
mask_index = header.loc[((header['time'] > datetime.datetime(2021, 6, 14, 21, 0, 0, tzinfo=utc)) & (header['time'] <= datetime.datetime(2021, 6, 22, 3, 0, 0, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # days=7, seconds=21600
mask_index = header.loc[((header['time'] > datetime.datetime(2021, 8, 24, 17, 0, 0, tzinfo=utc)) & (header['time'] <= datetime.datetime(2021, 8, 24, 22, 15, 0, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # seconds=18900

#---- Mystery (computer restart fixed the problem)
mask_index = header.loc[((header['time'] > datetime.datetime(2020, 6, 6, 19, 0, 0, tzinfo=utc)) & (header['time'] <= datetime.datetime(2020, 6, 8, 16, 0, 0, tzinfo=utc)))].index
header.loc[mask_index, 'mask'] = np.nan # spectra a bit high throughout, days=1, seconds=75600


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
# fig, ax0 = hf.plot_setup("All Spectra", len(header.index), size=(6.4*1.5, 4.8))

# idxs = header['time'][header['mask']==0].sort_values().index

# ax0.plot(spc_data['x_THz'].loc[:,idxs]*1e12, spc_data['y_Ph/mode/s'].loc[:,idxs].apply(hf.dB, result_type='broadcast'))


# #for idx in header['time'][header['mask']==0].sort_values().index:
# #    # Per nm
# ##    ax0.plot(spc_data['x_nm'].loc[idx]*1e12, spc_data['y_P/nm'].apply(dB, result_type='broadcast'))
# ##    ax0.plot(spc_data['x_nm'].loc[idx]*1e12, spc_data['y_E/nm'].apply(dB, result_type='broadcast'))
# ##    ax0.plot(spc_data['x_nm'].loc[idx]*1e12, spc_data['y_Ph/nm'].apply(dB, result_type='broadcast'))
# #    # Per THz
# ##    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_P/THz'].apply(dB, result_type='broadcast'))
# ##    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_E/THz'].apply(dB, result_type='broadcast'))
# ##    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_Ph/THz'].apply(dB, result_type='broadcast'))
# #    ax0.plot(spc_data['x_THz']*1e12, spc_data['y_Ph/mode/s'].apply(dB, result_type='broadcast'))
# #    # Per Mode
# ##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_P/mode'].apply(dB, result_type='broadcast'))
# ##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_E/mode'].apply(dB, result_type='broadcast'))
# ##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_Ph/mode'].apply(dB, result_type='broadcast'))
# ##    ax0.plot(spc_data['x_mode']*1e12, spc_data['y_Ph/mode/s'].apply(dB, result_type='broadcast'))
# #    # Flux

# #ylim = plt.ylim()
# #plt.ylim((ylim[-1]-100, ylim[-1]))
# ax0.xaxis.set_major_formatter(ticker.EngFormatter(unit='Hz'))

# ax1 = hf.complementary_x_ticks(ax0, hf.m_to_Hz, formatter=ticker.EngFormatter(unit='m'))
# plt.tight_layout()

# %% Output Power
fig, ax0 = hf.plot_setup("Amp-Stb Int-Spectra", 1, size=(6.4*1.5, 4.8))
ax0.plot(header['time'][header['mask']==0], header['output_power'][header['mask']==0], '.')
ax0.yaxis.set_major_formatter(ticker.EngFormatter(unit='W'))
ax0.set_ylim(bottom=0)
plt.tight_layout()


# %% Uptime

#--- Calculate
hpf_psb = (spc_data['x_nm'][0] >= 810) & (spc_data['x_nm'][0] <= 1280)
hpf_psb = hpf_psb.index[hpf_psb]

msk_idxs = header['time'][header['mask']==0].sort_values().index

# Integrated Power
avg_line_power = np.nanmedian(spc_data['y_Ph/mode/s'].loc[hpf_psb, :][msk_idxs], axis=1)
norm_power = np.trapz(
    spc_data['y_Ph/mode/s'].loc[hpf_psb, :][msk_idxs] / avg_line_power[:, np.newaxis],
    spc_data['x_mode'].loc[hpf_psb, :][msk_idxs],
    axis=0)
norm_power /= np.nanmedian(norm_power)

# Power flatness (smoothness)
power_std = np.nanstd(spc_data['y_Ph/mode/s'].loc[hpf_psb, :] / avg_line_power[:, np.newaxis], axis=0)[msk_idxs]

# Downtime Locations
time_delta = -header['time'].diff(periods=-1)
t_thr = np.array(int(1e9 * 1e4), dtype="timedelta64[ns]")
t_dwt_candidates = time_delta.index[time_delta > t_thr]
t_dwt = []
scheduled_dowtime = [
    datetime.datetime(2018,10,16,14,26,51,469000, tzinfo=utc), # maintenance trip
    datetime.datetime(2019,1,5,17,15,27,451000, tzinfo=utc), # maintenance trip
    datetime.datetime(2019,4,10,14,53,31,617000, tzinfo=utc), # updated kcube and optimization scripts
    datetime.datetime(2019,4,12,14,6,51,543000, tzinfo=utc),
    datetime.datetime(2019,4,19,16,56,52,332000, tzinfo=utc), # script error; flywheeled
    datetime.datetime(2019,11,11,14,53,31,509000, tzinfo=utc), # maintenance trip
    datetime.datetime(2019,11,12,0,36,49,221000, tzinfo=utc),
    datetime.datetime(2019,11,12,15,3,28,572000, tzinfo=utc),
    datetime.datetime(2019,11,12,21,26,52,873000, tzinfo=utc),
    datetime.datetime(2019,12,19,19,34,43,516000, tzinfo=utc), # maintenance trip
    datetime.datetime(2020,1,9,20,0,8,656000, tzinfo=utc), # rot. stg. failure, diagnostics
    datetime.datetime(2020,1,10,16,50,12,326000, tzinfo=utc),
    datetime.datetime(2020,6,6,15,37,28,461000, tzinfo=utc), # computer slowdown
    datetime.datetime(2020,6,9,15,20,10,39000, tzinfo=utc),
    datetime.datetime(2020,10,27,19,30,9,63000, tzinfo=utc), # maintenance trip
    datetime.datetime(2020,10,28,22,26,50,193000, tzinfo=utc),
    datetime.datetime(2020,11,25,17,56,46,302000, tzinfo=utc), # OSA (firmware); flywheeled
    datetime.datetime(2021,1,10,17,50,6,603000, tzinfo=utc),
    datetime.datetime(2021,1,29,16,0,6,326000, tzinfo=utc), # Fiberlock, OSA (firmware); flywheeled
    datetime.datetime(2021,1,30,17,50,6,592000, tzinfo=utc), # OSA (firmware); flywheeled
    datetime.datetime(2021,2,3,8,30,6,303000, tzinfo=utc),
    datetime.datetime(2021,6,6,12,20,6,313000, tzinfo=utc), # OSA (system optimization required); flywheeled
    datetime.datetime(2021,8,2,13,46,46,315000, tzinfo=utc), # maintenance trip
    datetime.datetime(2021,8,3,13,56,46,326000, tzinfo=utc),
    datetime.datetime(2021,8,4,13,50,6,327000, tzinfo=utc)
    ]
for candidate in t_dwt_candidates:
    if header["time"].loc[candidate] not in scheduled_dowtime:
        t_dwt.append(candidate)
t_dwt = np.array(t_dwt)

if len(t_dwt)>0:
    t_dwt_dt = time_delta.loc[t_dwt]
else:
    t_dwt_dt = pd.Series([], dtype='timedelta64[ns]')


p_dwt_idxs = np.flatnonzero((norm_power < 0.5) | ((power_std > 0.8) & (header['time'].loc[msk_idxs] > datetime.datetime(2018,10,18, tzinfo=utc))))
p_dwt_candidates = np.append(0, 1 + np.flatnonzero(np.diff(p_dwt_idxs) > 1))
if len(p_dwt_idxs)>0:
    p_dwt_dt = header['time'].loc[msk_idxs].iloc[p_dwt_idxs[np.append(p_dwt_candidates[1:]-1, -1)]].values - header['time'].loc[msk_idxs].iloc[p_dwt_idxs[p_dwt_candidates]].values
    p_dwt = p_dwt_idxs[p_dwt_candidates]
    nonzeros = np.flatnonzero(p_dwt_dt)
    p_dwt_dt = p_dwt_dt[nonzeros]
    p_dwt = p_dwt[nonzeros]
else:
    p_dwt_dt = np.array([], dtype=np.timedelta64)
    p_dwt = np.array([])

for dt in scheduled_dowtime:
    cond = (dt == header['time'].loc[msk_idxs].iloc[p_dwt])
    if any(cond):
        idx = np.argwhere(cond.values)
        p_dwt = np.delete(p_dwt, idx)
        p_dwt_dt = np.delete(p_dwt_dt, idx)


# 2D Spectral Amplitudes
spc_db_diff = spc_data['y_Ph/mode/s'].loc[hpf_psb].apply(hf.dB, result_type='broadcast')
spc_db_diff = spc_db_diff.sub(spc_db_diff.loc[:,msk_idxs].median(axis='columns'), axis='index')
spc_db_diff = 10**(spc_db_diff/10)

try:
    spc_db_diff.loc[:, t_dwt] *= np.NaN
except:
    pass
spc_db_diff = spc_db_diff.loc[:, msk_idxs]
try:
    spc_db_diff.iloc[:, p_dwt_idxs] *= np.NaN
except:
    pass

#%%% Totals
total_downtime = t_dwt_dt.sum() + p_dwt_dt.sum()
total_time = header['time'].max() - header['time'].min()
print("Start Time: {:}".format(header['time'].min()))
print("Stop Time: {:}".format(header['time'].max()))
print("Total Time:\t{:}".format(total_time))
print("Downtime:\t{:}".format(total_downtime))
print("Downtime %:\t{:}".format(100*total_downtime/total_time))

# print(p_dwt_dt.sum())
# print(p_dwt_dt.sum()/total_time)

print("\nUnresponsive Downtime")
print(header["time"].loc[t_dwt])
print(t_dwt_dt)
print(t_dwt_dt.sum())

print("\nPoor Spectrum Downtime")
print(header['time'].loc[msk_idxs].iloc[p_dwt])
print(pd.Series(p_dwt_dt))
print(pd.Series(p_dwt_dt).sum())

plt.figure("Amp-Stb Downtime-Histogram")
plt.clf()
plt.hist(
    (1/(60**2 * 24)) * np.append(p_dwt_dt.astype(float)*1e-9,t_dwt_dt.values.astype(float)*1e-9),
    bins=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

#%%% Plot Uptime

with plt.rc_context({"font.family":"arial", "font.size":17}):
    fig = plt.figure("Amp-Stb Spectral-Uptime")#, constrained_layout=True)
    fig.clf()
    # fig.set_size_inches(6.4*1.25 * 1.8, 4.8, forward=True)
    fig.set_size_inches(6.4*1.25, 4.8, forward=True)
    gs = fig.add_gridspec(nrows=20, ncols=40)
    ax0 = fig.add_subplot(gs[:6, :-1])
    ax1 = fig.add_subplot(gs[7:-1, :-1], sharex=ax0)
    ax2 = fig.add_subplot(gs[7:-1, -1])
    ax3 = fig.add_subplot(gs[-1, :-1], sharex=ax0)

    ax0.plot(header['time'].loc[msk_idxs], norm_power, '.', markersize=1, rasterized=True)
    # ax0.plot(header['time'].loc[msk_idxs], norm_power/norm_power[-1], '.', markersize=1)
    # ax0.set_title("Relative Comb Line Amplitude")
    ax0.set_ylabel("Average")
    ax0.set_ylim(bottom=0, top=3)
    ax0.grid(True, alpha=0.25)
    ax0.yaxis.set_label_position("right")
    ax0.yaxis.tick_right()

    ax3.errorbar(header['time'].loc[t_dwt], np.zeros_like(t_dwt_dt, dtype=float), xerr=[t_dwt_dt*0, t_dwt_dt], fmt=".")
    # ax3.errorbar(header['time'].loc[msk_idxs].iloc[p_dwt], np.zeros_like(p_dwt, dtype=float), xerr=[p_dwt_dt*0, p_dwt_dt], fmt=".", c="C0")

    pcolor_cmap = colorcet.cm.diverging_bwr_20_95_c54.copy() #plt.cm.nipy_spectral
    pcolor_cmap.set_bad(color='k')
    pc_time = pd.concat([header['time'].loc[msk_idxs], pd.Series(header['time'].loc[msk_idxs].iloc[-1] + datetime.timedelta(seconds=1000))])
    pc_wvl = spc_data['x_nm'].loc[hpf_psb,msk_idxs].mean(axis='columns')
    wvl_dx = np.abs(np.diff(pc_wvl).mean())
    pc_wvl = np.linspace(pc_wvl.min()-wvl_dx/2, pc_wvl.max()+wvl_dx/2, pc_wvl.size+1)
    im = ax1.pcolormesh(
        pc_time,
        1e-3*pc_wvl,
        spc_db_diff,
        # spc_db_diff.div(spc_db_diff.iloc[:,-1], axis="index"),
        cmap=pcolor_cmap,
        norm=plt.matplotlib.colors.LogNorm(vmin=1/3, vmax=3),
        # norm=plt.matplotlib.colors.Normalize(vmin=1/3, vmax=3),
        shading="flat", rasterized=True)
    ax1.set_ylabel(r"Wavelength ($\mu$m)", labelpad=0)

    tck_fmt = ticker.FormatStrFormatter("%.1g")
    cbar = fig.colorbar(im, cax=ax2, ticks=[1/3, 0.5, 1, 2, 3], format=tck_fmt)
    minorticks = np.arange(.4, 3, .1)
    cbar.ax.yaxis.set_ticks(minorticks, minor=True)
    cbar.ax.yaxis.set_minor_formatter(ticker.NullFormatter())
    cbar.set_label(r"Relative Amplitude")

    for label in ax0.xaxis.get_ticklabels():
        label.set_visible(False)
    ax1.xaxis.tick_bottom()
    for label in ax1.xaxis.get_ticklabels():
        label.set_visible(False)
    ax3.xaxis.tick_bottom()
    for label in ax3.xaxis.get_ticklabels():
        label.set_ha('right')
        label.set_rotation(20)
    ax3.yaxis.set_ticks([])
    ax3.xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator(maxticks=8))

    ax1.set_xlim(left=header['time'].loc[msk_idxs].min(), right=header['time'].loc[msk_idxs].max())
    plt.subplots_adjust(wspace=0, hspace=0.8, top=0.9425)
plt.tight_layout()

# %% Plot All Traces

spc_psb = (spc_data['x_nm'][0] >= 780) & (spc_data['x_nm'][0] <= 1320)
spc_psb = spc_psb.index[spc_psb]


with plt.rc_context({"font.family":"arial", "font.size":14}):#, 'lines.linewidth':3}):
    fig = plt.figure("Amp-Stb All-Traces")
    plt.clf()
    fig.set_size_inches(6.4*1.25, 4.8, forward=True)
    ax0 = plt.subplot2grid((2,1), (0,0))
    ax1 = plt.subplot2grid((2,1), (1,0), sharex=ax0)

    flat = header['time'][header['mask']==0].sort_values().index
    flat_cond = (
        ~flat.isin(flat[p_dwt_idxs])
        & (header['time'] > datetime.datetime(2018, 10, 20, tzinfo=utc))[header['mask']==0])
    flat = flat[flat_cond]

    # flat = flat[flat.isin(flat[(header['time']>datetime.datetime(2018, 10, 20, tzinfo=utc))[header['mask']==0]])]
    #flat = header['time'][header['mask']==0][header['time']<utc_tz.localize(datetime.datetime(2018, 7, 24, tzinfo=utc))].sort_values().index
    #flat = header['time'][header['mask']==0][header['time']>utc_tz.localize(datetime.datetime(2018, 7, 24, tzinfo=utc))].sort_values().index


    data = spc_data['y_Ph/mode'].loc[spc_psb,flat]
    db_data = data.apply(hf.dB, result_type='broadcast')
    db_data -= np.median(db_data.mean(axis='columns').values)
    std_data = 10**(spc_data['y_std'].loc[spc_psb,flat]/10) - 1
    # std_data = spc_data['y_std'].loc[spc_psb,flat]
    x_data = spc_data['x_nm'].loc[spc_psb,flat]
    n_bins = 500

    x_bins = np.linspace(x_data.values.min(), x_data.values.max(), len(x_data)+1)
    y_bins = np.linspace(db_data.values.min(), db_data.values.max(), n_bins)
    ax0.hist2d(x_data.values.flatten(), db_data.values.flatten(), bins=np.array([x_bins, y_bins]), cmap=plt.cm.Blues, norm=plt.matplotlib.colors.LogNorm(), rasterized=True)
    ax0.plot(x_data.mean(axis='columns'), db_data.mean(axis='columns'), color='0', markersize=0.5, alpha=1)

    x_bins = np.linspace(x_data.values.min(), x_data.values.max(), len(x_data)+1)
    # y_bins = np.geomspace(std_data.values[std_data.values > 0].min(), std_data.values.max(), n_bins)
    y_bins = np.geomspace(1e-3, std_data.values.max(), n_bins)
    ax1.hist2d(x_data.values.flatten(), std_data.values.flatten(), bins=np.array([x_bins, y_bins]), cmap=plt.cm.Blues, norm=plt.matplotlib.colors.LogNorm(), rasterized=True)
    ax1.semilogy(x_data.mean(axis='columns'), std_data.mean(axis='columns'), color="dodgerblue", markersize=1, alpha=1, label='Short Term')
    ax1.semilogy(x_data.mean(axis='columns'), 10**(db_data.std(axis='columns')/10) - 1, color='0', markersize=1, alpha=1, label='Long Term')
    ax1.autoscale(axis="x", tight=True)
    leg = ax1.legend(loc='upper right', ncol=2, borderaxespad=0.25, columnspacing=.75, handletextpad=0.25, handlelength=1.5, borderpad=0.25)
    for line in leg.get_lines():
        line.set_linewidth(3)

    # ax0.set_title("Relative Amplitude")
    ax0.set_ylabel(r'dB photons/mode')
    ax0.grid(alpha=0.25)
    # ax1.set_title("Standard Deviation")
    ax1.set_ylabel(r'std dev/mean', labelpad=0)
    ax1.set_xlabel('Wavelength (nm)')
    # ax1.set_ylim(bottom=1e-3)
    ax1.grid(alpha=0.25)

plt.tight_layout()
#plt.savefig('long_spectrum.png', dpi=600, transparent=True)

#avg_flat = copy.deepcopy(np.array([data_list[0], data_avg]))


# %% Flat 2D
flat = header['time'][header['mask']==0].sort_values().index

fig = plt.figure("Flat 2D")
plt.clf()
fig.set_size_inches(6.35*1.5, 4.8, forward=True)
plt.pcolormesh(header['time'].loc[flat],
               spc_data['x_nm'].loc[:,flat].mean(axis='columns'),
               spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast'),
#               hf.gaus_filt(
#                       spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').sub(spc_data['y_P/nm'].loc[:,flat].apply(hf.dB).mean(axis='columns'), axis='index'),
#                       (10, 1),
#                       ),
               cmap=plt.cm.nipy_spectral)#plt.cm.seismic)
plt.ylabel("Wavelength (nm)")
c_bar = plt.colorbar()
c_bar.set_label(r"dB")
fig.autofmt_xdate()
#plt.xlim([736810.5475672083, 736970.9387923519])
#plt.gca().xaxis.set_major_locator(MonthLocator())
#plt.ylim(800, 1300)
plt.tight_layout()


# %% Flat 2D Diff
flat = header['time'][header['mask']==0].sort_values().index

fig = plt.figure("Flat 2D Diff")
plt.clf()
fig.set_size_inches(7.65, 4.8, forward=True)
plt.pcolormesh(header['time'].loc[flat],
               spc_data['x_nm'].loc[:,flat].mean(axis='columns'),
               spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').sub(spc_data['y_P/nm'].loc[:,flat].apply(hf.dB).mean(axis='columns'), axis='index'),
#               hf.gaus_filt(
#                       spc_data['y_P/nm'].loc[:,flat].apply(hf.dB, result_type='broadcast').sub(spc_data['y_P/nm'].loc[:,flat].apply(hf.dB).mean(axis='columns'), axis='index'),
#                       (10, 1),
#                       ),
               cmap=plt.cm.nipy_spectral)#plt.cm.seismic)
# plt.clim(-1,1)
plt.clim(-3,3)
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

fig = plt.figure("Amp-Stb 2D-Std-Dev")
plt.clf()
fig.set_size_inches(7.65, 4.8, forward=True)
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
