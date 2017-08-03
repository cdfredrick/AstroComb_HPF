# -*- coding: utf-8 -*-
"""
Created on Thu Aug 03 12:47:46 2017

@author: Wesley Brand

Module simple_daq_driver

Public class:
    SimpleDAQ(daq_objects.DAQAnalogIn)

Public methods:
    float = query_analog #Volts
    TF = query_threshold
"""

import daq_objects as do
import eventlog as log

class SimpleDAQ(do.DAQAnalogIn):
    """Holds daq data for a simple analog channel monitor."""

    def __init__(self, chan_num, threshold=0):
        self.daq_object = super(SimpleDAQ, self).__init__(chan_num)
        self.threshold = threshold

    def query_analog(self):
        """Returns analog measurement in volts."""
        return self.daq_object.point_measure()

    def query_threshold(self, warning_text):
        """Returns True if value exceeds threshold."""
        volts = self.daq_object.point_measure()
        if volts >= self.threshold:
            return True
        log.log_warn(__name__, 'query_threshold', warning_text)
        return False
