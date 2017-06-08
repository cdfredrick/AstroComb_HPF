# -*- coding: utf-8 -*-
Created on Mon Jan 20 10:30:45 2014

@author: NIST
"""
# %% Initialize ===============================================================

import visa
from mongologger import MongoLogger
from datetime import datetime

ML = MongoLogger()


# %% Constants ================================================================

gate_time = 10. # Gate time in seconds
tm_out_mult = 2. # Multiple of gate time before timeout


# %% Load Counter =============================================================

device_name = "GPIB0::16::INSTR"

rm = visa.ResourceManager()

if device_name not in rm.list_resources():
    raise Exception("Counter not found. Check device_name, whether counter is plugged in, etc.")


# %% Initialize Counter to Known State ========================================

ctr = rm.get_instrument(device_name)
ctr.clear() # Clear the Counter and Interface
ctr.write('*RST') # Reset the instrument
ctr.write('*CLS') # Clear Statue Register and Error Que
ctr.write('*SRE 0') # Clear Service Request Enable Register
ctr.write('*ESE 0') # CLear Event Status Enable Register
ctr.write(':STAT:PRES') # Preset for operation
ctr.write(':INP:IMP 50') # Set 50 ohm input impedence (as opposed to 1 mega ohm)
ctr.write(':ROSC:SOUR EXT') # Set oscillator to external source
ctr.write(':ROSC:EXT:CHECK OFF') # Don't check for external source
print ctr.query("*IDN?")
print datetime.now().strftime('%c')+' -  Initialized'

ctr.timeout = tm_out_mult*gate_time*1e3


# %% Gating ===================================================================

ctr.write(":FUNC 'FREQ 1'") # Frequency measurement on channel 1
ctr.write("FREQ:ARM:STAR:SOUR IMM") # Start measuring upon INIT
ctr.write("FREQ:ARM:STOP:TIM "+str(gate_time)) # Stop after gate time
# Extend first gate time, to calculate expected freq.


# %% Detect Measuring and Service Request (SRQ) ===============================

ctr.write(':STAT:OPER:PTR 0;NTR 16') # Detect transition from measuring to non measuring
ctr.write(':STAT:OPER:ENABLE 16') # Detect measuring
ctr.write('*SRE 128') # Assert SRQ on Operation Summary bit


# %% Measure f Expected =======================================================

ctr.write('INIT') # Start Measurement
ctr.wait_for_srq(timeout=(tm_out_mult*gate_time*1e3)) # wait for SRQ
ctr.write('*CLS') # Clear SRQ

f_exp = ctr.query("FETC:FREQ?") # Read frequency
try:
    float(f_exp)
    print datetime.now().strftime('%c')+' - Setting Expected Frequency To: '+f_exp
    ctr.write(':FREQ:EXP: '+f_exp) # Set expected frequency
except:
    print datetime.now().strftime('%c')+' - GPIB Read Error: '+f_exp
    float(f_exp)


# %% Continuous Measurements ==================================================

ctr.write('*CLS') # Clear SRQ
ctr.write("FREQ:ARM:STOP:TIM "+str(gate_time)) # Set Gate Time
ctr.write('INIT') # Start Measurement

while True:
    # Read Measurement --------------------------------------------------------
    ctr.wait_for_srq(timeout=tm_out_mult*gate_time*1e3) # Wait for SRQ
    f = ctr.query("FETC:FREQ?") # Read frequency

    # Start Next Measurement --------------------------------------------------
    ctr.write('*CLS') # Clear SRQ
    ctr.write('INIT') # Start Measurement
    
    # Analysis ----------------------------------------------------------------
    try:
        float(f)
        print datetime.now().strftime('%c')+' - Clarity_PFR: '+f
        ML.logData(f, path="CountFR/clarity")
    except ValueError:
        print datetime.now().strftime('%c')+' - GPIB Read Error: '+f

