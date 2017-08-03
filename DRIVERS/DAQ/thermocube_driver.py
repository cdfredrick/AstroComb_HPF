# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 16:11:51 2017

@author: Wesley Brand

Module thermocube

Public class:
    ThermoCube(daq_object.DAQAnalogIn)

Public method:
    TF = query_alarms()

"""

import eventlog as log
import daq_objects as do

TEMP_ALARM_CHANNEL = 0 #DAQ analog input channel ##NEEDS correct number!!!
SYSTEM_ALARM_CHANNEL = 1 #DAQ analog input channel ##NEEDS correct number!!!


class ThermoCube(do.DAQAnalogIn):
    """Holds daq data for Thermo Cube and checks the analog out for alarm."""

    def __init__(self, temp_chan=TEMP_ALARM_CHANNEL,
                 sys_chan=SYSTEM_ALARM_CHANNEL):
        self.temp_alarm = super(ThermoCube, self).__init__(temp_chan)
        self.sys_alarm = super(ThermoCube, self).__init__(sys_chan)

    def query_alarms(self):
        """Returns True if alarm is active."""
        temp = self.temp_alarm.point_measure()
        sys = self.sys_alarm.point_measure()
        attempts = 0
        while True:
            if temp > 4.3:
                alarm1 = False
            elif temp < 0.7:
                alarm1 = True
                log.log_warn(__name__, 'check_alarms',
                             'Thermocube temperature is out of range!', 50)
            else:
                alarm1 = 'Retry'
                log.log_warn(__name__, 'check_alarms',
                             'Thermocube temp alarm outside of voltage range!')

            if sys > 4.3:
                alarm2 = False
            elif sys < 0.7:
                alarm2 = True
                log.log_warn(__name__, 'check_alarms',
                             'Thermocube system error!', 50)
            else:
                alarm2 = 'Retry'
                log.log_warn(__name__, 'check_alarms',
                             'Thermocube system alarm outside of voltage range!')

            if alarm1 is True or alarm2 is True:
                return True
            if alarm1 != 'Retry' and alarm2 != 'Retry':
                return False
            if attempts == 3:
                return True
            attempts += 1

#def data_loop(daq1, daq2, loops):
#    """Takes some data from the DAQ"""
#    tempdata = []
#    systemdata = []
#    for i in np.arange(loops):
#        tempdata.append(point_measure(daq1))
#        systemdata.append(point_measure(daq2))
#        if tempdata[i] > 4.3:
#            print 'Temp Normal'
#        elif tempdata[i] < 0.7:
#            print 'Temp Alarm!'
#        else:
#            print 'Temp Alert'
#        if systemdata[i] > 4.3:
#            print 'System Normal'
#        elif systemdata[i] < 0.7:
#            print 'System Alarm!'
#        else:
#            print 'System Alert'
#    plt.plot(systemdata)
#    plt.show()
#    plt.plot(tempdata)
#
#log.start_logging()
#
#TEMPALARM = daq.DAQ(0)
#SYSTEMALARM = daq.DAQ(1)
#data_loop(TEMPALARM, SYSTEMALARM, 100)
