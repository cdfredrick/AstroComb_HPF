# -*- coding: utf-8 -*-
"""
Created on Mon Jun 12 15:29:26 2017

@author: wjb4
"""
import visa
import pyvisa

class Visa(object):
    """Defines the basic visa operations for all visa controlled devices"""

    def __init__(self, res_name, res_address):
        self.name = res_name
        self.address = res_address

    def open_resource(self):
        """Returns specified resource object."""
        try:
            res_man = visa.ResourceManager()
            resource = res_man.open_resource(self.address)
            print 'Connected'
            return resource

        except (pyvisa.errors.VisaIOError, UnboundLocalError):
            print '%s Cannot Be Connected To!' % self.name
            return None

    def check_connection(self, resource):
        """If resource is not connected initiates resources disconnection commands."""
        connected = self.open_resource()
        if connected is None:
            resource.disconnected()
