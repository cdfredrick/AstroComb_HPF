# -*- coding: utf-8 -*-
"""
Created on Tue Aug 01 15:14:41 2017

@author: Wesley Brand

Public class:
    StageOne(object)

Public methods:
    stage_one_startup_sequence()
    stage_one_soft_shutdown_sequence()
    stage_one_hard_shutdown_sequence()
    query_lock_status()
"""
#pylint: disable=R0913
##All buf first argument is hard coded in this file,
## don't care that there's a lot of arguments

#Python Imports
import time

#Astrocomb imports
import eventlog as log
import ac_excepts

def rio_locked_to_connors_laser():
    """A placeholder function, remove later."""
    return True


class StageOne(object):
    """Holds all of the first stage device objects and startup methods."""
    def __init__(self, s1_dict):
        """Creates python objects for all stage 1 devices."""
        self.yokogawa = s1_dict['yokogawa']
        self.ilx = s1_dict['ilx']
        self.rio_laser = s1_dict['rio_laser']
        self.preamp = s1_dict['preamp']
        self.rio_pd_monitor = s1_dict['rio_pd_monitor']
        self.thermocube = s1_dict['thermocube']
        self.eo_comb_dc_bias = s1_dict['eo_comb_dc_bias']

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
            self.yokogawa.manual_spectrum_verify()
            log.log_warn(__name__, 'stage_one_startup_sequence', 'Stage one\
                         start up completed!', 20)
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 1 start up failed',
                                          self.stage_one_startup_sequence)

    @log.log_this()
    def stage_one_soft_shutdown(self):
        """Turns off all lasers only, not TECs."""
        try:
            #Turn RF Oscillator off
            self._soft_disable_ilx_device(self.preamp)
            self._soft_disable_ilx_device(self.rio_laser)
            log.log_warn(__name__, 'stage_one_soft_shutdown', 'Stage\
                         one soft shutdown completed!', 20)
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 1 soft shutdown failed',
                                          self.stage_one_soft_shutdown)

    @log.log_this()
    def stage_one_hard_shutdown(self):
        """Turns off all lasers and TECs, close visa devices."""
        try:
            #Turn RF Oscillator off
            self._hard_disable_ilx_device(self.preamp)
            self._hard_disable_ilx_device(self.rio_laser)
            self.ilx.close()
            self.yokogawa.close()
            log.log_warn(__name__, 'stage_one_hard_shutdown', 'Stage\
                         one hard shutdown completed!', 20)
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 1 hard shutdown failed',
                                          self.stage_one_hard_shutdown)

    @log.log_this()
    def _enable_ilx_device(self, device):
        """Checks that tec is on and then turns on the laser."""
        if not device.query_tec_on():
            device.enable_tec(True)
            time.sleep(1)
            if not device.query_tec_on():
                raise ac_excepts.EnableError(
                    '%s TEC will not turn on!' % device.__name__,
                    self._enable_ilx_device)

        device.enable_las(True)
        time.sleep(1)
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
