# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 17:29:37 2019

@author: cdf1
"""

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