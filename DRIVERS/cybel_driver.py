# -*- coding: utf-8 -*-
"""
Created on Mon Jun 05 13:54:03 2017

@author: Wesley Brand

List of public methods in class Cybel:

Initiate:
    __init__(res_address)
    full_initiate()

General:
    disconnected()
    reboot()
    eeprom_save()

Enable:
    enable_pump(pump_number, pump_on)
    enable_tec(tec_number, tec_on)

Queries:
    serial_str, fw_str = query_serial_and_firmware()
    str = query_cpld_firmware()
    TF = query_pump_status(pump_number)
    TF0, TF1, TF2, TF3 = query_temperature_error()
    TF0, TF1  = query_trigger_n_laser_status()
    TF = query_tec_status(tec_number)
    query_pump_read_constants([force]) #writes values to Cybel.pccr_list
    query_pump_write_constants([force]) #writes values to Cybel.pccw_list
    query_pump_current_limits([force]) #writes values to Cybel.pcl_list
    float_list_length_17 = query_analog_input_values()
    float_list_length_8 = query_analog_output_values()

Set Values:
    set_analog_output_values(item_str, val_str)
    set_tec_temp(tec_number, temp)
    set_pump_current(pump_number, current)
    set_seed_bias_voltage(voltage)

"""

import time
import numpy as np
import visa
import pyvisa

CYBEL_ADDRESS = ''

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
    constants_list = (1470, 235, 147)
    return raw_val*pccw/4095000./constants_list[pump_num-1]

def compute_pd_power(raw_val, pd_num):
    """Returns photodiode power from raw device reading."""
    constants_list = (0.202, 3.912)
    return raw_val/1638.*constants_list[pd_num-1]

def compute_analog_temp(raw_val):
    """Returns sensor temperature from raw device reading."""
    return 100.*(raw_val/1638. - 0.5)

def form_temp_command(temp):
    """Makes set temperature into machine-readable format"""
    temp_val = np.floor(1638.*((temp-25.)/40.+1.25))
    if temp_val > 4095 or temp_val < 0:
        print 'Temperature to be set is out of bounds!'
        return
    temp_str = str(temp_val).zfill(4)
    return temp_str

def form_current_command(resource, pump_number, current):
    """Makes set pump current into machine-readable format"""
    if pump_number == 0:
        current_val = current*1638.
    else:
        constants_list = (1470., 235., 147.)
        current_val = current*constants_list[pump_number-1]/resource.pccw_list[pump_number-1]*1638.
        current_str = str(current_val).zfill(4)
        return current_str

class Cybel():
    """Holds cybel amplifier's attributes and function library."""
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
        self.pccr_list = [] #Pump read constants, will have length 3
        self.pccw_list = [] #Pump write constants, will have length 3
        self.pcl_list = [] #Pump current limits, will have length 4 (includes seed)
        try:
            self.res.query('SEN') #Disable echo, echo interferes with string reading
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def full_initiate(self):
        """Needs more added, should be run immediately after __init__()"""
        self.query_pump_read_constants()
        self.query_pump_write_constants()
        self.query_pump_current_limits()

    def disconnected(self):
        """Announces connection error."""
        print 'Cybel has disconnected!'
        self.connected = 0

    def query_serial_and_firmware(self):
        """Returns 8 character SN and 4 character microcontroller firmware #."""
        try:
            serial_and_firmware = self.res.query('CO')
            serial = serial_and_firmware[:8]
            firmware = serial_and_firmware [:10]
            return serial, firmware
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_cpld_firmware(self):
        """Returns 4 character CPLD firmware version."""
        try:
            cpld = self.res.query('CPLD?')
            return cpld[4:8]
        except pyvisa.errors.VisaIOError:
            self.disconnected()

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

    def enable_pump(self, pump_number, pump_on):
        """Turns pump on (pump_on=True) or off (pump_on=False),
        pump numbers are 1,2, or 3"""
        try:
            self.res.query('P%d%d' % (pump_number, tf_toggle(pump_on)))
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

    def query_temperature_error(self):
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
        """tec_number=0 for seed, ={1,2,3} for corresponding pumps,
        returns True if tec is on"""
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

    def enable_tec(self, tec_number, tec_on):
        """tec_number=0 for seed, ={1,2,3} for corresponding pumps, turns on if tec_on=True."""
        try:
            if tec_number == 0:
                tec_number = 'S'
            self.res.query('TEC%s%d?' % (tec_number, tf_toggle(tec_on)))
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pump_read_constants(self, force=False):
        """Saves pump read multiplying factors for computing pump currents in Cybel object
        Must read from device if function argument True is used"""
        try:
            if self.pccr_list is None or force is True:
                constants = self.res.query('PCCR?')
                start = np.arange(0, 2*5, 5)
                new_pccr_list = []
                for i in start:
                    new_pccr_list.append(int(constants[start[i]:(start[i]+4)]))
                self.pccr_list = new_pccr_list
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pump_write_constants(self, force=False):
        """Saves pump write multiplying factors for computing pump currents in Cybel object
        Must read from device if function argument True is used"""
        try:
            if self.pccw_list is None or force is True:
                constants = self.res.query('PCCW?')
                start = np.arange(0, 2*5, 5)
                new_pccw_list = []
                for i in start:
                    new_pccw_list.append(int(constants[start[i]:(start[i]+4)]))
                self.pccw_list = new_pccw_list
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_pump_current_limits(self, force=False):
        """Saves pump current limits in Cybel object
        Must read from device if function argument True is used"""
        try:
            if self.pcl_list is None or force is True:
                raw_limits = self.res.query('AOL?')
                start = np.arange(0, 2*5, 5)
                new_pcl_list = [2.5]
                for i in start:
                    raw_val = int(raw_limits[start[i]:(start[i]+4)])
                    pcl = compute_output_current(raw_val, self.pccw_list[i], i)
                    new_pcl_list.append(pcl)
                self.pcl_list = new_pcl_list
        except pyvisa.errors.VisaIOError:
            self.disconnected()

    def query_analog_input_values(self):
        """Returns a length 17 list of manual-specifed values."""
        try:
            analog_vals = self.res.query('AI?')
            val_list = []
            ai_vals = np.zeros(17)
            start = np.arange(0, 16*5, 5)
            for i in start:
                val_list.append(float(analog_vals[start[i]:(start[i]+4)]))
            #Seed and 3 pump TEC temperatures in Celsius
            ai_vals[0:3] = compute_tec_temp(val_list[0:3])
            #Pump currents in amps
            self.query_pump_read_constants()
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
            analog_vals = self.res.query('AO?')
            val_list = []
            ao_vals = np.zeros(9)
            start = np.arange(0, 8*5, 5)
            for i in start:
                val_list.append(float(analog_vals[start[i]:(start[i]+4)]))
            #Seed and 3 pump TEC temperatures in Celsius
            ao_vals[0:3] = compute_tec_temp(val_list[0:3])
            #Seed current in amps
            ao_vals[4] = val_list[4]/1638.
            #Pump currents in amps
            self.query_pump_write_constants()
            ao_vals[5:7] = compute_output_current(val_list[4:6], self.pccw_list[0:2], np.arange(3))
            #Seed bias voltage in volts
            ao_vals[8] = val_list[8]/1638.
            return ao_vals
        except pyvisa.errors.VisaIOError:
            self.disconnected()

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
        self.query_pump_current_limits()
        if current > self.pcl_list[pump_number] or current < 0:
            print 'Pump current to be set is out of bounds!'
            return
        item_str = '0%d' % (pump_number + 3)
        current_str = form_current_command(self, pump_number, current)
        self.set_analog_output_values(item_str, current_str)

    def set_seed_bias_voltage(self, voltage):
        """Sets the voltage in volts"""
        item_str = '08'
        volt_val = voltage*1638.
        if volt_val > 4095 or volt_val < 0:
            print 'Seed bias voltage to be set is out of bounds!'
            return
        volt_str = str(volt_val).zfill(4)
        self.set_analog_output_values(item_str, volt_str)
