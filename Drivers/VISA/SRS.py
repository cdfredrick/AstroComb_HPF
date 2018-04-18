# -*- coding: utf-8 -*-
"""
Created on Tue Nov 28 13:14:23 2017

@author: cdf1
"""
# %% Modules
import Drivers.VISA.VISAObjects as vo
from Drivers.Logging import ACExceptions
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
            raise ACExceptions.VirtualDeviceError('Could not create SRS SIM900 instrument!', self.__init__)
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
        result = self.resource.query(message, delay=delay).strip()
        return result

    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def read(self, termination=None, encoding=None):
        result = self.resource.read(termination=termination, encoding=encoding).strip()
        return result
    
    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def write(self, message, termination=None, encoding=None):
        self.resource.write(message, termination=termination, encoding=encoding)


# %% SIM960 PID Controller
class SIM960(SIM900):
    @log.log_this()
    def __init__(self, visa_address, port, res_manager=None):
        super(SIM960, self).__init__(visa_address, port, res_manager=res_manager)
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
            return bool(float(result))
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
            return bool(float(result))
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
            return bool(float(result))
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
            return bool(float(result))
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
            return bool(float(result))
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
            return bool(float(result))
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
            return bool(float(result))
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
            return bool(float(result))
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
        return bool(float(result))
    
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
            return bool(float(result))
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
            return bool(float(result))
        else:
        # Limit range
            set_display = vo.tf_to_10(set_display)
        # Send command
            self.write('DISX {:}'.format(['OFF','ON'][set_display]))

# %% SIM940 10 MHz Rubidium Oscillator
class SIM940(SIM900):
    @log.log_this()
    def __init__(self, visa_address, port, res_manager=None):
        super(SIM940, self).__init__(visa_address, port, res_manager=res_manager)
        self.open_resource()
        self.write_termination = '\r' # different termination than mainframe
        self.read_termination = '\r'
        self.close_resource()

    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def read(self, encoding=None):
        result = self.resource.read(termination=self.read_termination, encoding=encoding).strip()
        return result
    
    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def write(self, message, encoding=None):
        self.resource.write(message, termination=self.write_termination, encoding=encoding)
    
    @vo._handle_visa_error
    @_auto_connect
    @log.log_this()
    def query(self, message, delay=None):
        self.resource.write(message, termination=self.write_termination)
        result = self.resource.read(termination=self.read_termination).strip()
        return result
    
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
        2           PLL active (locked)
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
        results = {byte:{bit:bool(int(value)) for (bit,value) in enumerate(binary_string[::-1])} for (byte,binary_string) in enumerate(results)}
        return results
    
    def lock(self, set_lock=None):
        '''Lock. This command can be used to stop the frequency lock-loop (FLL).
        
        It is essentially the same as setting the gain parameter to zero. It
        may be desirable in a particular application to stop the FLL and set
        the frequency control value for the 10MHz oscillator manually. (See the
        FC command.)
        
        The query will return whether the FLL is active (locked) or not.
        
        LO {value} value = 0 or 1
        LO? 
        
        Example:
            LO 0
            will stop the FLL.
        Example:
            LO?
            will return a value of 0 (if the FLL is not active) or 1 (if the
            FLL is active.)
        '''
        if (set_lock == None):
        # Send query
            result = self.query('LO?')
            return bool(int(result))
        else:
        # Limit range
            set_lock = vo.tf_to_10(set_lock)
        # Send command
            self.write('LO {:}'.format(set_lock))
    
    def frequency_control(self):
        '''Frequency control. These commands allow direct control of the 22bit
        value which controls the frequency of the 10 MHz ovenized oscillator.
        
        Normally, this value is controlled by the FLL control algorithm,
        however, the FLL may be stopped, and the value adjusted manually (See
        the LO command.) Two 12-bit DACs are scaled (by 1000:1) and summed to
        provide a varactor voltage which controls the frequency of the 10 MHz
        oscillator. The low DAC, which operates over half its range (to avoid
        FFL oscillations at the roll-over to the high DAC) provides a LSB
        frequency resolution of 1.5:10^-12. The high DAC, which has a nominal
        value of 2048, has a LBS resolution of 1.5:10^-9. These DACs provide a
        total tuning range of about ±3 ppm.
        
        Both DACs may be set to any value in the range specified above. 
        However, it is possible to set the frequency of the 10 MHz oscillator
        so far from the correct frequency that the FLL signal disappears,
        making the lock impossible. If this happens, the last saved FC value
        may be read from EEPROM with the FC!? command and restored with the
        FC{high,low} command. 
        
        The FC! command is used to save the current FC values in the unit’s
        EEPROM. The FC!? Command may be used to read the value which is stored
        in the EEPROM. The value stored in EEPROM is used to set the 10 MHz at
        startup, before the FLL can be established. Occasionally while the unit
        is operating (at about 20 minutes after power-on and once a day there
        after) the program will write a new value to EEPROM to correct the
        value for crystal aging.
        
        FC?
        FC {high,low}  0 ≤ high ≤ 4095, 1024 ≤ low ≤ 3072
        FC!
        FC!?
        
        Example:
            FC?
            will return the current value of the DAC pair which might be
            2021,1654 (Tracking the FC value over a long period of time tells
            you about the frequency variations of the 10MHz crystal. The FC
            values will change to correct for variations in the crystal
            frequency due to aging and ambient conditions.)
        Example:
            FC 2048,2048
            will set the 10MHz oscillator back to the middle of its tuning
            range. 
        Example:
            FC!? 
            will return four values (separated by commas), the number of power
            cycles the unit has undergone, the number of times the FC pair has
            been written to EEPROM, and the value of the FC pair (high, low)
            which is used at turn-on and restart. 
        '''
    # Send query
        result = self.query('FC?')
    # Parse result
        results = {key:int(fc) for (key,fc) in zip(['high','low'],result.split(','))}
        return results
    
    def detected_signals(self):
        '''Detected signals. This command returns two numbers corresponding to
        the synchronously detected signals at the modulation frequency, ωmod,
        and at twice the modulation frequency, 2ωmod. The returned value is a
        spot measurement taken over just one cycle of the modulation frequency.
        Since the signals have several Hz of equivalent noise bandwidth, they
        will be rather noisy.
        
        The first number, the amplitude of the signal at ωmod, is the error
        signal in the rubidium frequency lock loop. The value is proportional
        to the instantaneous frequency error of the 10 MHz oscillator as
        detected by the physics package. The value may be large when the unit
        is first locking, and will bobble around zero in steady state. Each LSB
        corresponds to about 15 µVrms of signal at ωmod.
        
        The second number is the amplitude (in millivolts rms) of the 
        synchronously detected signal at twice the modulation frequency, 2ωmod.
        The amplitude of this signal is proportional to the strength of the
        rubidium hyperfine transition signal.
        
        DS? 
        
        Example:
            DS?
            could return 55,800 indicating a small error signal and a strong
            resonance signal. 
        '''
    # Send query
        result = self.query('DS?')
    # Parse result
        results = {key:int(ds) for (key,ds) in zip(['mod','2mod'],result.split(','))}
        return results
    
    def set_frequency(self):
        '''Set frequency. This command is used to override the internal
        calibration pot (or external calibration voltage) to set the frequency
        directly, relative to the calibration values in EEPROM (see the SP and
        MO commands.)
        
        The command sets the frequency offset in units of parts in 10^-12
        (corresponding to a frequency resolution of 10 µHz at 10 MHz.)
        
        The SF? command will return the currently set relative frequency value
        (with a range of ±2000) whether the value comes from the internal
        calibration pot position, an external frequency control voltage, an SF
        command, or from the external 1pps phase lock loop control algorithm.
        
        However, SF set command is ignored if the unit is phase-locked to an
        external 1pps signal. (To re-establish direct control via the SF
        command, the PLL must be disabled. See PL 0 command.) 
        
        Data from the SF command cannot be saved when the power is turned off.
        (To do this type of calibration, see the SP and MO commands.) Once
        executed, the SF command will disable the analog channels (internal
        calibration pot and external calibration voltage) until the power is 
        cycled or the unit is restarted. 
        
        SF {value}  -2000 ≤ value ≤ +2000
        SF?
        
        Example:
            SF 100
            will set the frequency 100 x 10^-12 (or 0.001 Hz) above the stored
            calibration value, and the SF? command will return 100.
        '''
    # Send query
        result = self.query('SF?')
        return int(result)
    
    def set_slope(self):
        '''Set slope. This command is used to read the slope calibration
        parameter for the SF command. This parameter compensates for a variety
        of factors which affect the magnitude of the coefficient between
        magnetic coil current and transition frequency.
        
        This calibration parameter may not be altered by the end user. The
        (factory only) SS! command is used to store the current value of the SS
        parameter to the unit’s EEPROM.
        
        The SS!? will return the value of the SS parameter which is used on
        powerup or restart. 
        
        SS?
        SS {value}  1000 ≤ value ≤ 1900
        SS!?
        
        Example:
            SS?
            might return 1450, the nominal parameter value. 
        '''
    # Send query
        result = self.query('SS?')
        return int(result)
    
    def gain(self):
        '''Gain. This command sets the gain parameter in the frequency 
        lock-loop algorithm. Higher gain values have shorter time constants, 
        (the time constant is the time it takes for the frequency lock-loop to
        remove 67% of the frequency error) but have larger equivalent noise
        bandwidths (which will reduce the short-term stability of the 10 MHz
        output.)
        
        A gain of 0 will stop the frequency lock-loop so that the frequency of
        the output is determined by the 10MHz ovenized oscillator alone. The
        gain setting, approximate time constants, and approximate equivalent
        noise bandwidths are detailed in the following table. The gain
        parameter is set automatically by the program.
        
        The user may want control over the parameter in special circumstances.
        Setting the gain parameter during the first 6 minutes after turn-on or
        restart will abort the automatic gain sequencing. 
        
        The GA! command stores the current value of the frequency lock loop
        gain parameter into the unit’s EEPROM. 
        
        GA?
        GA {value}  0≤ value ≤ 10
        GA!
        GA!? 
        
        Example:
            GA?
            could return a value of 8 just after restart, which has a short
            time constant of about 1 s to assist the initial frequency locking.
        Example:
            GA 7
            will set the gain parameter to 7, which has a time constant of
            about 2 s, which is a typical value for normal operation.
        Example:
            GA!
            if the current value of the gain is 6, the command will write 6 to
            the unit’s EEPROM which will be used to initialize the gain
            parameter after the next power-on or restart. Then GA!? will return
            a 6.
        
        Setting     Time Constant   Noise Bandwidth 
                    (seconds)       (Hz)
        0           Infinite        0
        1           128             0.002
        2           64              0.004
        3           32              0.008
        4           16              0.016
        5           8               0.032
        6           4               0.064
        7           2               0.128
        8           1               0.256
        9           0.5             0.512
        10          0.25            1.024 
        '''
    # Send query
        result = self.query('GA?')
        return int(result)
    
    def phase(self):
        '''Phase. This command is used to set the phase of the synchronous
        detection algorithm. 
        
        The frequency lock-loop (FLL) uses the in-phase component of the 
        photo-signal at the modulation frequency (70 Hz) as the error signal
        for the FLL. The phase between modulation source and the error signal
        is affected by phase shifts in the modulation and signal filters and 
        by optical pumping time constants. This parameter corrects for the
        accumulation of all of these phase shifts. Each modulation cycle 
        consists of 32 phase slots, so each phase increment corresponds to
        11.25°. 
        
        The PH! command is used to write the current phase parameter into the
        unit’s EEPROM. This is a factory only command. The value which is
        burned in EEPROM is used on power-on and restart, and may be queried by
        the PH!? command. 
        
        PH?
        PH {value}  0 ≤ value ≤ 31
        PH!
        PH!? 
        
        Example:
            PH?
            would typically return a value of 24.
        Example:
            PH!?
            could return a typical value of 24.
        '''
    # Send query
        result = self.query('PH?')
        return int(result)
    
    def set_parameters(self, set_params=None):
        '''Set Parameters. This command is used to set or query the frequency
        synthesizer’s parameters, which will coarsely adjust the unit’s output
        frequency. These parameters may need to be adjusted if the unit cannot
        be calibrated by magnetic field adjustment.
        
        The SP! command is used to write the current frequency synthesizer
        parameters to the unit’s EEPROM for use after the nest restart or
        power-on cycle. This command is used after the SP command is used
        during the calibration of the unit.
        
        SP!? will return the values for R, N and A which are currently in the
        unit’s EEPROM. The SP!? command may be used to verify that the SP!
        write command executed correctly. 
        
        A frequency synthesizer, which uses the 10 MHz OCXO as a frequency
        reference, is used to generate the RF which sweeps the rubidium 
        hyperfine transition. The frequency synthesizer multiplies the 10 MHz
        by a factor M = 19 * (64*N + A) / R, to generate a frequency near
        6.834 GHz. (The factor of 19 is from frequency multiplication in the 
        step recovery diode, and the other terms come from the operation of the
        dual modulus frequency synthesizer integrated circuit.) The apparent
        transition frequency is different for each physics package, due mostly
        to variations in the fill pressure of the resonance cell. The frequency
        synthesizer parameters, R, N and A, are used to adjust the frequency
        synthesizer’s output frequency to the closest frequency just above the
        apparent transition frequency, then the magnetic field is set to move
        the transition frequency up to the synthesizer frequency. During 
        frequency locking, the frequency of the 10 MHz OCXO is adjusted to
        maintain the output of the frequency synthesizer on the rubidium
        hyperfine transition frequency. Initial calibration of the unit will
        involve finding the synthesizer parameters and magnetic field value
        which will lock the 10 MHz OCXO at exactly 10 MHz.
        
        During the lifetime of the unit, there will be some aging of the
        physics package, which will cause the apparent transition frequency to
        change. This is usually corrected by minor calibration adjustments of
        the magnetic field strength, which provides a setting resolution of a
        few parts in 10^-12. (See the MO command.) However, if the magnetic
        field strength reaches its lower or upper limit, it is necessary to
        change the frequency synthesizer parameters, which can change the
        output frequency in steps of about one part in 10^-9. The table in
        Appendix A (of the PRS10 user's manual) details the values for R, N and A
        for the range of frequencies needed.
        
        SP?
        SP {R,N,A}  1500≤ R ≤ 8191, 800≤ N ≤ 4095, 0≤ A ≤ 63
        SP!
        SP!?
        
        Example:
            During calibration, a unit’s 10 MHz output frequency is found to
            be low by 0.010 Hz, and the magnetic field offset adjustment is
            already at its maximum. (See the MO command.) Sending the SP?
            command returns the current values of R, N and A which are 
            2610,1466,63 in this example. This corresponds to line 38 in the
            table in Appendix A (of the PRS10 user's manual). To increase the
            frequency of the 10 MHz output, we select the next higher setting,
            line 37, which will increase the frequency by 0.01986 Hz. To do
            this, we send the command SP 5363,3014,22 (which are the parameters
            from line 37). Waiting for the frequency to settle, we now measure
            the output to be about 0.0098 Hz high. Now the magnetic field is
            adjusted down to calibrate the unit to exactly 10 MHz. (The SP!
            command is used to save these new values in EEPROM for the next
            power-on or restart. Also see the MO command for adjusting the
            magnetic field.)
        Example:
            SP!
            will write the frequency synthesizer parameters (R, N and A) which
            are currently in use to the unit’s EEPROM. 
        '''
        if set_params == None:
        # Send query
            result = self.query('SP?')
        # Parse result
            results = {key:int(ds.strip()) for (key,ds) in zip(['R','N','A'],result.split(','))}
            return results
        else:
        # Limit range
            if (set_params['R'] < 1500):
                set_params['R'] = 1500
            elif (set_params['R'] >8191):
                set_params['R'] = 8191
            if (set_params['N'] < 800):
                set_params['N'] = 800
            elif (set_params['N'] > 4095):
                set_params['N'] = 4095
            if (set_params['A'] < 0):
                set_params['A'] = 0
            elif (set_params['A'] > 63):
                set_params['A'] = 63
            for key in set_params:
                set_params[key] = int(set_params[key])
        # Send command
            self.write('SP {R:},{N:},{A:}'.format(**set_params))
            self.write('SP!')
    
    def magnetic_switching(self, set_switching=None):
        '''Magnetic switching. The MS command is used to turn off or on the 5Hz
        switching of the frequency tuning magnetic field.
        
        Magnetic switching is enabled when the unit is powered-on or after a
        restart. (Since the PRS10 is calibrated with the field switching
        enabled, turning off the field switching may alter the calibration.)
        
        MS?
        MS {0 or 1}
        
        Example:
            MS 1
            will turn on the magnetic field switching
        Example:
            MS 0
            will turn it off
        Example:
            MS?
            will return a “1” if the field switching is currently enabled. 
        '''
        if (set_switching == None):
            # Send query
            result = self.query('MS?')
            return bool(int(result))
        else:
        # Limit range
            set_switching = vo.tf_to_10(set_switching)
        # Send command
            self.write('MS {:}'.format(set_switching))
    
    def magnetic_offset(self, set_offset=None):
        '''Magnetic offset. The magnetic offset is the value, determined when
        the unit is calibrated, which calibrates the unit to 10 MHz. The
        restricted range is necessary to allow room for user calibration via
        the internal frequency calibration pot or by an external voltage. If
        the unit cannot be calibrated to 10 MHz within the allowed range of MO
        values, then a different setting for the frequency synthesizer is
        required (see SP command and the table in Appendix A of the PRS10
        user's manual).
        
        The MO? command reads back the current value of the magnetic offset.
        
        MO! is used to store the current value of the magnetic offset parameter
        to EEPROM for use after the next restart.
        
        MO!? may be used to query the value stored in EEPROM. This value is
        used on power-up or restarts.

        A magnetic field coil inside the resonance cell is used to tune the
        apparent hyperfine transition frequency. The magnetic field is
        controlled by a 12-bit DAC. Increasing the magnetic field will increase
        the hyperfine transition frequency, which will increase the frequency
        of the 10 MHz output. The transition frequency may be tuned over about
        ±3 x 10^-9 by the magnetic field, which corresponds to ±0.030 Hz at
        10 MHz. The output frequency (at 10 MHz) tunes quadratically with field
        strength, and ∆f(Hz) ≈ 0.08 * (DAC/4096)^2. A minimum magnetic field
        should always be present to avoid locking to the wrong Zeeman component
        of the hyperfine transition, so the 12-bit DAC may be set from 1000 to
        4095 with 3000 being the nominal midscale value. (A DAC value of 1000
        corresponds to about 6% of the full-scale frequency tuning range, 3000
        corresponds to about 53%, while 4095 is 100% of the full-scale range.)
        
        To help cancel frequency shifts due to external magnetic fields, the
        current in the coil is switched at a 5 Hz rate. The frequency lock-loop
        averages over a full period of the switch rate to avoid injecting a
        spur at 5 Hz onto the 10 MHz control signal. The switching of the 
        magnetic field is enabled at power-on and restart, but may be turned
        on or off by RS-232 command. (see MS command.)
        
        The commands associated with magnetic field control (MO, MS, and MR)
        allow direct control of the magnetic field circuitry. Most users will
        not want to control the magnetic field directly, but will instead
        allow the program to read the frequency calibration pot or external 
        control voltage and then control the magnetic field. If they want
        software control of the unit’s calibration, they may choose to use the
        SF commands, which disable the analog control and allow the frequency
        to be adjusted over a range of ±2000x10^-12. (The program will linearize
        the magnetic field control of the frequency offset with either analog
        or software control.)
        
        MO?
        MO {value}  2300 ≤ value ≤ 3600
        MO!
        MO!? 
        
        Example:
            MO 3000
            sets the magnetic offset to 3000, which is its nominal (mid-linear
            scale) value. 
        '''
        if (set_offset == None):
        # Send query
            result = self.query('MO?')
            return int(result.strip())
        else:
        # Limit range
            if (set_offset < 2300):
                set_offset = 2300
            elif (set_offset > 3600):
                set_offset = 3600
        # Send command
            self.write('MO {:}'.format(int(set_offset)))
            self.write('MO!')
    
    def magnetic_read(self):
        '''Magnetic read. This command returns the value that the 12-bit DAC is
        using to control the magnetic field.
        
        This value is computed from the magnetic offset value (see MO command)
        and the position of the internal frequency calibration pot, external
        calibration voltage, or value sent by the SF command. The value is
        computed from the equation DAC = √(SF*SLOPE + MO2), where SF is the 
        desired frequency offset in parts per 10^-12 (from the cal pot
        position, the SF command, or the 1pps PLL and is in the range
        –2000 < SF < 2000), SLOPE is the SF calibration factor with a nominal
        value of 1450 (see SS command), and MO is the magnetic offset value.
        The returned value should be in the range of 1000 to 4095.
        
        MR? 
        
        Example:
            MR?
            would return a value of 3450 if the magnetic offset is at 3000,
            the SF command requested an offset of +2000 x 10-12, and the SS CAL
            factor has the nominal value of 1450.
        '''
    # Send query
        result = self.query('MR?')
        return int(result)
    
    def time_tag(self):
        '''Time-tag. This command returns the value of the most recent time-tag
        result in units of nanoseconds.
        
        If a new time-tag value is not available then -1 (the only case for
        which the returned value is negative) will be returned. Returned values
        range from 0 to 999999999.
        
        To facilitate system integration, the PRS10 provides a 1pps output
        which may be set over an interval from 0 to 999,999,999 ns with 1ns
        resolution. The unit also has the ability to measure the arrival time
        of a 1pps input over the same interval and with the same resolution.
        The ability to time-tag a 1pps input allows the PRS10 to be
        phase-locked to other clock sources (such as the 1pps output from a
        GPS receiver) with very long time-constants. This is a very useful
        feature for network synchronization, and allows the configuration of a
        reliable Stratum I source. 
        
        TT? 
        
        Example:
            TT?
            would return the value 123456789 to indicate that the most recent
            1pps input arrived 123,456,789ns after the 1pps output.
        '''
    # Send query
        result = self.query('TT?')
    # Format result
        result = int(result)
        if (result < 0):
            result = None
        elif (result > 1000000000//2):
            result = int(result - 1000000000)
        return result
    
    def time_slope(self):
        '''Time slope. This command is used to calibrate the analog portion of
        the time-tagging circuit.
        
        The analog portion is used to digitize the time of arrival with 1 ns
        resolution and 400 ns fullscale (counters are used for the portion of a
        time interval longer than 400 ns). The analog circuit stretches the
        time interval between the 1pps input and the next edge of a internal
        2.5 MHz clock by a factor of about 2000, and measures the duration of
        the stretched pulse by counting a 2.5 MHz clock. The analog portion of
        the time-tag result is calculated from the equation
        ∆T(ns) = counts * TS / 2^16, where TS is the time slope value, which
        has a nominal value of 13,107.
        
        TS? will return the current value of the time slope.
        
        The TS! command is used to write the current value of the time slope
        parameter into the unit’s EEPROM. The TS {value} and TS! are factory
        only commands. 
        
        TS?
        TS {value}  7000 ≤ value ≤ 25000
        TS!
        TS!? 
        
        Example:
            TS!
            will write the current value of the time slope (which may be
            queried with the TS? command) to the unit’s EEPROM. 
        Example:
            TS!? 
            will return the time slope calibration factor which is in the
            unit’s EEPROM. 
        Example:
            TS?
            might return 14,158 which is a time slope parameter value a bit
            above the nominal value, which would be required if the analog
            portion of the time-tagging circuit stretched the pulse by a bit
            less than a factor of 2000. 
        '''
    # Send query
        result = self.query('TS?')
        return int(result)
    
    def phase_lock_control(self, set_lock=None):
        '''Phase lock control. This command may be used to disable the 1pps
        PLL, or to re-enable (and so restart) the 1pps PLL.
        
        The unit is shipped with the phase lock control enabled. This command
        would be used if the 1pps time-tagging were being used to measure the
        position of 1pps inputs and phase locking is not desired.
        
        PL? will return a “1” if the PLL to the 1pps is enabled.
        
        PL! is used to write the current value (0 or 1) to the EEPROM for use
        after the next start up.
        
        PL!? is used to query the value of the phase lock control parameter
        which is stored in the unit’s EEPROM. 
        
        PL?
        PL {0 or 1}
        PL!
        PL!?
        
        Example:
            PL 0
            will disable the PLL to the 1pps inputs so that the frequency of
            the rubidium standard will not be affected by the 1pps inputs.
            
        '''
        if (set_lock == None):
        # Send query
            result = self.query('PL?')
            return bool(int(result))
        else:
        # Limit range
            set_lock = vo.tf_to_10(set_lock)
        # Send command
            self.write('PL {:}'.format(set_lock))
            self.write('PL!')
    
    def integrator_time_constant(self, set_constant=None):
        '''Phase-lock integrator time constant. This command is used to set the
        PLL’s integrator’s time constant, τ1, which phase-locks the PRS10 to an
        external 1pps input.
        
        The integrator time constant is equal to 2^(value+8) seconds. The
        default value is 8, which provides an integrator time constant of
        2^(8+8) or 65536 seconds. Integrator’s time constants can range from
        256 to 4,194,304 seconds, or from about 4 minutes to 18 days. It is
        important to note that the natural time constant, τn, is different from
        the integrator time constant, as shown in the table below.
        
        The natural time constant is the best measure of the loop response. The
        PLL natural time constant spans between 8 minutes and 18 hours for PT
        values between 0 and 14. 
        
        PT? will return the current value of the time constant parameter. 
        
        A phase lock time constant may be stored in EEPROM as a new default
        with the PT! command. 
        
        The PT!? command may be used to verify the value stored in EEPROM.
        
        PT?
        PT {value}  0 ≤ value ≤ 14 ; τ1 = 2^(value+8) seconds (256, 512, ... 4,194,304)
        PT!
        PT!? 
        
        Example:
            PT 10
            sets the integrator time constant to 2(10+8) seconds, or about 72
            hours. (Refer to Table below.) For PT 10 the natural time constant
            is about 4.5 hours. 
        
        The following case will illustrate the operation of the PLL:
            Suppose that the PRS10 has been phase locked to a stable 1pps
            reference for a very long time (several periods of τn) when the 
            1pps reference input makes an abrupt shift of +100ns (moving later
            in time). The PRS10’s 1pps PLL algorithm will reduce the PRS10’s
            frequency of operation (by adjusting its SF parameter) to eliminate
            the 100ns phase shift between the 1pps reference input and the 1pps
            output. After the phase shift is eliminated, the PRS10 will settle
            to the “correct” operating frequency. The PLL algorithm computes
            integral and proportional terms from time-tag measurements, 
            adjusting the SF parameter to phase lock the 1pps output to the
            1pps input. The table below shows the integral and proportional
            gain terms. For the nominal PT value of 8, the integral term is
            -0.055 SF bits per hour per ns of time-tag and the proportional
            gain is -0.25 SF bits per ns of time-tag. Per the table below for
            PT 8, if the input reference shifts by +100ns, the proportional
            term will adjust the SF by -0.25bits/ns * 100ns = -25 bits. Each SF
            bit corresponds to 1:10^-12 of the operating frequency, and so the
            PRS10 frequency will be shifted by about -25 x 10^-12. The integral
            term will begin ramping by (-0.055bits/hour/ns) * 100ns, or by -5.5
            bits per hour. The phase shift between the 1pps input and 1pps
            output will be gradually eliminated. (Phase jumps of 100ns are
            quite common on 1pps outputs from GPS receivers, which are a likely
            1pps reference to the PRS10. The corresponding frequency jumps of
            25 x 10^-12 may be excessive in some applications, and so a digital
            pre-filter is used to smooth the time-tag values before they are
            used by the PLL algorithm. See LM command.) 
        
        PLL Table for all PT values, assuming a stability factor, ζ=1.
        PT Parameter    Integrator TC   Integral Gain       Proportional Gain   Natural Time Constant
        (Parameter set  (hours)         (SF bits per hour   (SF bits per ns of  (Characterizes PLL
        by PT command)                  per ns of time-tag) time-tag)           response, hours)
        0               0.07            -14.063             -3.95               0.14
        1               0.14            -7.031              -2.80               0.20
        2               0.28            -3.516              -1.98               0.28
        3               0.57            -1.758              -1.40               0.40
        4               1.14            -0.879              -0.99               0.56
        5               2.28            -0.439              -0.70               0.80
        6               4.55            -0.220              -0.49               1.12
        7               9.10            -0.110              -0.35               1.59
        8               18.20           -0.055              -0.25               2.25
        9               36.41           -0.027              -0.17               3.18
        10              72.82           -0.014              -0.12               4.50
        11              145.64          -0.007              -0.09               6.36
        12              291.27          -0.003              -0.06               8.99
        13              582.54          -0.002              -0.04               12.72
        14              1,165.08        -0.001              -0.03               17.99 
        '''
        if (set_constant == None):
        # Send query
            result = self.query('PT?')
            return int(result)
        else:
        # Limit range
            if (set_constant < 0):
                set_constant = 0
            elif (set_constant > 14):
                set_constant = 14
        # Send command
            self.write('PT {:}'.format(int(set_constant)))
            self.write('PT!')
    
    def stability_factor(self, set_factor=None):
        '''Phase-lock stability factor. This command is used to set the 
        stability factor, ζ, of the 1pps PLL.
        
        The stability factor is equal to 2^(value-2). The default value is 2,
        which provides a stability factor of 2^(2-2) = 2^0 = 1. Stability
        factors can range from 0.25 to 4.0.
        
        PF? will return the current value of the stability factor parameter.
        
        PF! may be used to write the current stability factor to the EEPROM for
        use as the new default. 
        
        PF!? may be used to read the value of the stability factor which is
        stored in EEPROM.
        
        PF?
        PF {value}  0 ≤ value ≤ 4 ; (value:ζ):(0:1/4, 1:1/2, 2:1, 3:2, or 4:4)
        PF!
        PF!?
        
        Example:
            PF 1
            sets the stability factor to 0.5, which will reduce the equivalent
            noise bandwidth of the PLL at the cost of increasing the ringing
            near the natural frequency (relative to the default settings). 
        '''
        if (set_factor == None):
        # Send query
            result = self.query('PF?')
            return int(result)
        else:
        # Limit range
            if (set_factor < 0):
                set_factor = 0
            elif (set_factor > 4):
                set_factor = 4
        # Send command
            self.write('PF {:}'.format(int(set_factor)))
    
    def integrator_gain(self):
        '''Phase-lock integrator. This command is used to set the value of the
        integral term in the PLL’s digital filter.
        
        It is not necessary to set this value, as it will be initialized by the
        PLL routine to the current frequency setting parameter when the PLL
        begins. Users may want access to the value to alter the PLL
        characteristics, or to investigate its operation.
        
        PI? will return the current value of the PLL integrator (there are two
        terms which control the phase locking of the PRS10 to an external 1pps
        source: the integral term and the proportional term. The proportional
        term is equal to the value returned by an SF? minus the value returned
        by the PI?).
        
        PI?
        PI {value}  -2000 ≤ value ≤ 2000
        
        Example: 
            PI 0
            will set the integrator in the PLL’s digital filter to 0, which is
            the center of the ±2000 bit range. 
        '''
    # Send query
        result = self.query('PI?')
        return int(result)
    
    def dac(self, port):
        '''Set DAC. This command is used to set (or read the settings of) an
        octal 8bit DAC which provides analog signals to control systems
        parameters. 
        
        The command which sets values is only available to the
        factory. The command to query values may be used by all. The query 
        command returns a single integer in the range of 0 to 255.
        
        The SD{port}! is a factory only command which writes the data from the
        corresponding SD port to the unit’s EEPROM for use on subsequent
        restarts. 
        
        SD {port}?
        SD {port,value}  0 ≤ port ≤ 7, 0 ≤ value ≤ 255 (factory only)
        SD {port}!
        SD {port}!?
        
        Example:
            SD 2?
            could return the value 255 indicating that the unit has set the
            discharge lamp’s FET drain voltage to the maximum (which it does
            while it is trying to start the lamp.)
        Example:
            SD 3!?
            will return the start-up value for SD 3 (lamp temperature control
            value) which is stored in the unit’s EEPROM
        
        Port    Function
        0       Controls the amplitude of the RF to multiplier in resonance cell
        1       Controls the analog portion (0 to 99 ns) of the delay for the 1pps output 
        2       Controls the drain voltage for the discharge lamp’s FET oscillator
        3       Controls the temperature of the discharge lamp
        4       Controls the temperature of the 10 MHz SC-cut crystal
        5       Controls the temperature of the resonance cell
        6       Controls the amplitude of the 10 MHz oscillator
        7       Controls the peak deviation for the RF phase modulation
        '''
    # Send query
        result = self.query('SD {:}?'.format(int(port)))
        return int(result)
    
    def adc(self, port):
        '''Analog to digital. This command reads the voltage at the
        corresponding 12-bit ADC port and returns the voltage as a floating
        point number. Values can range from 0.000 to 4.998.
        
        A/D via CPU’s E-port. This command also returns a value corresponding
        to the voltage present at the input to the microcontroller’s octal 8bit
        ADC (port E on the MC68HC11). Only the first four ports are in use.
        
        The voltages correspond to various test points in the system per the
        table below. Note that this command can only query. 
        
        AD {port}?  0 ≤ port ≤ 19
        
        Examples:
            AD 10?
            could return the value 0.710 indicating that the case temperature
            sensor is at 71 °C (this sensor indicates a temperature which is
            about midway between the baseplate temperature and the lamp
            temperature.) 
        Example:
            AD 17?
            could return a value of 4.81 indicating that the 360 MHz RF
            synthesizer has acquired lock. 
        
        Port    Returned voltage
            12-bit ADC ports
        0       Spare (J204)
        1       +24V(heater supply) divided by 10.
        2       +24V(electronics supply) divided by 10
        3       Drain voltage to lamp FET divided by 10
        4       Gate voltage to lamp FET divided by 10
        5       Crystal heater control voltage
        6       Resonance cell heater control voltage
        7       Discharge lamp heater control voltage
        8       Amplified ac photosignal
        9       Photocell’s I/V converter voltage divided by 4
        10      Case temperature (10 mV/°C)
        11      Crystal thermistors
        12      Cell thermistors
        13      Lamp thermistors
        14      Frequency calibration pot / external calibration voltage
        15      Analog ground
            8-bit microcontroller’s ADC ports
        16      Varactor voltage for 22.48 MHz VCXO (inside RF synthesizer) / 4
        17      Varactor voltage for 360 MHz VCO (output of RF synthesizer) / 4
        18      Gain control voltage for amplifier which drives frequency multiplier / 4
        19      RF synthesizer’s lock indicator voltage (nominally 4.8 V when locked ) 
        '''
    # Send query
        result = self.query('AD {:}?'.format(int(port)))
        return float(result)


