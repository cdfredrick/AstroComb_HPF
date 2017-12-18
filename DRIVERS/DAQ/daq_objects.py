# -*- coding: utf-8 -*-
"""
Created on Fri Jun 23 11:40:31 2017

@author: Wesley Brand

Module: daq_objects

Public class:
   DAQAnalogIn(object)

Public methods:
    creat_analog_in(n_samples, log_rate, max_v=10, min_v=-10)
    list_of_floats = read_analog_in() #Volts
    end_task()
    float = point_measure(samples=100, rate=10000)
"""
#pylint: disable=E1101
##PyDAQmx has all of these functions, its just wonky

#Python imports
from functools import wraps
import time

#3rd party imports
import numpy as np
import PyDAQmx as pydaq

#Astrocomb imports
import eventlog as log
import ac_excepts

#Private functions
def _handle_daq_error(func):
    """A function decorator that handles daq errors."""
    @wraps(func)
    def attempt_func(self, *args, **kwargs):
        """Wrapped function"""
        try:
            result = func(self, *args, **kwargs)
            return result
        except pydaq.DAQError as err:
            log.log_error(func.__module__, func.__name__, err)
            self.clear_task() #May be problematic if err raised while ending task
            raise ac_excepts.DAQError('See previous error', _handle_daq_error)
    return attempt_func


class DAQAnalogIn(object):
    """Defines basic DAQ actions."""
    @log.log_this()
    def __init__(self, device_address, chan_num):
        """Initializes attributes."""
        self.address = device_address
        self.chan_num = chan_num
        self.params = {}
        self.task_handle = None
        self.chan_name = None

    @_handle_daq_error
    @log.log_this()
    def analog_in(self, samples=None, rate=10e3, max_v=10., min_v=-10.):
        """Sets up a task handler for an analog input channel."""
        if samples is None:
        # Return the channel parameters
            return self.params
        else:
            self.clear_task()
            self.params['samples'] = samples
            self.params['rate'] = rate
            self.params['max_v'] = max_v
            self.params['min_v'] = min_v
            self.chan_name = '{0:}/ai{1:}'.format(self.address, self.chan_num)
            self.task_handle = pydaq.TaskHandle()

            pydaq.DAQmxCreateTask('', pydaq.byref(self.task_handle))

            pydaq.DAQmxCreateAIVoltageChan(self.task_handle, self.chan_name, '',
                                           pydaq.DAQmx_Val_Cfg_Default,
                                           self.params['min_v'],
                                           self.params['max_v'],
                                           pydaq.DAQmx_Val_Volts, None)

            pydaq.DAQmxCfgSampClkTiming(self.task_handle, '',
                                        self.params['rate'],
                                        pydaq.DAQmx_Val_Rising,
                                        pydaq.DAQmx_Val_FiniteSamps,
                                        self.params['samples'])

    @_handle_daq_error
    @log.log_this()
    def read_analog_in(self):
        """Reads from analog input channel that has a task handler."""
        read = pydaq.int32()
        data = np.zeros((self.params['samples'],), dtype=pydaq.float64)
        self.start_task()
        pydaq.DAQmxReadAnalogF64(self.task_handle, self.params['samples'],
                                 self.params['max_v'],
                                 pydaq.DAQmx_Val_GroupByChannel, data,
                                 self.params['samples'],
                                 pydaq.byref(read), None)
        self.stop_task()
        return data

    @_handle_daq_error
    @log.log_this()
    def start_task(self, timeout=5):
        started = False
        start_time = time.time()
        while (not started) and (time.time()-start_time < timeout):
            try:
                pydaq.DAQmxStartTask(self.task_handle)
            except pydaq.DAQError as daq_err:
                if daq_err.error == -50103: # "The specified resource is reserved."
                    pass
                else:
                    raise daq_err
            else:
                started = True
        if not started:
            raise pydaq.DAQError(-50103)
            
    @_handle_daq_error
    @log.log_this()
    def stop_task(self):
        """Stops DAQ, releasing the resource while keeping the task handle"""
        if self.task_handle:
            pydaq.DAQmxStopTask(self.task_handle)

    @_handle_daq_error
    @log.log_this()
    def clear_task(self):
        """Stops and Clears the DAQ task handle"""
        if self.task_handle:
            self.stop_task()
            pydaq.DAQmxClearTask(self.task_handle)
        
    @log.log_this()
    def point_measure(self, samples=100, rate=10e3):
        """Averages over a quick data run to return one point"""
        self.create_analog_in(samples, rate)
        result = np.average(self.read_analog_in())
        self.clear_task()
        return result
