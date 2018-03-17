# -*- coding: utf-8 -*-
"""
Created on Tue Nov 28 13:14:23 2017

@author: cdf1
"""
# %% Modules
import Drivers.VISA.VisaObjects as vo
from Drivers.Logging import AcExceptions
from Drivers.Logging import EventLog as log
import math

from functools import wraps


# %% Private Functions
@log.log_this()
def _auto_connect(func):
    """A function decorator that handles automatic connections."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """Wrapped function"""
        if self.auto_connect:
            self.open_port()
            result = func(self, *args, **kwargs)
            self.close_port()
            return result
        else:
            result = func(self, *args, **kwargs)
            return result
    return wrapper


# %% SIM900 Mainframe
class SIM900(vo.VISA):
    @log.log_this()
    def __init__(self, visa_address, port, res_manager=None):
        super(SIM900, self).__init__(visa_address, res_manager=res_manager)
        if self.resource is None:
            raise AcExceptions.VirtualDeviceError('Could not create SRS SIM900 instrument!', self.__init__)
        self.clear_resource()
        self.port = port
        self.open_command = 'CONN '+str(self.port)+',"xyz"'
        self.close_command = 'xyz'
    
    @vo._handle_visa_error
    @log.log_this()
    def open_port(self):
        self.open_resource()
        self.resource.write(self.open_command)
    
    @vo._handle_visa_error
    @log.log_this()
    def close_port(self):
        self.resource.write(self.close_command)
        self.close_resource()
    
    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def query(self, message, delay=None):
        result = self.resource.query(message, delay=delay)
        return result

    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def read(self, termination=None, encoding=None):
        result = self.resource.read(termination=termination, encoding=encoding)
        return result
    
    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def write(self, message, termination=None, encoding=None):
        self.resource.write(message, termination=termination, encoding=encoding)


# %% SIM960 PID Controller
class SRS_SIM960(SIM900):
    @log.log_this()
    def __init__(self, visa_address, port, res_manager=None):
        super(SRS_SIM960, self).__init__(visa_address, port, res_manager=res_manager)
        self.token_mode(set_mode=0)
        self.lower_limit = self.lower_output_limit()
        self.upper_limit = self.upper_output_limit()
        self.center = .5*(self.upper_limit + self.lower_limit)

    @log.log_this()
    def proportional_action(self, set_action=None):
        '''
        The proportional control. When ON, the PID Control path includes the 
        proportional control term.
        '''
        if set_action is None:
        # Send query
            result = self.query('PCTL?')
            return bool(result)
        else:
        # Limit range
            set_action = vo.tf_to_10(set_action)
        # Send command
            self.write('PCTL {:}'.format(['OFF','ON'][set_action]))
    
    @log.log_this()
    def integral_action(self, set_action=None):
        '''
        The integral control. When ON, the PID Control path includes the 
        integral control term.
        '''
        if set_action is None:
        # Send query
            result = self.query('ICTL?')
            return bool(result)
        else:
        # Limit range
            set_action = vo.tf_to_10(set_action)
        # Send command
            self.write('ICTL {:}'.format(['OFF','ON'][set_action]))
    
    @log.log_this()
    def derivative_action(self, set_action=None):
        '''
        The derivative control. When ON, the PID Control path includes the 
        derivative control term.
        '''
        if set_action is None:
        # Send query
            result = self.query('DCTL?')
            return bool(result)
        else:
        # Limit range
            set_action = vo.tf_to_10(set_action)
        # Send command
            self.write('DCTL {:}'.format(['OFF','ON'][set_action]))
    
    @log.log_this()
    def offset_action(self, set_action=None):
        '''
        The offset control. When ON, the PID Control path includes the constant
        output offset.
        '''
        if set_action is None:
        # Send query
            result = self.query('OCTL?')
            return bool(result)
        else:
        # Limit range
            set_action = vo.tf_to_10(set_action)
        # Send command
            self.write('OCTL {:}'.format(['OFF','ON'][set_action]))
    
    @log.log_this()
    def proportional_gain(self, set_gain=None):
        '''
        The proportional gain (P), in V/V. Setting GAIN overrides the previous
        setting of APOL.
        '''
        if set_gain is None:
        # Send query
            result = self.query('GAIN?')
            return float(result)
        else:
        # Limit range
            if abs(set_gain)<1e-1:
                set_gain=1e-1*math.copysign(1, set_gain)
            elif abs(set_gain)>1e3:
                set_gain=1e3*math.copysign(1, set_gain)
        # Command syntax
            if set_gain<1e0:
                command = 'GAIN {:.1G}'.format(set_gain)
            elif set_gain<=1e3:
                command = 'GAIN {:.2G}'.format(set_gain)
        # Send command
            self.write(command)
    
    @log.log_this()
    def polarity(self, set_polarity=None):
        '''
        The proportional gain polarity {to z=(POS 1, NEG 0)}. Setting APOL will
        override the sign of a previously-commanded GAIN.
        '''
        if set_polarity is None:
        # Send query
            result = self.query('APOL?')
            return bool(result)
        else:
        # Limit range
            set_polarity = vo.tf_to_10(set_polarity)
        # Send command
            self.write('APOL {:}'.format(['NEG','POS'][set_polarity]))
    
    @log.log_this()
    def integral_gain(self, set_gain=None):
        '''
        The integral gain (I), in V/(V·s).
        '''
        if set_gain is None:
        # Send query
            result = self.query('INTG?')
            return float(result)
        else:
        # Limit range
            if set_gain<1e-2:
                set_gain=1e-2
            elif set_gain>5e5:
                set_gain=5e5
        # Command syntax
            if set_gain<1e-1:
                command = 'INTG {:.1G}'.format(set_gain)
            elif set_gain<=5e5:
                command = 'INTG {:.2G}'.format(set_gain)
        # Send command
            self.write(command)
    
    @log.log_this()
    def derivative_gain(self, set_gain=None):
        '''
        The derivative gain (D), in V/(V/s).
        '''
        if set_gain is None:
        # Send query
            result = self.query('DERV?')
            return float(result)
        else:
        # Limit range
            if set_gain<1e-6:
                set_gain=1e-6
            elif set_gain>1e1:
                set_gain=1e1
        # Command syntax
            if set_gain<1e-5:
                command = 'DERV {:.1G}'.format(set_gain)
            elif set_gain<=1e1:
                command = 'DERV {:.2G}'.format(set_gain)
        # Send command
            self.write(command)
    
    @log.log_this()
    def offset(self, set_offset=None):
        '''
        The output offset, in volts. Offsets the PID output point.
        '''
        if set_offset is None:
        # Send query
            result = self.query('OFST?')
            return float(result)
        else:
        # Limit range
            if set_offset<-10.:
                set_offset=-10.
            elif set_offset>10.:
                set_offset=10.
        # Send command
            self.write('OFST {:.3f}'.format(set_offset))
    
    @log.log_this()
    def pid_action(self, set_action=None):
        '''
        The controller output state.
        '''
        if set_action is None:
        # Send query
            result = self.query('AMAN?')
            return bool(result)
        else:
        # Limit range
            set_action = vo.tf_to_10(set_action)
        # Send command
            self.write('AMAN {:}'.format(['MAN','PID'][set_action]))
    
    @log.log_this()
    def external_setpoint_action(self, set_action=None):
        '''
        The setpoint input state.
        '''
        if set_action is None:
        # Send query
            result = self.query('INPT?')
            return bool(result)
        else:
        # Limit range
            set_action = vo.tf_to_10(set_action)
        # Send command
            self.write('INPT {:}'.format(['INT','EXT'][set_action]))
    
    @log.log_this()
    def internal_setpoint(self, set_setpoint=None):
        '''
        The internal setpoint value, in volts. If ramping is enabled (see RAMP),
        SETP will initiate a ramp to f. Otherwise, the setpoint value changes
        immediately to the new value.
        '''
        if set_setpoint is None:
        # Send query
            result = self.query('SETP?')
            return float(result)
        else:
        # Limit range
            if set_setpoint<-10.:
                set_setpoint=-10.
            elif set_setpoint>10.:
                set_setpoint=10.
        # Send command
            self.write('SETP {:.3f}'.format(set_setpoint))
    
    @log.log_this()
    def ramp_action(self, set_action=None):
        '''
        Internal setpoint ramping. When ON, the changes to the internal setpoint
        are made with constant slew-rate ramping enabled.
        '''
        if set_action is None:
        # Send query
            result = self.query('RAMP?')
            return bool(result)
        else:
        # Limit range
            set_action = vo.tf_to_10(set_action)
        # Send command
            self.write('RAMP {:}'.format(['OFF','ON'][set_action]))
    
    @log.log_this()
    def ramp_rate(self, set_rate=None):
        '''
        The setpoint ramping rate, in V/s.
        '''
        if set_rate is None:
        # Send query
            result = self.query('RATE?')
            return float(result)
        else:
        # Limit range
            if set_rate<1e-3:
                set_rate=1e-3
            elif set_rate>1e4:
                set_rate=1e4
        # Command syntax
            if set_rate<1e-2:
                command = 'RATE {:.1G}'.format(set_rate)
            elif set_rate<=1e4:
                command = 'RATE {:.2G}'.format(set_rate)
        # Send command
            self.write(command)
    
    @log.log_this()
    def ramp_status(self):
        '''
        Setpoint ramping status. For slow ramps of the internal setpoint, the 
        RMPS? query will monitor the real-time status of a setpoint transition. 
        The response is one of the following token values: 
            IDLE 0, PENDING 1, RAMPING 2, PAUSED 3.
        '''
    # Send query
        result = self.query('RMPS?')
        return int(result)
    
    @log.log_this()
    def manual_output(self, set_output=None):
        '''
        The manual output value, in volts.
        '''
        if set_output is None:
        # Send query
            result = self.query('MOUT?')
            return float(result)
        else:
        # Limit range
            if set_output<self.lower_limit:
                set_output=self.lower_limit
            elif set_output>self.upper_limit:
                set_output=self.upper_limit
        # Send command
            self.write('MOUT {:.3f}'.format(set_output))
    
    @log.log_this()
    def upper_output_limit(self, set_limit=None):
        '''
        The upper output limit, in volts. the output voltage will always be 
        clamped to remain less positive than the ULIM limit. Combined with the 
        LLIM limit, this results in the output obeying:
            −10.00 ≤ LLIM ≤ Output ≤ ULIM ≤ +10.00
        '''
        if set_limit is None:
        # Send query
            result = self.query('ULIM?')
            return float(result)
        else:
        # Limit range
            if set_limit<self.lower_limit:
                set_limit=self.lower_limit
            elif set_limit>10.:
                set_limit=10.
        # Send command
            self.write('ULIM {:.2f}'.format(set_limit))
            self.upper_limit = set_limit
            self.center = .5*(self.upper_limit + self.lower_limit)
    
    @log.log_this()
    def lower_output_limit(self, set_limit=None):
        '''
        The lower output limit, in volts. the output voltage will always be 
        clamped to remain less negative than the LLIM limit. Combined with the 
        ULIM limit, this results in the output obeying:
            −10.00 ≤ LLIM ≤ Output ≤ ULIM ≤ +10.00
        '''
        if set_limit is None:
        # Send query
            result = self.query('LLIM?')
            return float(result)
        else:
        # Limit range
            if set_limit<-10.:
                set_limit=-10.
            elif set_limit>self.upper_limit:
                set_limit=self.upper_limit
        # Send command
            self.write('LLIM {:.2f}'.format(set_limit))
            self.lower_limit = set_limit
            self.center = .5*(self.upper_limit + self.lower_limit)
    
    @log.log_this()
    def setpoint_monitor(self):
        '''
        Query the setpoint input voltage to the error amplifier, in volts. If 
        INPT INT is set, then SMON? monitors the value of the internally
        generated setpoint. If INPT EXT, then SMON? monitors the voltage applied
        at the front-panel Setpoint BNC input.
        '''
    # Send query
        result = self.query('SMON?')
        return float(result)
    
    @log.log_this()
    def measure_monitor(self):
        '''
        Query the Measure input voltage to the error amplifier, in volts. MMON?
        always reports the voltage applied at the front-panel Measure BNC input.
        '''
    # Send query
        result = self.query('MMON?')
        return float(result)
    
    @log.log_this()
    def error_monitor(self):
        '''
        Query the P × ε voltage, in volts. ε is the difference between the 
        setpoint and measure inputs (ε = SP-M), and P is the proportional gain.
        '''
    # Send query
        result = self.query('EMON?')
        return float(result)
    
    @log.log_this()
    def output_monitor(self):
        '''
        Query the Output voltage, in volts. OMON? always reports the voltage
        generated at the front-panel OUTPUT BNC connector.
        '''
    # Send query
        result = self.query('OMON?')
        return float(result)
    
    @log.log_this()
    def new_output_monitor(self):
        '''
        Query the Analog to Digital Status Register for a completed output
        monitor measurement. This only the requested bit is by reading. The 
        output monitor is the 3rd bit.
        '''
    # Send query
        result = self.query('ADSR? 3')
        return bool(result)
    
    @log.log_this()
    def power_line_frequency(self, set_frequency=None):
        '''
        The power line cycle frequency in Hz. FPLC is used to program the
        power-line rejection frequency for the precision voltage monitors (SMON?,
        MMON?, EMON?, OMON?). Valid inputs are 50 or 60 Hz.
        '''
        if set_frequency is None:
        # Send query
            result = self.query('FPLC?')
            return int(result)
        else:
        # Limit range
            if set_frequency not in [50, 60]:
                set_frequency = min([50, 60], key=lambda x:abs(x-set_frequency))
        # Send command
            self.write('FPLC {:}'.format(set_frequency))
    
    @log.log_this()
    def device_identification(self):
        '''
        Read the device identification string. The identification string is
        formatted as:
            Stanford Research Systems,SIM960,s/n******,ver#.#
        where SIM960 is the model number, ****** is the 6-digit serial number, 
        and #.# is the firmware revision level.
        '''
    # Send query
        result = self.query('*IDN?')
        return result
    
    @log.log_this()
    def token_mode(self, set_mode=None):
        '''
        The Token Query mode. If TOKN ON is set, then queries to the SIM960 that return tokens will 
        return the text keyword; otherwise they return the decimal integer value.
        '''
        if set_mode is None:
        # Send query
            result = self.query('TOKN?')
            return bool(result)
        else:
        # Limit range
            set_mode = vo.tf_to_10(set_mode)
        # Send command
            self.write('TOKN {:}'.format(['OFF','ON'][set_mode]))
    
    @log.log_this()
    def display(self, set_display=None):
        '''
        The front panel display status. When the display is turned off 
        (DISX OFF), all front panel indicators and buttons are disabled.
        '''
        if set_display is None:
        # Send query
            result = self.query('DISX?')
            return bool(result)
        else:
        # Limit range
            set_display = vo.tf_to_10(set_display)
        # Send command
            self.write('DISX {:}'.format(['OFF','ON'][set_display]))

# %% SIM940 10 MHz Rubidium Oscillator
class SRS_SIM940(SIM900):
    @log.log_this()
    def __init__(self, visa_address, port, res_manager=None):
        super(SRS_SIM940, self).__init__(visa_address, port, res_manager=res_manager)
        self.resource.open_resource()
        self.resource.read_termination = '\r'
        self.resource.write_termination = '\r'
        self.resource.close_resource()
    
    @log.log_this()
    def status(self):
        '''
        Status query. This command returns the six system status bytes which are
        used to indicate the health and status of the unit. The values ranges 
        from 0 to 255. The six status bytes are detailed in the tables below. A
        status bit will remained set until it is read, even though the condition
        which caused the error has been removed.
        
        ST1 : Power supplies and Discharge Lamp
        ST1 bit     Condition which sets bit        Corrective Action
        0           +24 for electronic < +22 Vdc    Increase supply voltage
        1           +24 for electronics > +30 Vdc   Decrease supply voltage
        2           +24 for heaters <+22 Vdc        Increase supply voltage 
        3           +24 for heaters > +30 Vdc       Decrease supply voltage
        4           Lamp light level too low        Wait: check SD2 setting
        5           Lamp light level too high       Check SD2 setting
        6           Gate voltage too low            Wait: check SD2 setting
        7           Gate voltage too high           Check SD2 setting
        
        ST2: RF Synthesizer
        ST2 bit     Condition which sets bit        Corrective Action
        0           RF synthesizer PLL unlocked     Query SP? verify values
        1           RF crystal varactor too low     Query SP? verify values
        2           RF crystal varactor too high    Query SP? verify values
        3           RF VCO control too low          Query SP? verify values
        4           RF VCO control too high         Query SP? verify values
        5           RF AGC control too low          Check SD0? values
        6           RF AGC control too high         Check SD0? values
        7           Bad PLL parameter               Query SP? verify values

        ST3: Temperature Controllers
        ST3 bit     Condition which sets bit        Corrective Action
        0           Lamp temp below set point       Wait for warm-up
        1           Lamp temp above set point       Check SD3, ambient
        2           Crystal temp below set point    Wait for warm-up
        3           Crystal temp above set point    Check SD4, ambient
        4           Cell temp below set point       Wait for warm-up
        5           Cell temp above set point       Check SD5, ambient
        6           Case temperature too low        Wait for warm-up
        7           Case temperature too high       Reduce ambient

        ST4: Frequency Lock-Loop Control
        ST4 bit     Condition which sets bit        Corrective Action
        0           Frequency lock control is off   Wait for warm-up
        1           Frequency lock is disabled      Enable w/LO1 command
        2           10 MHz EFC is too high          SD4,SP,10MHz cal,Tamb
        3           10 MHz EFC is too low           SP, 10 MHz cal 
        4           Analog cal voltage > 4.9 V      Int cal. pot, ext cal. volt
        5           Analog cal voltage < 0.1        Int cal. pot, ext cal. volt
        6
        7

        ST5: Frequency Lock to External 1pps
        ST5 bit     Condition which sets bit        Corrective Action
        0           PLL disabled                    Send PL 1 to enable
        1           < 256 good 1pps inputs          Provide stable 1pps inputs
        2           PLL active
        3           > 256 bad 1pps inputs           Provide stable 1pps inputs
        4           Excessive time interval         Provide accurate 1pps
        5           PLL restarted                   Provide stable 1pps inputs
        6           f control saturated             Wait, check 1pps inputs
        7           No 1pps input                   Provide 1pps input
        
        ST6: System Level Events
        ST6 bit     Condition which sets bit
        0           Lamp restart
        1           Watchdog time-out and reset
        2           Bad interrupt vector
        3           EEPROM write failure
        4           EEPROM data corruption
        5           Bad command syntax
        6           Bad command parameter
        7           Unit has been reset 
        '''
    # Send query
        result = self.query('ST?')
    # Parse result
        results = list(map(int,''.join(result.split()).split(',')))
        results = ['{:08b}'.format(bit) for bit in results]
        results = [[bit for bit, value in enumerate(binary_string[::-1]) if value == '1'] for binary_string in results]
        return results
    
