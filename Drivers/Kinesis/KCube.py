# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 13:55:39 2018

@author: National Institute
"""


# %% Modules
import ctypes as c
from functools import wraps
import time

warning_timer = {}
warning_interval = 100 # seconds

import os
kinesis = os.path.dirname(__file__)

from Drivers.Logging import EventLog as log

# %% Private Functions
def _auto_connect(func):
    """A function decorator that handles automatic connections."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """Wrapped function"""
        if (self.auto_connect and not(self.connected)):
            try:
                self.open_comms()
                result = func(self, *args, **kwargs)
                return result
            finally:
                self.close_comms()
        else:
            result = func(self, *args, **kwargs)
            return result
    return wrapper

# %% Load DLLs
manager = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.DeviceManager.dll'))
#piezo = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.KCube.Piezo.dll'))

# %% Rotation Stage and DC Motor

class KDC101_PRM1Z8():
    def __init__(self, serialNo):
        self.dc_servo = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.KCube.DCServo.dll'))
        self.enc_cnt_per_deg = 1919.64 # encoder count per degree
        self.auto_connect = True
        self.connected = False
        self.serialNo = c.create_string_buffer(serialNo.encode())
        # Setup "GetStatusBits"
        self.CC_GetStatusBits = self.dc_servo.CC_GetStatusBits
        self.CC_GetStatusBits.restype = c.c_uint
    
    def open_comms(self):
        mod_name = self.open_comms.__module__
        func_name = self.open_comms.__name__
        wait_for_init = True
        warning_caught = False
        while wait_for_init:
            result = self.dc_servo.CC_Open(c.byref(self.serialNo))
            if result:
                self.close_comms()
            # Lock error
                warn_str = 'Error connecting to device, code {:}'.format(result)
                if (warn_str in warning_timer):
                    if (time.time() - warning_timer[warn_str]) > warning_interval:
                        log.log_warning(mod_name, func_name, warn_str)
                        warning_caught = True
                else:
                    warning_timer[warn_str] = time.time()
                    log.log_warning(mod_name, func_name, warn_str)
                    warning_caught = True
            else:
                wait_for_init = False
        wait_for_connection = True
        while wait_for_connection:
            connected = self.dc_servo.CC_CheckConnection(c.byref(self.serialNo))
            if (connected == 1):
                wait_for_connection = False
                self.connected = True
            elif (connected == 0):
                raise Exception('Error connecting to device, not listed by the ftdi controller'.format(result))
            else:
                time.sleep(0.01)
        if warning_caught:
            log_str = ' Successfully connected'
            log.log_info(mod_name, func_name, log_str)
            
    def close_comms(self):
        self.dc_servo.CC_Close(c.byref(self.serialNo))
        self.connected = False
    
    @_auto_connect
    def position(self, set_position=None):
        if (set_position == None):
            result = self.dc_servo.CC_RequestPosition(c.byref(self.serialNo))
            if result:
                raise Exception('Error requesting device position, code {:}'.format(result))
            device_units = self.dc_servo.CC_GetPosition(c.byref(self.serialNo))
            return (device_units/self.enc_cnt_per_deg)
        else:
            device_units = int(round(set_position*self.enc_cnt_per_deg))
            result = self.dc_servo.CC_MoveToPosition(c.byref(self.serialNo),c.c_int(device_units))
            if result:
                raise Exception('Error setting device position, code {:}'.format(result))
    
    @_auto_connect
    def home(self, start_homing=None):
        if (start_homing == None):
            result = self.dc_servo.CC_RequestStatusBits(c.byref(self.serialNo))
            if result:
                raise Exception('Error requesting status bits, code {:}'.format(result))
            else:
                status = self.CC_GetStatusBits(c.byref(self.serialNo))
                homing = bool(status & (1 << 9)) # Homing status bit
                homed = bool(status & (1 << 10)) # Homed status bit
                return {'homed':homed, 'homing':homing}
        elif (start_homing == True):
            result = self.dc_servo.CC_Home(c.byref(self.serialNo))
            if result:
                raise Exception('Error homing the device, code {:}'.format(result))


