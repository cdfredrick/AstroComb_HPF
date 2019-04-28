# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 11:29:37 2019

@author: cdf1
"""

# broadening_stage --------------------------------------------------------
    # States --------------------------------
'broadening_stage/state_2nd_stage',

# comb_generator ----------------------------------------------------------
    # States --------------------------------
'comb_generator/state_12V_supply',
'comb_generator/state_IM_bias',

# cw_laser ----------------------------------------------------------------
    # States --------------------------------
'cw_laser/state_frequency',

# filter_cavity -----------------------------------------------------------
    # States --------------------------------
'filter_cavity/state',

# mll_f0 ------------------------------------------------------------------
    # States --------------------------------
'mll_f0/state',

# mll_fR ------------------------------------------------------------------
    # States --------------------------------
'mll_fR/state',

# monitor_DAQ -------------------------------------------------------------
    # States --------------------------------
'monitor_DAQ/state_analog',
'monitor_DAQ/state_digital',

# rf_oscillators ----------------------------------------------------------
    # States --------------------------------
'rf_oscillators/state_PLOs',
'rf_oscillators/state_Rb_clock',

# spectral_shaper ---------------------------------------------------------
    # States --------------------------------
'spectral_shaper/state_SLM',
'spectral_shaper/state_optimizer',
]

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