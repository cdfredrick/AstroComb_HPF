# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 13:55:39 2018

@author: National Institute
"""
#
#from Drivers.Kinesis.KCube_mp import KDC101_PRM1Z8
#test = KDC101_PRM1Z8('27251608')
#
#
#with Pool(processes=1) as pool:
#    result = pool.apply(test.position)
#    print(result.get())

# %% Modules
import ctypes as c
from functools import wraps
import time
import datetime

warning_timer = {}
warning_interval = 100 # seconds

from multiprocessing import Pool

import os
kinesis = os.path.dirname(__file__)

from Drivers.Logging import EventLog as log


# %% Load DLLs
manager = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.DeviceManager.dll'))
#piezo = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.KCube.Piezo.dll'))

# %% Rotation Stage and DC Motor

class KDC101_PRM1Z8():
    def __init__(self, serialNo):
        self.enc_cnt_per_deg = 1919.64 # encoder count per degree
        self.auto_connect = True
        self.connected = False
        self.serialNo_str = serialNo
    
    def serialNo_c(self):
        return c.create_string_buffer(self.serialNo_str.encode())
    
    def open_comms(self, dc_servo):
        wait_for_init = True
        warning_caught = False
        iteration = 0
        while wait_for_init:
            result = dc_servo.CC_Open(c.byref(self.serialNo_c()))
            if result:
                iteration += 1
                self.close_comms(dc_servo)
            # Lock error
                warn_str = ':\tError connecting to KDC101, code {:}'.format(result)
                if (warn_str in warning_timer):
                    if (time.time() - warning_timer[warn_str]) > warning_interval:
                        warn_str = warn_str + '. Iteration {:}'.format(iteration)
                        print('\t'+str(datetime.datetime.now())+warn_str)
                        warning_caught = True
                else:
                    warning_timer[warn_str] = time.time()
            else:
                wait_for_init = False
        wait_for_connection = True
        while wait_for_connection:
            connected = dc_servo.CC_CheckConnection(c.byref(self.serialNo_c()))
            if (connected == 1):
                wait_for_connection = False
                self.connected = True
            elif (connected == 0):
                raise Exception('Error connecting to device, not listed by the ftdi controller'.format(result))
            else:
                time.sleep(0.01)
        if warning_caught:
            log_str = ':\tSuccessfully connected'
            print('\t'+str(datetime.datetime.now())+log_str)
            
    def close_comms(self, dc_servo):
        dc_servo.CC_Close(c.byref(self.serialNo_c()))
        self.connected = False
    
    def position(self, set_position=None):
        with Pool(processes=1) as pool:
            result = pool.apply(self._position, [set_position])
            return result
    
    def _position(self, set_position=None):
        # Load DLLs
        manager = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.DeviceManager.dll'))
        dc_servo = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.KCube.DCServo.dll'))
        try:
            # Open Comms
            self.open_comms(dc_servo)
            # Communicate
            if (set_position == None):
                result = dc_servo.CC_RequestPosition(c.byref(self.serialNo_c()))
                if result:
                    raise Exception('Error requesting device position, code {:}'.format(result))
                device_units = dc_servo.CC_GetPosition(c.byref(self.serialNo_c()))
                return (device_units/self.enc_cnt_per_deg)
            else:
                device_units = int(round(set_position*self.enc_cnt_per_deg))
                result = dc_servo.CC_MoveToPosition(c.byref(self.serialNo_c()),c.c_int(device_units))
                if result:
                    raise Exception('Error setting device position, code {:}'.format(result))
        finally:
            self.close_comms(dc_servo)
            
    
    def home(self, start_homing=None):
        with Pool(processes=1) as pool:
            result = pool.apply(self._home, [start_homing])
            return result
    
    def _home(self, start_homing=None):
        # Load DLLs
        manager = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.DeviceManager.dll'))
        dc_servo = c.CDLL(os.path.join(kinesis,'Thorlabs.MotionControl.KCube.DCServo.dll'))
        try:
            # Open Comms
            self.open_comms(dc_servo)
            # Communicate
            if (start_homing == None):
                # Setup "GetStatusBits"
                CC_GetStatusBits = dc_servo.CC_GetStatusBits
                CC_GetStatusBits.restype = c.c_uint
                result = dc_servo.CC_RequestStatusBits(c.byref(self.serialNo_c()))
                if result:
                    raise Exception('Error requesting status bits, code {:}'.format(result))
                else:
                    status = CC_GetStatusBits(c.byref(self.serialNo_c()))
                    homing = bool(status & (1 << 9)) # Homing status bit
                    homed = bool(status & (1 << 10)) # Homed status bit
                    return {'homed':homed, 'homing':homing}
            elif (start_homing == True):
                result = dc_servo.CC_Home(c.byref(self.serialNo_c()))
                if result:
                    raise Exception('Error homing the device, code {:}'.format(result))
        finally:
            self.close_comms(dc_servo)


