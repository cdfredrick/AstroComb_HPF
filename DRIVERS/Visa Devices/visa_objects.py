# -*- coding: utf-8 -*-
"""
Created on Mon Jun 12 15:29:26 2017

@author: Wesley Brand


Defines the super class to which all visa controlled devices should belong

Using this file you should not need to import visa and pyvisa into the drivers for other visa devices

import visa_objects as vo


List of public functions:

0/1 = tf_toggle(var)
method = handle_timeout(method)


List of public methods in class Visa:

__init__(res_name, res_address)
open_resource()
check_connection()
disconnected()
"""

import visa
import pyvisa

def tf_toggle(var):
    """Returns 0 or 1 in place of T/F variable."""
    if var is True:
        binary = 1
    elif var is False:
        binary = 0
    return binary

def handle_timeout(method):
    """To be used as a function decorator that does timeout error coding"""
    def attempt_method(self, *args, **kwargs):
        try:
            method(self, *args, **kwargs)
        except pyvisa.errors.VisaIOError:
            super(type(self), self).check_connection()
    return attempt_method


class Visa(object):
    """Defines the basic visa operations for all visa controlled devices"""

    def __init__(self, res_name, res_address):
        self.name = res_name
        self.address = res_address
        self.connected = []

    def open_resource(self):
        """Returns specified resource object."""
        try:
            res_man = visa.ResourceManager()
            resource = res_man.open_resource(self.address)
            self.connected = True
            print 'Connected'
            return resource

        except (pyvisa.errors.VisaIOError, UnboundLocalError):
            print '%s Cannot Be Connected To!' % self.name
            return None

    def check_connection(self):
        """If resource is not connected initiates resources disconnection commands."""
        connected = self.open_resource()
        if connected is None:
            self.disconnected()

    def disconnected(self):
        """Announces connection error."""
        print '%s has timed out!' % self.name
        self.connected = False
