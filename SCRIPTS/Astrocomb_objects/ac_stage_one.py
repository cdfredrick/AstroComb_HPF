# -*- coding: utf-8 -*-
"""
Created on Tue Aug 01 15:14:41 2017

@author: Wesley Brand

Public class:
    StageOne(object)

Public methods: 
    TF = stage_one_startup_sequence()
    TF = query_lock_status()
"""
#pylint: disable=R0913
##All the arguments are hard coded, don't care that there's a lot of them


#Astrocomb imports
import ilx_driver
import thermocube_driver
import simple_daq_driver
import eventlog as log


#Constants
RIO_CARD_NUM = 0 #NEED correct ILX card number of rio laser!!!
PREAMP_CARD_NUM = 1 #NEED correct ILX card number of preamp!!!
RIO_PD_CHAN = 3 #NEED Correct analog in channel of monitor photodiode!!!
RIO_PD_THRESHOLD = 0.5 #NEED correct threshold value in volts!!!
DC_BIAS_CHAN = 4 #NEED Correct analog in channel of EO Comb DC BIAS!!!
DC_BIAS_THRESHOLD = 0.5 #NEED correct threshold value in volts!!!


def connor_locked():
    """A placeholder function, remove later."""
    return True


class StageOne(object):
    """Holds all of the first stage device objects and startup methods."""
    def __init__(self, rio_card=RIO_CARD_NUM, preamp_card=PREAMP_CARD_NUM,
                 pd_chan=RIO_PD_CHAN, pd_threshold=RIO_PD_THRESHOLD,
                 dc_chan=DC_BIAS_CHAN, dc_threshold=DC_BIAS_THRESHOLD):
        """Creates python objects for all stage 1 devices."""
        #NEED correct address put into ilx_driver!!!
        self.ilx = ilx_driver.ILX()
        self.rio_laser = ilx_driver.LDControl(self.ilx, rio_card)
        self.preamp = ilx_driver.LDControl(self.ilx, preamp_card)
        self.rio_pd_monitor = simple_daq_driver.SimpleDAQ(pd_chan,
                                                          pd_threshold)
        #NEED correct analog in channels in thermocube_driver!!!
        self.thermocube = thermocube_driver.ThermoCube()
        self.dc_bias = simple_daq_driver.SimpleDAQ(dc_chan, dc_threshold)

    def stage_one_startup_sequence(self):
        """Runs through start up commands."""
        if not self._enable_rio():
            return False
        if not self.rio_pd_monitor.query_threshold('Rio not emiting enough power!'):
            return False
        if not self._enable_preamp():
            return False
        if not self.query_lock_status():
            return False
        if not self.thermocube.query_alarms():
            return False
        if not self.dc_bias.query_threshold('EO Comb is off!'):
            return False
        #if not Turn RF Oscillator on
        #    return False
        return True


    @log.log_this()
    def _enable_rio(self):
        """Checks that tec is on and then turns on the rio laser."""
        if not self.rio_laser.query_tec_on():
            self.rio_laser.enable_tec(True)
            if not self.rio_laser.query_tec_on():
                log.log_warn(__name__, 'enable_rio',
                             'Rio TEC will not turn on!')
                return False
        self.rio_laser.enable_las(True)
        if not self.rio_laser.query_las_on():
            log.log_warn(__name__, 'enable_rio',
                         'Rio laser will not turn on!')
            return False
        return True

    @log.log_this()
    def _enable_preamp(self):
        """Turns on the preamp."""
        if not self.preamp.query_tec_on():
            self.preamp.enable_tec(True)
            if not self.preamp.query_tec_on():
                log.log_warn(__name__, 'enable_preamp',
                             'Preamp TEC will not turn on!')
                return False
        self.preamp.enable_las(True)
        if not self.preamp.query_las_on():
            log.log_warn(__name__, 'enable_rio',
                         'Preamp laser will not turn on!')
            return False
        return True

    @log.log_this()
    def query_lock_status(self):
        """ Sees if Connor's lock is established."""
        if not connor_locked():
            log.log_warn(__name__, 'query_lock_status',
                         'Not locked to Connors laser!')
            return False
        return True
