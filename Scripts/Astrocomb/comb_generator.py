# -*- coding: utf-8 -*-
"""
Created on Sun Mar 18 08:18:06 2018

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

from Drivers.SNMP.TrippLite import PDUOutlet
from Drivers.VISA.Keysight import E36103A


# %% Helper Functions =========================================================

'''The following are helper functionss that increase the readablity of code in
    this script. These functions are defined by the user and should not
    directly appear in the main loop of the state machine.'''


# %% Initialization ===========================================================

sm = Machine()


# %% Databases and Settings ===================================================

# Communications queue --------------------------------------------------------
'''The communications queue is a couchbase queue that serves as the
intermediary between this script and others. The entries in this queue
are parsed as commands in this script.
'''
COMMS = 'comb_generator'
sm.init_comms(COMMS)

# Internal database names --------------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function.
'''
STATE_DBs = [
        'comb_generator/state_12V_supply', 'comb_generator/state_IM_bias']
DEVICE_DBs =[
        'comb_generator/device_PDU_12V', 'comb_generator/device_IM_bias']
MONITOR_DBs = ['comb_generator/IM_bias']
LOG_DB = 'comb_generator'
CONTROL_DB = 'comb_generator/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]
sm.init_master_DB_names(STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB)

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = ['ambience/box_temperature_0']
READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs
sm.init_read_DB_names(R_STATE_DBs, R_DEVICE_DBs, R_MONITOR_DBs)

# Default settings ------------------------------------------------------------
'''A template for all settings used in this script. Upon initialization
these settings are checked against those saved in the database, and
populated if found empty. Each state and device database should be represented.
'''
STATE_SETTINGS = {
        'comb_generator/state_12V_supply':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'on',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()},
        'comb_generator/state_IM_bias':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'on',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()}}
DEVICE_SETTINGS = {
        # PDU settings
        'comb_generator/device_PDU_12V':{
                'driver':PDUOutlet,
                'queue':'192.168.0.2',
                '__init__':[['192.168.0.2', 1]],
                'outlet_state':None, 'outlet_ramp_action':0},
        # DC IM Bias settings
        'comb_generator/device_IM_bias':{
                'driver':E36103A,
                'queue':'IM_bias',
                '__init__':[['USB0::0x2A8D::0x0702::MY57427460::INSTR']],
                'output':True, 'voltage_setpoint':None}
        }
CONTROL_PARAMS = {CONTROL_DB:{}}
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))
sm.init_default_settings(STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS)


# %% Initialize Databases, Devices, and Settings ==============================

# Connect to MongoDB ----------------------------------------------------------
'''Creates a client and connects to all defined databases'''
sm.init_DBs()

# Start Logging ---------------------------------------------------------------
'''Initializes logging for this script.
'''
sm.init_logging(
    database_object=sm.db[LOG_DB],
    logger_level=logging.INFO,
    log_buffer_handler_level=logging.DEBUG,
    log_handler_level=logging.WARNING)

# Initialize all Devices and Settings -----------------------------------------
'''This initializes all device drivers and checks that all settings
(as listed in SETTINGS) exist within the databases. Any missing
settings are populated with the default values.
'''
sm.init_device_drivers_and_settings()

# Initialize Local Copy of Monitors -------------------------------------------
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
sm.init_monitors()


# %% State Functions ==========================================================

# Global Timing Variable ------------------------------------------------------
timer = {}
thread = {}
array = {}


# %% Monitor Functions ========================================================
'''This section is for defining the methods needed to monitor the system.'''

# Get PDU Data -------------------------------------------------------------
pdu_control_interval = 1 # s
timer['monitor_pdu:control'] = sm.get_lap(pdu_control_interval)
def get_PDU_data():
# Update control loop variables -------------------------------------
# PDU -------------------------------------------------
    device_db = 'comb_generator/device_PDU_12V'
    settings_list = [{'outlet_state':None}]
    sm.update_device_settings(device_db, settings_list, write_log=False)
thread['get_PDU_data'] = ThreadFactory(target=get_PDU_data)

# Monitor Outlet --------------------------------------------------------------
def monitor_pdu(state_db):
    new_control_lap = sm.get_lap(pdu_control_interval)
    if (new_control_lap > timer['monitor_pdu:control']):
    # Pull data from PDU ----------------------------------
        thread_name = 'get_PDU_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Pull data from external databases -------------------
        monitor_db = 'ambience/box_temperature_0'
        new_data = []
        for doc in sm.mon[monitor_db]['cursor'].read():
            new_data.append(doc['V'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            with sm.lock[monitor_db]:
                sm.mon[monitor_db]['new'] = True
                sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    new_data, 500, extend=True)
    # Propogate lap numbers -----------------------------------------
        timer['monitor_pdu:control'] = new_control_lap

# Get IM Bias Data ------------------------------------------------------------
IM_control_interval = 1 # s
IM_record_interval = 10 # s
timer['monitor_IM:control'] = sm.get_lap(IM_control_interval)
timer['monitor_IM:record'] = sm.get_lap(IM_record_interval)
array['IM_bias'] = []
def get_IM_bias_data():
# Get lap number
    new_record_lap = sm.get_lap(IM_record_interval)
# Update control loop variables -------------------------------------
# DC Supply -----------------------------------------------
    device_db = 'comb_generator/device_IM_bias'
# Queue
    sm.dev[device_db]['queue'].queue_and_wait()
# Output State and Voltage Setpoint
    settings_list = [{'output':None, 'voltage_setpoint':None}]
    sm.update_device_settings(device_db, settings_list, write_log=False)
# Measured Voltage
    voltage = sm.dev[device_db]['driver'].voltage()
# De-queue
    sm.dev[device_db]['queue'].remove()
# Update buffers and databases --------------------------------------
    # Measured Bias ---------------------------------------
    monitor_db = 'comb_generator/IM_bias'
    array_id = 'IM_bias'
    data = voltage
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = sm.update_buffer(
                sm.mon[monitor_db]['data'],
                data, 100)
        sm.db[monitor_db].write_buffer({'V':data})
            # Append to the record array
        array[array_id].append(data)
        if (new_record_lap > timer['monitor_IM:record']):
            array[array_id] = np.array(array[array_id])
            # Record statistics ---------------------
            sm.db[monitor_db].write_record({
                    'V':array[array_id].mean(),
                    'std':array[array_id].std(),
                    'n':array[array_id].size})
            # Empty the array
            array[array_id] = []
    # Propogate lap numbers -----------------------------------------
        timer['monitor_IM:record'] = new_record_lap
thread['get_IM_bias_data'] = ThreadFactory(target=get_IM_bias_data)

# Monitor IM Bias -------------------------------------------------------------
def monitor_IM(state_db):
    new_control_lap = sm.get_lap(IM_control_interval)
    if (new_control_lap > timer['monitor_IM:control']):
    # Get IM Bias data
        thread_name = 'get_IM_bias_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Propogate lap numbers -----------------------------------------
        timer['monitor_IM:control'] = new_control_lap

# %% Search Functions =========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''

# Outlet Off ------------------------------------------------------------------
def turn_outlet_off(state_db):
    mod_name = turn_outlet_off.__module__
    func_name = turn_outlet_off.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = sm.local_settings[device_db]['outlet_state']
    if outlet_state != 1:
        # Outlet is on
        settings_list = [{'outlet_state':1}]
        sm.update_device_settings(device_db, settings_list)
    else:
    # Outlet is off
        # Update the state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = True
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
        log_str = ' Outlet off successful'
        log.log_info(mod_name, func_name, log_str)

# Outlet on -------------------------------------------------------------------
def turn_outlet_on(state_db):
    mod_name = turn_outlet_on.__module__
    func_name = turn_outlet_on.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = sm.local_settings[device_db]['outlet_state']
    if outlet_state != 2:
        # Outlet is off
        settings_list = [{'outlet_state':2}]
        sm.update_device_settings(device_db, settings_list)
    else:
    # Outlet is on
        # Update the state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = True
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
        log_str = ' Outlet on successful'
        log.log_info(mod_name, func_name, log_str)

# Bias on -------------------------------------------------------------------
def turn_bias_on(state_db):
    mod_name = turn_bias_on.__module__
    func_name = turn_bias_on.__name__
    device_db = 'comb_generator/device_IM_bias'
    # Get bias state
    bias_state = sm.local_settings[device_db]['output']
    if bias_state != True:
        # Bias is off
        settings_list = [{'output':True}]
        sm.update_device_settings(device_db, settings_list)
    else:
    # Bias is on
        # Update the state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = True
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
        log_str = ' IM bias on successful'
        log.log_info(mod_name, func_name, log_str)


# %% Maintain Functions =======================================================
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''

# Keep Outlet Off -------------------------------------------------------------
def keep_outlet_off(state_db):
    mod_name = keep_outlet_off.__module__
    func_name = keep_outlet_off.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = sm.local_settings[device_db]['outlet_state']
    if outlet_state != 1:
        # Update the state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = False
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
        log_str = ' Outlet on detected, turning off 12V outlet'
        log.log_info(mod_name, func_name, log_str)

# Keep Outlet On --------------------------------------------------------------
def keep_outlet_on(state_db):
    mod_name = keep_outlet_on.__module__
    func_name = keep_outlet_on.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = sm.local_settings[device_db]['outlet_state']
    if outlet_state != 2:
        # Update the state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = False
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
        log_str = ' Outlet off detected, turning on 12V outlet'
        log.log_info(mod_name, func_name, log_str)

# Keep Bias On ----------------------------------------------------------------
def keep_bias_on(state_db):
    mod_name = keep_bias_on.__module__
    func_name = keep_bias_on.__name__
    device_db = 'comb_generator/device_IM_bias'
    # Get bias state
    bias_state = sm.local_settings[device_db]['output']
    if bias_state != True:
        # Bias is off
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = False
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
        log_str = ' IM bias off detected, turning on IM bias'
        log.log_info(mod_name, func_name, log_str)


# %% Operate Functions ========================================================
'''This section is for defining the methods called only when the system is in
    its defined states.'''


# %% States ===================================================================

'''Defined states are composed of collections of settings, prerequisites,
and routines:
    settings:
        -Only the settings particular to a state need to be listed, and
        they should be in the same format as those in SETTINGS:
            'settings':{
                <device database path>:{
                    <method>:<args>,...},...}
        -The settings listed here should be thought of as stationary
        prerequisites, or as known initialization states that the system
        should pass through to ease the transition to the compliant state.
        -Dynamic settings should be dealt with in the state's methods.
        -These settings will be applied before the system transitions from
        one state to the next.
        -Place groups of settings together in lists if the order of the
        operations matter. The groups of settings will be applied as
        ordered in the list:
            'settings':{
                <device database path>:[
                    {<first group>},{<second group>},...]
    prerequisites:
        -Prerequisites should be entered as lists of dictionaries that
        include the database and key:value pair that corresponds to a
        passing prerequisite for the given state:
            'prerequisites':{
                {'critical':[{
                    'db':<database path>,
                    'key':<entry's key>,
                    'test':<desired value>},...],
                'necessary':[{...},...],
                'optional':[{...}]}}
        -The "test" should be a lambda function that evaluates to true
        if the prerequisite has passed.
        -The automated "from_keys()" checks for lists of keys needed to
        retrieve values from nested dictionaries.
        -Prereqs should be separated by severity:
            critical:
                -A failed critical prereq could jeopardize the health of
                the system if brought into or left in the applied state.
                -Critical prerequisites are continuously monitored.
                -The system is placed into a temporary "safe" state upon
                failure of a critical prereq.
            necessary:
                -Failure of a necessary prereq will cause the system to
                come out of, or be unable to reach, compliance.
                -Necessary prereqs are checked if the system is out
                of compliance.
                -The system is allowed to move into the applied state upon
                failure of a necessary prereq, but no attempts are made to
                bring the system into compliance.
            optional:
                -Failure of an optional prereq should not cause failure
                elsewhere, but system performance or specifications can't
                be guaranteed. Think of it more as "non compulsory" than
                "optional".
                -Optional prereqs are checked when the system is out of
                compliance, and when the system is in compliance, but the
                optional prereqs are listed as failed.
                -The system is allowed to move into the applied state upon
                failure of an optional prereq.
    routines:
        -The routines are the functions needed to monitor the state, bring
        the state into compliance, maintain the state in compliance, and
        operate any other scripts that require a compliant state.
        -All routines must accept the path of a state DB as an argument:
            routine(<state database path>)
        -Only one function call should be listed for each method. The
        methods themselves may call others.
        -Routines should be entered for the 4 cases:
            'routines':{
                'monitor':<method>, 'search':<method>,
                'maintain':<method>, 'operate':<method>}
        monitoring:
            -The monitor method should generally update all state
            parameters necessary for the "search" or "maintain" methods as
            well as any secondary parameters useful for passive monitoring.
            -Updating state parameters includes getting new values from
            connected instruments and pulling new values from connected
            databases.
            -New values from instruments should always be saved to their
            respective databases. The main entry in the database
            should typically be keyed with the symbols for the units of the
            measurement (V, Hz, Ohm,...):
                db[device_db].write_record_and_buffer({<unit>:<value>})
            -Suggested refresh times for control loop parameters is 0.2
            seconds, while a 1.0 second or longer refresh time should be
            sufficient for passive monitoring parameters.
            -All values should be stored locally in circular buffers. The
            sizes of which should be controlled within these methods.
        searching:
            -The search method should be able to bring the system into
            compliance from any noncompliant state.
            -The most important cases to consider are those starting from
            the configuration as given in the state's "settings", and the
            cases where the state has transitioned from a compliant to a
            noncompliant state.
            -It is the search method's responsibility to change the state's
            compliance state variable as the "maintain" and "operate"
            scripts are only called if the state's compliance variable is
            set to True.
            -The search method should use testing criteria to determine if the
            found state is truly in compliance before setting the state's
            compliance variable.
            -The compliance state variable is accessible by calling:
                current_state[<state database path>]['compliance']
            -Any important device setting changes should be propogated to
            their respective databases.
        maintaining:
            -The maintain method should observe the state parameters and
            make any needed adjustments to the state settings in order to
            maintain the state.
            -If time series are needed in order to maintain the state, a
            global variable may be used within the maintain and search
            methods to indicate when the search method brought the state
            into compliance. The maintain method may then use that
            knowledge to selectively pull values from the "monitor"
            buffers or simply clear the buffers on first pass.
            -The maintain method is responsible for changing the compliance
            variable to False if it is unable to maintain the state.
            -The compliance state variable is accessible by calling:
                current_state[<state database path>]['compliance']
            -Any important device setting changes should be propogated to
            their respective databases.
        operating:
            -The operate method is a catchall function for use cases that
            are only valid while the state is in compliance. An example
            could be to only read values from an instrument buffer while
            the instrument's data collection state is active.
'''
STATES = {
        'comb_generator/state_12V_supply':{
                'on':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[
                                    {'db':'ambience/box_temperature_0',
                                     'key':'V',
                                     'test':(lambda t: (t<0.35) and (t>0.10)),
                                     'doc':"lambda t: (t<0.35) and (t>0.10)"}], # Below max temperature threshold 35 C
                                        },
                        'routines':{
                                'monitor':monitor_pdu, 'search':turn_outlet_on,
                                'maintain':keep_outlet_on, 'operate':sm.nothing}},
                'safe':{
                        'settings':{},
                        'prerequisites':{
                                'exit':[
                                    {'db':'ambience/box_temperature_0',
                                     'key':'V',
                                     'test':(lambda t: (t<0.245) and (t>0.10)),
                                     'doc':"(lambda t: (t<0.245) and (t>0.10))"}]},
                        'routines':{
                                'monitor':monitor_pdu, 'search':turn_outlet_off,
                                'maintain':keep_outlet_off, 'operate':sm.nothing}},
                'engineering':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}}
                        },
        'comb_generator/state_IM_bias':{
                'on':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':monitor_IM, 'search':turn_bias_on,
                                'maintain':keep_bias_on, 'operate':sm.nothing}},
                'safe':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':monitor_IM, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}},
                'engineering':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}}
                        }
        }
sm.init_states(STATES)


# %% STATE MACHINE ============================================================

'''Operates the state machine.'''
sm.operate_machine(main_loop_interval=0.5)


