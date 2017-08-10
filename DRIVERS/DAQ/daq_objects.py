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
            self.end_task() #May be problematic if err raised while ending task
            raise ac_excepts.DAQError('See previous error', _handle_daq_error)
    return attempt_func


class DAQAnalogIn(object):
    """Defines basic DAQ actions."""
    @log.log_this()
    def __init__(self, chan_num):
        """Initializes attributes."""
        self.chan_num = chan_num
        self.params = {}
        self.task_handle = None
        self.chan_name = None

    @_handle_daq_error
    @log.log_this()
    def create_analog_in(self, n_samples, log_rate, max_v=10., min_v=-10.):
        """Sets up a task handler for an analog input channel."""
        self.params['samples'] = n_samples
        self.params['rate'] = log_rate
        self.params['max_v'] = max_v
        self.params['min_v'] = min_v
        self.chan_name = 'Dev1/ai%s' % self.chan_num
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
        pydaq.DAQmxStartTask(self.task_handle)

        pydaq.DAQmxReadAnalogF64(self.task_handle, self.params['samples'],
                                 self.params['max_v'],
                                 pydaq.DAQmx_Val_GroupByChannel, data,
                                 self.params['samples'],
                                 pydaq.byref(read), None)
        return data

    @_handle_daq_error
    @log.log_this()
    def end_task(self):
        """Stops DAQ"""
        if self.task_handle:
            pydaq.DAQmxStopTask(self.task_handle)
            pydaq.DAQmxClearTask(self.task_handle)

    def point_measure(self, samples=100, rate=10000):
        """Averages over a quick data run to return one point"""
        self.create_analog_in(samples, rate)
        result = np.average(self.read_analog_in())
        self.end_task()
        return result
