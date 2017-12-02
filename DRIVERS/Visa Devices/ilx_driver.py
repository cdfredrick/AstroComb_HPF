# -*- coding: utf-8 -*-
"""
Created on Mon Jun 26 10:31:06 2017

@author: Wesley Brand

Module: ilx_driver
#Laser diode control

Public Classes:
    ILX(vo.Visa)
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


#Astrocomb imports
import visa_objects as vo
import eventlog as log
import ac_excepts


#Constants
_MARKER = object()  #To check errors in LDControl class inheritance
ILX_ADDRESS = '' #ADD ME!!!

# %% ILX LDC-3900 Mainframe
class ILX_LDC3900(vo.Visa):
    """Holds commands for ILX chassis and passes commands for components."""
    @log.log_this()
    def __init__(self, visa_address, res_manager=None):
        super(ILX_LDC3900, self).__init__(visa_address, res_manager=res_manager)
        if self.resource is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create ILX instrument!', self.__init__)
    
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
            z = vo.tf_toggle(z)
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
            z = vo.tf_toggle(z)
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
            z = vo.tf_toggle(z)
        # Send command
            self.laser_display(z=z)
            self.tec_display(z=z)

# %% ILX LDC-3900 Mainframe - Laser Module
class LaserModule(ILX_LDC3900):
    def __init__(self, visa_address, laser_channel, res_manager=None):
        super(LaserModule, self).__init__(visa_address, res_manager=res_manager)
        self.las_channel = laser_channel
        self.las_open_command = 'LAS:CHAN {:}'.format(self.las_channel)
    
    @log.log_this()
    @vo.handle_visa_error
    def query_las(self, message, delay=None):
        self.open_resource()
        self.resource.write(self.las_open_command)
        result = self.resource.query('LAS:'+message, delay=delay)
        self.close_resource()
        return result
    
    @log.log_this()
    @vo.handle_visa_error
    def write_las(self, message, termination=None, encoding=None):
        self.open_resource()
        self.resource.write(self.las_open_command)
        self.resource.write('LAS:'+message, termination=termination, encoding=encoding)
        self.close_resource()
    
    def laser_channel(self):
        '''
        The LASer:CHAN? query returns the channel number of the LASER module
        which has been selected for display and adjustment. If no LASER channels
        exist, the response will be 0. In local mode, the user would read the 
        LASER channel selection visually. The selected channel would have the 
        corresponding orange "LAS" LED lit in the ADJUST section.
        '''
    # Send query
        result = self.write_las('CHAN?')
        return int(result)
    
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
        results = [bit for bit, value in enumerate(results[::-1]) if value == '1']
        return results

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
        results = [bit for bit, value in enumerate(results[::-1]) if value == '1']
        return results

    def laser_enable_conditions(self, l=None):
        '''
        The LASer:ENABle:COND command sets the condition status enable register
        of the selected channel’s LASER operations for summary (in bit 3 of the
        status byte) and generation of service requests. "l" accepts a list of 
        the enabled bits (i.e. [4, 7, 8, 13, 14]):
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
        if l is None:
        # Send query
            result = self.query_las('ENAB:COND?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = [bit for bit, value in enumerate(results[::-1]) if value == '1']
            return results
        else:
        # Parse input
            l=''.join([int(bit in l) for bit in range(16)][::-1])
            l=int(l, 2)
        # Send command
            self.write_las('ENAB:COND {:}'.format(l))
    
    def laser_enable_events(self, l=None):
        '''
        The LASer:ENABle:EVEnt command sets the status event enable register of
        the LASER operations for the selected LAS channel. These events are 
        summarized in bit 2 of the status byte register. "l" accepts a list of 
        the enabled bits (i.e. [4, 7, 8, 13, 14]):
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
        if l is None:
        # Send query
            result = self.query_las('ENAB:EVE?')
        # Parse result
            results = '{:016b}'.format(int(result))
            results = [bit for bit, value in enumerate(results[::-1]) if value == '1']
            return results
        else:
        # Parse input
            l=''.join([int(bit in l) for bit in range(16)][::-1])
            l=int(l, 2)
        # Send command
            self.write_las('ENAB:EVE {:}'.format(l))
    
    def laser_off_triggers(self, l=None):
        '''
        The LASer:ENABle:OUTOFF command sets the status outoff enable register
        of the selected channel’s LASER operations (things which will turn the 
        LASER output off). "l" accepts a list of the enabled bits
        (i.e. [0, 1, 2, 4, 12]):
            Bit     Condition which disables laser output
            1       LASER Current Limit 
            2       LASER Voltage Limit 
            4       TEC Output is Off (Channel 1) Event
            8       Power Limit (With Output On)
            16      N/A 
            32      TEC Output is Off (Channel 2) Event
            64      TEC Output is Off (Channel 3) Event
            128     N/A 
            256     N/A
            512     Output is Out of Tolerance
            1024    TEC Output is Off (Channel 4) Event
            2048    TEC High Temp. Limit (Channel 1) Condition
            4096    Hardware Error
            8192    TEC High Temp. Limit (Channel 2) Condition
            16384   TEC High Temp. Limit (Channel 3) Condition
            32768   TEC High Temp. Limit (Channel 4) Condition
        The enabled LASER outoff bits for the selected channel can be read by
        using the LASer:ENABle:OUTOFF? query. If the Output is Outside of 
        Tolerance Limit condition is set in this register when the LASER output
        is off, you will not be able to turn the LASER output on until this bit
        is reset. The enable registers normally retain their values at power−up
        (as they were at power−down) unless the power−on status clear flag is 
        set true (see *PSC, Chapter 3).
        
        The factory default value for this register is #B1110100000001000, 
        or #HE808, or 59400 decimal. To set to this value l=[0,1,2,3,12]
        '''

# %% ILX LDC-3900 Mainframe - TEC Module
class TECModule(ILX_LDC3900):
    def __init__(self, visa_address, tec_channel, res_manager=None):
        super(LaserModule, self).__init__(visa_address, res_manager=res_manager)
        self.tec_channel = tec_channel
        self.tec_open_command = 'LAS:CHAN {:}'.format(self.tec_channel)
    
    @log.log_this()
    @vo.handle_visa_error
    def query_tec(self, message, delay=None):
        self.open_resource()
        self.resource.write(self.tec_open_command)
        result = self.resource.query('TEC:'+message, delay=delay)
        self.close_resource()
        return result
    
    @log.log_this()
    @vo.handle_visa_error
    def write_tec(self, message, termination=None, encoding=None):
        self.open_resource()
        self.resource.write(self.tec_open_command)
        self.resource.write('TEC:'+message, termination=termination, encoding=encoding)
        self.close_resource()

# %% ILX LDC-3900 Mainframe - Laser and TEC Module
class LaserAndTECModule(LaserModule, TECModule):
    def __init__(self, visa_address, channel, res_manager=None):
        LaserModule.__init__(self, visa_address, channel, res_manager=res_manager)
        TECModule.__init__(self, visa_address, channel, res_manager=self.res_man)

# %% OLD STUFF
    @log.log_this()
    def las_chan_switch(self, chan_num):
        """Sets the laser channel to read write from, must be 1-4."""
        if self.las_chan != chan_num:
            self.write('LAS:CHAN %d' % chan_num)
            self.las_chan = chan_num

    @log.log_this()
    def tec_chan_switch(self, chan_num):
        """Sets the laser channel to read write from, must be 1-4."""
        if self.tec_chan != chan_num:
            self.write('LAS:CHAN %d' % chan_num)
            self.tec_chan = chan_num

    @log.log_this()
    def close(self):
        """Ends device session."""
        self.close_resource()
    
    #Private command passing methods

    def _las_query(self, command):
        """Swtiches comm channel and queries LAS:"""
        self.las_chan_switch(self.num)
        result = self.query('LAS:' + command)
        return result

    def _las_set(self, command):
        """Swtiches comm channel and writes to LAS:"""
        self.las_chan_switch(self.num)
        self.write('LAS:' + command)

    def _tec_query(self, command):
        """Swtiches comm channel and queries TEC:"""
        self.tec_chan_switch(self.num)
        result = self.query('TEC:' + command)
        return result

    def _tec_set(self, command):
        """Swtiches comm channel and writes to TEC:"""
        self.tec_chan_switch(self.num)
        self.write('TEC:' + command)

class LDControl(ILX):
    """Holds commands for laser control cards inside ILX.

    The ILX housing must be instantiated first and the object passed
    as an argument when instantiating the individual cards"""

    _inherited = ['res', 'las_chan', 'tec_chan']

    @log.log_this()
    def __init__(self, ilx_object, card_num):
        self._parent = ilx_object
        self.num = card_num

    def __getattr__(self, name, default=_MARKER):
        """Checks for attribute in parent ILX object."""
        if name in self._inherited:
            # Get from parent object
            try:
                return getattr(self._parent, name)
            except AttributeError:
                if default is _MARKER:
                    raise
                return default

        if name not in self.__dict__:
            raise AttributeError(name)

#Enable methods

    @log.log_this(20)
    def enable_las(self, las_on):
        """Turns the laser on if las_on is True.

        TEC must be on to prevent frying"""
        if self.query_tec_on():
            self._las_set('ONLY:OUT %d' % vo.tf_toggle(las_on))
        else:
            raise ac_excepts.EnableError("Can't turn laser on if TEC is off!",
                                         self.enable_las)
    @log.log_this(20)
    def enable_tec(self, tec_on):
        """Turns the TEC on if tec_on is True."""
        self._tex_set('ONLY:OUT %d' % vo.tf_toggle(tec_on))

#laser query methods

    @log.log_this()
    def query_las_on(self):
        """Returns True if laser on, False if not."""
        return bool(int(self._las_query('OUT?')))

    @log.log_this()
    def query_las_mode(self):
        """Returns laser mode string.

        Modes:
        IHBW -> constant current, high bandwidth
        ILBW -> constant current, low bandwidth
        MDP -> constant optical power
        """
        return self._las_query('MODE?')

    @log.log_this()
    def query_las_current(self):
        """Returns the present laser current in mA."""
        return float(self._las_query('LDI?'))

    @log.log_this()
    def query_las_current_limit(self):
        """Returns the max laser current in mA."""
        return float(self._las_query('LIM:I?'))

    @log.log_this()
    def query_las_current_set_point(self):
        """Returns the laser current set point in mA."""
        return float(self._las_query('SET:LDI?'))

#Laser settings methods

    @log.log_this()
    def set_las_current(self, current):
        """Sets the laser current in mA."""
        self._las_set('LDI %s' % int(current))
    @log.log_this()
    def set_las_current_limit(self, current):
        """Sets the max laser current in mA."""
        self._las_set('LDI %s' % int(current))

    @log.log_this()
    def set_las_mode(self, mode_num):
        """Sets the laser stabilization mode.

        Modes:
        0 -> constant current, high bandwidth
        1 -> constant current, low bandwidth
        2 -> constant optical power
        """
        modes = ['IHBW', 'ILBW', 'MDP']
        self._las_set('MODE:%s' % modes[mode_num])

#TEC query methods

    @log.log_this()
    def query_tec_on(self):
        """Returns True if TEC on, False if not."""
        return bool(int(self._tec_query('OUT?')))

    @log.log_this()
    def query_tec_mode(self):
        """Returns TEC mode string.

        Modes:
        ITE -> constant current
        R -> constant resistance
        T -> constant temperature
        """
        return self._tec_query('MODE?')

    @log.log_this()
    def query_tec_temp(self):
        """Returns the TEC temp in C with 6 digits of precision."""
        return float(self._teq_query('T?'))

#TEC settings methods

    @log.log_this()
    def set_tec_mode(self, mode_num):
        """Sets the TEC stabilization mode.

        Modes:
        0 -> constant current
        1 -> constant resistance
        2 -> constant temperature
        """
        modes = ['ITE', 'R', 'T']
        self._tec_set('MODE:%s' % modes[mode_num])

    @log.log_this()
    def set_tec_temp(self, temp):
        """Sets TEC temp in C"""
        self._tec_set('T %s' % temp)
