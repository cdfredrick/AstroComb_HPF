# -*- coding: utf-8 -*-
"""
Created on Thu Aug 17 14:13:03 2017

@author: Wesley Brand

Module: ac_stage_four

Public class:
    StageFour(object)

Public methods:
    stage_four_warm_up()
    stage_four_start_up()
    stage_four_soft_shutdown()
    stage_four_hard_shutdown()
"""

#Astrocomb imports
import eventlog as log
import ac_excepts


class StageFour(object):
    """Holds all of the fourth stage device objects and startup methods."""

    def __init__(self, s4_dict):
        self.yokogawa = s4_dict['yokogawa']
        self.pulse_shaper = s4_dict['pulse_shaper']

    @log.log_this(20)
    def stage_four_warm_up(self):
        """Turns on the TECs."""
        try:
            #I don't know if there is anything to turn on here
            pass
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 4 warm up failed',
                                          self.stage_four_warm_up)

    @log.log_this(20)
    def stage_four_start_up(self):
        """Runs through start up commands."""
        try:
            #Turn on pulse shaper
            self.yokogawa.manual_spectrum_verify()
        except:
            raise ac_excepts.StartupError('Stage 4 start up failed',
                                          self.stage_four_start_up)

    @log.log_this(20)
    def stage_four_soft_shutdown(self):
        """Turns off cybel pumps, not TECs."""
        try:
            #Turn off pulse shaper
            pass
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Stage 4 soft shutdown failed',
                                           self.stage_four_soft_shutdown)

    @log.log_this(20)
    def stage_four_hard_shutdown(self):
        """Turns off all pumps and TECs, closes cybel virtual object."""
        try:
            #Turn off pulse shaper including TECs if any
            pass
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Stage 4 hard shutdown failed',
                                           self.stage_four_hard_shutdown)
