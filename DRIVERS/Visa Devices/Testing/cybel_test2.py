# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 10:47:11 2017

@author: Wesley Brand
"""

import visa
import pyvisa

CYBEL_ADDRESS = u'ASRL3::INSTR'

def initiate(address):
    """Opens Cybel instrument and sets channel characteristics."""
    cyb = visa.ResourceManager().open_resource(address)
    cyb.term_chars = 'CR+LF'
    cyb.timeout = 3
    cyb.baud_rate = 57600
    cyb.data_bits = 8
    cyb.stop_bits = pyvisa.constants.StopBits.one
    print 'Initiated!'
    return cyb

def echo(cyb, is_on):
    """Turns device echo on or off."""
    if is_on is True:
        cyb.write('SEE')
        print  'Echo on'
    if is_on is False:
        cyb.write('SEN')
        print 'Echo off'

def basic_queries(cyb):
    """Attempts some basic intrument queries."""
    print 'Serial num: ', cyb.query('CO')
    print 'Firmware: ', cyb.query('CPLD?')
    print 'Temp error: ', cyb.query('FB?')
    print 'Trigger and laser: ', cyb.query('TS?')

def run():
    """Initiates and queries Cybel instrument."""
    cyb = initiate(CYBEL_ADDRESS)
    try:
        echo(cyb, False)
        basic_queries(cyb)
    finally:
        cyb.close()

if __name__ == '__main__':
    run()
