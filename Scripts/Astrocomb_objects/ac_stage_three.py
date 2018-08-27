# -*- coding: utf-8 -*-
"""
Created on Thu Aug 17 14:11:47 2017

@author: Wesley Brand

Module: ac_stage_three

Public class:
    StageThree(object)

Public methods:
    stage_three_warm_up()
    stage_three_start_up()
    stage_three_soft_shutdown()
    stage_three_full_shutdown()
"""

#Astrocomb imports
import eventlog as log
import ac_excepts


class StageThree(object):
    """Holds all of the second stage device objects and startup methods."""

    def __init__(self, s3_dict):
        self.yokogawa = s3_dict['yokogawa']
        self.tem_controller2 = s3_dict['tem_controller2']
        self.nufern = s3_dict['nufern']
        self.finisar = s3_dict['finisar']

    @log.log_this(20)
    def stage_three_warm_up(self):
        """Turns on the TECs."""
        try:
            #turn on NuFern TECs
            pass
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 3 warm up failed',
                                          self.stage_three_warm_up)

    @log.log_this(20)
    def stage_three_start_up(self):
        """Runs through start up commands."""
        try:
            self.finisar.enable_waveshaper()
            self.finisar.set_waveshape() #NEED VALUES for amp, phase, port, dim
            #Check CW power?
            #Turn on NuFern amp TECs
            #Turn on NuFern amp pumps
            #Turn on TEM controller2
            self._verify_coupling()
            #self._ramp_nufern_power()
            self.yokogawa.manual_spectrum_verify()
        except:
            raise ac_excepts.StartupError('Stage 3 start up failed',
                                          self.stage_three_start_up)

    @log.log_this(20)
    def stage_three_soft_shutdown(self):
        """Turns off cybel pumps, not TECs."""
        try:
            #Turn NuFern pump current to zero
            #Turn off NuFern pumps
            #Turn off TEM controller 2
            pass
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Stage 3 soft shutdown failed',
                                           self.stage_three_soft_shutdown)

    @log.log_this(20)
    def stage_three_full_shutdown(self):
        """Turns off all pumps and TECs, closes cybel virtual object."""
        try:
            #Turn NuFern pump current to zero
            #Turn off NuFern pumps
            #Turn off TEM controller 2
            #Turn off NuFern TECs
            self.finisar.disable_waveshaper()
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Stage 3 full shutdown failed',
                                           self.stage_three_full_shutdown)

    @log.log_this()
    def _verify_coupling(self):
        """Verify with TEM fiberlock."""
        #Use TEM Controller to verify coupling
        pass
