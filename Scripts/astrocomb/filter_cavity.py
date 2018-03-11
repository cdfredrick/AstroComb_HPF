# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:51:36 2017

@author: AstroComb
"""

# %%

import numpy as np

import matplotlib.pyplot as plt

from scipy.optimize import curve_fit

import visa

from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from PyDAQmx import DAQError

import time


# %% Functions

def open_busy(resource):
    opened = False
    while not opened:
        try:
            resource.open()
        except visa.VisaIOError as visa_err:
            if visa_err[0] == visa.VisaIOError(visa.constants.VI_ERROR_RSRC_BUSY)[0]:
                pass
            else:
                raise
        else:
            opened = True

def start_busy(task):
    started = False
    while not started:
        try:
            task.StartTask()
        except DAQError as daq_err:
            if daq_err.error == -50103: # "The specified resource is reserved."
                pass
            else:
                raise
        else:
            started = True


class ni_USB6361:
    def __init__(self, dev_channel_id, low_v = 0, high_v = 10):
        self.NSAMPS = 10
        self.read = int32()
        self.data = np.zeros( (self.NSAMPS,), dtype = np.float64)
        self.t = Task()
        self.t.CreateAIVoltageChan(dev_channel_id, "", DAQmx_Val_RSE, low_v, high_v, DAQmx_Val_Volts, None)
    
    def read_analog(self):
        start_busy(self.t)
        self.t.ReadAnalogF64(self.NSAMPS, 10.0, DAQmx_Val_GroupByChannel, self.data, self.NSAMPS, byref(self.read), None)
        self.t.StopTask()
    
    def get_peak_freq(self):
        self.read_analog()
        han_win = np.hanning(self.NSAMPS)
        freqs = 1e4*np.fft.rfftfreq(self.NSAMPS)
        amps = np.abs(np.fft.rfft(han_win*self.data))
        peak_ind = np.argmax(amps)
        return freqs[peak_ind]
    
    def get_avg(self):
        self.read_analog()
        amps = self.data
        return np.mean(amps)


class srs_SIM900:
    def __init__(self, visa_id, channel, rm = None, thrsh_1 = .2, thrsh_2 = .01):
        print(time.strftime('%c')+' - Initializing communication with the SRS SIM900.')
        if rm is None:
            rm = visa.ResourceManager()
        opened = False
        while not opened:
            try:
                self.srs = rm.open_resource(visa_id, open_timeout = 5000)
            except visa.VisaIOError as visa_err:
                if visa_err[0] == visa.VisaIOError(visa.constants.VI_ERROR_RSRC_BUSY)[0]:
                    pass
                else:
                    raise
            else:
                opened = True
        self.srs.close()
        self.open_cmd = 'CONN '+str(channel)+',"xyz"\n'
        # Get settings (from instrument or database?)
        self.ulim, self.llim = self.get_output_lims()
        self.center = np.mean([self.ulim, self.llim])
        self.threshold_1 = (self.ulim - self.llim)*(1.-thrsh_1*2.)/2.
        self.threshold_2 = (self.ulim - self.llim)*(1.-thrsh_2*2.)/2.
        print(time.strftime('%c')+' - Initialized.')
    
    def get_man_output(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        man_output = self.srs.query('MOUT?').strip()
        self.srs.query('xyz*IDN?\n')
        self.srs.close()
        return float(man_output)
    
    def set_man_output(self, output):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        self.srs.write('MOUT {:.3f}'.format(output))
        self.srs.query('xyz*IDN?\n')
        self.srs.close()
    
    def get_output(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        level = self.srs.query('OMON?\n').strip()
        self.srs.query('xyz*IDN?\n')
        self.srs.close()
        return float(level)
    
    def get_output_cond(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        u_lim = self.srs.query('INCR? 1').strip()
        l_lim = self.srs.query('INCR? 2').strip()
        anti_wind = self.srs.query('INCR? 3').strip()
        self.srs.query('xyz*IDN?\n')
        self.srs.close()
        return [int(u_lim), int(l_lim), int(anti_wind)]
    
    def get_output_lims(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        ulim = self.srs.query('ULIM?\n').strip()
        llim = self.srs.query('LLIM?\n').strip()
        self.srs.query('xyz*IDN?\n')
        self.srs.close()
        return [float(ulim), float(llim)]
    
    def get_pid_state(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        state = self.srs.query("AMAN?\n").strip()
        self.srs.query('xyz*IDN?\n')
        self.srs.close()
        return int(state)
    
    def set_pid_state(self, state):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        self.srs.write("AMAN {:}\n".format(int(state)))
        self.srs.query('xyz*IDN?\n')
        self.srs.close()


def get_lock(srs, daq, last_good_pos = None):
    #Turn off PID servo
    srs.set_pid_state(0)
    
    #Try locking at last good position
    if last_good_pos is not None:
        srs.set_man_output(last_good_pos)
        time.sleep(.1)
        srs.set_pid_state(1)
        time.sleep(1)
        current_output = srs.get_output()
        #current_err = daq.get_avg()
        if abs(current_output - srs.center) < srs.threshold_2:
        #if current_err < 1.:
            return
        else:
            srs.set_pid_state(0)
    
    #Find lock point    
        #Get Data
    x = np.linspace(srs.center-srs.threshold_2, srs.center+srs.threshold_2, 20)
    y = np.copy(x)
    for ind, x_val in enumerate(x):
        srs.set_man_output(x_val)
        time.sleep(.5)
        y[ind] = daq.get_avg()
    srs.set_man_output(srs.center)
        #Coarse Estimate
    min_index = np.argmin(y)
    new_output = x[min_index]
    print(time.strftime('%c')+' - maximum DAC = {:.3f}.'.format(np.max(y)))
#    plt.plot(x, y)
#    plt.show()

    #Get Lock
    print(time.strftime('%c')+' - estimated voltage setpoint = {:.3f}, locking.'.format(new_output))
    srs.set_man_output(new_output)
    time.sleep(.2)
    srs.set_pid_state(1)
    if abs(new_output - srs.center) >= srs.threshold_2:
        print(time.strftime('%c')+' - estimated voltage setpoint is near rails, adjust HV amplifier'.format(new_output))


# %% Setup
rm = visa.ResourceManager()

cav_pid = srs_SIM900('ASRL9::INSTR', 3, rm)
cav_err = ni_USB6361('Dev1/ai1')

last_good_pos = None
err_hist = np.array([])

# %% Test

test = 0
while test:
    #Begin Test
    if cav_pid.get_pid_state():
        current_err = cav_err.get_avg()
        current_output = cav_pid.get_output()
        current_output_cond = cav_pid.get_output_cond()
        print(current_err)
        print(current_output)
        if abs(current_output - cav_pid.center) > cav_pid.threshold_2:
            print(time.strftime('%c')+' - lost cavity lock')
            get_lock(cav_pid, cav_err, last_good_pos)
            err_hist = np.array([])
        elif err_hist.size > 50:
            if current_err/np.mean(err_hist) > 5:
                print(time.strftime('%c')+' - lost cavity lock')
                get_lock(cav_pid, cav_err, last_good_pos)
                err_hist = np.array([])
            elif err_hist.size < 100:
                err_hist = np.append(err_hist, current_err)
            else:
                err_hist = np.roll(err_hist, 1)
                err_hist[0] = current_err
            last_good_pos = current_output
        elif current_err > .5: #resonance should be ~.1
            get_lock(cav_pid, cav_err)
        else:
            err_hist = np.append(err_hist, current_err)
    else:
        current_err = cav_err.get_avg()
        current_output = cav_pid.get_output()
        current_output_cond = cav_pid.get_output_cond()
        print(current_err)
        print(current_output)
        get_lock(cav_pid, cav_err)
    #End Test
    test = 0
    print('Test Ended')



# %% Main Loop

while 1:
    current_err = cav_err.get_avg()
    current_output = cav_pid.get_output()
    current_output_cond = cav_pid.get_output_cond()
    if cav_pid.get_pid_state():
        if abs(current_output - cav_pid.center) > cav_pid.threshold_2:
            print(time.strftime('%c')+' - lost cavity lock')
            get_lock(cav_pid, cav_err, last_good_pos)
            err_hist = np.array([])
        elif current_err > .3: #on resonance is ~.1 V, off is ~.5V
            print(time.strftime('%c')+' - DAC was {:.3f}, lost cavity lock'.format(current_err))
            get_lock(cav_pid, cav_err)
            err_hist = np.array([])
        elif err_hist.size > 50:
            if current_err/np.abs(np.mean(err_hist)) > 5:
                print(time.strftime('%c')+' - DAC was {:.3f}, lost cavity lock'.format(current_err))
                get_lock(cav_pid, cav_err, last_good_pos)
                err_hist = np.array([])
            elif err_hist.size < 100:
                err_hist = np.append(err_hist, current_err)
            else:
                err_hist = np.roll(err_hist, 1)
                err_hist[0] = current_err
            last_good_pos = current_output
        else:
            err_hist = np.append(err_hist, current_err)
            if err_hist.size == 5:
                print(time.strftime('%c')+' - cavity locked, current DAC {:.3f}'.format(current_err))
    else:
        print(time.strftime('%c')+' - cavity unlocked, current DAC {:.3f}'.format(current_err))
        get_lock(cav_pid, cav_err)
        err_hist = np.array([])

    