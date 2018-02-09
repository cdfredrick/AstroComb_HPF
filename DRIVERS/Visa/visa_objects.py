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


#Python imports
from functools import wraps
import time

#3rd party imports
import visa
from pyvisa import errors as visa_errors # for error handling

#Astrocomb imports
from DRIVERS.Logging import eventlog as log
from DRIVERS.Logging import ac_excepts


#Constants
SB_ONE = visa.constants.StopBits.one


#Public functions
def tf_toggle(var):
    """Returns 0 or 1 in place of T/F variable."""
    if var == True:
        binary = 1
    elif var == False:
        binary = 0
    return binary

def handle_visa_error(method):
    """
    To be used as a function decorator that does general visa error handling
    Returns None if an error occurs, driver code should handle that possibility.
    """
    @wraps(method)
    def attempt_method(self, *args, **kwargs):
        """Wrapped function"""
        try:
            result = method(self, *args, **kwargs)
            return result
        except (visa_errors.VisaIOError,visa_errors.InvalidSession) as visa_err:
            result = None
            log.log_error(method.__module__, method.__name__, visa_err)
            self.check_resource()
            if self.opened is True:
                self.close_resource()
            return result
    return attempt_method

class ResourceManager(visa.ResourceManager):
    def get_resource(self, resource_name, resource_pyclass=None, **kwargs):
        """Return an instrument without opening a session to the resource.
        
        This is a direct port of open_resource from the pyvisa code with only 
            slight adjustments.
        
        :param resource_name: name or alias of the resource to open.
        :param resource_pyclass: resource python class to use to instantiate the Resource.
                                 Defaults to None: select based on the resource name.
        :param kwargs: keyword arguments to be used to change instrument attributes
                       after construction.

        :rtype: :class:`visa.resources.Resource`
        """
        if resource_pyclass is None:
            info = self.resource_info(resource_name, extended=True)
            try:
                resource_pyclass = self._resource_classes[(info.interface_type, info.resource_class)]
            except KeyError:
                resource_pyclass = self._resource_classes[(visa.constants.InterfaceType.unknown, '')]
                visa.logger.warning('There is no class defined for %r. Using Resource', (info.interface_type, info.resource_class))
        res = resource_pyclass(self, resource_name)
        res.close()
        return res

class Visa(object):
    """
    Defines the basic visa operations for all visa controlled devices. A resource
    manager is automatically generated if one is not provided.
    """
    @log.log_this()
    def __init__(self, res_address, res_manager=None):
        self.address = res_address
        if res_manager is None:
            self.res_man = ResourceManager()
        else:
            self.res_man = res_manager
        self.check_resource()
        self.opened = False
        self.initialize_resource()

    @log.log_this()
    def check_resource(self):
        """
        Checks if the resource is valid.
        """
        res_list = self.res_man.list_resources()
        if self.address in res_list:
            self.valid_resource = True
        else:
            self.valid_resource = False
            raise ac_excepts.VisaConnectionError('No device at {:}'.format(self.address), self.check_resource)

    @log.log_this()
    def clear_resource(self):
        '''
        Clears the device's controller
        '''
        self.resource.clear()

    @log.log_this()
    @handle_visa_error
    def flush_resource(self):
        '''
        Flushes the device's buffer
        '''
        self.open_resource()
        self.resource.flush(visa.constants.VI_READ_BUF)
        self.close_resource()

    @log.log_this()
    def close_resource(self):
        '''
        Closes the resource session. All data structures that had been allocated
            for the specified instrument are freed.
        '''
        self.resource.close()
        self.opened = False
        
    @log.log_this()
    def initialize_resource(self):
        '''
        Initializes a resource object
        '''
        try:
            self.resource = self.res_man.get_resource(self.address)
        except (visa_errors.VisaIOError, UnboundLocalError) as err:
            self.resource = None
            log.log_error('visa_objects', 'initialize_resource', err)
    
    @log.log_this()
    def open_resource(self, timeout=5):
        """
        Opens the resource to accept commands.
        """
        start_time = time.time()
        while (not self.opened) and (time.time()-start_time < timeout):
            try:
                self.resource.open()
            except visa.VisaIOError as visa_err:
                if (visa_err.error_code == visa.constants.VI_ERROR_RSRC_BUSY):
                    # Keep trying if the resource is busy
                    pass
                else:
                    log.log_error('visa_objects', 'open_resource', visa_err)
                    raise visa_err
            else:
                self.opened = True
        if not self.opened:
            raise visa.VisaIOError(visa.constants.VI_ERROR_RSRC_BUSY)
    
    @log.log_this()
    @handle_visa_error
    def query(self, message, delay=None):
        self.open_resource()
        result = self.resource.query(message, delay=delay)
        self.close_resource()
        return result

    @log.log_this()
    @handle_visa_error
    def read(self, termination=None, encoding=None):
        self.open_resource()
        result = self.resource.read(termination=termination, encoding=encoding)
        self.close_resource()
        return result
    
    @log.log_this()
    @handle_visa_error
    def write(self, message, termination=None, encoding=None):
        self.open_resource()
        self.resource.write(message, termination=termination, encoding=encoding)
        self.close_resource()
