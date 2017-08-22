# -*- coding: utf-8 -*-
"""
Created on Fri Aug 18 15:59:26 2017

@author: Wesley Brand
"""
#Python imports
import time

#Astrocomb imports
import visa_objects as vo
import eventlog as log
import ac_excepts


#Constants
FIBERLOCK_ADDRESS = '' #ADD ME!!
FIBERLOCK_INT_THRESH = 0 #ADD ME!!, the minimum intensity to lock.  =1-2000


class FiberLock(vo.Visa):
    """Holds TEM fiberlock's attributes and method library."""

#General methods

    @log.log_this()
    def __init__(self, res_address=FIBERLOCK_ADDRESS,
                 int_threshold=FIBERLOCK_INT_THRESH):
        super(FiberLock, self).__init__(res_address)
        self.res = super(FiberLock, self).open_resource()
        if self.res is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create TEM FiberLock instrument!', self.__init__)
        self.res.term_chars = 'CR'
        self.int_threshold = int_threshold

    @log.log_this()
    def search_and_lock(self):
        """ """
        self.res.write('ScanM_Mode=2') #Search
        time.sleep(10)
        if not self.query_lock_status:
            raise ac_excepts.FiberLockError('Not meeting threshold power',
                                            self.search_and_lock)
        self.res.write('ScanM_Mode=3') #Lock, its unclear from manual if 
                                       #this is redundant. i.e. autolocks
                                       #at end of search

#Query methods

    @log.log_this()
    def query_lock_status(self):
        """Checks the intensity and compares to threshold, returns T/F."""
        fl_vars = self.res.query('FL_PrintVars')
        #The manual doesn't give enough information to extract the intensity
        #   some experimentation required 
        intensity = int(fl_vars[0:3]) #??? Can the string be sliced like this,
                                 # or do we need to cut it at a comma?
                                 # Intensity is the first value? followed by x
                                 # and y positions
        if intensity < self.int_threshold:
            return False
        return True