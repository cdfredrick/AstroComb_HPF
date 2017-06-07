# -*- coding: utf-8 -*-
"""
Created on Mon Jun 05 13:54:03 2017

@author: rm3531
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
    return (raw_val/1638.-1.25)/0.025+25.

def compute_input_current(raw_val, pccr):
    """Returns pump input current from raw device reading."""
    return raw_val*pccr/4095000.

def compute_pd_power(raw_val, pd_num):
    """Returns photodiode power from raw device reading."""
    if pd_num == 1:
        return raw_val/1638.*0.202
    if pd_num == 2:
        return raw_val/1638.*3.912

def compute_analog_temp(raw_val):
    """Returns sensor temperature from raw device reading."""
    return (raw_val/1638. - 0.5)/0.01


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
        try:
            self.res.query('SEN') #Disable echo
        except pyvisa.errors.VisaIOError:
            print 'Cybel has disconnected!'
            self.connected = 0

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
                print '%s TEC is off!'
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

    def query_pump_read_constants(self):
        """Returns pump read multiplying factors for computing pump currents"""
        try:
            constants = self.res.query('PCCR?')
            start = np.arange(0, 2*5, 5)
            pccr_list = []
            for i in start:
                pccr_list.append(int(constants[start[i]:(start[i]+4)]))
            return pccr_list
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
                val_list.append(int(analog_vals[start[i]:(start[i]+4)]))
            #Seed and 3 pump TEC temperatures
            ai_vals[0:3] = compute_tec_temp(val_list[0:3])
            #Pump currents
            pccr_list = self.query_pump_read_constants()
            ai_vals[4:6] = compute_input_current(val_list[4:6], pccr_list[0:2])
            #Pumps 1 and 2 photodiode powers
            ai_vals[7] = compute_pd_power(val_list[7], 1)
            ai_vals[8] = compute_pd_power(val_list[8], 1)
            #Seed bias voltage
            ai_vals[9] = val_list[9]/1638.
            #Analog temperature sensors
            ai_vals[10:11] = compute_analog_temp(val_list[10:11])
            #Voltage tests: 5V, 1.8V, and 28V. Monitor photodiodes 1 and 2
            ai_vals[12:16] = val_list[12:16]/1638.
            return ai_vals
        except pyvisa.errors.VisaIOError:
            self.disconnected()
