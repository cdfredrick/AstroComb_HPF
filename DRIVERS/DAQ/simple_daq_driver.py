# -*- coding: utf-8 -*-
"""
Created on Thu Aug 03 12:47:46 2017

@author: Wesley Brand

Module simple_daq_driver

Public class:
    SimpleDAQ(daq_objects.DAQAnalogIn)

Public methods:
    float = query_analog #Volts
    query_over_threshold() #Raise error if not, otherwise nothing
    query_under_threshold() #Raise error if not, otherwise nothing
"""


#Astrocomb imports
import daq_objects as do
import ac_excepts


class SimpleDAQ(do.DAQAnalogIn):
    """Holds daq data for a simple analog channel monitor."""

    def __init__(self, chan_num, error_text, threshold=0):
        self.daq_object = super(SimpleDAQ, self).__init__(chan_num)
        self.threshold = threshold
        self.error_text = error_text # Says what quantity the channel is
                                     # monitoring i.e. 'Laser power'

#Query methods

    def query_analog(self):
        """Returns analog measurement in volts."""
        return self.daq_object.point_measure()

    def query_over_threshold(self):
        """Raises error  if value under threshold."""
        volts = self.daq_object.point_measure()
        if volts < self.threshold:
            raise ac_excepts.ThresholdError(
                self.error_text + ' is under threshold.', self.query_threshold)

    def query_under_threshold(self):
        """Raises error  if value under threshold."""
        volts = self.daq_object.point_measure()
        if volts > self.threshold:
            raise ac_excepts.ThresholdError(
                self.error_text + ' is over threshold.', self.query_threshold)
