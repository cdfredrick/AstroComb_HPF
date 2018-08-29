# -*- coding: utf-8 -*-
"""
Created on Mon Aug 27 14:34:48 2018

@author: cdf1
"""
# %% Modules

import datetime
from Drivers.Database import MongoDB

# %%

records = [
    # ambience ----------------------------------------------------------------
        # Data ----------------------------------
    'ambience/box_temperature_0',
    'ambience/box_temperature_1',
    'ambience/rack_temperature_0',
    # broadening_stage --------------------------------------------------------
        # Devices -------------------------------
    'broadening_stage/device_rotation_mount',
        # States --------------------------------
    'broadening_stage/state_2nd_stage',
    'broadening_stage/control',
    # comb_generator ----------------------------------------------------------
        # Data ----------------------------------
    'comb_generator/IM_bias',
        # Devices -------------------------------
    'comb_generator/device_IM_bias',
    'comb_generator/device_PDU_12V',
        # States --------------------------------
    'comb_generator/state_12V_supply',
    'comb_generator/state_IM_bias',
    'comb_generator/control',
    # cw_laser ----------------------------------------------------------------
        # Data ----------------------------------
    'cw_laser/dac_limits',
    'cw_laser/dac_output',
    'cw_laser/freq_err',
        # States --------------------------------
    'cw_laser/state_frequency',
    # filter_cavity -----------------------------------------------------------
        # Data ----------------------------------
    'filter_cavity/DAQ_Vout_vs_reflect',
    'filter_cavity/DAQ_error_signal',
    'filter_cavity/HV_output',
    'filter_cavity/PID_output',
    'filter_cavity/PID_output_limits',
    'filter_cavity/heater_temperature',
        # Devices -------------------------------
    'filter_cavity/device_DAQ_Vout_vs_reflect',
    'filter_cavity/device_HV',
    'filter_cavity/device_PID',
        # States --------------------------------
    'filter_cavity/state',
    'filter_cavity/control',
    # mll_f0 ------------------------------------------------------------------
        # Data ----------------------------------
    'mll_f0/dac_limits',
    'mll_f0/dac_output',
    'mll_f0/freq_err',
        # States --------------------------------
    'mll_f0/state',
    # mll_fR ------------------------------------------------------------------
        # Data ----------------------------------
    'mll_fR/DAQ_Vout_vs_freq',
    'mll_fR/DAQ_error_signal',
    'mll_fR/HV_output',
    'mll_fR/PID_output',
    'mll_fR/PID_output_limits',
    'mll_fR/TEC_current',
    'mll_fR/TEC_temperature',
    'mll_fR/TEC_event_status',
        # Devices -------------------------------
    'mll_fR/device_DAQ_Vout_vs_freq',
    'mll_fR/device_HV',
    'mll_fR/device_PID',
    'mll_fR/device_TEC',
        # States --------------------------------
    'mll_fR/state',
    'mll_fR/control',
    # monitor_DAQ -------------------------------------------------------------
        # Devices -------------------------------
    'monitor_DAQ/device_DAQ_analog_in',
    'monitor_DAQ/device_DAQ_digital_in',
        # States --------------------------------
    'monitor_DAQ/state_analog',
    'monitor_DAQ/state_digital',
    'monitor_DAQ/control',
    # rf_oscillators ----------------------------------------------------------
        # Data ----------------------------------
    'rf_oscillators/100MHz_phase_lock',
    'rf_oscillators/1GHz_phase_lock',
    'rf_oscillators/Rb_OCXO_control',
    'rf_oscillators/Rb_detected_signals',
    'rf_oscillators/Rb_frequency_offset',
    'rf_oscillators/Rb_magnetic_read',
    'rf_oscillators/status',
    'rf_oscillators/Rb_time_tag',
        # Devices -------------------------------
    'rf_oscillators/device_Rb_clock',
        # States --------------------------------
    'rf_oscillators/state_PLOs',
    'rf_oscillators/state_Rb_clock',
    'rf_oscillators/control',
    # spectral_shaper ---------------------------------------------------------
        # Data ----------------------------------
    'spectral_shaper/DW',
    'spectral_shaper/DW_vs_IM_bias',
    'spectral_shaper/DW_vs_waveplate_angle',
    'spectral_shaper/mask',
    'spectral_shaper/spectrum',
        # Devices -------------------------------
    'spectral_shaper/device_IM_bias',
    'spectral_shaper/device_OSA',
    'spectral_shaper/device_rotation_mount',
        # States --------------------------------
    'spectral_shaper/state_SLM',
    'spectral_shaper/state_optimizer',
    'spectral_shaper/control',
]
# More rf_oscillators
for idx in range(20):
    records.append('rf_oscillators/Rb_adc_{:}'.format(idx))
for idx in range(8):
    records.append('rf_oscillators/Rb_dac_{:}'.format(idx))

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

# %% Connect to database and pull results

local_client = MongoDB.MongoClient()
remote_client = MongoDB.MongoClient(port=27018)

start_time = datetime.datetime.utcnow()
print('Starting sync', datetime.datetime.now())
try:
    for database in records:
        print('Syncing {:},'.format(database), 'Elapsed Time =',(datetime.datetime.utcnow()-start_time))
        MongoDB.sync_to_local_record(local_client, remote_client, database, sync_stop_time=start_time)
    for database in logs:
        print('Syncing {:},'.format(database), 'Elapsed Time =',(datetime.datetime.utcnow()-start_time))
        MongoDB.sync_to_local_log(local_client, remote_client, database, sync_stop_time=start_time)
finally:
    try:
        remote_client.close()
    finally:
        local_client.close()
print('Sync complete!', 'Elapsed Time =',(datetime.datetime.utcnow()-start_time))
    