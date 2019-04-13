# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:25:58 2019

@author: cdf1
"""

# rf_oscillators ----------------------------------------------------------
    # Data ----------------------------------
'rf_oscillators/100MHz_phase_lock',
'rf_oscillators/1GHz_phase_lock',
'rf_oscillators/Rb_OCXO_control',
'rf_oscillators/Rb_detected_signals',
'rf_oscillators/Rb_frequency_offset',
'rf_oscillators/Rb_magnetic_read',
'rf_oscillators/Rb_status',
'rf_oscillators/Rb_time_tag',
    # Devices -------------------------------
'rf_oscillators/device_Rb_clock',
    # States --------------------------------
'rf_oscillators/state_PLOs',
'rf_oscillators/state_Rb_clock',
'rf_oscillators/control',
# More rf_oscillators
for idx in range(20):
    records.append('rf_oscillators/Rb_adc_{:}'.format(idx))
for idx in range(8):
    records.append('rf_oscillators/Rb_dac_{:}'.format(idx))

# mll_fR ------------------------------------------------------------------
    # Data ----------------------------------
'mll_fR/DAQ_error_signal', # rms should be related to rms freq error (V is prop to phase)
    # States --------------------------------
'mll_fR/state',

# mll_f0 ------------------------------------------------------------------
    # Data ----------------------------------
'mll_f0/freq_err',
    # States --------------------------------
'mll_f0/state',

# cw_laser ----------------------------------------------------------------
    # Data ----------------------------------
'cw_laser/freq_err',
    # States --------------------------------
'cw_laser/state_frequency',