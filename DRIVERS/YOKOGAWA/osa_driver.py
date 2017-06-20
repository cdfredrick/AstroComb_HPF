# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 07:26:32 2017
@author: ajm6
"""

import visa_objects as vo
import eventlog as log
import numpy as np
import matplotlib.pyplot as plt



OSA_NAME = 'OSA'
OSA_ADDRESS = u'GPIB0::28::INSTR'

class OSA(vo.Visa):
    @log.log_this(20)
    def __init__(self, res_name, res_address):
        super(OSA, self).__init__(res_name, res_address)
        self.res = super(OSA, self).open_resource()
        if self.res is None:
            print 'Could not create OSA instrument!'
            return
        
    @log.log_this()  
    def close(self):
        """Ends device session"""
        self.res.close()
        
    @vo.handle_timeout
    @log.log_this()
    def test(self):
        """Returns 0 if all good, not 0 if a test fails"""
        return self.res.query('*TST?')
        
    @vo.handle_timeout
    @log.log_this()
    def read(self):
        """Queries Laser Diode Unit's current operating values"""
        osa_data = self.res.query('*IDN?')
        print 'osa_data = ' +str(osa_data)
        
        
    @vo.handle_timeout
    @log.log_this()
    def write(self):
        """Queries Laser Diode Unit's current operating values"""
        temp = self.res.write('CFORM1')
        temp = self.res.query(':TRACE:DATA:Y? TRA')
        temp2 = self.res.query(':TRACE:DATA:X? TRA')
        lambdas = np.fromstring(temp2,sep=',')*1000000000
        levels = np.fromstring(temp, sep=',')        
        lambdas[0]
        lambdas = lambdas[1:]
        levels[0]
        levels = levels[1:]
        
        #startWL = float(osa.query("STAWL?")[0:-2])
        #stopWL  = float(osa.query("STPWL?")[0:-2])
        #self.lambdas = np.linspace(startWL,stopWL,nPoints)
        lambdas,levels

        plt.plot(lambdas,levels)
        plt.xlabel('wavelength nm')
        plt.ylabel('dBm')
        plt.grid(True) 
        plt.show()