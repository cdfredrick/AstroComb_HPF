# -*- coding: utf-8 -*-
"""
Created on Fri Aug 18 15:59:26 2017

@author: Wesley Brand

Public class:
    FiberLock(visa_objects.Visa)

With public methods:

    Initiate:
        __init__(res_address)

    Enable Components:
        enable_lock(lock_on)
        enable_noise_eater_mode(noise_etater_on)

    Query:
        TF = query_lock_status()
"""
#Python imports
import time

#Astrocomb imports
import visa_objects as vo
import eventlog as log
import ac_excepts


class FiberLock(vo.Visa):
    """Holds TEM fiberlock's attributes and method library."""

#General methods

    @log.log_this()
    def __init__(self, res_address, intensity_threshold):
        super(FiberLock, self).__init__(res_address)
        if self.resource is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create TEM FiberLock instrument!', self.__init__)
        self.term_chars = 'CR'
        self.int_thresh = intensity_threshold
        self.locked = False

#Enable Methods

    
    @log.log_this()
    def enable_lock(self, lock_on=True):
        """Searches for lock position and locks there, or turns off."""
        if lock_on:
            self.write('ScanM_Mode=2') #Search
            time.sleep(10)
            self.write('ScanM_Mode=3') #Lock, its unclear from manual if
                                           #this is redundant. i.e. autolocks
                                           #at end of search
            if not self.query_lock_status():
                raise ac_excepts.CouplingkError('Not meeting threshold power',
                                                self.enable_lock)
        if not lock_on:
            self.write('ScanM_Mode=0') #Off

    
    @log.log_this()
    def enable_noise_eater_mode(self, noise_eater_on):
        """Turns on constant intensity mode."""
        if noise_eater_on and self.locked():
            self.write('FL_IntReg=1') #Noise eating on
        elif noise_eater_on and not self.locked():
            raise ac_excepts.EnableError("Can't turn on noise eater mode if\
                                         not already locked.",
                                         self.enable_noise_eater_mode)
        elif not noise_eater_on:
            self.write('FL_IntReg=0') #Noise eating off
            self.enable_lock() #Not sure if need to relock now

#Query methods

    
    @log.log_this()
    def query_lock_status(self):
        """Checks the intensity and compares to threshold, returns T/F."""
        fl_vars = self.query('FL_PrintVars')
        #The manual doesn't give enough information to extract the intensity
        #   some experimentation required
        intensity = int(fl_vars[0:3]) #??? Can the string be sliced like this,
                                 # or do we need to cut it at a comma?
                                 # Intensity is the first value? followed by x
                                 # and y positions
        if intensity < self.int_thresh:
            self.locked = False
        else:
            self.locked = True
        return self.locked
