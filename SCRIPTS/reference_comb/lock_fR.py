# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:51:36 2017

@author: AstroComb
"""

# %%

import numpy as np

from scipy.optimize import curve_fit

import visa

from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from PyDAQmx import DAQError



import matplotlib.pyplot as plt

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


class ilx_LDC3900:
    def __init__(self, visa_id, channel, rm = None):
        print(time.strftime('%c')+' - Initializing communication with the ILX LDC-3900.')
        if rm is None:
            rm = visa.ResourceManager()
        opened = False
        while not opened:
            try:
                self.ilx = rm.open_resource(visa_id, open_timeout = 5000)
            except visa.VisaIOError as visa_err:
                if visa_err[0] == visa.VisaIOError(visa.constants.VI_ERROR_RSRC_BUSY)[0]:
                    pass
                else:
                    raise
            else:
                opened = True
        self.ilx.close()
        self.las_open_cmd = 'LAS:CHAN {:}'.format(int(channel))
        self.tec_open_cmd = 'TEC:CHAN {:}'.format(int(channel))
        self.tec_settling_time = 30 # seconds
        self.last_tec_change = time.time()
        self.nominal_tec_r = 7.8
        self.safe_tec_range = .3
        print(time.strftime('%c')+' - Initialized.')
    
    def get_resistance(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        res = self.ilx.query('TEC:R?').strip()
        self.ilx.close()
        return float(res)
    
    def set_resistance(self, resistance):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:R {:.3f}'.format(resistance))
        self.ilx.close()
        
    def get_resistance_setpoint(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        res = self.ilx.query('TEC:SET:R?').strip()
        self.ilx.close()
        return float(res)
    
    def set_tec_step(self, step):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:STEP {:}'.format(int(step)))
        self.ilx.close()
    
    def dec_tec(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:DEC')
        self.ilx.close()
    
    def inc_tec(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:INC')
        self.ilx.close()
    
    def change_tec_output(self, direction):
        now = time.time()
        if now - self.last_tec_change > 1:
            old_res = self.get_resistance()
            new_res = old_res
            while abs(new_res - old_res) < .002:
                if direction>0:
                    if new_res - (self.nominal_tec_r+self.safe_tec_range) < 0:
                        self.inc_tec()
                    else:
                        print(time.strftime('%c')+' - at the limit of the safe TEC range. Raising no farther.')
                        return
                elif direction<0:
                    if new_res - (self.nominal_tec_r-self.safe_tec_range) > 0:
                        self.dec_tec()
                    else:
                        print(time.strftime('%c')+' - at the limit of the safe TEC range. Lowering no farther.')
                        return
                time.sleep(.5)
                new_res = self.get_resistance()
            self.last_tec_change = time.time()
        else:
            print(time.strftime('%c')+' - TEC has not settled. {:.3f}s left'.format(now - self.last_tec_change))
        #time.sleep(20) #let the temperature settle


class ni_USB6361:
    def __init__(self, dev_channel_id, low_v = -1, high_v = 1):
        self.NSAMPS = 1000
        self.read = int32()
        self.data = np.zeros( (self.NSAMPS,), dtype = np.float64)
        self.t = Task()
        self.t.CreateAIVoltageChan(dev_channel_id, "", DAQmx_Val_Diff, low_v, high_v, DAQmx_Val_Volts, None)
    
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


def get_lock(srs, daq, ilx, last_good_pos = None):
    #Turn off PID servo
    srs.set_pid_state(0)
    srs.set_man_output(srs.center - srs.threshold_2) # reset the hysteresis
    #Try locking at last good position
    if last_good_pos is not None:
        srs.set_man_output(last_good_pos)
        time.sleep(.1)
        srs.set_pid_state(1)
        time.sleep(1)
        current_output = srs.get_output()
        if abs(current_output - srs.center) < srs.threshold_2:
            return
        else:
            srs.set_pid_state(0)
    
    #Find lock point    
    to_fit = lambda v, v0, s: s*np.abs(v-v0)
        #Get Data
    x = np.linspace(srs.center-srs.threshold_2, srs.center+srs.threshold_2, 4)
    y =np.copy(x)
    for ind, x_val in enumerate(x):
        srs.set_man_output(x_val)
        y[ind] = daq.get_peak_freq()
    srs.set_man_output(x[0]) # reset the hysteresis
        #Coarse Estimate
    slopes = np.diff(y)/np.diff(x)
    slope_ind = np.argmax(np.abs(slopes))
    output_coarse = -y[slope_ind]/slopes[slope_ind] + x[slope_ind]
    slope_coarse = np.abs(slopes[slope_ind])
        #Fine Estimate
    new_output = curve_fit(to_fit, x, y, [output_coarse, slope_coarse])[0][0]
    
    #Get Lock
    if abs(new_output - srs.center) < srs.threshold_2:
        print(time.strftime('%c')+' - estimated voltage setpoint = {:.3f}, locking.'.format(new_output))
        srs.set_man_output(new_output)
        time.sleep(.1)
        srs.set_pid_state(1)
    elif new_output < srs.center:
        print(time.strftime('%c')+' - estimated voltage setpoint = {:.3f}, raising the resistance setpoint.'.format(new_output))
        ilx.change_tec_output(+1)
        #time.sleep(30)
    elif new_output > srs.center:
        print(time.strftime('%c')+' - estimated voltage setpoint = {:.3f}, lowering the resistance setpoint.'.format(new_output))
        ilx.change_tec_output(-1)
        #time.sleep(30)


# %% Setup
rm = visa.ResourceManager()

fr_pid = srs_SIM900('ASRL16::INSTR', 1, rm)
fr_err = ni_USB6361('Dev5/ai0')
fr_tec = ilx_LDC3900(u'GPIB1::20::INSTR', 1, rm)

last_good_pos = None

#pid_ulim, pid_llim = fr_pid.get_output_lims()
#
#pid_center = np.mean([pid_ulim, pid_llim])
#pid_hyst = (pid_ulim - pid_llim)*(1.-.2*2.)/2.
#pid_hyst2 = (pid_ulim - pid_llim)*(1.-.01*2.)/2.

# %% Test

test = 0
while test:
    #Begin Test
    if fr_pid.get_pid_state():
        current_output = fr_pid.get_output()
        current_output_cond = fr_pid.get_output_cond()
        if abs(current_output - fr_pid.center) > fr_pid.threshold_2:
            print(time.strftime('%c')+' - lost fR lock')
            get_lock(fr_pid, fr_err, fr_tec, last_good_pos)
        elif abs(current_output - fr_pid.center) > fr_pid.threshold_1:
            if current_output - fr_pid.center > 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, lowering the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(-1)
            elif current_output - fr_pid.center < 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, raising the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(1)
        else:
            last_good_pos = current_output
    else:
        get_lock(fr_pid, fr_err, fr_tec)
    time.sleep(.1)
    #End Test
    test = 0
    


# %% Main Loop

while 1:
    if fr_pid.get_pid_state():
        current_output = fr_pid.get_output()
        current_output_cond = fr_pid.get_output_cond()
        if abs(current_output - fr_pid.center) > fr_pid.threshold_2:
            print(time.strftime('%c')+' - lost fR lock')
            get_lock(fr_pid, fr_err, fr_tec, last_good_pos)
        elif abs(current_output - fr_pid.center) > fr_pid.threshold_1:
            if current_output - fr_pid.center > 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, lowering the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(-1)
            elif current_output - fr_pid.center < 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, raising the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(1)
        else:
            last_good_pos = current_output
    else:
        get_lock(fr_pid, fr_err, fr_tec)
    time.sleep(.1)


print('temperature setpoint is out of range')


    