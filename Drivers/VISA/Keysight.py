# -*- coding: utf-8 -*-
"""
Created on Tue May  1 11:41:13 2018

@author: Connor
"""


# %% Modules ------------------------------------------------------------------

#Astrocomb imports
from Drivers.VISA import VISAObjects as vo
from Drivers.Logging import ACExceptions as ac_excepts
from Drivers.Logging import EventLog as log

# %% DC Power Supply
class E36103A(vo.VISA):
#General Methods
    @log.log_this()
    def __init__(self, res_address):
        res_manager = vo.ResourceManager()
        super(E36103A, self).__init__(res_address, res_manager=res_manager)
        if self.resource is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create Keysight E36103A instrument!', self.__init__)
    
    def voltage(self):
        '''
        MEASure[:VOLTage][:DC]?
        
        Returns the sensed DC output voltage in volts in the format
        "1.23456789E+00". Use the [SOURce:]VOLTage:SENSe[:SOURce] command to
        specify whether the voltage uses internal or external (remote) sensing
        '''
        output_voltage = float(self.query('MEASure:VOLTage:DC?').strip())
        return output_voltage
    
    def voltage_setpoint(self, set_voltage=None):
        '''
        [SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude] <voltage>
        [SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude]?
        
        Sets the output voltage in volts. The query returns a number of the
        form "+#.########E+##".
        '''
        if (set_voltage == None):
            set_voltage = float(self.query('SOURce:VOLTage:LEVel:IMMediate:AMPLitude?').strip())
            return set_voltage
        else:
            self.write('SOURce:VOLTage:LEVel:IMMediate:AMPLitude {:}'.format(set_voltage))
    
    def output(self, set_state=None):
        '''
        OUTPut[:STATe] ON | 1 | OFF | 0
        OUTPut[:STATe]?
        
        Enables or disables the instrument's output.The query returns 0 (OFF)
        or 1 (ON). At *RST, the output state is off.
        '''
        if (set_state == None):
            set_state = int(self.query('OUTPut:STATe?').strip())
            return bool(set_state)
        else:
            self.write('OUTPut:STATe {:}'.format(int(set_state)))
