# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 16:11:51 2017

@author: Wesley Brand

Module thermocube

Public class:
    ThermoCube(daq_object.DAQAnalogIn)

Public method:
    query_alarms() #Raise error if either alarm on, otherwise nothing

"""


#Astrocomb imports
import eventlog as log
import daq_objects as do
import ac_excepts


#Constants
TEMP_ALARM_CHANNEL = 0 #DAQ analog input channel ##NEEDS correct number!!!
SYSTEM_ALARM_CHANNEL = 1 #DAQ analog input channel ##NEEDS correct number!!!


class ThermoCube(do.DAQAnalogIn):
    """Holds daq data for Thermo Cube and checks the analog out for alarm."""

    def __init__(self, temp_chan=TEMP_ALARM_CHANNEL,
                 sys_chan=SYSTEM_ALARM_CHANNEL):
        self.temp_alarm = super(ThermoCube, self).__init__(temp_chan)
        self.sys_alarm = super(ThermoCube, self).__init__(sys_chan)

#Query methods

    def query_alarms(self):
        """Returns True if alarm is active."""
        temp = self.temp_alarm.point_measure()
        sys = self.sys_alarm.point_measure()
        attempts = 0
        while True:
            retry = False
            if temp >= 4.3:
                pass #In range, do nothing
            elif temp < 0.7:
                raise ac_excepts.TempError(
                    'Thermocube temperature is out of range',
                    self.query_alarms)
            else:
                retry = True
                channel = 'temp'
                log.log_warn(__name__, 'query_alarms',
                             'Thermocube temp alarm out of voltage range')

            if sys >= 4.3:
                pass #In range, do nothing
            elif sys < 0.7:
                raise ac_excepts.TempError('Thermocube system error!',
                                           self.query_alarms)
            else:
                retry = True
                channel = 'system'
                log.log_warn(__name__, 'query_alarms',
                             'Thermocube system alarm out of voltage range')

            if not retry: #retries if either signal is an intermediate value
                return
            if attempts == 3: #only 3 retries allowed, before throws error
                raise ac_excepts.TempError(
                    'Thermocube %s alarm is out of voltage range!' % channel,
                    self.query_alarms)
            attempts += 1
