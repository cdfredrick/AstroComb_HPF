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
import ac_excepts


#Constants
RIO_CARD_NUM = 0 #NEED correct ILX card number of rio laser!!!
PREAMP_CARD_NUM = 1 #NEED correct ILX card number of preamp!!!
RIO_PD_CHAN = 3 #NEED Correct analog in channel of monitor photodiode!!!
RIO_PD_THRESHOLD = 0.5 #NEED correct threshold value in volts!!!
DC_BIAS_CHAN = 4 #NEED Correct analog in channel of EO Comb DC BIAS!!!
DC_BIAS_THRESHOLD = 0.5 #NEED correct threshold value in volts!!!


def rio_locked_to_connors_laser():
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
                                                          'Rio laser power',
                                                          pd_threshold)
        #NEED correct analog in channels in thermocube_driver!!!
        self.thermocube = thermocube_driver.ThermoCube()
        self.eo_comb_dc_bias = simple_daq_driver.SimpleDAQ(dc_chan,
                                                           'EO Comb voltage',
                                                           dc_threshold)

    @log.log_this()
    def stage_one_startup_sequence(self):
        """Runs through start up commands."""
        try:
            self._enable_ilx_device(self.rio_laser)
            self.rio_pd_monitor.query_over_threshold()
            self._enable_ilx_device(self.preamp)
            self.query_lock_status()
            self.thermocube.query_alarms()
            self.eo_comb_dc_bias.query_under_threshold()
            #Turn RF Oscillator on
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 1 start up failed',
                                          self.stage_one_startup_sequence)

    @log.log_this()
    def stage_one_soft_shutdown_sequence(self):
        """Turns off all lasers only, not TECs."""
        try:
            #Turn RF Oscillator off
            self._soft_disable_ilx_device(self.preamp)
            self._soft_disable_ilx_device(self.rio_laser)
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 1 soft shutdown failed',
                                          self.stage_one_soft_shutdown_sequence)

    @log.log_this()
    def stage_one_hard_shutdown_sequence(self):
        """Turns off all lasers only, not TECs."""
        try:
            #Turn RF Oscillator off
            self._hard_disable_ilx_device(self.preamp)
            self._hard_disable_ilx_device(self.rio_laser)
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 1 hard shutdown failed',
                                          self.stage_one_soft_shutdown_sequence)

    @log.log_this()
    def _enable_ilx_device(self, device):
        """Checks that tec is on and then turns on the laser."""
        if not device.query_tec_on():
            device.enable_tec(True)
            if not device.query_tec_on():
                raise ac_excepts.EnableError(
                    '%s TEC will not turn on!' % device.__name__,
                    self._enable_ilx_device)

        device.enable_las(True)
        if not device.query_las_on():
            raise ac_excepts.EnableError(
                '%s laser will not turn on!' %device.__name__,
                self._enable_ilx_device)

    @log.log_this()
    def _soft_disable_ilx_device(self, device):
        """Turns off device laser, leaves TEC on."""
        device.enable_las(False)
        if device.query_las_on():
            raise ac_excepts.EnableError(
                '%s will not turn off!' % device.__name__,
                self._soft_disable_ilx_device)

    @log.log_this()
    def _hard_disable_ilx_device(self, device):
        """Turns off device laser and TEC."""
        self._soft_disable_ilx_device(device)
        device.enable_tec(False)
        if device.query_tec_on():
            raise ac_excepts.EnableError(
                '%s TEC will not turn off!' % device.__name__,
                self._enable_ilx_device)

    @log.log_this()
    def query_lock_status(self):
        """ Sees if Connor's lock is established."""
        if not rio_locked_to_connors_laser():
            raise ac_excepts.LaserLockError('Not locked to Connors laser!',
                                            self.query_lock_status)
