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

import os
import sys
sys.path.append(os.getcwd())

from Drivers.Logging import EventLog as log

from Drivers.StateMachine import ThreadFactory, Machine

from Drivers.SNMP.TrippLite import PDUOutlet


# %% Helper Functions =========================================================

'''The following are helper functionss that increase the readablity of code in
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

# Communications queue --------------------------------------------------------
'''The communications queue is a couchbase queue that serves as the
intermediary between this script and others. The entries in this queue
are parsed as commands in this script:
    Requesting to change state:
        {'state': {<state DB path>:{'state':<state>},...}}
    Requesting to change device settings:
        {'device_setting': {<device driver DB path>:{<method name>:<args>,...},...}}
    Requesting to change a control parameter:
        {'control_parameter': {<parameter name>:<value>,...}}
-Commands are sent into the queue by setting the "message" keyword argument
within the CouchbaseDB queue.push() method. 
-Commands are read from the queue with the queue.pop() method.
-If the DB path given does not exist in the defined STATE_DBs and
DEVICE_DBs, or the given method and parameter does not exist in 
CONTROL_PARAMS, no attempt is made to excecute the command.
-All commands are caught and logged at the INFO level.
-Multiple commands may be input simultaneously by nesting single commands
within the 'state', 'device_setting', and 'control_parameter' keys:
    message = {
        'state':{<state DB path>:{'state':<state>},...},
        'device_setting':{<device driver DB path>:{<method name>:<args>,...},...},
        'control_parameter':{<parameter name>:<value>,...}}
'''
COMMS = 'comb_generator'
sm.init_comms(COMMS)

# Internal database names --------------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function:
    state:
        -The entries in state databases should reflect the current state of
        the system and the level of compliance. Other scripts should look
        to these databases in order to resolve prerequisites.
    device:
        -The entries in visa databases should include the settings for
        each unique device or device/channel combination.
    monitor:
        -The entries in monitor databases should contain secondary 
        variables used to determine compliance with the state of the 
        system, and to determine any actions required to maintain
        compliance. 
        -In general, data for use in control loops should have
        an updated value every 0.2 seconds. Data for passive monitoring
        should have a relaxed 1.0 second or longer update period.
    log:
        -This should be a single database that serves as the repository of
        all logs generated by this script.
    control:
        -This should be a single database that contains all control loop 
        variables accessible to commands from the comms queue.
'''
STATE_DBs = [
        'comb_generator/state_12V_supply']
DEVICE_DBs =[
        'comb_generator/device_PDU_12V']
MONITOR_DBs = []
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
-Default values are only added to a database if the setting keys are not
found within the database (if the database has not yet been initialized
with that setting).
-For device databases, default settings of None are populated with values
from the device, but set values are written to the device. All
initialized settings are read from the device at startup.
-Include all settings that need to be tracked in the database:
    states:
        -Entries in the state databases are specified as follows:
            {<state database path>:{
            'state':<name of the current state>,
            'prerequisites':{
                    'critical':<critical>,
                    'necessary':<necessary>,
                    'optional':<optional>},
            'compliance':<compliance of current state>
            'desired_state':<name of the desired state>,
            'initialized':<initialization state of the control script>,
            'heartbeat':<datetime.datetime.utcnow()>},...}
        -The state name should correspond to one of the defined states.
        -The prerequisites should be a 3 part dictionary of boolean values
        that indicates whether the prerequisites pass for the current
        state. The 3 severity levels are critical, necessary, and optional.
        -The compliance level should be a boolean value that indicates
        whether the system is compliant with the current state.
        -The "desired_state" is mostly for internal use, particularly for
        cases where the state is temporarliy changed. The script should
        seek to bring the current state to the desired state. The script 
        should not change the current state if the desired state is
        undefined.
        -The "initialized" parameter is a boolean value that indicates that
        the current state is accurate. This is useful for cases where a
        master program or watchdog starts the control scripts. It should
        be set to False by the master program before the control scripts
        are executed, and should only be set to True after the
        control scripts have determined the current state. In order to 
        smoothly connect to the system if the instruments are already 
        running, initialization prerequisites should be either
        "necessary" or "optional" ("critical" would force the "safe" state).
        -The "heartbeat" parameter is a datetime.datetime utc timestamp
        that indicates when the control script last checked the state.
        Every time the control script finishes a loop it writes the state
        db to the buffer with a new heartbeat value. This is useful to
        determine if the current state in the database is "stale". The 
        heartbeat is only incidentally updated in the record as items are 
        written to it in the coarse of normal control script operation.
    devices:
        -Entries in the device databases are specified as follows:
            {<device database path>:{
                'driver':<driver class>,
                'queue':<queue name>,
                '__init__':<args>,
                <method name>:<args>,...},...}
        -The entries should include the settings for each unique device
        or device/channel combination. 
        -The "driver" should contain an uninitialized instance of the
        driver class
        -The "queue" should contain the name of the device queue. The queue
        is needed to coordinate access to the devices. Each blocking
        connection to a device should have a unique queue name. If access
        to one part of an instrument blocks access to other parts, that set
        of parts should all use the same unique queue. A good queue name is
        the instrument address.
        -The "__init__" method should hold all arguments necessary to 
        initialize the device driver.
        -For automation purposes, the setting names and parameters should
        be derived from the names of the device driver methods.
        -Single arguments should be entered as is:
            <method name>:<arg>
        -Place multiple arguments in a list containing a list of positional
        arguments and a dictionary of keyword arguments:
            <method name>:[[<args>], {<kwargs>}]
            <method name>:[[<args>]]
            <method name>:[{<kwargs>}]
        -A setting of None calls the methods without any arguments. Device
        drivers should reserve such cases for getting the current device
        settings:
            <method name>:None -> returns current device settings
        -The automated "send_args()" checks for the above cases before
        parsing and sending the commands.
    control parameter:
        -Entries in the control parameter database are specified as
        follows:
            {<control database path>:{
                <control parameter>:{'value':<value>,'type':<type str>},...}}
        -Control parameters have both a value and a type.
        -Only include parameters that should have remote access. There is
        no protection against the insertion of bad values.
        -The "main_loop" parameter is reserved for operation of the
        state machine.
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
                'heartbeat':datetime.datetime.utcnow()}}
DEVICE_SETTINGS = {
        # DAQ settings
        'comb_generator/device_PDU_12V':{
                'driver':PDUOutlet,
                'queue':'192.168.0.2',
                '__init__':[['192.168.0.2', 1]],
                'outlet_state':None, 'outlet_ramp_action':0}}
CONTROL_PARAMS = {CONTROL_DB:{}}
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))
sm.init_default_settings(STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS)


# %% Initialize Databases, Devices, and Settings ==============================

# Connect to MongoDB ----------------------------------------------------------
'''Creates a client and connects to all defined databases'''
db = {}
sm.init_DBs(db=db)

# Start Logging ---------------------------------------------------------------
'''Initializes logging for this script. If the logging database is unset then
all logs will be output to the stout. When the logging database is set
there are two logging handlers, one logs lower threshold events to the log 
buffer and the other logs warnings and above to the permanent log database.
The threshold for the base logger, and the two handlers, may be set in the
following command.
'''
sm.init_logging(database_object=db[LOG_DB], logger_level=logging.INFO, log_buffer_handler_level=logging.DEBUG, log_handler_level=logging.WARNING)

# Initialize all Devices and Settings -----------------------------------------
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
mon = {}
    # External ------------------------
sm.init_monitors(mon=mon)


# %% State Functions ==========================================================

# Global Timing Variable ------------------------------------------------------
timer = {}
thread = {}

# Do nothing function ---------------------------------------------------------
'''A functional placeholder for cases where nothing should happen.'''
@log.log_this()
def nothing(state_db):
    pass


# %% Monitor Functions ========================================================
'''This section is for defining the methods needed to monitor the system.'''

# Get PDU Data -------------------------------------------------------------
control_interval = 1 # s
timer['monitor:control'] = get_lap(control_interval)
def get_PDU_data():
# Get lap number
    new_control_lap = get_lap(control_interval)
# Update control loop variables -------------------------------------
    if (new_control_lap > timer['monitor:control']):
    # PDU -------------------------------------------------
        device_db = 'comb_generator/device_PDU_12V'
        settings_list = [{'outlet_state':None}]
        sm.update_device_settings(device_db, settings_list, write_log=False)
    # Pull data from external databases -------------------
        new_data = []
        for doc in mon['ambience/box_temperature_0']['cursor']:
            new_data.append(doc['V'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            mon['ambience/box_temperature_0']['new'] = True
            mon['ambience/box_temperature_0']['data'] = update_buffer(
                mon['ambience/box_temperature_0']['data'],
                new_data, 500)
    # Propogate lap numbers -----------------------------------------
        timer['monitor:control'] = new_control_lap
thread['get_PDU_data'] = ThreadFactory(target=get_PDU_data)


# Monitor Outlet --------------------------------------------------------------
def monitor(state_db):
    new_control_lap = get_lap(control_interval)
    if (new_control_lap > timer['monitor:control']):
    # Pull data from SRS ----------------------------------
        thread_name = 'get_PDU_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()

# %% Search Functions =========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''
    
# Outlet Off ------------------------------------------------------------------
def turn_outlet_off(state_db):
    mod_name = turn_outlet_off.__module__
    func_name = turn_outlet_off.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = local_settings[device_db]['outlet_state']
    dev[device_db]['queue'].remove()
    if outlet_state != 1:
        # Outlet is on
        settings_list = [{'outlet_state':1}]
        sm.update_device_settings(device_db, settings_list)
    else:
    # Outlet is off
        # Update the state variable
        with sm.lock[state_db]:
            current_state[state_db]['compliance'] = True
            db[state_db].write_record_and_buffer(current_state[state_db])
        log_str = ' Outlet off successful'
        log.log_info(mod_name, func_name, log_str)

# Outlet on -------------------------------------------------------------------
def turn_outlet_on(state_db):
    mod_name = turn_outlet_on.__module__
    func_name = turn_outlet_on.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = local_settings[device_db]['outlet_state']
    dev[device_db]['queue'].remove()
    if outlet_state != 2:
        # Outlet is off
        settings_list = [{'outlet_state':2}]
        sm.update_device_settings(device_db, settings_list)
    else:
    # Outlet is on
        # Update the state variable
        with sm.lock[state_db]:
            current_state[state_db]['compliance'] = True
            db[state_db].write_record_and_buffer(current_state[state_db])
        log_str = ' Outlet on successful'
        log.log_info(mod_name, func_name, log_str)


# %% Maintain Functions =======================================================
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''

# Keep Off --------------------------------------------------------------------
def keep_outlet_off(state_db):
    mod_name = keep_outlet_off.__module__
    func_name = keep_outlet_off.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = local_settings[device_db]['outlet_state']
    if outlet_state != 1:
        # Update the state variable
        with sm.lock[state_db]:
            current_state[state_db]['compliance'] = False
            db[state_db].write_record_and_buffer(current_state[state_db])
        log_str = ' Outlet on detected, turning off 12V outlet'
        log.log_info(mod_name, func_name, log_str)

# Keep On ---------------------------------------------------------------------
def keep_outlet_on(state_db):
    mod_name = keep_outlet_on.__module__
    func_name = keep_outlet_on.__name__
    device_db = 'comb_generator/device_PDU_12V'
    # Get outlet state
    outlet_state = local_settings[device_db]['outlet_state']
    if outlet_state != 2:
        # Update the state variable
        with sm.lock[state_db]:
            current_state[state_db]['compliance'] = False
            db[state_db].write_record_and_buffer(current_state[state_db])
        log_str = ' Outlet off detected, turning on 12V outlet'
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
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor, 'search':turn_outlet_on,
                                'maintain':keep_outlet_on, 'operate':nothing}},
                'safe':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[],
                                'exit':[
                                    {'db':'ambience/box_temperature_0',
                                     'key':'V',
                                     'test':(lambda t: (t<0.245) and (t>0.10)),
                                     'doc':"(lambda t: (t<0.245) and (t>0.10))"}]},
                        'routines':{
                                'monitor':monitor, 'search':turn_outlet_off,
                                'maintain':keep_outlet_off, 'operate':nothing}},
                'engineering':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':nothing, 'search':nothing,
                                'maintain':nothing, 'operate':nothing}}
                        }                        
        }
sm.init_states(STATES)


# %% STATE MACHINE ============================================================

'''Operates the state machine.'''
current_state={}
sm.operate_machine(current_state=current_state, main_loop_interval=0.5)


