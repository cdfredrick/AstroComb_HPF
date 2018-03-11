"""
# -*- coding: utf-8 -*-
Created on Mon Jan 20 10:30:45 2014

@author: NIST
"""
# %% Initialize ===============================================================

import visa
from datetime import datetime

# %% Constants ================================================================

gate_time = 1. # Gate time in seconds
tm_out_mult = 2. # Multiple of the gate time before visa timeout

device_name = "GPIB0::16::INSTR"

# %% Load Counter =============================================================

rm = visa.ResourceManager()

if device_name not in rm.list_resources():
    raise Exception("Counter not found. Check device_name, whether counter is plugged in, etc.")


# %% Initialize Counter to Known State ========================================

ctr = rm.open_resource(device_name)
ctr.clear() # Clear the Counter and Interface
ctr.write('*RST') # Reset the instrument
ctr.write('*CLS') # Clear Statue Register and Error Que
ctr.write('*SRE 0') # Clear Service Request Enable Register
ctr.write('*ESE 0') # CLear Event Status Enable Register
ctr.write(':STAT:PRES') # Preset for operation
ctr.write(':INP:IMP 50') # Set 50 ohm input impedence (as opposed to 1 mega ohm)
ctr.write(':ROSC:SOUR EXT') # Set oscillator to external source
ctr.write(':ROSC:EXT:CHECK OFF') # Don't check for external source
ctr.write(':FORMat:DATA ASC')
print(ctr.query("*IDN?"))
print(datetime.now().strftime('%c')+' -  Initialized')

ctr.timeout = tm_out_mult*gate_time*1e3 # in ms


# %% Gating ===================================================================

ctr.write(":FUNC 'FREQ 1'") # Frequency measurement on channel 1
ctr.write(":FREQ:ARM:STAR:SOUR IMM") # Start measuring upon INIT
ctr.write(":FREQ:ARM:STOP:TIM "+str(gate_time)) # Stop after gate time

# %% Measure f Expected =======================================================

f_exp = ctr.query(":READ:FREQ?") # Read frequency
try:
    float(f_exp)
    print(datetime.now().strftime('%c')+' - Setting Expected Frequency To: '+f_exp)
    ctr.write(':FREQ:EXP: '+f_exp) # Set expected frequency
except:
    print(datetime.now().strftime('%c')+' - GPIB Read Error: '+f_exp)

# %% Continuous Measurements ==================================================

# Start Continuous Measurements
ctr.write(':INIT:CONT')

while True:
# Read Measurement ------------------------------------------------------------
    f = ctr.query(":FETC:FREQ?") # Read frequency
# Analysis --------------------------------------------------------------------
    try:
        float(f)
        print(datetime.now().strftime('%c')+' - Frequency: '+f)
    except ValueError:
        print(datetime.now().strftime('%c')+' - GPIB Read Error: '+f)


