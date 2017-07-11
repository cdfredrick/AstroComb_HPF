# -*- coding: utf-8 -*-
"""
Created on Mon Jun 12 15:29:26 2017

@author: Wesley Brand

Module: visa_objects
    import visa_objects as vo

Defines the super class to which all visa controlled devices should belong

Using this file you should not need to import visa
and pyvisa into the drivers for other visa devices

List of public functions:

0/1 = tf_toggle(var)
method = handle_timeout(method)


List of public methods in class Visa:

__init__(res_name, res_address)
open_resource()
check_connection()
disconnected()
"""

from functools import wraps
import visa
import pyvisa
import eventlog as log

SB_ONE = pyvisa.constants.StopBits.one

def tf_toggle(var):
    """Returns 0 or 1 in place of T/F variable."""
    if var is True:
        binary = 1
    elif var is False:
        binary = 0
    return binary

def handle_timeout(method):
    """To be used as a function decorator that does timeout error coding"""
    @wraps(method)
    def attempt_method(self, *args, **kwargs):
        """Wrapped function"""
        try:
            result = method(self, *args, **kwargs)
            return result
        except pyvisa.errors.VisaIOError as err:
            log.log_error(method.__module__, method.__name__, err)
            super(type(self), self).check_connection()
            if self.connected is True:
                self.close()
                self.res = super(type(self), self).open_resource()
    return attempt_method


class Visa(object):
    """Defines the basic visa operations for all visa controlled devices"""

    @log.log_this()
    def __init__(self, res_name, res_address):
        self.name = res_name
        self.address = res_address
        self.connected = None

    @log.log_this()
    def open_resource(self):
        """Returns specified resource object."""
        try:
            res_man = visa.ResourceManager()
            resource = res_man.open_resource(self.address)
            self.connected = True
            print 'Connected'
            return resource

        except (pyvisa.errors.VisaIOError, UnboundLocalError) as err:
            print '%s Cannot Be Connected To!' % self.name
            log.log_error('visa_objects', 'open_resource', err)
            self.connected = False
            return None

    @log.log_this()
    def check_connection(self):
        """If not connected initiates resources disconnection commands."""
        res_man = visa.ResourceManager()
        res_list = res_man.list_resources()
        self.connected = False
        for raddress in res_list:
            if raddress == self.address:
                self.connected = True
                break
        if self.connected is False:
            self.disconnected()

    @log.log_this(30)
    def disconnected(self):
        """Announces connection error."""
        print '%s has disconnected!' % self.name
        #Do thing that depends on device
