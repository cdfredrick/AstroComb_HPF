# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 16:11:51 2017

@author: Wesley Brand

Module thermocube
"""

import numpy as np
import matplotlib.pyplot as plt
import eventlog as log
import daq_objects as daq


log.start_logging()

THERMO = daq.DAQ(0)

data = []

for i in np.arange(20):
    THERMO.create_analog_in(5, 100.)
    data.append(np.average(THERMO.read_analog_in()))
    THERMO.end_task()
    if data[i] > 4.3:
        print 'Normal'
    elif data[i] < 0.7:
        print 'Alarm!'
    else:
        print 'Alert'
plt.plot(data)












#import numpy as np
#import PyDAQmx
#import matplotlib.pyplot as plt
#
#n_samples = 100
#log_rate = 100.
#
#task_handle = daq.TaskHandle()
#read = daq.int32()
#data = np.zeros((n_samples,), dtype=daq.float64)
#
#try:
#    # DAQmx Configure Code
#    daq.DAQmxCreateTask('', daq.byref(task_handle))
#    daq.DAQmxCreateAIVoltageChan(task_handle, 'Dev1/ai0', '',
#                                 daq.DAQmx_Val_Cfg_Default, -10.0, 10.0,
#                                 daq.DAQmx_Val_Volts, None)
#    daq.DAQmxCfgSampClkTiming(task_handle, '', log_rate, daq.DAQmx_Val_Rising,
#                              daq.DAQmx_Val_FiniteSamps, n_samples)
#
#    # DAQmx Start Code
#    daq.DAQmxStartTask(task_handle)
#
#    # DAQmx Read Code
#    daq.DAQmxReadAnalogF64(task_handle, n_samples, 10.0,
#                           daq.DAQmx_Val_GroupByChannel, data, n_samples,
#                           daq.byref(read), None)
#
#    print 'Acquired %d points' % read.value
#    plt.plot(data)
#except daq.DAQError as err:
#    print 'DAQmx Error: %s' % err
#finally:
#    if task_handle:
#        # DAQmx Stop Code
#        daq.DAQmxStopTask(task_handle)
#        daq.DAQmxClearTask(task_handle)
