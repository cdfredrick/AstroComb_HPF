# -*- coding: utf-8 -*-
"""
Created on Mon Apr 30 16:26:02 2018

@author: Connor
"""


# %% Import Modules ===========================================================

import numpy as np
import time
import datetime
import logging
import threading

import os
import sys
sys.path.append(os.getcwd())

from Drivers.Logging import EventLog as log

from Drivers.StateMachine import ThreadFactory, Machine

from Drivers.Thorlabs.APT import KDC101_PRM1Z8, KPZ101, TNA001

# %% Helper Functions =========================================================

'''The following are helper functions that increase the readablity of code in
    this script. These functions are defined by the user and should not
    directly appear in the main loop of the state machine.'''

# Update a 1D circular buffer -------------------------------------------------
@log.log_this()
def update_buffer(buffer, new_data, length):
    length = int(abs(length))
    buffer = np.append(buffer, new_data)
    if buffer.size > length:
        buffer = buffer[-length:]
    return buffer

# Periodic Timer --------------------------------------------------------------
@log.log_this()
def get_lap(time_interval):
    return int(time.time() // time_interval)


# %% Initialization ===========================================================
sm = Machine()


# %% Databases and Settings ===================================================

#--- Communications queue -----------------------------------------------------
COMMS = 'broadening_stage'
sm.init_comms(COMMS)

#--- Internal database names --------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function
'''
STATE_DBs = [
    'broadening_stage/state_2nd_stage']
DEVICE_DBs =[
    'broadening_stage/device_rotation_mount',
    'broadening_stage/device_piezo_x_in',
    'broadening_stage/device_piezo_y_in',
    'broadening_stage/device_piezo_z_in',
    'broadening_stage/device_piezo_x_out',
    'broadening_stage/device_piezo_y_out',
    'broadening_stage/device_piezo_z_out',
    'broadening_stage/device_nanotrack_in',
    'broadening_stage/device_nanotrack_out']
MONITOR_DBs = [
    'broadening_stage/piezo_x_in_HV_output',
    'broadening_stage/piezo_y_in_HV_output',
    'broadening_stage/piezo_z_in_HV_output',
    'broadening_stage/piezo_x_out_HV_output',
    'broadening_stage/piezo_y_out_HV_output',
    'broadening_stage/piezo_z_out_HV_output',
    'broadening_stage/nanotrack_in_position',
    'broadening_stage/nanotrack_in_TIA',
    'broadening_stage/nanotrack_out_position',
    'broadening_stage/nanotrack_out_TIA']
LOG_DB = 'broadening_stage'
CONTROL_DB = 'broadening_stage/control'

MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]

sm.init_master_DB_names(STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB)

#--- External database names --------------------------------------------------
'''This is a list of all databases external to this control script that are
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = []
READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs
sm.init_read_DB_names(R_STATE_DBs, R_DEVICE_DBs, R_MONITOR_DBs)

#--- Default settings ---------------------------------------------------------
'''A template for all settings used in this script. Upon initialization
these settings are checked against those saved in the database, and
populated if found empty. Each state and device database should be represented.
'''
STATE_SETTINGS = {
        'broadening_stage/state_2nd_stage':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'lock',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()}}
DEVICE_SETTINGS = {
        'broadening_stage/device_rotation_mount':{
                'driver':KDC101_PRM1Z8,
                'queue':'27251608',
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':27251608}],
                'home':None, 'position':None},
        'broadening_stage/device_piezo_x_in':{
                'driver':KPZ101,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'position_control_mode':None, 'input_voltage_source':None,
                'io_settings':None, 'voltage':None},
        'broadening_stage/device_piezo_y_in':{
                'driver':KPZ101,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'position_control_mode':None, 'input_voltage_source':None,
                'io_settings':None, 'voltage':None},
        'broadening_stage/device_piezo_z_in':{
                'driver':KPZ101,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'position_control_mode':None, 'input_voltage_source':None,
                'io_settings':None, 'voltage':None},
        'broadening_stage/device_piezo_x_out':{
                'driver':KPZ101,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'position_control_mode':None, 'input_voltage_source':None,
                'io_settings':None, 'voltage':None},
        'broadening_stage/device_piezo_y_out':{
                'driver':KPZ101,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'position_control_mode':None, 'input_voltage_source':None,
                'io_settings':None, 'voltage':None},
        'broadening_stage/device_piezo_z_out':{
                'driver':KPZ101,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'position_control_mode':None, 'input_voltage_source':None,
                'io_settings':None, 'voltage':None},
        'broadening_stage/device_nanotrack_in':{
                'driver':TNA001,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'track_mode':None, 'track_threshold':None, 'position':None,
                'circle_parameters':None, 'phase_comp':None,
                'tia_range_parameters':None, 'gain':None,
                'feedback_source':None, 'io_settings':None},
        'broadening_stage/device_nanotrack_out':{
                'driver':TNA001,
                'queue':'', #TODO: add serial number
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':0}],
                'track_mode':None, 'track_threshold':None, 'position':None,
                'circle_parameters':None, 'phase_comp':None,
                'tia_range_parameters':None, 'gain':None,
                'feedback_source':None, 'io_settings':None}}
CONTROL_PARAMS = {CONTROL_DB:{}}
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))

sm.init_default_settings(STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS)


# %% Initialize Databases, Devices, and Settings ==============================

#--- Connect to MongoDB -------------------------------------------------------
'''Creates a client and connects to all defined databases'''
db = {}
sm.init_DBs(db=db)

#--- Start Logging ------------------------------------------------------------
'''Initializes logging for this script. If the logging database is unset then
all logs will be output to the stout. When the logging database is set
there are two logging handlers, one logs lower threshold events to the log
buffer and the other logs warnings and above to the permanent log database.
The threshold for the base logger, and the two handlers, may be set in the
following command.
'''
sm.init_logging(database_object=db[LOG_DB], logger_level=logging.INFO, log_buffer_handler_level=logging.DEBUG, log_handler_level=logging.WARNING)

#--- Initialize All Devices and Settings --------------------------------------
'''This initializes all device drivers and checks that all settings
(as listed in SETTINGS) exist within the databases. Any missing
settings are populated with the default values. This function
automatically restarts if an error is encoutered.
-If the setting does not exist within a device database that setting is
propogated to the device, otherwise the local settings are read from the
device.
-The "driver" settings are saved as strings.
-The settings for "__init__" methods are are not sent or pulled to devices.
-A local copy of all settings is contained within the local_settings
dictionary.
-Each device database should be associated with a driver and a queue. The
format is as follows:
    dev[<device database path>] = {
            'driver':<driver object>,
            'queue':<queue objecct>}
'''
dev = {}
local_settings={}
sm.init_device_drivers_and_settings(dev=dev, local_settings=local_settings)

#--- Initialize Local Copy of Monitors ----------------------------------------
'''Monitors should associate the monitor databases with the local, circular
buffers of the monitored data. Monitors should indicate when they have
recieved new data.
-Monitors from the internal databases should be associated with the device
that they pull data from:
    {<database path>:{'data':<placeholder for local data copy>},
                      'device':<device object>,
                      'new':<bool>}
-Monitors from the read database should have their cursors exhausted so
that only their most recent values are accessible:
    {<database path>:{'data':<placeholder for local data copy>},
                      'cursor':<tailable cursor object>,
                      'new':<bool>}
-Only the read databases are automatically populated. The monitors for the
internal databases must be entered manually into "mon".
'''
mon = {}
sm.init_monitors(mon=mon)


# %% State Functions ==========================================================

# Global Timing Variable ------------------------------------------------------
timer = {}
thread = {}
array = {}

# Do nothing function ---------------------------------------------------------
'''A functional placeholder for cases where nothing should happen.'''
@log.log_this()
def nothing(state_db):
    pass


# %% Monitor Functions ========================================================
'''This section is for defining the methods needed to monitor the system.'''

# Get Rotation Mount Data -----------------------------------------------------
array['rot_angle'] = np.array([])
rot_mount_record_interval = 100.0 # seconds
timer['rot_mount:record'] = get_lap(rot_mount_record_interval)
def get_rotation_mount_data():
# Get lap number
    new_record_lap = get_lap(rot_mount_record_interval)
# Device DB
    device_db = 'broadening_stage/device_rotation_mount'
# Wait for queue
    dev[device_db]['queue'].queue_and_wait()
# Get rotation angle
    settings_list = [{'position':None, 'home':None}]
    sm.update_device_settings(device_db, settings_list, write_log=False)
# Remove from Queue
    dev[device_db]['queue'].remove()
# Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer['rot_mount:record']:
        timer['rot_mount:record'] = new_record_lap
thread['get_rotation_mount_data'] = ThreadFactory(target=get_rotation_mount_data)

# Monitor 2nd Stage -----------------------------------------------------------
passive_interval = 10.0 # s
timer['monitor_2nd_stage:passive'] = get_lap(passive_interval)
def monitor_2nd_stage(state_db):
# Get lap number
    new_passive_lap = get_lap(passive_interval)
# Update passive monitoring variables -------------------------------
    if (new_passive_lap > timer['monitor_2nd_stage:passive']):
    # Pull data from SRS ----------------------------------
        thread_name = 'get_rotation_mount_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Propogate lap numbers ---------------------------------------------
        timer['monitor_2nd_stage:passive'] = new_passive_lap


# %% Search Functions =========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''


# %% Maintain Functions =======================================================
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''


# %% Operate Functions ========================================================
'''This section is for defining the methods called only when the system is in
    its defined states.'''


# %% States ===================================================================
'''Defined states are composed of collections of settings, prerequisites,
and routines'''

STATES = {
        'broadening_stage/state_2nd_stage':{
                'lock':{
                        'settings':{
                                'broadening_stage/device_rotation_mount':{
                                        'enable':True},
                                'broadening_stage/device_piezo_x_in':{
                                        'enable':True},
                                'broadening_stage/device_piezo_y_in':{
                                        'enable':True},
                                'broadening_stage/device_piezo_z_in':{
                                        'enable':True},
                                'broadening_stage/device_piezo_x_out':{
                                        'enable':True},
                                'broadening_stage/device_piezo_y_out':{
                                        'enable':True},
                                'broadening_stage/device_piezo_z_out':{
                                        'enable':True},
                                'broadening_stage/device_nanotrack_in':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}},
                                'broadening_stage/device_nanotrack_out':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}}}},
                        'prerequisites':{}, #TODO: prereqs are setup and 1st stage properties
                        'routines':{
                                'monitor':monitor_2nd_stage, 'search':nothing,
                                'maintain':nothing, 'operate':nothing}
                        },
                'safe':{
                        'settings':{
                                'broadening_stage/device_rotation_mount':{
                                        'enable':True},
                                'broadening_stage/device_piezo_x_in':{
                                        'enable':True},
                                'broadening_stage/device_piezo_y_in':{
                                        'enable':True},
                                'broadening_stage/device_piezo_z_in':{
                                        'enable':True},
                                'broadening_stage/device_piezo_x_out':{
                                        'enable':True},
                                'broadening_stage/device_piezo_y_out':{
                                        'enable':True},
                                'broadening_stage/device_piezo_z_out':{
                                        'enable':True},
                                'broadening_stage/device_nanotrack_in':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}},
                                'broadening_stage/device_nanotrack_out':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}}},
                        'prerequisites':{},
                        'routines':{
                                'monitor':monitor_2nd_stage, 'search':nothing,
                                'maintain':nothing, 'operate':nothing}
                        },
                'setup':{ #TODO: check home, etc., and then go to "lock" state
                        'settings':{}, # turn off HP amp, etc... (turn back on in "lock" state)
                        'prerequisites':{},
                        'routines':{
                                'monitor':nothing, 'search':nothing,
                                'maintain':nothing, 'operate':nothing}
                        },
                'engineering':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':nothing, 'search':nothing,
                                'maintain':nothing, 'operate':nothing},
                        }
                }
sm.init_states(STATES)


# %% STATE MACHINE ============================================================

'''Operates the state machine.'''
current_state={}
sm.operate_machine(current_state=current_state, main_loop_interval=0.5)
