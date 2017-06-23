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

def point_measure(daq_object, samples=100, rate=10000):
    """Averages over a quick data run to return one point"""
    daq_object.create_analog_in(samples, rate)
    result = np.average(daq_object.read_analog_in())
    daq_object.end_task()
    return result

def data_loop(daq1, daq2, loops):
    """Takes some data from the DAQ"""
    tempdata = []
    systemdata = []
    for i in np.arange(loops):
        tempdata.append(point_measure(daq1))
        systemdata.append(point_measure(daq2))
        if tempdata[i] > 4.3:
            print 'Temp Normal'
        elif tempdata[i] < 0.7:
            print 'Temp Alarm!'
        else:
            print 'Temp Alert'
        if systemdata[i] > 4.3:
            print 'System Normal'
        elif systemdata[i] < 0.7:
            print 'System Alarm!'
        else:
            print 'System Alert'
    plt.plot(systemdata)
    plt.show()
    plt.plot(tempdata)

log.start_logging()

TEMPALARM = daq.DAQ(0)
SYSTEMALARM = daq.DAQ(1)
data_loop(TEMPALARM, SYSTEMALARM, 100)
