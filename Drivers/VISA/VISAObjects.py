# -*- coding: utf-8 -*-
"""
Created on Mon Jun 12 15:29:26 2017

@author: Wesley Brand

Module: VisaObjects
    import VisaObjects as vo

Defines the super class to which all visa controlled devices should belong

Using this file you should not need to import visa
and pyvisa into the drivers for other visa devices

List of public functions:

0/1 = tf_to_10(var)
method = handle_timeout(method)


List of public methods in class VISA:

__init__(res_name, res_address)
open_resource()
check_connection()
disconnected()
"""

# %% Modules
#Python imports
from functools import wraps
import time
import sys

#3rd party imports
import visa
from pyvisa import errors as visa_errors # for error handling

#Astrocomb imports
from Drivers.Logging import EventLog as log
from Drivers.Logging import ACExceptions


# %% Constants
SB_ONE = visa.constants.StopBits.one


# %% Public functions
def tf_to_10(var):
    """Returns 0 or 1 in place of T/F variable."""
    if var == True:
        binary = 1
    elif var == False:
        binary = 0
    return binary


# %% Private functions
def _handle_visa_error(func):
    """A function decorator that closes the visa resource upon untamed errors."""
    @wraps(func)
    def handle_visa_error(self, *args, **kwargs):
        """Wrapped function"""
        try:
            result = func(self, *args, **kwargs)
            return result
        except:
            pass # try again
        try:
            result = func(self, *args, **kwargs)
            return result
        except:
            error = sys.exc_info()
#            try:
#                self.resource.open()
#                self.resource.clear()
#            except:
#                pass
#            try:
#                self.close_resource()
#            except:
#                pass
            raise error[1].with_traceback(error[2])
    return handle_visa_error

@log.log_this()
def _auto_connect(func):
    """A function decorator that handles automatic connections."""
    @wraps(func)
    def auto_connect(self, *args, **kwargs):
        """Wrapped function"""
        if (self.auto_connect and not(self.opened)):
            try:
                self.open_resource()
                result = func(self, *args, **kwargs)
                return result
            finally:
                self.close_resource()
        else:
            result = func(self, *args, **kwargs)
            return result
    return auto_connect


# %% Resource Manager
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
#        res.close()
        return res


# %% VISA
class VISA(object):
    """
    Defines the basic visa operations for all visa controlled devices. A resource
    manager is automatically generated if one is not provided.
    """
    @log.log_this()
    def __init__(self, res_address, res_manager=None, timeout=5.0):
        self.timeout = timeout
        self.address = res_address
        if res_manager is None:
            self.res_man = ResourceManager()
        else:
            self.res_man = res_manager
        self.initialize_resource()
        self.opened = False
        self.auto_connect = True
    
    @log.log_this()
    def initialize_resource(self):
        '''
        Initializes a resource object
        '''
        try:
            self.resource = self.res_man.get_resource(self.address)
        except (visa_errors.VisaIOError, UnboundLocalError) as err:
            self.resource = None
            log.log_error('VisaObjects', 'initialize_resource', err)
    
    @log.log_this()
    def open_resource(self):
        """
        Opens the resource to accept commands.
        """
        start_time = time.time()
        while (not self.opened):
            try:
                self.resource.open()
            except visa.VisaIOError as visa_err:
                if (visa_err.error_code == visa.constants.VI_ERROR_RSRC_BUSY) and (time.time()-start_time < self.timeout):
                    # Keep trying if the resource is busy
                    pass
                else:
                    raise visa_err
            else:
                self.opened = True
    
    @_auto_connect
    @log.log_this()
    @_handle_visa_error
    def query(self, message, delay=None):
        '''
        Send a query command to the instrument and returns the result
        '''
        result = self.resource.query(message, delay=delay)
        return result
    
    @_auto_connect
    @log.log_this()
    @_handle_visa_error
    def query_list(self, message, converter='f', separator=',', delay=None):
        '''
        Send a query command to the instrument and returns the result
        '''
        result = self.resource.query_ascii_values(message, converter=converter, separator=separator, container=list, delay=delay)
        return result

    @_auto_connect
    @log.log_this()
    @_handle_visa_error
    def read(self, termination=None, encoding=None):
        '''
        Send a read command to the instrument and returns the result
        '''
        result = self.resource.read(termination=termination, encoding=encoding)
        return result
    
    @_auto_connect
    @log.log_this()
    @_handle_visa_error
    def write(self, message, termination=None, encoding=None):
        '''
        Send a write command to the instrument
        '''
        self.resource.write(message, termination=termination, encoding=encoding)
    
    @_auto_connect
    @log.log_this()
    def clear_resource(self):
        '''
        Clears the device's controller, resetting the communication interface.
        '''
        self.resource.clear()
    
    @log.log_this()
    def close_resource(self):
        '''
        Closes the resource session. All data structures that had been allocated
            for the specified instrument are freed.
        '''
        self.resource.close()
        self.opened = False


