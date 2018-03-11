# -*- coding: utf-8 -*-
"""
Created on Fri Aug 11 16:09:38 2017

@author: Wesley Brand

Module: ac_stage_two

Public class:
    StageTwo(object)

Public methods:
    stage_two_warm_up()
    stage_two_start_up()
    stage_two_soft_shutdown()
    stage_two_full_shutdown()
"""

#Python imports
import time

#Astrocomb imports
import eventlog as log
import ac_excepts


class StageTwo(object):
    """Holds all of the second stage device objects and startup methods."""

    def __init__(self, s2_dict):
        self.cybel = s2_dict['cybel']
        self.yokogawa = s2_dict['yokogawa']
        self.tem_controller1 = s2_dict['tem_controller1']

    @log.log_this(20)
    def stage_two_warm_up(self):
        """Turns on the TECs."""
        try:
            self._cybel_tec_start(False)
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Stage 2 warm up failed',
                                          self.stage_two_warm_up)

    @log.log_this(20)
    def stage_two_start_up(self):
        """Runs through start up commands."""
        try:
            self._cybel_tec_start()
            self._cybel_pump_start()
            #Turn on TEM controller
            self._verify_coupling()
            self._ramp_cybel_power()
            self.yokogawa.manual_spectrum_verify()
        except:
            raise ac_excepts.StartupError('Stage 2 start up failed',
                                          self.stage_two_start_up)

    @log.log_this(20)
    def stage_two_soft_shutdown(self):
        """Turns off cybel pumps, not TECs."""
        try:
            #Turn off TEM fiber controller
            self._soft_disable_cybel_pumps()
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Stage 2 soft shutdown failed',
                                           self.stage_two_soft_shutdown)

    @log.log_this(20)
    def stage_two_full_shutdown(self):
        """Turns off all pumps and TECs, closes cybel virtual object."""
        try:
            #Turn off TEM fiber controller
            self._full_disable_cybel_pumps()
            self.cybel.close()
        except ac_excepts.AstroCombExceptions as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Stage 2 full shutdown failed',
                                           self.stage_two_full_shutdown)

    @log.log_this()
    def _cybel_tec_start(self, force_temp_in_error_range=True):
        """Starts and checks the Cybel TECs."""
        for i in [2, 3]:
            if not self.cybel.query_tec_status(i):
                self.cybel.enable_tec(i, True)
                time.sleep(1)
                if not self.cybel.query_tec_status(i):
                    raise ac_excepts.EnableError(
                        'Cybel TEC %s did not turn on!' % i,
                        self._cybel_tec_start)
        time_len = 20
        while force_temp_in_error_range: #while is effectively an if here
            time.sleep(time_len)
            if self.cybel.query_temp_error == (True, True):
                break
            while True:
                retry = input('Cybel temperature not within error range, wait\
                              longer? y=yes, n=abort')
                if retry == 'y':
                    time_len *= 2
                    break
                elif retry == 'n':
                    raise ac_excepts.TempError(
                        'Cybel temperature not within error range!',
                        self._cybel_tec_start)
                else:
                    print "Must enter 'y' or 'n'"

    @log.log_this()
    def _cybel_pump_start(self):
        """Starts and checks the Cybel pumps."""
        self.cybel.set_pump_current(3, 0)
        for i in [2, 3]:
            self.cybel.enable_pump(i, True)
            time.sleep(1)
            if not self.cybel.query_pump_status(i):
                raise ac_excepts.EnableError(
                    'Cybel pump %s did not turn on!' % i,
                    self._cybel_pump_start)
        analog_out_dict = self.cybel.query_analog_output_values()
        if analog_out_dict['pump2_current'] <= 2.2*0.95 or\
            analog_out_dict['pump2_current'] >= 2.2*1.05:
            raise ac_excepts.CurrentError('Cybel pump 2 is not turning on to\
                                          manual specified current.',
                                          self._cybel_pump_start)
    @log.log_this()
    def _verify_coupling(self):
        """Verify with TEM fiberlock."""
        #Use TEM Controller to verify coupling
        pass

    @log.log_this()
    def _ramp_cybel_power(self):
        """Increases pump 3 current by 1A until at max of 7."""
        for i in range(1, 7):
            self.cybel.set_pump_current(3, i)
            time.sleep(2)
            analog_out_dict = self.cybel.query_analog_output_values()
            if analog_out_dict['pump3_current'] <= i*0.95 or\
                analog_out_dict['pump3_current'] >= i*1.05:
                raise ac_excepts.CurrentError('Cybel pump 3 is not pumping at\
                                              the correct current.',
                                              self._ramp_cybel_power)
            if not self.cybel.query_temp_error == (True, True):
                raise ac_excepts.TempError(
                    'Cybel temperature not within error range!',
                    self._ramp_cybel_power)
            self._verify_coupling()

    @log.log_this()
    def _soft_disable_cybel_pumps(self):
        """Turns off current to pump 3 and turns off pumps."""
        self.cybel.set_pump_current(3, 0)
        time.sleep(1)
        analog_out_dict = self.cybel.query_analog_output_values()
        if not analog_out_dict['pump3_current'] <= 0.2:
            raise ac_excepts.CurrentError('Cybel pump 3 is not turning off\
                                          current.',
                                          self._soft_disable_cybel_pumps)
        for i in [2, 3]:
            self.cybel.enable_pump(i, False)
            time.sleep(1)
            if self.cybel.query_pump_status(i):
                raise ac_excepts.EnableError(
                    'Cybel pump %s did not turn off!' % i,
                    self._soft_disable_cybel_pumps)

    @log.log_this()
    def _full_disable_cybel_pumps(self):
        """Turns off pumps completely including TECs."""
        self._soft_disable_cybel_pumps()
        for i in [2, 3]:
            self.cybel.enable_tec(i, False)
            time.sleep(1)
            if self.cybel.query_tec_status(i):
                raise ac_excepts.EnableError(
                    'Cybel TEC %s did not turn off!' % i,
                    self._full_disable_cybel_pumps)
