# -*- coding: utf-8 -*-
"""
Created on Mon Jun 05 13:54:03 2017

@author: Wesley Brand

List of public methods in class Cybel:

General:
    __init__(res_address)
    disconnected()
    reboot()
    eeprom_save()

Enable Components:
    enable_pump(pump_number, pump_on)
    enable_tec(tec_number, tec_on)

Queries:
    sn_str, fw_str = query_serial_and_firmware()
    str = query_cpld_firmware()
    TF = query_pump_status(pump_number)
    TF0, TF1, TF2, TF3 = query_temp_error()
    TF0, TF1  = query_trigger_n_laser_status()
    TF = query_tec_status(tec_number)
    query_pump_read_constants() #writes values to Cybel.pccr_list
    query_pump_write_constants() #writes values to Cybel.pccw_list
    query_pump_current_limits() #writes values to Cybel.pcl_list
    float_list_length_17 = query_analog_input_values()
    float_list_length_8 = query_analog_output_values()
    float = query_trigger_timeout() #Hz
    float = query_pulse_width() #ns
    float1, float2 = query_digital_temp_sensors(self) #Celsius
    float = query_pulse_rep_rate() #kHz
    TF = query_keep_on()
    query_allowed_components()

Set Values:
    set_analog_output_values(item_str, val_str)
    set_tec_temp(tec_number, temp) #celsius
    set_pump_current(pump_number, current) #amps
    set_seed_bias_voltage(voltage) #volts
    set_trigger_timeout(frequency) #Hz
    set_pulse_width(pw_val) #see table
    set_pump_read_constant(pump_number, val)
    set_pump_write_constant(pump_number, val)

"""

import time
import numpy as np
import visa
import pyvisa

CYBEL_ADDRESS = '' #ADD ME!!!!

def open_resource(res_address):
    """Returns specified resource object."""
    try:
        res_man = visa.ResourceManager()
        resource = res_man.open_resource(res_address)
        print 'Connected'
        return resource

    except (pyvisa.errors.VisaIOError, UnboundLocalError):
        print 'Device Cannot Be Connected To!'
        return None

def check_connection(resource, res_address):
    """If resource is not connected initiates resources disconnection commands."""
    connected = open_resource(res_address)
    if connected is None:
        resource.disconnected()

def tf_toggle(var):
    """Returns 0 or 1 in place of T/F variable."""
    if var is True:
        binary = 1
    elif var is False:
        binary = 0
    return binary

def compute_tec_temp(raw_val):
    """Returns temperature from raw device reading."""
    return 40.*(raw_val/1638.-1.25)+25.

def compute_input_current(raw_val, pccr):
    """Returns pump input current from raw device reading."""
    return raw_val*pccr/4095000.

def compute_output_current(raw_val, pccw, pump_num):
    """Returns pump output current from raw device reading."""
    constants_list = [1470, 235, 147]
    return raw_val*pccw/4095000./constants_list[pump_num-1]

def compute_pd_power(raw_val, pd_num):
    """Returns photodiode power from raw device reading."""
    constants_list = [0.202, 3.912]
    return raw_val/1638.*constants_list[pd_num-1]

def compute_analog_temp(raw_val):
    """Returns sensor temperature from raw device reading."""
    return 100.*(raw_val/1638. - 0.5)

def form_temp_command(temp):
    """Makes set temperature into machine-readable format"""
    temp_val = int(np.floor(1638.*((temp-25.)/40.+1.25)))
    if temp_val > 4095 or temp_val < 0:
        print 'Temperature to be set is out of bounds!'
        return
    temp_str = str(temp_val).zfill(4)
    return temp_str

def form_current_command(resource, pump_number, current):
    """Makes set pump current into machine-readable format"""
    if pump_number == 0:
        current_val = int(np.floor(current*1638.))
    else:
        constants_list = [1470., 235., 147.]
        current_val = current*constants_list[pump_number-1]/resource.pccw_list[pump_number-1]*1638.
        current_val = int(np.floor(current_val))
        current_str = str(current_val).zfill(4)
        return current_str

def string_to_bits(string=''):
    """Converts ascii character into bit string"""
    return [bin(ord(x))[2:].zfill(8) for x in string][0]

class Cybel():
    """Holds cybel amplifier's attributes and function library."""

    #General methods

    def __init__(self, res_address):
        self.res = open_resource(res_address)
        if self.res is None:
            print 'Could not create Cybel instrument!'
            return
        self.res.clear()
        self.res.term_chars = 'CR+LF'
        self.res.timeout = 3
        self.res.baud_rate = 57600
        self.res.data_bits = 8
        self.res.stop_bits = 1
        self.connected = 1
        try:
            self.res.query('SEN') #Disable echo, echo interferes with string reading
        except pyvisa.errors.VisaIOError:
            self.disconnected()
        self.pccr_list = [] #Pump read constants, will have length 3
        self.query_pump_read_constants()
        self.pccw_list = [] #Pump write constants, will have length 3
        self.query_pump_write_constants()
        self.pcl_list = [] #Pump current limits, will have length 4 (includes seed)
        self.query_pump_current_limits()

    def disconnected(self):
        """Announces connection error."""
        print 'Cybel has disconnected!'
        self.connected = 0

    def reboot(self):
        """Reboots electronic board."""
        try:
            self.res.query('RESET')
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def eeprom_save(self):
        """Saves manual-specified values into electronic board."""
        try:
            self.res.query('SAVE')
            time.sleep(3) #Takes a few seconds and can't be interrupted
        except pyvisa.errors.VisaIOError:
            self.disconnected()

#Enable Component Methods

    def enable_pump(self, pump_number, pump_on):
        """Turns pump on (pump_on=True) or off (pump_on=False),
        pump numbers are 1,2, or 3"""
        try:
            self.res.query('P%d%d' % (pump_number, tf_toggle(pump_on)))
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def enable_tec(self, tec_number, tec_on):
        """tec_number=0 for seed, ={1,2,3} for corresponding pumps, turns on if tec_on=True."""
        try:
            if tec_number == 0:
                tec_number = 'S'
            self.res.query('TEC%s%d?' % (tec_number, tf_toggle(tec_on)))
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def enable_keep_on(self, keep_on):
        """Enables keeping laser on when electronic board connection ends if True"""
        try:
            self.res.query('KP%d' % tf_toggle(keep_on))
        except pyvisa.errors.VisaIOError:
            self.disconnected()

#Query Methods

    def query_serial_and_firmware(self):
        """Returns 8 character SN and 4 character microcontroller firmware #."""
        try:
            raw_sn_and_fw = self.res.query('CO')
            serial = raw_sn_and_fw[:8]
            firmware = raw_sn_and_fw[:10]
            return serial, firmware
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_cpld_firmware(self):
        """Returns 4 character CPLD firmware version."""
        try:
            raw_cpld = self.res.query('CPLD?')
            return raw_cpld[4:8]
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pump_status(self, pump_number):
        """Returns True if pump is on and False if pump is off,
        pump_numbers are 1,2, or 3"""
        try:
            pump_status = self.res.query('P%d?' % pump_number)
            if pump_status[2] == '0':
                print 'Pump %d is off!' % pump_number
                return False
            return True
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_temp_error(self):
        """Returns a value for each TEC, True if within error, False if not"""
        try:
            temp_error = self.res.query('FB?')
            seed_temp = pump1_temp = pump2_temp = pump3_temp = True
            if temp_error[2] == '0':
                print 'Seed temperature outsde error limit!'
                seed_temp = False
            if temp_error[3] == '0':
                print 'Pump 1 temperature outsde error limit!'
                pump1_temp = False
            if temp_error[4] == '0':
                print 'Pump 2 temperature outsde error limit!'
                pump2_temp = False
            if temp_error[5] == '0':
                print 'Pump 3 temperature outsde error limit!'
                pump3_temp = False
            return seed_temp, pump1_temp, pump2_temp, pump3_temp
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def  query_trigger_n_laser_status(self):
        """Returns True's if trigger is correct and laser is emitting"""
        try:
            tl_status = self.res.query('TS?')
            trigger_match = laser_on = True
            if tl_status[2] == '0':
                print 'External trigger does not match requirement!'
                trigger_match = False
            if tl_status[3] == '0':
                print 'Laser not emitting!'
                laser_on = False
            return trigger_match, laser_on
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_tec_status(self, tec_number):
        """tec_number=0 for seed, ={1,2,3} for corresponding pumps, returns True if tec is on"""
        try:
            if tec_number == 0:
                tec_number = 'S'
            tec_status = self.res.query('TEC%s?' % tec_number)
            if tec_status[4] == '0':
                print '%s TEC is off!' % tec_number
                return False
            return True
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pump_read_constants(self):
        """Saves pump read multiplying factors for computing pump currents in Cybel object"""
        try:
            raw_constants = self.res.query('PCCR?')
            start = np.arange(0, 2*5, 5)
            new_pccr_list = []
            for i in start:
                new_pccr_list.append(float(raw_constants[start[i]:(start[i]+4)]))
            self.pccr_list = new_pccr_list
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pump_write_constants(self):
        """Saves pump write multiplying factors for computing pump currents in Cybel object"""
        try:
            raw_constants = self.res.query('PCCW?')
            start = np.arange(0, 2*5, 5)
            new_pccw_list = []
            for i in start:
                new_pccw_list.append(float(raw_constants[start[i]:(start[i]+4)]))
            self.pccw_list = new_pccw_list
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pump_current_limits(self):
        """Saves pump current limits in Cybel object"""
        try:
            raw_limits = self.res.query('AOL?')
            start = np.arange(0, 2*5, 5)
            new_pcl_list = [2.5]
            for i in start:
                raw_val = float(raw_limits[start[i]:(start[i]+4)])
                pcl = compute_output_current(raw_val, self.pccw_list[i], i)
                new_pcl_list.append(pcl)
            self.pcl_list = new_pcl_list
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_analog_input_values(self):
        """Returns a length 17 list of manual-specifed values."""
        try:
            analog_raw = self.res.query('AI?')
            val_list = []
            ai_vals = np.zeros(17)
            start = np.arange(0, 16*5, 5)
            for i in start:
                val_list.append(float(analog_raw[start[i]:(start[i]+4)]))
            #Seed and 3 pump TEC temperatures in Celsius
            ai_vals[0:3] = compute_tec_temp(val_list[0:3])
            #Pump currents in amps
            ai_vals[4:6] = compute_input_current(val_list[4:6], self.pccr_list[0:2])
            #Pumps 1 and 2 photodiode powers in watts
            ai_vals[7] = compute_pd_power(val_list[7], 1)
            ai_vals[8] = compute_pd_power(val_list[8], 1)
            #Seed bias voltage
            ai_vals[9] = val_list[9]/1638.
            #Analog temperature sensors in celsius
            ai_vals[10:11] = compute_analog_temp(val_list[10:11])
            #Voltage tests: 5V, 1.8V, and 28V in volts
            #And Monitor photodiodes 1 and 2 in volts
            ai_vals[12:16] = val_list[12:16]/1638.
            return ai_vals
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_analog_output_values(self):
        """Returns a length 9 list of manual-specifed values."""
        try:
            analog_raw = self.res.query('AO?')
            val_list = []
            ao_vals = np.zeros(9)
            start = np.arange(0, 8*5, 5)
            for i in start:
                val_list.append(float(analog_raw[start[i]:(start[i]+4)]))
            #Seed and 3 pump TEC temperatures in Celsius
            ao_vals[0:3] = compute_tec_temp(val_list[0:3])
            #Seed current in amps
            ao_vals[4] = val_list[4]/1638.
            #Pump currents in amps
            ao_vals[5:7] = compute_output_current(val_list[4:6], self.pccw_list[0:2], np.arange(3))
            #Seed bias voltage in volts
            ao_vals[8] = val_list[8]/1638.
            return ao_vals
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_trigger_timeout(self):
        """Returns the minimum trigger value in Hz"""
        try:
            trig_raw = self.res.query('TRTO?')
            trig_val = float(trig_raw[4:8])
            trig_freq = 75000./trig_val
        except pyvisa.errors.VisaIOError:
            self.disconnected()
        return trig_freq

    def query_pulse_width(self):
        """Returns pulse width in ns"""
        try:
            pw_raw = self.res.query('PWA?')
            pw_val = int(pw_raw[3])
            #          | 0 |  1 |  2 |  3 |  4 |  5 |  6 |  7 |  8 |  9 |
            pw_table = [2.7, 3.4, 3.8, 3.9, 4.6, 4.9, 5.2, 5.7, 6.8, 7.7]
            width = pw_table[pw_val]
            return width
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_digital_temp_sensors(self):
        """Returns temperature from two digital sensors in Celsius"""
        try:
            raw_temps = self.res.query('TEMP?')
            temp1 = float(raw_temps[4:8])/16.
            temp2 = float(raw_temps[10:14])/16.
            return temp1, temp2
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pulse_rep_rate(self):
        """Returns pulse repetition rate in kHz"""
        try:
            raw_prr = self.res.query('PR?')
            prr_val = float(raw_prr[2:6])
            rep_rate = prr_val/75000.+0.5
            return rep_rate
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_keep_on(self):
        """Returns True if laser is set to 'Keep ON' when connection with electronic board ends"""
        try:
            keep_on = self.res.query('KP?')
            if keep_on[2] == '1':
                return True
            return False
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_allowed_components(self):
        """Prints a list of components that are connected to electronic board"""
        try:
            raw_allowed = self.res.query('DC?')
            device_list1 = ['Seed current', 'Pump 1 current', 'Pump 2 current',
                            'Pump 3 current', 'Seed temperature', 'Pump 1 temperature',
                            'Pump 2 temperature', 'Pump 3 temperature']
            device_list2 = ['Digital temperature sensor 1', 'Digital temperature sensor 2',
                            'Analog temperature sensor 1', 'Analog temperature sensor 1',
                            'Voltage test 28V', 'Voltage test 1.8V', 'Voltage test 5V',
                            'Pump 1 photodiode']
            device_list3 = ['Pump 2 photodiode', 'Monitor photodiode 1',
                            'Monitor photodiode 2', 'Trigger', 'Pulse width',
                            'Pulse rate', '', '']
            device_list4 = ['', '', '', 'Seed bias voltage', '', '', '', '']
            device_array = [device_list1, device_list2, device_list3, device_list4]
            allowed = ['allowed!', 'NOT ALLOWED!']
            i = 0
            while i < len(device_array):
                ascii = raw_allowed[2+i]
                bits = string_to_bits(ascii)
                j = 0
                while j < len(bits):
                    if device_array[i][j]:
                        print device_array[i][j] + ' is ' + allowed[int(bits[j])]
                    j += 1
                i += 1
        except pyvisa.errors.VisaIOError:
            self.disconnected()

#Set Value Methods

    def set_analog_output_values(self, item_str, val_str):
        """Sets a value, accessed by other set commands"""
        try:
            self.res.query('AO%s,%s' % (item_str, val_str))
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def set_tec_temp(self, tec_number, temp):
        """tec_number=0 for seed, ={1,2,3} for corresponding pumps,
        sets temperature in Celsius"""
        item_str = '0%d' % tec_number
        temp_str = form_temp_command(temp)
        if temp_str is None:
            return
        self.set_analog_output_values(item_str, temp_str)

    def set_pump_current(self, pump_number, current):
        """
        !!!! Manual gives units of seed current in volts?!?!

        pump_number=0 for seed, ={1,2,3} for corresponding pumps,
        sets current in amps"""
        if current > self.pcl_list[pump_number] or current < 0:
            print 'Pump current to be set is out of bounds!'
            return
        if pump_number == 2 and current != 2:
            print 'Pump 2 must stay at 2 amps!'
            return
        item_str = '0%d' % (pump_number + 3)
        current_str = form_current_command(self, pump_number, current)
        self.set_analog_output_values(item_str, current_str)

    def set_seed_bias_voltage(self, voltage):
        """Sets the voltage in volts"""
        item_str = '08'
        volt_val = int(np.floor(voltage*1638.))
        if volt_val > 4095 or volt_val < 0:
            print 'Seed bias voltage to be set is out of bounds!'
            return
        volt_str = str(volt_val).zfill(4)
        self.set_analog_output_values(item_str, volt_str)

    def set_trigger_timeout(self, frequency):
        """Sets the trigger timeout in Hz"""
        trig_val = int(np.floor(frequency/75000.))
        if trig_val < 751 or trig_val > 8190:
            print 'Trigger timeout to be set is out of bounds!'
            return
        trig_str = str(trig_val).zfill(4)
        try:
            self.res.query('TRTO%s' % trig_str)
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def set_pulse_width(self, pw_val):
        """Sets the pulse width in ns, use table below for correct pw_val

        pw_val =      | 0 |  1 |  2 |  3 |  4 |  5 |  6 |  7 |  8 |  9 |
        pulse in ns = |2.7| 3.4| 3.8| 3.9| 4.6| 4.9| 5.2| 5.7| 6.8| 7.7|"""
        try:
            self.res.query('PWA%d' % pw_val)
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def set_pump_read_constant(self, pump_number, val):
        """Sets the read constant of pump_number={1,2,3}

        val must be an integer between 0 and 4095(?)"""
        try:
            val_str = str(val).zfill(4)
            self.res.query('PCCR%d%s' % (pump_number, val_str))
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def set_pump_write_constant(self, pump_number, val):
        """Sets the write constant of pump_number={1,2,3}

        val must be an integer between 0 and 4095(?)
        probably safest to leave these alone unless desired current cant be reached"""
        try:
            if pump_number == 2:
                print 'Cannot change pump 2 current!'
                return
            val_str = str(val).zfill(4)
            self.res.query('PCCW%d%s' % (pump_number, val_str))
        except pyvisa.errors.VisaIOError:
            self.disconnected()
