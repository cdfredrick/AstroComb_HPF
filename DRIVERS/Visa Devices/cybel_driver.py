# -*- coding: utf-8 -*-
"""
Created on Mon Jun 05 13:54:03 2017

@author: Wesley Brand


Depends on visa_objects.py


The functions in this module are all private


List of public methods in class Cybel:

General:
    __init__(res_address, res_name)
    reboot()
    eeprom_save()

Enable Components:
    enable_pump(pump_num, pump_on)
    enable_tec(tec_num, tec_on)
    enable_keep_on(keep_on)

Queries:
    sn_str, fw_str = query_serial_and_firmware()
    str = query_cpld_firmware()
    TF = query_pump_status(pump_num)
    TF0, TF1, TF2, TF3 = query_temp_error()
    TF0, TF1  = query_trigger_n_laser_status()
    TF = query_tec_status(tec_num)
    query_pump_read_constants() #writes values to Cybel.pccr_list
    query_pump_write_constants() #writes values to Cybel.pccw_list
    query_pump_current_limits() #writes values to Cybel.pcl_list
    dict = query_analog_input_values()
    dict = query_analog_output_values()
    float = query_trigger_timeout() #Hz
    float = query_pulse_width() #ns
    float1, float2 = query_digital_temp_sensors() #Celsius
    float = query_pulse_rep_rate() #kHz
    TF = query_keep_on()
    query_allowed_components()

Set Values:
    set_tec_temp(tec_num, temp) #Celsius
    set_pump_current(pump_num, current) #amps
    set_seed_bias_voltage(voltage) #volts
    set_trigger_timeout(frequency) #Hz
    set_pulse_width(pw_val) #see table
    set_pump_read_constant(pump_num, val)
    set_pump_write_constant(pump_num, val)

"""
#pylint: disable=R0904
### There's good reason to have this many public methods

import time
import numpy as np
import visa_objects as vo
import eventlog as log

CYBEL_NAME = 'Cybel Amplifier'
CYBEL_ADDRESS = '' #ADD ME!!!!


def _dict_assign(dictionary, keys, values):
    """Assigns multiple values to dictionary at once."""
    dictionary.update(zip(keys, values))

def _compute_tec_temp(raw_val):
    """Returns temperature from raw device reading."""
    return 40.*(raw_val/1638.-1.25)+25.

def _compute_input_current(raw_val, pccr):
    """Returns pump input current from raw device reading."""
    return raw_val*pccr/4095000.

def _compute_output_current(raw_val, pccw, pump_num):
    """Returns pump output current from raw device reading."""
    constants_list = [1470, 235, 147]
    return raw_val*pccw/4095000./constants_list[pump_num-1]

def _compute_pd_power(raw_val, pd_num):
    """Returns photodiode power from raw device reading."""
    constants_list = [0.202, 3.912]
    return raw_val/1638.*constants_list[pd_num-1]

def _compute_analog_temp(raw_val):
    """Returns sensor temperature from raw device reading."""
    return 100.*(raw_val/1638. - 0.5)

def _form_temp_command(temp):
    """Makes set temperature into machine-readable format."""
    temp_val = int(np.floor(1638.*((temp-25.)/40.+1.25)))
    if temp_val > 4095 or temp_val < 0:
        log.log_warn(__name__, '_form_temp_command',
                     'Temperature to be set is out of bounds!')
        return
    temp_str = str(temp_val).zfill(4)
    return temp_str

def _form_current_command(pump_num, current, pccw_list):
    """Makes set pump current into machine-readable format."""
    if pump_num == 0:
        current_val = int(np.floor(current*1638.))
    else:
        const_list = [1470., 235., 147.]
        factor = const_list[pump_num-1]/pccw_list[pump_num-1]*1638.
        current_val = int(np.floor(current*factor))
    current_str = str(current_val).zfill(4)
    return current_str

def _string_to_bits(string=''):
    """Converts ascii character into bit string."""
    return [bin(ord(x))[2:].zfill(8) for x in string][0]


class Cybel(vo.Visa):
    """Holds cybel amplifier's attributes and method library."""

    #General methods

    @log.log_this()
    def __init__(self, res_name, res_address):
        super(Cybel, self).__init__(res_name, res_address)
        self.res = super(Cybel, self).open_resource()
        if self.res is None:
            log.log_warn(__name__, '__init__',
                         'Could not create Cybel instrument!')
            return
        self.res.term_chars = 'CR+LF'
        self.res.timeout = 3
        self.res.baud_rate = 57600
        self.res.data_bits = 8
        self.res.stop_bits = vo.SB_ONE
        self.__disable_echo()
        self.pccr_list = [] #Pump read constants, length 3
        self.query_pump_read_constants()
        self.pccw_list = [] #Pump write constants, length 3
        self.query_pump_write_constants()
        self.pcl_list = [] #Pump current limits, length 4 (includes seed)
        self.query_pump_current_limits()

    @log.log_this(20)
    def close(self):
        """Ends device session."""
        self.res.close()

    @vo.handle_timeout
    @log.log_this(20)
    def reboot(self):
        """Reboots electronic board."""
        self.res.query('RESET')

    @vo.handle_timeout
    @log.log_this(20)
    def eeprom_save(self):
        """Saves manual-specified values into electronic board."""
        self.res.query('SAVE')
        time.sleep(3) #Takes a few seconds and can't be interrupted

#Enable Methods

    @vo.handle_timeout
    @log.log_this()
    def __disable_echo(self, echo_off=True):
        """Turns off echo, made private because it should stay off."""
        if echo_off is True:
            self.res.write('SEN')
        if echo_off is False:
            self.res.write('SEE')

    @vo.handle_timeout
    @log.log_this(20)
    def enable_pump(self, pump_num, pump_on):
        """Turns pump on (pump_on=True) or off (pump_on=False).3"""
        self.res.write('P%d%d' % (pump_num, vo.tf_toggle(pump_on)))

    @vo.handle_timeout
    @log.log_this(20)
    def enable_tec(self, tec_num, tec_on):
        """tec_num=0 for seed, ={1,2,3} for pumps, turns on if tec_on=True."""
        if tec_num == 0:
            tec_num = 'S'
        self.res.write('TEC%d%d' % (tec_num, vo.tf_toggle(tec_on)))

    @vo.handle_timeout
    @log.log_this()
    def enable_keep_on(self, keep_on):
        """Enables keeping laser on when connection ends if True"""
        self.res.write('KP%d' % vo.tf_toggle(keep_on))

#Query Methods

    @vo.handle_timeout
    @log.log_this()
    def query_serial_n_firmware(self):
        """Returns 8 character SN and 4 character ucontroller firmware #."""
        raw_sn_and_fw = self.res.query('CO')
        serial = raw_sn_and_fw[:8]
        firmware = raw_sn_and_fw[:10]
        return serial, firmware

    @vo.handle_timeout
    @log.log_this()
    def query_cpld_firmware(self):
        """Returns 4 character CPLD firmware version."""
        raw_cpld = self.res.query('CPLD?')
        return raw_cpld[4:8]

    @vo.handle_timeout
    @log.log_this()
    def query_pump_status(self, pump_num):
        """Returns True if pump is on and False if pump is off."""
        pump_status = self.res.query('P%d?' % pump_num)
        if pump_status[2] == '0':
            log.log_warn(__name__, 'query_pump_status',
                         'Pump %d is off!' % pump_num)
            return False
        return True

    @vo.handle_timeout
    @log.log_this()
    def query_temp_error(self):
        """Returns True for each TEC within error, False if not."""
        temp_error = self.res.query('FB?')
        seed_temp = pump1_temp = pump2_temp = pump3_temp = True
        if temp_error[2] == '0':
            log.log_warn(__name__, 'query_temp_error',
                         'Seed temperature outsde error limit!')
            seed_temp = False
        if temp_error[3] == '0':
            log.log_warn(__name__, 'query_temp_error',
                         'Pump 1 temperature outsde error limit!')
            pump1_temp = False
        if temp_error[4] == '0':
            log.log_warn(__name__, 'query_temp_error',
                         'Pump 2 temperature outsde error limit!')
            pump2_temp = False
        if temp_error[5] == '0':
            log.log_warn(__name__, 'query_temp_error',
                         'Pump 3 temperature outsde error limit!')
            pump3_temp = False
        return seed_temp, pump1_temp, pump2_temp, pump3_temp

    @vo.handle_timeout
    @log.log_this()
    def  query_trigger_n_laser_status(self):
        """Returns True's if trigger is correct and laser is emitting."""
        tl_status = self.res.query('TS?')
        trigger_match = laser_on = True
        if tl_status[2] == '0':
            log.log_warn(__name__, 'query_trigger_n_laser_status',
                         'External trigger does not match requirement!')
            trigger_match = False
        if tl_status[3] == '0':
            log.log_warn(__name__, 'query_trigger_n_laser_status',
                         'Laser not emitting!')
            laser_on = False
        return trigger_match, laser_on

    @vo.handle_timeout
    @log.log_this()
    def query_tec_status(self, tec_num):
        """tec_num=0 for seed, ={1,2,3} for pumps, returns True if tec on."""
        if tec_num == 0:
            tec_num = 'S'
        tec_status = self.res.query('TEC%s?' % tec_num)
        if tec_status[4] == '0':
            log.log_warn(__name__, 'query_tec_status',
                         '%s TEC is off!' % tec_num)
            return False
        return True

    @vo.handle_timeout
    @log.log_this()
    def query_pump_read_constants(self):
        """Saves pump current read multiplying factors in Cybel object."""
        raw_constants = self.res.query('PCCR?')
        start = np.arange(0, 2*5, 5)
        new_pccr_list = []
        for i in start:
            new_pccr_list.append(float(raw_constants[start[i]:(start[i]+4)]))
        self.pccr_list = new_pccr_list

    @vo.handle_timeout
    @log.log_this()
    def query_pump_write_constants(self):
        """Saves pump current write multiplying factors in Cybel object."""
        raw_constants = self.res.query('PCCW?')
        start = np.arange(0, 2*5, 5)
        new_pccw_list = []
        for i in start:
            new_pccw_list.append(float(raw_constants[start[i]:(start[i]+4)]))
        self.pccw_list = new_pccw_list

    @vo.handle_timeout
    @log.log_this()
    def query_pump_current_limits(self):
        """Saves pump current limits in Cybel object."""
        raw_limits = self.res.query('AOL?')
        start = np.arange(0, 2*5, 5)
        new_pcl_list = [2.5]
        for i in start:
            raw_val = float(raw_limits[start[i]:(start[i]+4)])
            pcl = _compute_output_current(raw_val, self.pccw_list[i], i)
            new_pcl_list.append(pcl)
        self.pcl_list = new_pcl_list

    @vo.handle_timeout
    @log.log_this()
    def query_analog_input_values(self):
        """Returns a dictionary of values.

        Dictionary entries:
            'seed_temp', 'pump1_temp', 'pump2_temp', 'pump3_temp'  ## Celsius
            'pump1_amps', 'pump2_amps', 'pump3_amps'               ## Amps
            'pump1_pd_power','pump2_pd_power'                      ## Watts
            'seed_bias_volts'                                      ## Volts
            'anlg_temp_sens1', 'anlg_temp_sens2'                   ## Celsius
            'test_5volt', 'test_1_8volt', 'test_28volt'            ## Volts
            'monitor_pd1','monitor_pd2'                            ## Volts
        """
        analog_raw = self.res.query('AI?')
        val_list = []
        ai_vals = {}
        start = np.arange(0, 16*5, 5)
        for i in start:
            val_list.append(float(analog_raw[start[i]:(start[i]+4)]))
        #Seed and 3 pump TEC temperatures in Celsius
        _dict_assign(ai_vals, ('seed_temp', 'pump1_temp', 'pump2_temp',
                               'pump3_temp'),
                     _compute_tec_temp(val_list[0:3]))
        #Pump currents in amps
        _dict_assign(ai_vals, ('pump1_amps', 'pump2_amps', 'pump3_amps'),
                     _compute_input_current(val_list[4:6],
                                            self.pccr_list[0:2]))
        #Pumps 1 and 2 photodiode powers in watts
        _dict_assign(ai_vals, ('pump1_pd_power', 'pump2_pd_power'),
                     _compute_pd_power(val_list[7:8], [1, 2]))
        #Seed bias voltage
        ai_vals['seed_bias_volts'] = val_list[9]/1638.
        #Analog temperature sensors in celsius
        _dict_assign(ai_vals, ('anlg_temp_sens1', 'anlg_temp_sens2'),
                     _compute_analog_temp(val_list[10:11]))
        #Voltage tests: 5V, 1.8V, and 28V in volts
        #And Monitor photodiodes 1 and 2 in volts
        _dict_assign(ai_vals, ('test_5volt', 'test_1_8volt', 'test_28volt',
                               'monitor_pd1', 'monitor_pd2'),
                     val_list[12:16]/1638.)
        return ai_vals

    @vo.handle_timeout
    @log.log_this()
    def query_analog_output_values(self):
        """Returns a dictionary of values.'

        Dictionary entries:
            'seed_temp', 'pump1_temp', 'pump2_temp', 'pump3_temp'  ## Celsius
            'seed_amps', 'pump1_amps', 'pump2_amps', 'pump3_amps'  ## Amps
            'seed_bias_volts'                                      ## Volts
            """
        analog_raw = self.res.query('AO?')
        val_list = []
        ao_vals = {}
        start = np.arange(0, 8*5, 5)
        for i in start:
            val_list.append(float(analog_raw[start[i]:(start[i]+4)]))
        #Seed and 3 pump TEC temperatures in Celsius
        _dict_assign(ao_vals, ('seed_temp', 'pump1_temp', 'pump2_temp',
                               'pump3_temp'),
                     _compute_tec_temp(val_list[0:3]))
        #Seed current in amps
        ao_vals['seed_amps'] = val_list[4]/1638.
        ao_vals[4] = val_list[4]/1638.
        #Pump currents in amps
        _dict_assign(ao_vals, ('pump1_amps', 'pump2_amps', 'pump3_amps'),
                     _compute_output_current(val_list[5:7],
                                             self.pccw_list[0:2],
                                             np.arange(3)))
        #Seed bias voltage in volts
        ao_vals['seed_bias_volts'] = val_list[8]/1638.
        return ao_vals

    @vo.handle_timeout
    @log.log_this()
    def query_trigger_timeout(self):
        """Returns the minimum trigger value in Hz"""
        trig_raw = self.res.query('TRTO?')
        trig_val = float(trig_raw[4:8])
        trig_freq = 75000./trig_val
        return trig_freq

    @vo.handle_timeout
    @log.log_this()
    def query_pulse_width(self):
        """Returns pulse width in ns"""
        pw_raw = self.res.query('PWA?')
        pw_val = int(pw_raw[3])
        #          | 0 |  1 |  2 |  3 |  4 |  5 |  6 |  7 |  8 |  9 |
        pw_table = [2.7, 3.4, 3.8, 3.9, 4.6, 4.9, 5.2, 5.7, 6.8, 7.7]
        width = pw_table[pw_val]
        return width

    @vo.handle_timeout
    @log.log_this()
    def query_digital_temp_sensors(self):
        """Returns temperature from two digital sensors in Celsius"""
        raw_temps = self.res.query('TEMP?')
        temp1 = float(raw_temps[4:8])/16.
        temp2 = float(raw_temps[10:14])/16.
        return temp1, temp2

    @vo.handle_timeout
    @log.log_this()
    def query_pulse_rep_rate(self):
        """Returns pulse repetition rate in kHz"""
        raw_prr = self.res.query('PR?')
        prr_val = float(raw_prr[2:6])
        rep_rate = prr_val/75000.+0.5
        return rep_rate

    @vo.handle_timeout
    @log.log_this()
    def query_keep_on(self):
        """Returns True if laser is set to 'Keep ON'"""
        keep_on = int(self.res.query('KP?'))
        return bool(keep_on)

    @vo.handle_timeout
    @log.log_this()
    def query_allowed_components(self):
        """Prints a list of components connected to electronic board"""
        raw_allowed = self.res.query('DC?')
        device_list1 = ['Seed current', 'Pump 1 current', 'Pump 2 current',
                        'Pump 3 current', 'Seed temperature',
                        'Pump 1 temperature', 'Pump 2 temperature',
                        'Pump 3 temperature']
        device_list2 = ['Digital temperature sensor 1',
                        'Digital temperature sensor 2',
                        'Analog temperature sensor 1',
                        'Analog temperature sensor 1',
                        'Voltage test 28V', 'Voltage test 1.8V',
                        'Voltage test 5V', 'Pump 1 photodiode']
        device_list3 = ['Pump 2 photodiode', 'Monitor photodiode 1',
                        'Monitor photodiode 2', 'Trigger', 'Pulse width',
                        'Pulse rate', '', '']
        device_list4 = ['', '', '', 'Seed bias voltage', '', '', '', '']
        device_array = [device_list1, device_list2,
                        device_list3, device_list4]
        allowed = ['allowed!', 'NOT ALLOWED!']
        i = 0
        while i < len(device_array):
            ascii = raw_allowed[2+i]
            bits = _string_to_bits(ascii)
            j = 0
            while j < len(bits):
                if device_array[i][j]:
                    log.log_warn(__name__, 'query_allowed_components',
                                 device_array[i][j] + ' is '
                                 + allowed[int(bits[j])])
                j += 1
            i += 1

#Set Value Methods

    @vo.handle_timeout
    @log.log_this()
    def __set_analog_output_values(self, item_str, val_str):
        """Sets a value, accessed by other set commands"""
        self.res.write('AO%s,%s' % (item_str, val_str))

    @log.log_this()
    def set_tec_temp(self, tec_num, temp):
        """tec_num=0 for seed, ={1,2,3} for corresponding pumps,
        sets temperature in Celsius"""
        item_str = '0%d' % tec_num
        temp_str = _form_temp_command(temp)
        if temp_str is None:
            return
        self.__set_analog_output_values(item_str, temp_str)

    @log.log_this()
    def set_pump_current(self, pump_num, current):
        """
        !!!! Manual gives units of seed current in volts?!?!

        pump_num=0 for seed, ={1,2,3} for corresponding pumps,
        sets current in amps"""
        if current > self.pcl_list[pump_num] or current < 0:
            log.log_warn(__name__, 'set_pump_current',
                         'Pump current to be set is out of bounds!')
            return
        if pump_num == 2 and current != 2:
            log.log_warn(__name__, 'set_pump_current',
                         'Pump 2 must stay at 2 amps!')
            return
        item_str = '0%d' % (pump_num + 3)
        current_str = _form_current_command(pump_num, current, self.pccw_list)
        self.__set_analog_output_values(item_str, current_str)

    @log.log_this()
    def set_seed_bias_voltage(self, voltage):
        """Sets the voltage in volts"""
        item_str = '08'
        volt_val = int(np.floor(voltage*1638.))
        if volt_val > 4095 or volt_val < 0:
            log.log_warn(__name__, 'set_seed_bia_voltage',
                         'Seed bias voltage to be set is out of bounds!')
            return
        volt_str = str(volt_val).zfill(4)
        self.__set_analog_output_values(item_str, volt_str)

    @vo.handle_timeout
    @log.log_this()
    def set_trigger_timeout(self, frequency):
        """Sets the trigger timeout in Hz"""
        trig_val = int(np.floor(frequency/75000.))
        if trig_val < 751 or trig_val > 8190:
            log.log_warn(__name__, 'set_trigger_timeout',
                         'Trigger timeout to be set is out of bounds!')
            return
        trig_str = str(trig_val).zfill(4)
        self.res.write('TRTO%s' % trig_str)

    @vo.handle_timeout
    @log.log_this()
    def set_pulse_width(self, pw_val):
        """Sets the pulse width in ns, use table below for correct pw_val

        pw_val =      | 0 |  1 |  2 |  3 |  4 |  5 |  6 |  7 |  8 |  9 |
        pulse in ns = |2.7| 3.4| 3.8| 3.9| 4.6| 4.9| 5.2| 5.7| 6.8| 7.7|"""
        self.res.write('PWA%d' % pw_val)

    @vo.handle_timeout
    @log.log_this()
    def set_pump_read_constant(self, pump_num, val):
        """Sets the read constant of pump_num={1,2,3}

        val must be an integer between 0 and 4095(?)"""
        val_str = str(val).zfill(4)
        self.res.write('PCCR%d%s' % (pump_num, val_str))

    @vo.handle_timeout
    @log.log_this()
    def set_pump_write_constant(self, pump_num, val):
        """Sets the write constant of pump_num={1,2,3}

        val must be an integer between 0 and 4095(?)
        probably safest to leave these alone
        unless desired current cant be reached"""
        if pump_num == 2:
            log.log_warn(__name__, 'set_pump_write_constants',
                         'Cannot change pump 2 current!')
            return
        val_str = str(val).zfill(4)
        self.res.write('PCCW%d%s' % (pump_num, val_str))
