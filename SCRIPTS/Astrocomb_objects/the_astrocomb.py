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
import ac_stage_one
import ac_stage_two
import ac_stage_three
import ac_stage_four


class AstroComb(object):
    """The master object that contains all devices and system commands."""
    
    def __init__(self):
        log.start_logging()
        self.stage1 = ac_stage_one.StageOne()
        self.stage2 = ac_stage_two.StageTwo()
        self.stage3 = ac_stage_three.StageThree()
        self.stage4 = ac_stage_four.StageFour()

    def main_startup_sequence(self):
        """Starts all of the devices in the comb, while checks if working."""
        if not self.stage1.stage_one_startup_sequence():
            log.log_warn(__name__, 'main_startup_sequence',
            'Start up aborted!')
            return

        if not self.stage2.stage_two_startup_sequence():
            log.log_warn(__name__, 'main_startup_sequence',
            'Start up aborted!')
            return

        if not self.stage3.stage_three_startup_sequence():
            log.log_warn(__name__, 'main_startup_sequence',
            'Start up aborted!')
            return

        if not self.stage4.stage_four_startup_sequence():
            log.log_warn(__name__, 'main_startup_sequence',
            'Start up aborted!')
            return
