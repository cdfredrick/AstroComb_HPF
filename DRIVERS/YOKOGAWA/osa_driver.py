# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 07:26:32 2017

@authors: AJ Metcalf and Wesley Brand

Module: osa_driver
    import osa_driver as yok

Requires:
    eventlog.py
    visa_objects.py

Public class:
    OSA

with Public Methods:
    __init__(res_name, res_address)
    close()
    query_identity()
    query_spectrum()


"""

import numpy as np
import visa_objects as vo
import eventlog as log

OSA_NAME = 'OSA'
OSA_ADDRESS = u'GPIB0::28::INSTR'

class OSA(vo.Visa):
    """Holds Yokogawa OSA's attributes and method library."""
    @log.log_this(20)
    def __init__(self, res_name, res_address):
        super(OSA, self).__init__(res_name, res_address)
        self.res = super(OSA, self).open_resource()
        if self.res is None:
            print 'Could not create OSA instrument!'
            return
        self.__set_command_format()

    @log.log_this()
    def close(self):
        """Ends device session"""
        self.res.close()


    @vo.handle_timeout
    @log.log_this()
    def __set_command_format(self):
        """Sets the OSA's formatting to AQ6370 style, should always be 1"""
        self.res.write('CFORM1')


    @vo.handle_timeout
    @log.log_this()
    def query_identity(self):
        """Queries OSA's identity"""
        ident = self.res.query('*IDN?')
        print 'OSA Identity = %s' % ident

    @vo.handle_timeout
    @log.log_this()
    def query_spectrum(self):
        """Queries OSA's spectrum"""
        y_trace = self.res.query(':TRACE:DATA:Y? TRA')
        x_trace = self.res.query(':TRACE:DATA:X? TRA')
        lambdas = np.fromstring(x_trace, sep=',')*1000000000
        levels = np.fromstring(y_trace, sep=',')
        lambdas = lambdas[1:]
        levels = levels[1:]
        return lambdas, levels
        #startWL = float(osa.query("STAWL?")[0:-2])
        #stopWL  = float(osa.query("STPWL?")[0:-2])
        #self.lambdas = np.linspace(startWL,stopWL,nPoints)
        