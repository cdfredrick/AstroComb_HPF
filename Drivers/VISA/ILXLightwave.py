# -*- coding: utf-8 -*-
"""
Created on Mon Jun 26 10:31:06 2017

@author: Wesley Brand

Module: ilx_driver
#Laser diode control

Public Classes:
    ILX(vo.VISA)
    LDC(ILX)


ILX's Public Methods:

    las_chan_switch()
    tec_chan_switch()


LDC's Public Methods:

Enable:
    enable_las(las_on)
    enable_tec(tec_on)

Query laser:
    TF = query_las_on()
    str = query_las_mode()
    float = query_las_current()
    float = query_las_current_limit()
    float = query_las_current_set_point()

Set laser:
    set_las_current(current)
    set_las_current_limit(current)
    set_las_mode(mode_num)

Query TEC:
    TF = query_tec_on()
    str = query_tec_mode()
    float = query_tec_temp()

Set TEC:
    set_tec_mode(mode_num)
    set_tec_temp(temp)

"""
#pylint: disable=W0231
### Avoid ILX.__init__() in LDControl.__init__ because inherits
###  from ILX instance

# %% Modules
#Astrocomb imports
import Drivers.VISA.VISAObjects as vo
from Drivers.Logging import ACExceptions
from Drivers.Logging import EventLog as log

from functools import wraps


# %% Constants
_MARKER = object()  #To check errors in LDControl class inheritance
ILX_ADDRESS = '' #ADD ME!!!


# %% Private Functions
@log.log_this()
def _auto_connect_las(func):
    """A function decorator that handles automatic laser channel connections."""
    @wraps(func)
    def auto_connect_las(self, *args, **kwargs):
        """Wrapped function"""
        if (self.auto_connect and not(self.opened)):
            try:
                self.open_las()
                result = func(self, *args, **kwargs)
                return result
            finally:
                self.close_las()
        else:
            result = func(self, *args, **kwargs)
            return result
    return auto_connect_las

def _auto_connect_tec(func):
    """A function decorator that handles automatic TEC channel connections."""
    @wraps(func)
    def auto_connect_tec(self, *args, **kwargs):
        """Wrapped function"""
        if (self.auto_connect and not(self.opened)):
            try:
                self.open_tec()
                result = func(self, *args, **kwargs)
                return result
            finally:
                self.close_tec()
        else:
            result = func(self, *args, **kwargs)
            return result
    return auto_connect_tec


# %% ILX LDC-3900 Mainframe
class LDC3900(vo.VISA):
    """Holds commands for ILX chassis and passes commands for components."""
    @log.log_this()
    def __init__(self, visa_address, res_manager=None):
        super(LDC3900, self).__init__(visa_address, res_manager=res_manager)
        if self.resource is None:
            raise ACExceptions.VirtualDeviceError(
                'Could not create ILX instrument!', self.__init__)
        self.radix(set_radix='DEC')
    
    @log.log_this()
    def laser_display(self, z=None):
        '''
        The LASer:DISplay command enables or disables (turns off) the LASER 
        display and LASER section’s indicator LEDs. Turning the LASER display 
        and LEDs off means that a message of all blank spaces is sent to the 
        LASER display, and all of the LASER section’s indicator LEDs will be 
        turned off.
        
        The LASer:DISplay? query returns the value shown on the LASER display.
        The response will be character data which represents what is on the LASER
        display. Returns the actual (6−character) string from the output buffer
        to the LASER display. If the display is disabled, it returns " .".
        '''
        if z is None:
        # Send query
            result = self.query('LAS:DIS?')
        # Parse result
            try:
                return float(result)
            except ValueError:
                return False
        else:
        # Limit range
            z = vo.tf_to_10(z)
        # Send command
            self.write('LAS:DIS {:}'.format(['OFF','ON'][z]))
    
    @log.log_this()
    def tec_display(self, z=None):
        '''
        The TEC:DISplay command enables or disables (turns off) the TEC display
        and TEC section’s indicator LEDs. Turning the TEC display and LEDs off
        means that a message of all blank spaces is sent to the TEC display, and
        all of the TEC section’s indicator LEDs will be turned off.
        '''
        if z is None:
        # Send query
            result = self.query('TEC:DIS?')
        # Parse result
            try:
                return float(result)
            except ValueError:
                return False
        else:
        # Limit range
            z = vo.tf_to_10(z)
        # Send command
            self.write('TEC:DIS {:}'.format(['OFF','ON'][z]))
    
    @log.log_this()
    def display(self, z=None):
        '''
        This is a wrapper that combines the laser_display and tec_display methods.
        '''
        if z is None:
        # Send query
            laser_result = self.laser_display()
            tec_result = self.tec_display()
            return laser_result, tec_result
        else:
        # Limit range
            z = vo.tf_to_10(z)
        # Send command
            self.laser_display(z=z)
            self.tec_display(z=z)
    
    @log.log_this()
    def radix(self, set_radix=None):
        '''
        The RADix command allows the programmer to select the radix type for 
        status, condition, and event query response data. Decimal, binary, 
        hexadecimal, and octal are allowed. DECimal is the default type. Only 
        the first three letters of the words decimal, hexadecimal, binary, or 
        octal are required. When the RADIX is selected, all status, condition, 
        and event queries will return values in the new radix. In the cases 
        where the radix is not DECimal, the flexible numeric type <nrf value> 
        (as shown in the Command Reference diagrams) will be replaced by HEX, 
        BIN, or OCT representation. All of the above radixes may be used to 
        enter program data at any time, without the need for issuing the RADix 
        command. The proper prefix must also be used with Hex (#H), binary 
        (#B), or octal (#O).
        '''
        if set_radix is None:
        # Send query
            result = self.query('RAD?')
            return result
        else:
        # Limit range
            if set_radix in ['DEC', 'BIN', 'HEX', 'OCT']:
                set_radix = ['DEC', 'BIN', 'HEX', 'OCT'].index(set_radix)
            else:
                set_radix = int(set_radix)
        # Send command
            self.write('MODE:{:}'.format(['DEC', 'BIN', 'HEX', 'OCT'][set_radix]))
            

# %% ILX LDC-3900 Mainframe - Laser Module
class LaserModule(LDC3900):
    @log.log_this()
    def __init__(self, visa_address, laser_channel, res_manager=None):
        super(LaserModule, self).__init__(visa_address, res_manager=res_manager)
        self.las_channel = laser_channel
        self.las_open_command = 'LAS:CHAN {:}'.format(self.las_channel)
        self.las_opened = False
    
    
    @log.log_this()
    @vo._handle_visa_error
    def open_las(self):
        self.open_resource()
        self.resource.write(self.las_open_command)
        self.opened = True
    
    @log.log_this()
    @vo._handle_visa_error
    def close_las(self):
        self.close_resource()
        self.opened = False
    
    @log.log_this()
    @_auto_connect_las
    @vo._handle_visa_error
    def query_las(self, message, delay=None):
        result = self.resource.query('LAS:'+message, delay=delay).strip()
        return result
    
    
    @log.log_this()
    @_auto_connect_las
    @vo._handle_visa_error
    def write_las(self, message, termination=None, encoding=None):
        self.resource.write('LAS:'+message, termination=termination, encoding=encoding)
    
    @log.log_this()
    def get_laser_channel(self):
        '''
        The LASer:CHAN? query returns the channel number of the LASER module
        which has been selected for display and adjustment. If no LASER channels
        exist, the response will be 0. In local mode, the user would read the 
        LASER channel selection visually. The selected channel would have the 
        corresponding orange "LAS" LED lit in the ADJUST section.
        '''
    # Send query
        result = self.write_las('CHAN?')
        return int(float(result))
    
    @log.log_this()
    def laser_status(self):
        '''
        The LASer:STB? query is used to read back the selected LAS channel’s 
        status summaries for conditions and events. This value is used to 
        determine which LAS channel(s) have conditions and/or events which have
        been summarized and reported to the Status Byte Register (which is read
        via the *STB? query). The response is the sum of the following:
            Bit     Condition which sets bit
            0       N/A
            1       N/A
            2       LASER Event Status Register Summary
            3       LASER Condition Status Register Summary
        If the Status Byte Register is read via the *STB?, and a LASER condition
        or event is summarized in bits 3 or 2, any or all of the enabled LASER 
        channels may have been responsible. The LAS:STB? may then be used to 
        poll each of the LASER channels to determine which channel’s summarized
        conditions or events have been reported.
        '''
    # Send query
        result = self.query_las('STB?')
    # Parse result
        results = '{:04b}'.format(int(result))
        results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
        return results
    
    @log.log_this()
    def laser_conditions(self):
        '''
        The LASer:COND? query returns the value of the status condition register 
        of the LASER operations of the selected LASER channel. The response is 
        the sum of the following:
            Bit     Condition which sets bit
            0       Laser limit current
            1       Voltage limit error
            2       N/A
            3       Power limit 
            4       Interlock disabled 
            5       N/A 
            6       N/A 
            7       Open circuit 
            8       Output is shorted
            9       Output is outside tolerance limit
            10      Output on/off state
            11      Ready for calibration data state
            12      Calculation error
            13      Error communicating with LASER board
            14      Software error in LASER control
            15      LASER eeprom checksum error
        The LASER conditions which are reported to the status byte are set via 
        the LASer:ENABle:COND command (for each channel). The Open circuit 
        condition is only present while a LASER output is on, and when the hardware 
        detects this condition, it will turn that LASER output off. Therefore, 
        the Open Circuit condition is fleeting and may be missed via the LAS:COND?
        query. Therefore, the user should test for the Open Circuit Event via 
        the LAS:EVEnt? query. The LASER condition status is constantly changing,
        while the event status is only cleared when the event status is read or
        the *CLS or *RST command is issued.
        '''
    # Send query
        result = self.query_las('COND?')
    # Parse result
        results = '{:016b}'.format(int(result))
        results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
        return results

    @log.log_this()
    def laser_events(self):
        '''
        The LASer:EVEnt? query returns the value of the selected channel’s status
        event register of the LASER operations. 
        The is the sum of the following:
            Bit     Condition which sets bit
            0       Laser current limit
            1       Laser voltage limit
            2       N/A
            3       Power limit 
            4       Interlock disabled 
            5       N/A 
            6       N/A 
            7       Open circuit 
            8       Output is shorted
            9       Output Changed to be In/Out of Tolerance
            10      Output On/Off State Changed
            11      New Measurements Taken
            12      Calculation error
            13      Error communicating with LASER board
            14      Software error in LASER control
            15      LASER eeprom checksum error
        The selected channel’s LASER conditions that are reported in the status
        byte can be set by using the LASer:ENABle:EVEnt command. The LASER event
        status is only cleared when the event status is read or by the *CLS
        command, while the condition status is constantly changing.
        '''
    # Send query
        result = self.query_las('EVE?')
    # Parse result
        results = '{:016b}'.format(int(result))
        results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
        return results

    @log.log_this()
    def laser_enable_conditions(self, enable_bits=None):
        '''
        The LASer:ENABle:COND command sets the condition status enable register
        of the selected channel’s LASER operations for summary (in bit 3 of the
        status byte) and generation of service requests. "enable_bits" accepts 
        a list of the enabled bits (i.e. [4, 7, 8, 13, 14]) or a dictionary
        specifying both enabled and disabled bits (i.e. {'0':False,'1':False,...}):
            Bit     Condition which sets bit
            0       LASER Current Limit 
            1       LASER Voltage Limit
            2       N/A 
            3       Power Limit 
            4       Interlock Disabled
            5       N/A 
            6       N/A 
            7       Open Circuit
            8       Output is Shorted
            9       Output is Outside Tolerance Limit
            10      Output On/Off State
            11      Ready for Calibration Data State
            12      Calculation Error
            13      Error Communicating LASER Board
            14      Software Error in LASER Control
            15      LASER EEPROM Checksum Error
                
        The LASer:ENABle:COND? query returns the value of the selected channel’s
        status condition enable register of the LASER operations. The selected 
        channel’s enabled LASER conditions can be set by using the 
        LASer:ENABle:COND command. The LASER condition status can be monitored 
        by the LASer:COND? query.  If any of the enabled LASER conditions are 
        true, bit 3 of the status byte register will be set. The enable registers
        normally retain their values at power−up (as they were at power−down) 
        unless the power−on status clear flag is set true.
        '''
        if enable_bits is None:
        # Send query
            result = self.query_las('ENAB:COND?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
            return results
        else:
        # Parse input
            if isinstance(enable_bits, list):
                enable_bits=''.join([str(int(bit in enable_bits)) for bit in range(16)][::-1])
            elif isinstance(enable_bits, dict):
                enable_bits=''.join([str(int(enable_bits[str(bit)])) for bit in range(16)][::-1])
            enable_bits=int(enable_bits, 2)
        # Send command
            self.write_las('ENAB:COND {:}'.format(enable_bits))
    
    @log.log_this()
    def laser_enable_events(self, enable_bits=None):
        '''
        The LASer:ENABle:EVEnt command sets the status event enable register of
        the LASER operations for the selected LAS channel. These events are 
        summarized in bit 2 of the status byte register. "enable_bits" accepts 
        a list of the enabled bits (i.e. [4, 7, 8, 13, 14]) or a dictionary
        specifying both enabled and disabled bits (i.e. {'0':False,'1':False,...}):
            Bit     Condition which sets bit
            0       LASER Current Limit 
            1       LASER Voltage Limit
            2       N/A 
            3       Power Limit 
            4       Interlock State Changed
            5       N/A 
            6       N/A 
            7       Open Circuit
            8       Output is Shorted
            9       Output Changed to be In/Out of Tolerance
            10      Output On/Off State Changed
            11      New Measurements Taken
            12      Calculation Error
            13      Error Communicating LASER Board
            14      Software Error in LASER Control
            15      LASER EEPROM Checksum Error
        The LASer:ENABle:EVEnt? query returns the value of the selected channel’s
        status event enable register of the LASER operations. The enabled LASER
        events for the selected LAS channel can be set by using the 
        LASer:ENABle:EVEnt command. The selected channel’s LASER event status 
        can be monitored by the LASer:EVEnt? query. The enable registers normally
        retain their values at power−up (as they were at power−down) unless the
        power−on status clear flag is set true.
        '''
        if enable_bits is None:
        # Send query
            result = self.query_las('ENAB:EVE?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
            return results
        else:
        # Parse input
            if isinstance(enable_bits, list):
                enable_bits=''.join([str(int(bit in enable_bits)) for bit in range(16)][::-1])
            elif isinstance(enable_bits, dict):
                enable_bits=''.join([str(int(enable_bits[str(bit)])) for bit in range(16)][::-1])
            enable_bits=int(enable_bits, 2)
        # Send command
            self.write_las('ENAB:EVE {:}'.format(enable_bits))
    
    @log.log_this()
    def laser_off_triggers(self, trigger_bits=None):
        '''
        The LASer:ENABle:OUTOFF command sets the status outoff enable register
        of the selected channel’s LASER operations (things which will turn the 
        LASER output off). "trigger_bits" accepts a list of the enabled bits
        (i.e. [0, 1, 2, 4, 12]) or a dictionary specifying both enabled and
        disabled bits (i.e. {'0':False,'1':False,...}):
            Bit     Condition which disables laser output
            0       LASER Current Limit 
            1       LASER Voltage Limit 
            2       TEC Output is Off (Channel 1) Event
            3       Power Limit (With Output On)
            4       N/A 
            5       TEC Output is Off (Channel 2) Event
            6       TEC Output is Off (Channel 3) Event
            7       N/A 
            8       N/A
            9       Output is Out of Tolerance
            10      TEC Output is Off (Channel 4) Event
            11      TEC High Temp. Limit (Channel 1) Condition
            12      Hardware Error
            13      TEC High Temp. Limit (Channel 2) Condition
            14      TEC High Temp. Limit (Channel 3) Condition
            15      TEC High Temp. Limit (Channel 4) Condition
        The enabled LASER outoff bits for the selected channel can be read by
        using the LASer:ENABle:OUTOFF? query. If the Output is Outside of 
        Tolerance Limit condition is set in this register when the LASER output
        is off, you will not be able to turn the LASER output on until this bit
        is reset. The enable registers normally retain their values at power−up
        (as they were at power−down) unless the power−on status clear flag is 
        set true (see *PSC, Chapter 3).
        
        The factory default value for this register is #B1110100000001000, 
        or #HE808, or 59400 decimal. This corresponds to 
        trigger_bits=[3, 11, 13, 14, 15]
        '''
        if trigger_bits is None:
        # Send query
            result = self.query_las('ENAB:OUTOFF?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
            return results
        else:
        # Parse input
            if isinstance(trigger_bits, list):
                trigger_bits=''.join([str(int(bit in trigger_bits)) for bit in range(16)][::-1])
            elif isinstance(trigger_bits, dict):
                trigger_bits=''.join([str(int(trigger_bits[str(bit)])) for bit in range(16)][::-1])
            trigger_bits=int(trigger_bits, 2)
        # Send command
            self.write_las('ENAB:OUTOFF {:}'.format(trigger_bits))
      
    @log.log_this()  
    def laser_current_setpoint(self, set_current=None):
        '''
        The LASer:LDI command sets the laser control current for the selected 
        LAS channel. f represents the (laser) output current, in mA. 
        
        The LASer:SET:LDI? query returns the constant I value which is used for
        both bandwidth modes. The response is the selected channel’s constant I
        set point value, in mA.
        '''
        if set_current is None:
        # Send query
            result = self.query_las('SET:LDI?')
            return float(result)
        else:
        # Send command
            self.write_las('LDI {:G}'.format(set_current))
    
    @log.log_this()
    def laser_current(self):
        '''
        The LASer:LDI? query returns the value of the measured laser current for
        the selected LAS channel. Response is the selected channel’s measured 
        laser output current, for either low or high bandwidth modes. This 
        measurement is updated approximately once every 600 mSec.
        '''
    # Send query
        result = self.query_las('LDI?')
        return float(result)
    
    @log.log_this()
    def laser_current_limit(self, set_limit=None):
        '''
        The LASer:LIMit:I command sets the selected channel’s LASER current 
        limit value. The current limit is in effect in all modes of operation 
        of the selected channel’s laser output. If the new limit value is lower
        than the present current set point, the current set point will be forced
        down to the value of the current limit and an E534 error will be generated.
        '''
        if set_limit is None:
        # Send query
            result = self.query_las('LIM:I?')
            return int(float(result))
        else:
        # Limit range
            set_limit = int(abs(set_limit))
        # Send command
            self.write_las('LIM:I {:}'.format(set_limit))
    
    @log.log_this()
    def laser_power_limit(self, set_limit=None):
        '''
        The LASer:LIMit:MDP command sets the laser monitor photodiode power 
        limit value. When constant MDP mode is used, the selected channel’s 
        output is limited only by the LIM I value. The LIM MDP condition may be
        used to shut the selected channel’s LASER output off, but this requires
        the use of the LASer:ENABle:OUTOFF command to set bit 3 of the LASER 
        OUTOFF ENABLE register.

        '''
        if set_limit is None:
        # Send query
            result = self.query_las('LIM:MDP?')
            return int(float(result))
        else:
        # Limit range
            set_limit = int(abs(set_limit))
        # Send command
            self.write_las('LIM:MDP {:}'.format(set_limit))
    
    @log.log_this()
    def laser_mode(self, set_mode_bandwidth=None):
        '''
        The LASer:MODE? query returns the present LAS channel’s selected laser 
        control mode. IHBW mode is the same as I mode (low bandwidth), except 
        that the output low bandpass filter is disabled in IHBW mode.
        
        set_mode_bandwidth takes either 'low' or 'high' as input.
        '''
        if set_mode_bandwidth is None:
        # Send query
            result = self.query_las('MODE?')
            return result
        else:
        # Limit range
            if set_mode_bandwidth in ['low', 'high']:
                set_mode_bandwidth = ['low', 'high'].index(set_mode_bandwidth)
            else:
                set_mode_bandwidth = vo.tf_to_10(set_mode_bandwidth)
        # Send command
            self.write_las('MODE:{:}'.format(['ILBW','IHBW'][set_mode_bandwidth]))
    
    @log.log_this()
    def laser_output(self, output=None):
        '''
        The LASer:ONLY:OUTput command turns the laser output (only) on or off 
        for the selected channel. This command is useful with combination 
        modules when the LAS and TEC outputs need to be controlled separately. 
        For combination modules this command effects only the LAS output. With
        combination modules, when only the TEC or LAS output is on, the 
        corresponding output LED will blink. After a channel’s output is turned
        on, it may be useful to wait until the output is stable (within 
        tolerance) before performing further operations, but it is not 
        necessary. When the LASER output is off, it is safe to connect or 
        disconnect devices to the LASER output terminals. When a LASER output is
        off, an internal short is placed across the output terminals. If this 
        occurs for the selected LAS channel, it causes the OUTPUT SHORTED light
        to come on.
        
        The LASer:OUTput? query returns the status of the selected laser 
        channel’s OUTPUT switch. Although the status of the switch is on, the 
        selected channel’s output may not have reached the set point value. For
        LAS/TEC combination modules, a response of "1" indicates that the output
        switch for that channel is enabled. Either the TEC or LAS output (or 
        both) may be on. 
        '''
        if output is None:
        # Send query
            result = self.query_las('OUT?')
            return bool(float(result))
        else:
        # Limit range
            output = vo.tf_to_10(output)
        # Send command
            self.write_las('ONLY:OUT {:}'.format(output))

# %% ILX LDC-3900 Mainframe - TEC Module
class TECModule(LDC3900):
    @log.log_this()
    def __init__(self, visa_address, tec_channel, res_manager=None):
        super(TECModule, self).__init__(visa_address, res_manager=res_manager)
        self.tec_channel = tec_channel
        self.tec_opened = False
        self.tec_open_command = 'TEC:CHAN {:}'.format(self.tec_channel)
        self.tec_step_size = self.tec_step()
    
    @log.log_this()
    @vo._handle_visa_error
    def open_tec(self):
        self.open_resource()
        self.resource.write(self.tec_open_command)
        self.opened = True
    
    @log.log_this()
    @vo._handle_visa_error
    def close_tec(self):
        self.close_resource()
        self.opened = False
    
    
    @log.log_this()
    @_auto_connect_tec
    @vo._handle_visa_error
    def query_tec(self, message, delay=None):
        result = self.resource.query('TEC:'+message, delay=delay).strip()
        return result
    
    @log.log_this()
    @_auto_connect_tec
    @vo._handle_visa_error
    def write_tec(self, message, termination=None, encoding=None):
        self.resource.write('TEC:'+message, termination=termination, encoding=encoding)
    
    @log.log_this()
    def get_tec_channel(self):
        '''
        The TEC:CHAN? query returns the channel number of the TEC module which 
        has been selected for display and adjustment. The response is the 
        channel number of the selected TEC module. If no TEC channels exist, 
        the response will be 0.
        '''
    # Send query
        result = self.query_tec('CHAN?')
        return int(float(result))
    
    @log.log_this()
    def tec_status(self):
        '''
        The TEC:STB? query is used to read back the selected TEC channel’s 
        status summaries for conditions and events. This value is used to 
        determine which TEC channel(s) have conditions and/or events which have
        been summarized and reported to the Status Byte Register (which is read
        via the *STB? query). The response is the sum of the following:
            Bit     Condition which sets bit
            0       TEC Event Status Register Summary
            1       TEC Condition Status Register Summary
        If the Status Byte Register is read via the *STB?, and a TEC condition
        or event is summarized in bits 1 or 0, any or all of the enabled TEC 
        channels may have been responsible. The TEC:STB? may then be used to 
        poll each of the TEC channels to determine which channel’s summarized 
        conditions or events have been reported.
        '''
    # Send query
        result = self.query_tec('STB?')
    # Parse result
        results = '{:02b}'.format(int(result))
        results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
        return results
    
    @log.log_this()
    def tec_conditions(self):
        '''
        The TEC:COND? query returns the value of the status condition register 
        of the TEC operations for the selected TEC channel. The response is the
        sum of the following:
            Bit     Condition which sets bit
            0       TE Current Limit 
            1       Voltage Limit Error 
            2       N/A
            3       High Temperature Limit 
            4       TEC Interlock Enable 
            5       Booster Enable 
            6       Sensor Open 
            7       TE Module Open 
            8       N/A
            9       Output Out of Tolerance
            10      Output On
            11      Ready for Calibration Data
            12      Calculation Error
            13      Internal Communication Error with TEC Board
            14      Software Error
            15      TEC EEPROM Checksum Error
        The enabled TEC conditions can be set by using the TEC:ENABle:COND 
        command for the selected TEC channel. The TEC condition status is 
        constantly changing, while the event status is only cleared when the 
        event status is read or the *CLS command is issued.
        '''
    # Send query
        result = self.query_tec('COND?')
    # Parse result
        results = '{:016b}'.format(int(result))
        results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
        return results
    
    @log.log_this()
    def tec_events(self):
        '''
        The TEC:EVEnt? query returns the value of the status event register of 
        the TEC operations for the selected TEC channel. The response is the 
        sum of the following:
            Bit     Condition which sets bit
            0       TE Current Limit 
            1       TE Voltage Limit
            2       N/A
            3       High Temperature Limit 
            4       TEC Interlock Disabled 
            5       Booster Changed 
            6       Sensor Open 
            7       TE Module Open 
            8       Sensor Type Changed
            9       Output Changed to be In or Out of Tolerance
            10      Output On/Off Changed
            11      New Measurements Taken
            12      Calculation Error
            13      Internal TEC Control Communication Error
            14      Software Error in TEC Control
            15      TEC EEPROM Checksum Error
        The TEC conditions for the selected TEC channel which are reported to 
        the status byte are set via the TEC:ENABle:EVEnt command. The TEC event
        status is only cleared when the event status is read for the selected 
        TEC channel, or a *CLS command is issued; the condition status 
        is constantly changing.
        '''
    # Send query
        result = self.query_tec('EVE?')
    # Parse result
        results = '{:016b}'.format(int(result))
        results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
        return results
    
    @log.log_this()
    def tec_enable_conditions(self, enable_bits=None):
        '''
        The TEC:ENABle:COND command sets the status condition enable register 
        of the TEC operations for the selected TEC channel. These conditions 
        are summarized in bit 1 of the status byte. "enable_bits" accepts 
        a list of the enabled bits (i.e. [4, 7, 8, 13, 14]) or a dictionary
        specifying both enabled and disabled bits (i.e. {'0':False,'1':False,...}):
            Bit     Condition which sets bit
            0       TE Current Limit 
            1       Voltage Limit Error 
            2       N/A
            3       High Temperature Limit 
            4       TEC Interlock Enable 
            5       Booster Enable 
            6       Sensor Open 
            7       TE Module Open 
            8       N/A
            9       Output Out of Tolerance
            10      Output On
            11      Ready for Calibration Data
            12      Calculation Error
            13      Internal Communication Error with TEC Board
            14      Software Error
            15      TEC EEPROM Checksum Error
         The enabled TEC conditions for the selected TEC channel can be read by
         using the TEC:ENABle:COND? query. The TEC condition status for the 
         selected TEC channel can be monitored by the TEC:COND? query. If any 
         of the enabled TEC conditions are true, bit 1 of the status byte 
         register will be set. The enable registers normally retain their values
         at power−up (as they were at power−down) unless the power−on status 
         clear flag is set true.
        '''
        if enable_bits is None:
        # Send query
            result = self.query_tec('ENAB:COND?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
            return results
        else:
        # Parse input
            if isinstance(enable_bits, list):
                enable_bits=''.join([str(int(bit in enable_bits)) for bit in range(16)][::-1])
            elif isinstance(enable_bits, dict):
                enable_bits=''.join([str(int(enable_bits[str(bit)])) for bit in range(16)][::-1])
            enable_bits=int(enable_bits, 2)
        # Send command
            self.write_tec('ENAB:COND {:}'.format(enable_bits))
        
    @log.log_this()    
    def tec_enable_events(self, enable_bits=None):
        '''
        The TEC:ENABle:EVEnt command sets the status event enable register of 
        the TEC operations for the selected TEC channel. These events are 
        summarized in bit 0 of the status byte register. "enable_bits" accepts 
        a list of the enabled bits (i.e. [4, 7, 8, 13, 14]) or a dictionary
        specifying both enabled and disabled bits (i.e. {'0':False,'1':False,...}):
            Bit     Condition which sets bit
            0       TE Current Limit 
            1       TE Voltage Limit
            2       N/A
            3       High Temperature Limit 
            4       TEC Interlock Disabled 
            5       Booster Changed 
            6       Sensor Open 
            7       TE Module Open 
            8       Sensor Type Changed
            9       Output Changed to be In or Out of Tolerance
            10      Output On/Off Changed
            11      New Measurements Taken
            12      Calculation Error
            13      Internal TEC Control Communication Error
            14      Software Error in TEC Control
            15      TEC EEPROM Checksum Error
        The enabled TEC events for the selected TEC channel can be read by using
        the TEC:ENABle:EVEnt? query. The enabled TEC event status for the 
        selected TEC channel can be monitored by the TEC:EVEnt? query. The enable
        registers normally retain their values at power−up (as they were at 
        power−down) unless the power−on status clear flag is set true.
        '''
        if enable_bits is None:
        # Send query
            result = self.query_tec('ENAB:EVE?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
            return results
        else:
        # Parse input
            if isinstance(enable_bits, list):
                enable_bits=''.join([str(int(bit in enable_bits)) for bit in range(16)][::-1])
            elif isinstance(enable_bits, dict):
                enable_bits=''.join([str(int(enable_bits[str(bit)])) for bit in range(16)][::-1])
            enable_bits=int(enable_bits, 2)
        # Send command
            self.write_tec('ENAB:EVE {:}'.format(enable_bits))
    
    @log.log_this()
    def tec_off_triggers(self, trigger_bits=None):
        '''
        The TEC:ENABle:OUTOFF command sets the status outoff enable register 
        of the TEC operations (things which will turn the TEC output off) for 
        the selected TEC channel. "trigger_bits" accepts a list of the enabled 
        bits (i.e. [0, 1, 2, 4, 12]) or a dictionary specifying both enabled
        and disabled bits (i.e. {'0':False,'1':False,...}):
            Bit     Condition which disables tec output
            0       TE Current Limit Condition 
            1       Voltage Limit Condition 
            2       N/A 
            3       High Temperature Limit Condition 
            4       TEC Interlock Changed Condition
            5       Booster Changed (While Output On) Event 
            6       Sensor Open (While Output On) Condition 
            7       Module Open (While Output On) Condition 
            8       Sensor Type Change (While OutputOn) Event
            9       Output Out of Tolerance Condition
            10      Sensor Shorted (While Output On) Condition
            11      N/A
            12      Software Error Condition
            13      N/A
            14      N/A
            15      N/A
        The enabled TEC outoff bits for the selected TEC channel can be read by 
        using the TEC:ENABle:OUTOFF? query. The value of the TEC outoff enable 
        register for the selected TEC channel is stored in non−volatile memory 
        and is retained at power−up. The High Temperature Limit Condition, Sensor 
        Open (While Output On) Condition, and Sensor Type Change (While Output 
        On) Event bits for the selected TEC channel will not be in effect and 
        will not cause the selected TEC output to be shut off, if the selected 
        TEC channel is in ITE mode. WARNING: If the Output Out of Tolerance Change
        Event bit is set when the power is off, the TEC output will not be able 
        to be turned on until this bit is reset.
        
        The factory default value for this register is #B0000010111101000, 
        or #H5E8, or 1512 decimal. This corresponds to 
        trigger_bits=[3, 5, 6, 7, 8, 10]
        '''
        if trigger_bits is None:
        # Send query
            result = self.query_tec('ENAB:OUTOFF?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = {str(bit):bool(int(value)) for (bit,value) in enumerate(results[::-1])}
            return results
        else:
        # Parse input
            if isinstance(trigger_bits, list):
                trigger_bits=''.join([str(int(bit in trigger_bits)) for bit in range(16)][::-1])
            elif isinstance(trigger_bits, dict):
                trigger_bits=''.join([str(int(trigger_bits[str(bit)])) for bit in range(16)][::-1])
            trigger_bits=int(trigger_bits, 2)
        # Send command
            self.write_tec('ENAB:OUTOFF {:}'.format(trigger_bits))
    
    @log.log_this()
    def tec_gain(self, set_gain=None):
        '''
        The TEC:GAIN command sets the TEC control loop gain for the selected TEC
        channel. If the user enters a gain value which is greater than 300, a 
        value of 300 will be stored. If the user enters a gain value which is 
        less than 1, a value of 1 will be stored. If the user enters a value 
        which is not legal, the LDC−3900 will round that value to the nearest 
        legal value, if possible.
        
        Valid entries are 1, 3, 10, 30, 100, or 300.
        '''
        if set_gain is None:
        # Send query
            result = self.query_tec('GAIN?')
            return int(float(result))
        else:
        # Send command
            self.write_tec('GAIN {:}'.format(int(set_gain)))
    
    @log.log_this()
    def tec_current_limit(self, set_limit=None):
        '''
        The TEC:LIMit:ITE command sets the TEC TE current limit value for the 
        selected TEC channel in Amps. This value also limits the TEC booster 
        output signal voltage to a value which is proportional to the TEC limit
        current (approximately 1 V/A). If the new limit value is lower than the
        present ITE set point, the ITE set point will be forced down to the 
        value of the ITE limit and an E434 error will be generated.
        '''
        if set_limit is None:
        # Send query
            result = self.query_tec('LIM:ITE?')
            return float(result)
        else:
        # Limit range
            if set_limit < 0:
                set_limit = 0
        # Send command
            self.qrite_tec('LIM:ITE {:.3f}'.format(set_limit))
    
    @log.log_this()
    def tec_temperature_limit(self, set_limit=None):
        '''
        The TEC:LIMit:THI command sets the TEC high temperature limit value for
        the selected TEC channel. The input represents the upper bound of the 
        TEC load temperature, in ×C, for the selected TEC channel. The THI limit
        value must be in the range 0 − 199.9 ×C. If an entered value is greater
        than 199.9, an error E222 will be generated, and the LIM:THI parameter 
        will not be changed. If an entered value is less than 0, an error E223 
        will be generated, and the LIM:THI parameter will not be changed. If the
        new limit value is lower than the present temperature set point, the 
        temperature set point will be forced down to the value of the THI limit
        and an E434 error will be generated. The default setting of the TEC 
        outoff enable register for the selected TEC channel forces the selected
        TEC output to be shut off if the high temperature limit is reached.
        '''
        if set_limit is None:
        # Send query
            result = self.query_tec('LIM:THI?')
            return float(result)
        else:
        # Limit range
            if set_limit < 0:
                set_limit = 0
            elif set_limit > 199.9:
                set_limit = 199.9
        # Send command
            self.write_tec('LIM:THI {:.1f}'.format(set_limit))
    
    @log.log_this()
    def tec_mode(self, set_mode=None):
        '''
        The TEC:MODE? query returns the present TEC control mode for the 
        selected TEC channel. The TEC mode also identifies the type of parameter
        which is controlled for a given TEC channel. The TEC output is kept at 
        the corresponding set point.
            The TEC:MODE:ITE command selects TEC constant TE current mode for 
            the selected TEC channel.
                This mode keeps the TEC current constant, regardless of load 
                temperature variations, on the selected TEC channel.
            The TEC:MODE:R command selects TEC constant thermistor 
            resistance/linear sensor reference mode for the selected TEC channel.
                Since sensor resistance (or linear sensor reference) is a 
                function of temperature, this mode also controls the TEC output
                load temperature, but it bypasses the use of the conversion 
                constants for set point calculation. This allows finer control 
                of temperature in cases where the sensor’s temperature model 
                (and therefore the constants) is not known.
            The TEC:MODE:T command selects TEC constant temperature mode for 
            the selected TEC channel.
                Since TEC load temperature is derived from sensor 
                resistance/reference, constant R and T modes are related. In T 
                mode the set point is converted to resistance or reference using
                the appropriate constants and conversion model.
        Changing modes causes the selected TEC channel’s output to be forced 
        off, and the new mode’s set point value will be displayed.
        '''
        if set_mode is None:
        # Send query
            result = self.query_tec('MODE?')
            return result
        else:
        # Limit range
            if set_mode in ['ITE', 'R', 'T']:
                set_mode = ['ITE', 'R', 'T'].index(set_mode)
            else:
                set_mode = int(set_mode)
        # Send command
            self.write_tec('MODE:{:}'.format(['ITE', 'R', 'T'][set_mode]))
        
    @log.log_this()    
    def tec_output(self, output=None):
        '''
        The TEC:ONLY:OUTput command turns the TEC output (only) on or off for 
        the selected channel. This command is useful with combination modules 
        when the LAS and TEC outputs need to be controlled separately. For 
        combination modules this command effects only the TEC output. With 
        combination modules, when only the TEC or LAS output is on, the 
        corresponding output LED will blink.
        
        The TEC:OUTput? query returns the status of the OUTPUT switch for the 
        selected TEC channel. Although the status of the switch is on, the 
        selected TEC output may not have reached the set point value. With a 
        LAS/TEC combination module, a response of "1" indicates that the output
        switch is enabled. Either the TEC or LAS output (or both) may be on.
        '''
        if output is None:
        # Send query
            result = self.query_tec('OUT?')
            return bool(float(result))
        else:
        # Limit range
            output = vo.tf_to_10(output)
        # Send command
            self.write_tec('ONLY:OUT {:}'.format(output))
    
    @log.log_this()
    def tec_sensor(self):
        '''
        The TEC:SENsor? query is used to read back the SENSOR SELECT (and 
        THERM SELECT) switch position value for the selected TEC channel. This 
        value is a coded representation of the sensor type/thermistor sensor 
        current. The response value of 
            1 = thermistor, at 100 mA;
            2 = thermistor, at 10 mA;
            3 = LM335 sensor; 
            4 = AD590 sensor; 
            5 = RTD. 
        The sensor code for the selected TEC channel is displayed on the TEC 
        display, and bit 8 of the TEC event register is set, whenever the back 
        panel SENSOR SELECT switch position is changed. The sensor selection 
        must be made locally at the back panel SENSOR SELECT and THERM SELECT 
        switches. If the response is 0, the sensor type is undetermined and a 
        hardware error must exist.
        '''
    # Send query
        result = self.query_tec('SEN?')
        return int(float(result))
    
    @log.log_this()
    def tec_resistance_setpoint(self, set_resistance=None):
        '''
        The TEC:R command sets the TEC’s constant thermistor resistance or 
        linear sensor reference set point for the selected TEC channel. Input 
        is the thermistor or RTD resistance set point value, in kOhms; the AD590
        current set point, in mA; or the LM335 voltage set point, in mV, 
        depending on the selected sensor type. The R set point is used to control
        the TEC output in R mode only. Using the R mode, the user may also 
        monitor the temperature of the TEC load via a remote algorithm of his/her
        own design. If an entered value is greater than 450, an error E222 will
        be generated, and the R set point parameter will not be changed. If an 
        entered value is less thann 0.001, an error E223 will be generated, and
        the R set point parameter will not be changed.
        '''
        if set_resistance is None:
        # Send query
            result = self.query_tec('SET:R?')
            return float(result)
        else:
        # Limit range
            if set_resistance < 0.001:
                set_resistance = 0.001
            elif set_resistance > 450:
                set_resistance = 450
        # Send command
            self.write_tec('R {:.3f}'.format(set_resistance))
        
    @log.log_this()
    def tec_resistance(self):
        '''
        The TEC:R? query returns the value of the TEC thermistor (or RTD) 
        resistance, or AD590 current, or LM335 voltage measurement, for the 
        selected TEC channel. The response value is the measured TEC thermistor
        (or RTD) resistance, in kOhms, or AD590 current in mA, or the measured 
        LM335 voltage in mV. TEC load temperature is derived from the thermistor
        resistance or linear sensor reference measurement for the selected TEC 
        channel. This measurement is updated approximately once every 600 msec.
        '''
    # Send query
        result = self.query_tec('R?')
        return float(result)
    
    @log.log_this()
    def tec_current_setpoint(self, set_current=None):
        '''
        The TEC:ITE command sets the TEC control current set point for the 
        selected TEC channel. It is also used to enter the TEC current 
        calibration value. The input is the ITE set point current for the 
        selected TEC channel, in Amps. This set point is used by the TEC’s 
        constant ITE mode only.
        '''
        if set_current is None:
        # Send query
            result = self.query_tec('SET:ITE?')
            return float(result)
        else:
        # Send command
            self.write_tec('ITE {:.3f}'.format(set_current))
    
    @log.log_this()
    def tec_current(self):
        '''
        The TEC:ITE? query returns the value of the measured TEC output current
        for the selected TEC channel. The response value represents the measured
        ITE current, in Amps. The TEC load current is constantly measured and 
        updated, regardless of the TEC mode of operation. This measurement is 
        updated approximately once every 600 msec. If an external booster is 
        used, the ITE measurement will remain zero, as the internal output 
        section is disabled in that case.
        '''
    # Send query
        result = self.query_tec('ITE?')
        return float(result)
    
    @log.log_this()
    def tec_temperature_setpoint(self, set_temperature=None):
        '''
        The TEC:T command sets the TEC’s constant temperature set point for the
        selected TEC channel. Input is the TEC temperature, in ×C, for the 
        selected TEC channel. The selected TEC’s temperature will be controlled
        to this set point only when the TEC is operated in T mode.
        '''
        if set_temperature is None:
        # Send query
            result = self.query_tec('SET:T?')
            return float(result)
        else:
        # Send command
            self.write_tec('T {:.1f}'.format(set_temperature))
    
    @log.log_this()
    def tec_temperature(self):
        '''
        The TEC:T? query returns the value of the TEC temperature measurement 
        for the selected TEC channel. The measured TEC temperature is valid for
        all modes of TEC operation. Temperature is continually updated. This 
        measurement is updated approximately once every 600 msec. In remote 
        operation, the response value has 6 digits of precision.
        '''
    # Send query
        result = self.query_tec('T?')
        return float(result)
    
    @log.log_this()
    def tec_sensor_constants(self, set_constants=None):
        '''
        The TEC:CONST command sets the TEC’s Steinhart−Hart equation constants 
        for the selected TEC channel. Three value for the three Steinhart−Hart
        equation constants or the two linear calibration constants for linear 
        IC sensors (and a third unused value). The range of values is −9.999 to
        +9.999 for all three constants. However, for a thermistor sensor, these
        values are scaled by the appropriate exponential value for the 
        Steinhart−Hart equation. When the LM335, AD590, or RTD sensors are 
        selected via the SENSOR SELECT switch, only C1 and C2 are used, C3 is 
        ignored. Versions of the LDC−3900 prior to v3.1 allowed parameters to 
        be omitted. This is no longer permitted. Also, with v3.1 and higher, 
        user−entered parameters outside of the valid range for that parameter 
        will be ignored and an error code will be generated. If an entered value
        is greater than 50.000, an error E222 will be generated, and the CONST 
        parameter will not be changed. If an entered value is less than −50.000,
        an error E223 will be generated, and the CONST parameter will not be 
        changed.
        
        The Steinhart-Hart Equation
            1/T = A + B(ln R) + C*(ln R)**3
        Once the three constants A, B, and C are accurately determined the 
        equation introduces small errors in the calculation of temperature over
        wide temperature ranges.
        '''
        if set_constants is None:
        # Send query
            result = self.query_tec('CONST?')
        # Parse results
            results = [float(constant) for constant in result.split(',')]
            return results
        else:
        # Send command
            self.write_tec('CONST {0:.3f},{1:.3f},{2:.3f}'.format(*set_constants))
    
    @log.log_this()
    def tec_step(self, step=None):
        '''
        The TEC:STEP command is used to increment or decrement the selected TEC
        control mode set point by the given amount, when used with the TEC:INC
        or TEC:DEC command. Accepts an integer value of the step amount, in the
        range +-9999.
            The TEC:DEC command decrements the selected control mode set point
            by one step and the TEC:INC command increments the selected control
            mode set point by one step for the selected TEC channel.
        The incremental amount is one step. The step size for the selected 
        channel can be edited via the STEP command, its default value is 
        0.1×C, 1 mA (ITE), 1 W (THERM), 0.01 mA (AD590), 0.1 mV (LM335), or 
        0.01 W (RTD), depending on the mode of operation.
        
        The TEC:STEP? query is used to read back the TEC STEP value for the 
        selected TEC channel. This value is used to increment or decrement the 
        selected TEC control mode set point by the given amount, when used with
        the TEC:INC or TEC:DEC command.
        '''
        if step is None:
        # Send query
            result = self.query_tec('STEP?')
            return int(float(result))
        else:
        # Limit range
            if step < -9999:
                step = -9999
            elif step > +9999:
                step = +9999
        # Check input step size
            if abs(step) != self.tec_step_size:
                self.write_tec('STEP {:}'.format(int(abs(step))))
                self.tec_step_size = int(abs(step))
            if step > 0:
                self.write_tec('INC')
            elif step < 0:
                self.write_tec('DEC')
    

# %% ILX LDC-3900 Mainframe - Laser and TEC Module
class CombinationModule(LaserModule, TECModule):
    @log.log_this()
    def __init__(self, visa_address, channel, res_manager=None):
        LaserModule.__init__(self, visa_address, channel, res_manager=res_manager)
        TECModule.__init__(self, visa_address, channel, res_manager=self.res_man)

    @log.log_this()
    def output(self, output=None):
        '''
        This combines the ONLY:OUTput commands of the laser and tec modules
        '''
        if output is None:
        # Send query
            laser_result = self.laser_conditions()
            tec_result = self.tec_conditions()
        # Parse results
            laser_result = 10 in laser_result
            tec_result = 10 in tec_result
            return laser_result, tec_result
        else:
        # Send commands
            if output:
                self.tec_output(output=output)
                self.laser_output(output=output)
            else:
                self.laser_output(output=output)
                self.tec_output(output=output)

