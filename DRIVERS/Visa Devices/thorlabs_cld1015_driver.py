# -*- coding: utf-8 -*-
"""
Spyder Editor

Module: thorlabs_cld1015

by Wesley Brand

Reads data from laser diode unit and its TEC and maintains stable operating conditions
"""

import visa_objects as vo
import eventlog as log

LD_NAME = 'Thorlabs CLD1015'
LD_ADDRESS = u'USB0::0x1313::0x804F::M00328014::INSTR'

class LaserDiodeControl(vo.Visa):
    """Holds Thorlabs laser diode controller's attributes and method library."""

    #General methods

    @log.log_this(20)
    def __init__(self, res_name, res_address):
        super(LaserDiodeControl, self).__init__(res_name, res_address)
        self.res = super(LaserDiodeControl, self).open_resource()
        if self.res is None:
            print 'Could not create laser diode control instrument!'
            return

    @log.log_this(20)
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
        ld_current = self.res.query('MEASure:CURRent1?')
        ld_voltage = self.res.query('MEASure:VOLTage1?')
        ld_temp = self.res.query('MEASure:TEMPerature?')
        pd_current = self.res.query('MEASure:CURRent2?') #PD is the photodiode
        power = self.res.query('MEASure:POWer?')
        resist = self.res.query('MEASure:RESistance?')

        print 'LD Current = ' + str(ld_current)
        print 'LD Voltage = ' + str(ld_voltage)
        print 'LD Temperature = ' + str(ld_temp)
        print 'PD Current = ' + str(pd_current)
        print 'Power = ' + str(power)
        print 'Resistance= ' + str(resist)

#    def pid_control_set(self):
#        """sets pid control values"""
#        #Set Parameters to first optimize P
#        self.res.write('SOURce2:TEMPerature:SPOint ' + str(20))
#        self.res.write('SOURCE2:LCONstants:GAIN 0.2')
#        self.res.write('SOURCE2:LCONstants:INTegral 0')
#        self.res.write('SOURCE2:LCONstants:DERivative 0')
#        self.res.write('SOURCE2:LCONstants:PERiod 0.2')