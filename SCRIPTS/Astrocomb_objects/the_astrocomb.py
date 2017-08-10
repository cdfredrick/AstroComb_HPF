# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 11:16:09 2017

@author: Wesley Brand

Public class:
    AstroComb

Public methods:
    main_startup_sequence()
"""

#Python imports

#3rd party imports

#Astrocomb imports
import eventlog as log
import ac_excepts
import ac_stage_one
import ac_stage_two
import ac_stage_three
import ac_stage_four


class AstroComb(object):
    """The master object that contains all devices and system commands."""

    def __init__(self):
        log.start_logging()
        try:
            self.stage1 = ac_stage_one.StageOne()
            self.stage2 = ac_stage_two.StageTwo()
            self.stage3 = ac_stage_three.StageThree()
            self.stage4 = ac_stage_four.StageFour()
        except ac_excepts.VirtualDeviceError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            #Stop the next process

    def main_startup_sequence(self):
        """Starts all of the devices in the comb, while checks if working."""
        try:
            self.stage1.stage_one_startup_sequence()
            self.stage2.stage_two_startup_sequence()
            self.stage3.stage_three_startup_sequence()
            self.stage4.stage_four_startup_sequence()
        except ac_excepts.StartupError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            #Don't try anything else
