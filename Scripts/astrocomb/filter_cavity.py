# -*- coding: utf-8 -*-
"""
Created on Sat Mar 17 17:59:37 2018

@author: Connor
"""


# %% Import Modules ===========================================================

import numpy as np
import time
import logging

import threading

import os
import sys
sys.path.append(os.getcwd())

from Drivers.Logging import EventLog as log

from Drivers.Database import MongoDB
from Drivers.Database import CouchbaseDB

from Drivers.VISA.SRS import SIM960
from Drivers.VISA.Thorlabs import MDT639B

from Drivers.DAQ.Tasks import AiTask


# %% Main Loop Functions ======================================================

'''The following are functions used in the main loop of the state machine. They
    should not require any alteration. Changes to these methods change the
    operation of the state machine logic.'''

# Check the Prerequisites of a Given State ------------------------------------
@log.log_this()
def check_prereqs(state_db, state, level, log_failures=None):
    if log_failures == None:
        log_failures = ((time.time() - log_failed_prereqs_timer[state_db][state][level]) > log_failed_prereqs_interval)
    prereqs_pass = True
    for prereq in STATES[state_db][state]['prerequisites'][level]:
        prereq_value = from_keys(db[prereq['db']].read_buffer(),prereq['key'])
        prereq_status = (prereq_value == prereq['value'])
        prereqs_pass *= prereq_status
        if (not(prereq_status) and log_failures):
            if (level=='critical'):
                log_str = 'Critical prerequisite failure: state_db: {:}; state: {:}; prereq: {:}'.format(state_db, state, prereq)
                log.log_critical(__name__,'check_prereqs',log_str)
                log_failed_prereqs_timer[state_db][state]['critical'] = time.time()
            elif (level=='necessary'):
                log_str = 'Necessary prerequisite failure: state_db: {:}; state: {:}; prereq: {:}'.format(state_db, state, prereq)
                log.log_warning(__name__,'check_prereqs',log_str)
                log_failed_prereqs_timer[state_db][state]['necessary'] = time.time()
            elif (level=='optional'):
                log_str = 'Optional prerequisite failure: state_db: {:}; state: {:}; prereq: {:}'.format(state_db, state, prereq)
                log.log_warning(__name__,'check_prereqs',log_str)
                log_failed_prereqs_timer[state_db][state]['optional'] = time.time()
    return prereqs_pass

# Update Device Settings ------------------------------------------------------
@log.log_this()
def update_device_settings(device_db, settings_list, write_log=True):
    updated = False
# Check settings_list type
    if isinstance(settings_list, dict):
    # If settings_list is a dictionary then use only one settings_group
        settings_list = [settings_list]
# Wait for queue
    queued = dev[device_db]['queue'].queue_and_wait()
# Push device settings
    for settings_group in settings_list:
        for setting in settings_group:
        # Log the device, method, and arguments
            if write_log:
                prologue_str = 'device: {:}; method: {:}; args: {:}'.format(device_db, setting, settings_group[setting])
                log.log_info(__name__, 'update_device_settings', prologue_str)
        # Try sending the command to the device
            try:
                result = send_args(getattr(dev[device_db]['driver'], setting),settings_group[setting])
            except:
                log.log_exception(__name__, 'update_device_settings')
            else:
            # Update the local copy if it exists in the device settings
                if (setting in local_settings[device_db]):
                    if settings_group[setting] == None:
                    # A setting was read from the device
                        new_setting = result
                    else:
                    # A new setting was applied to the device
                        new_setting = settings_group[setting]
                    if (local_settings[device_db][setting] != new_setting):
                        updated = True
                        local_settings[device_db][setting] = new_setting
            # Log the returned result if stringable
                try:
                    epilogue_str = 'Returned: {:}'.format(str(result))
                except:
                    epilogue_str = 'Returned successfully, but result was not stringable'
                if write_log:
                    log.log_info(__name__, 'update_device_settings', epilogue_str)
        # Touch queue (prevent timeout)
            dev[device_db]['queue'].touch()
# Remove from queue
    if not(queued):
        dev[device_db]['queue'].remove()
# Update the database if the local copy changed
    if updated:
        db[device_db].write_record_and_buffer(local_settings[device_db])

# Setup the Transition to a New State -----------------------------------------
@log.log_this()
def setup_state(state_db, state, critical=True, necessary=True, optional=True):
# Update the device settings
    for device_db in STATES[state_db][state]['settings']:
        update_device_settings(device_db, STATES[state_db][state]['settings'][device_db])
# Update the state variable
    current_state[state_db]['state'] = state
    current_state[state_db]['prerequisites'] = {
            'critical':critical,
            'necessary':necessary,
            'optional':optional}
    current_state[state_db]['compliance'] = False
    db[state_db].write_record_and_buffer(current_state[state_db]) # The desired state should be left unaltered

# Parse Messages from the Communications Queue --------------------------------
@log.log_this()
def parse_message(message):
    if ('message' in message):
        message = message['message']
        log.log_info(__name__, 'parse_message', str(message))
    # If requesting to change states,
        if ('state' in message):
            for state_db in message['state']:
                if ('state' in message['state'][state_db]):
                    desired_state = message['state'][state_db]['state']
                    if current_state[state_db]['desired_state'] != desired_state:
                    # Update the state variable
                        current_state[state_db]['desired_state'] = desired_state
                        db[state_db].write_record_and_buffer(current_state[state_db])
    # If requesting to change device settings,
        if ('device_setting' in message):
            for device_db in message['device_setting']:
            # Update the device settings
                if (device_db in DEVICE_DBs):
                    update_device_settings(device_db, message['device_setting'][device_db])
    # If requesting to change control parameters,
        if ('control_parameter' in message):
            updated = False
            for method in message['control_parameter']:
                if (method in local_settings[CONTROL_DB]):
                    for parameter in message['control_parameter'][method]:
                    # Update the control parameter
                        if (parameter in local_settings[CONTROL_DB][method]):
                        # Convert new parameter to the correct type
                            parameter_type = local_settings[CONTROL_DB][method][parameter]['type']
                            try:
                                result = convert_type(message['control_parameter'][method][parameter], parameter_type)
                            except:
                                result_str = 'Could not convert {:} to {:} for control parameter {:}.{:}'.format(message['control_parameter'][method][parameter], parameter_type, method, parameter)
                                log.log_info(__name__, 'parse_message', result_str)
                            else:
                                if (local_settings[CONTROL_DB][method][parameter]['value'] != result):
                            # Update the local copy
                                    updated = True
                                    local_settings[CONTROL_DB][method][parameter]['value'] = result
        # Update the database if the local copy changed
            if updated:
                db[CONTROL_DB].write_record_and_buffer(local_settings[CONTROL_DB])

# Get Values from Nested Dictionary -------------------------------------------
@log.log_this()
def from_keys(nested_dict, key_list):
    if isinstance(key_list, list):
        for key in key_list:
            nested_dict = nested_dict[key]
    else:
        nested_dict = nested_dict[key_list]
    return nested_dict

# Parse and Send Arguments to Functions ---------------------------------------
@log.log_this()
def send_args(func, obj=None):
    try:
        obj_length = len(obj)
    except:
        obj_length = None
    if (obj_length == 1):
    # Check for an internal list or dictionary
        if isinstance(obj[0], list):
            args = obj[0]
            kwargs = {}
        elif isinstance(obj[0], dict):
            args = []
            kwargs = obj[0]
        else:
            args = [obj]
            kwargs = {}
    elif (obj_length == 2):
    # Check for both an internal list and dictionary
        if ((list and dict) in [type(obj[0]), type(obj[1])]):
            if isinstance(obj[0], list):
                args = obj[0]
                kwargs = obj[1]
            else:
                args = obj[1]
                kwargs = obj[2]
        else:
            args = [obj]
            kwargs = {}
    else:
    # Check if no input
        if obj == None:
            args = []
            kwargs = {}
        else:
            args = [obj]
            kwargs = {}
    result = func(*args, **kwargs)
    return result

# Exhaust a MongoDB Cursor to Queue up the Most Recent Values -----------------
@log.log_this()
def exhaust_cursor(cursor):
    for doc in cursor:
        pass
    return cursor

# Convert Type from a "type string" -------------------------------------------
@log.log_this()
def convert_type(obj, type_str):
    valid_types = {'bool':bool, 'complex':complex,
                   'float':float, 'int':int, 'str':str}
    obj = valid_types[type_str](obj)
    return obj


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


# %% Databases and Settings ===================================================

# Communications queue --------------------------------------------------------
'''The communications queue should be a database that serves as the
    intermediary between this script and others. The entries in this queue
    are parsed as commands in this script:
        Requesting to change state:
            {'state': {<state DB path>:{'state':<state>},...}}
        Requesting to change device settings:
            {'device_setting': {<device driver DB path>:{<method name>:<args>,...},...}}
        Requesting to change a control parameter:
            {'control_parameter': {<local method>:{<parameter name>:<value>,...},...}}
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
            'control_parameter':{<local method>:{<parameter name>:<value>,...},...}}
    '''
COMMS = 'filter_cavity'

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
            variables accessible to commands from the comms queue.'''
STATE_DBs = [
    'filter_cavity/state']
DEVICE_DBs =[
    'filter_cavity/device_PID', 'filter_cavity/device_HV',
    'filter_cavity/device_DAQ_Vout_vs_reflect']
MONITOR_DBs = [
    'filter_cavity/PID_output', 'filter_cavity/PID_output_limits',
    'filter_cavity/PID_action', 'filter_cavity/HV_output',
    'filter_cavity/DAQ_Vout_vs_reflect']
LOG_DB = 'filter_cavity/log'
CONTROL_DB = 'filter_cavity/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are 
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = ['filter_cavity/TEC_temperature', 'filter_cavity/DAQ_error_signal']
READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs

# Default settings ------------------------------------------------------------
'''A template for all settings used in this script. Upon initialization 
    these settings are checked against those saved in the database, and 
    populated if found empty. Each state and device database should be
    represented. 
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
                'initialized':<initialization state of the control script>},...}
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
        devices:
            -Entries in the device databases are specified as follows:
                {<device database path>:{
                    {<method name>:<args>,...},...}
            -The entries should include the settings for each unique device or
            device/channel combination. 
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
            -The "__init__" method should hold all arguments necessary to 
            initialize the device driver.
        control parameter:
            -Entries in the control parameter database are specified as
            follows:
                {<control database path>:{
                    <local method>:{
                        <control parameter>:{'value':<value>,'type':<type str>},...}
                    ,...}}
            -Control parameters are grouped by the method that they contribute
            to. Choose one method in which to associate a single control
            parameter if it happens to be used in multiple local methods. These
            methods are executed based on their placement in STATES.
            -Control parameters have both a value and a type.
            -Only include parameters that should have remote access. There is
            no protection against the insertion of bad values.'''
STATE_SETTINGS = {
        'filter_cavity/state':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'lock',
                'initialized':False}}
DEVICE_SETTINGS = {
        # VISA device settings
        'filter_cavity/device_PID':{
                '__init__':[['ASRL1::INSTR', 3]],
                'proportional_action':True, 'integral_action':True,
                'derivative_action':False, 'offset_action':None, 'offset':None,
                'proportional_gain':-0.2, 'integral_gain':1.0e2, 'pid_action':None,
                'external_setpoint_action':False, 'internal_setpoint':0.000,
                'ramp_action':False, 'manual_output':None,
                'upper_output_limit':2.00, 'lower_output_limit':0.00, 'power_line_frequency':60},
        'filter_cavity/device_HV':{
                '__init__':[['ASRL30::INSTR']], 'master_scan_action':False,
                'y_min_limit':0.00, 'y_max_limit':150.00, 'y_voltage':99.1},
        # DAQ settings
        'filter_cavity/device_DAQ_Vout_vs_reflect':{
                '__init__':[
                    [[{'physical_channel':'Dev1/ai1', 'terminal_config':'NRSE',
                       'min_val':-1.0, 'max_val':1.0}],
                        250e3, int(250e3*0.01)],{'timeout':5.0}],
                'reserve_cont':False, 'reserve_point':False}}
CONTROL_PARAMS = {
        'filter_cavity/control':{ }}
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))


# %% Initialize Databases, Devices, and Settings ==============================

# Connect to MongoDB ----------------------------------------------------------
'''Creates a client and connects to all defined databases'''
mongo_client = MongoDB.MongoClient()
db = {}
for database in MASTER_DBs:
    db[database] = MongoDB.DatabaseMaster(mongo_client, database)

for database in READ_DBs:
    db[database] = MongoDB.DatabaseRead(mongo_client, database)

# Start Logging ---------------------------------------------------------------
'''Initializes logging for this script. If the logging database is unset then
    all logs will be output to the stout. When the logging database is set
    there are two logging handlers, one logs lower threshold events to the log 
    buffer and the other logs warnings and above to the permanent log database.
    The threshold for the base logger, and the two handlers, may be set in the
    following command.'''
log.start_logging(logger_level=logging.INFO) #database=db[LOG_DB])

# Connect to the Communications Queue -----------------------------------------
'''Creates a handle for the queue object defined in COMMS'''
comms = CouchbaseDB.PriorityQueue(COMMS)

# Initialize Devices ----------------------------------------------------------
'''Each device database should be associated with a driver and a queue. The 
    format is as follows:
        dev[<device database path>] = {
                'driver':<driver object>,
                'queue':<queue objecct>}
    -The queue is needed to coordinate access to the devices. Each blocking
    connection to a device should have a unique queue name. If access to one
    part of an instrument blocks access to other parts, that set of parts
    should all use the same unique queue. A good queue name is likely the 
    instrument address.'''
dev = {}
    # VISA drivers
dev['filter_cavity/device_PID'] = {
        'driver':send_args(SIM960, DEVICE_SETTINGS['filter_cavity/device_PID']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('ASRL1')}
dev['filter_cavity/device_HV'] = {
        'driver':send_args(MDT639B, DEVICE_SETTINGS['filter_cavity/device_HV']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('ASRL30')}
    # DAQ drivers
dev['filter_cavity/device_DAQ_Vout_vs_reflect'] = {
        'driver':send_args(AiTask, DEVICE_SETTINGS['filter_cavity/device_DAQ_Vout_vs_reflect']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('DAQ_ai')}

# Initialize all Database Settings --------------------------------------------
'''This checks that all settings (as listed in SETTINGS) exist within the
    databases. Any missing settings are populated with the default values. 
    -If the setting does not exist within a device database that setting is
    propogated to the device, otherwise the local settings are read from the
    device.
    -The settings for '__init__' methods are are not sent or pulled to devices.
    -A local copy of all settings is contained within the local_settings
    dictionary.'''
local_settings = {}
for database in SETTINGS:
    device_db_condition = (database in DEVICE_DBs)
    local_settings[database] = db[database].read_buffer()
# Check all SETTINGS
    db_initialized = True
    settings_list = []
    for setting in SETTINGS[database]:
    # Check that there is anything at all
        if (local_settings[database]==None):
            local_settings[database]={}
    # Check that the key exists in the database
        if not(setting in local_settings[database]):
            db_initialized = False
            local_settings[database][setting] = SETTINGS[database][setting]
            if (device_db_condition and (setting != '__init__')):
                settings_list.append({setting:SETTINGS[database][setting]})
        elif (device_db_condition and (setting != '__init__')):
            settings_list.append({setting:None})
    if device_db_condition:
        update_device_settings(database, settings_list)
    if not(db_initialized):
    # Update the database values if necessary
        db[database].write_record_and_buffer(local_settings[database])

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
                          'new':<bool>}'''
mon = {}
    # SRS -----------------------------
mon['filter_cavity/PID_action'] = {
        'data':np.array([]),
        'device':dev['filter_cavity/device_PID'],
        'new':False}
mon['filter_cavity/PID_output'] = {
        'data':np.array([]),
        'device':dev['filter_cavity/device_PID'],
        'new':False}
mon['filter_cavity/PID_output_limits'] = {
        'data':{'max':local_settings['filter_cavity/device_PID']['upper_output_limit'],
                'min':local_settings['filter_cavity/device_PID']['lower_output_limit']},
        'device':dev['filter_cavity/device_PID'],
        'new':False}
    # HV Piezo ------------------------
mon['filter_cavity/HV_output'] = {
        'data':np.array([]),
        'device':dev['filter_cavity/device_HV'],
        'new':False}
    # DAQ -----------------------------
mon['filter_cavity/DAQ_Vout_vs_reflect'] = {
        'data':np.array([]),
        'device':dev['filter_cavity/device_DAQ_Vout_vs_reflect'],
        'new':False}
    # External ------------------------
for database in R_MONITOR_DBs:
    cursor = db[database].read_buffer(tailable_cursor=True, no_cursor_timeout=True)
    mon[database] = {
            'data':np.array([]),
            'cursor':exhaust_cursor(cursor),
            'new':False}



# %% State and Monitor Functions ==============================================

# Global Variables ------------------------------------------------------------
timer = {}
array = {}
thread = {}

# Do nothing function ---------------------------------------------------------
'''A functional placeholder for cases where nothing should happen.'''
@log.log_this()
def nothing(state_db):
    pass


# Monitor Functions -----------------------------------------------------------
'''This section is for defining the methods needed to monitor the system.'''
array['srs:v_out'] = np.array([])
srs_record_interval = 10 # seconds
timer['srs:record'] = get_lap(srs_record_interval)
def get_srs_data():
# Get lap number
    new_record_lap = get_lap(srs_record_interval)
# Pull data from SRS ----------------------------------
    device_db = 'filter_cavity/device_PID'
    # Wait for queue
    dev[device_db]['queue'].queue_and_wait()
    # Get values --------------------------------
         # Output voltage -------------
    new_v_out = dev[device_db]['driver'].new_output_monitor()
    if new_v_out:
        v_out = dev[device_db]['driver'].output_monitor()
        # Output voltage limits -------
    v_min = dev[device_db]['driver'].lower_limit
    v_max = dev[device_db]['driver'].upper_limit
        # PID action ------------------
    pid_action = dev[device_db]['driver'].pid_action()
    # Remove from queue
    dev[device_db]['queue'].remove()
    # Update buffers and databases ----------
        # Output voltage --------------
    if new_v_out:
        mon['filter_cavity/PID_output']['new'] = True
        mon['filter_cavity/PID_output']['data'] = update_buffer(
                mon['filter_cavity/PID_output']['data'],
                v_out, 500)
            # Write to the buffer
        db['filter_cavity/PID_output'].write_buffer({'V':v_out})
            # Append to the record array
        array['srs:v_out'] = np.append(array['srs:v_out'], v_out)
        if new_record_lap > timer['srs:record']:
            # Record statistics
            db['filter_cavity/PID_output'].write_record({
                    'V':array['srs:v_out'].mean(),
                    'std':array['srs:v_out'].std(),
                    'n':array['srs:v_out'].size})
            # Empty the array
            array['srs:v_out'] = np.array([])
        # Voltage limits ----------
    if (mon['filter_cavity/PID_output_limits']['data'] != {'min':v_min, 'max':v_max}):
        mon['filter_cavity/PID_output_limits']['new'] = True
        mon['filter_cavity/PID_output_limits']['data'] = {'min':v_min, 'max':v_max}
        db['filter_cavity/PID_output_limits'].write_record_and_buffer({'min':v_min, 'max':v_max})
        # PID action --------------
    if (mon['filter_cavity/PID_action']['data'] != pid_action):
        mon['filter_cavity/PID_action']['new'] = True
        mon['filter_cavity/PID_action']['data'] = pid_action
        db['filter_cavity/PID_action'].write_record_and_buffer({'Action':pid_action})
    # Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer['srs:record']:
        timer['srs:record'] = new_record_lap
thread['get_srs_data'] = threading.Thread(target=get_srs_data, daemon=True)

array['hv:v_out'] = np.array([])
hv_record_interval = 10 # seconds
timer['hv:record'] = get_lap(hv_record_interval)
def get_HV_data():
# Get lap number
    new_record_lap = get_lap(hv_record_interval)
# Pull data from Thorlabs 3-axis piezo controller -----
    device_db = 'filter_cavity/device_HV'
    # Wait for queue
    dev[device_db]['queue'].queue_and_wait()
    # Get values
    hv_out = dev[device_db]['driver'].y_voltage()
    # Remove from queue
    dev[device_db]['queue'].remove()
    # Update buffers and databases ----------
    mon['filter_cavity/HV_output']['new'] = True
    mon['filter_cavity/HV_output']['data'] = update_buffer(
            mon['filter_cavity/HV_output']['data'],
            hv_out, 100)
    db['filter_cavity/HV_output'].write_buffer({'V':hv_out})
    # Append to the record array
    array['hv:v_out'] = np.append(array['hv:v_out'], hv_out)
    if new_record_lap > timer['hv:record']:
        # Record statistics
        db['filter_cavity/HV_output'].write_record({
                'V':array['hv:v_out'].mean(),
                'std':array['hv:v_out'].std(),
                'n':array['hv:v_out'].size})
        # Empty the array
        array['hv:v_out'] = np.array([])
    # Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer['hv:record']:
        timer['hv:record'] = new_record_lap
thread['get_HV_data'] = threading.Thread(target=get_HV_data, daemon=True)

control_interval = 0.5 # s
passive_interval = 1.0 # s
timer['monitor:control'] = get_lap(control_interval)
timer['monitor:passive'] = get_lap(passive_interval)
def monitor(state_db):
# Get lap number
    new_control_lap = get_lap(control_interval)
    new_passive_lap = get_lap(passive_interval)
# Update control loop variables -------------------------------------
    if (new_control_lap > timer['monitor:control']):
        if not(thread['get_srs_data'].is_alive()):
        # Start new thread
            thread['get_srs_data'] = threading.Thread(target=get_srs_data, daemon=True)
            thread['get_srs_data'].start()
    # Pull data from external databases -------------------
        new_data = []
        for doc in mon['filter_cavity/DAQ_error_signal']['cursor']:
            new_data.append(doc['V'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            mon['filter_cavity/DAQ_error_signal']['new'] = True
            mon['filter_cavity/DAQ_error_signal']['data'] = update_buffer(
                mon['filter_cavity/DAQ_error_signal']['data'],
                new_data, 500)
    # Propogate lap numbers ---------------------------------------------
        timer['monitor:control'] = new_control_lap
# Update passive monitoring variables -------------------------------
    if (new_passive_lap > timer['monitor:passive']):
        if not(thread['get_HV_data'].is_alive()):
        # Start new thread
            thread['get_HV_data'] = threading.Thread(target=get_HV_data, daemon=True)
            thread['get_HV_data'].start()
    # Pull data from external databases -------------------
        new_data = []
        for doc in mon['filter_cavity/TEC_temperature']['cursor']:
            new_data.append(doc['V'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            mon['filter_cavity/TEC_temperature']['new'] = True
            mon['filter_cavity/TEC_temperature']['data'] = update_buffer(
                mon['filter_cavity/TEC_temperature']['data'],
                new_data, 500)
    # Propogate lap numbers ---------------------------------------------
        timer['monitor:passive'] = new_passive_lap


# Search Functions ------------------------------------------------------------
'''This section is for defining the methods needed to bring the system into
    its defined states.'''
from scipy.interpolate import UnivariateSpline
from scipy.optimize import minimize
v_range_threshold = 0.1 #(limit-threshold)/(upper - lower limits)
log_setpoint_error_interval = 60*10 #s
lock_hold_interval = 1.0 #s
timer['find_lock:locked'] = time.time()
timer['find_lock:log_setpoint_error'] = time.time()
def find_lock(state_db, last_good_position=None):
# Queue the SRS PID controller --------------------------------------
    if thread['get_srs_data'].ident != None:
    # Wait for the monitor thread to complete
        thread['get_srs_data'].join()
    device_db = 'filter_cavity/device_PID'
    dev[device_db]['queue'].queue_and_wait(priority=True)
# Initialize threshold variables ------------------------------------
    v_high = (1-v_range_threshold)*dev[device_db]['driver'].upper_limit + v_range_threshold*dev[device_db]['driver'].lower_limit
    v_low = (1-v_range_threshold)*dev[device_db]['driver'].lower_limit + v_range_threshold*dev[device_db]['driver'].upper_limit
# Quick relock ------------------------------------------------------
    # Re-engage the lock at the last know position --------
    if last_good_position is not None:
        '''This is used to quicklyre-engage the lock starting from a known
        posistion. This is only activated if "last_good_position" is given as a 
        keyword argument to this function call. The state then skips the first
        round of lock tests.'''
        settings_list = [
                {'manual_output':last_good_position},
                {'pid_action':False},
                {'offset_action':True,'offset':last_good_position},
                {'pid_action':True}] # TODO: add delay?
        update_device_settings(device_db, settings_list)
    # Update lock timer -----------------------------------
        timer['find_lock:locked'] = time.time()
        locked = True
# Check if locked ---------------------------------------------------
    elif dev[device_db]['driver'].pid_action():
        '''This is the main logic used to determine if the current state is
        locked. The main check is that the current output is within the
        accepted range between the upper and lower hardware limits.'''
    # PID is enabled
        current_output = dev[device_db]['driver'].output_monitor()
        if (current_output < v_low) or (current_output > v_high):
        # Output is beyond voltage thresholds
            locked = False
        # TODO: elif reflect error signal is high -> locked = False
        else:
        # Lock is holding
            locked = True
    else:
    # PID is disabled
        locked = False
# If locked ---------------------------------------------------------            
    if locked:
        '''If the current state passed the previous tests the control script
        holds off on making a final judgement until the specified interval has
        passed since lock acquisition.'''
    # Remove the SRS PID controller from queue ------------
        dev[device_db]['queue'].remove()
    # Check lock interval ---------------------------------
        if (time.time() - timer['find_lock:locked']) > lock_hold_interval:
            log_str = 'Lock succesful'
            log.log_info(__name__, 'find_lock', log_str)
        # Lock is succesful, update state variable
            current_state[state_db]['compliance'] = True
            db[state_db].write_record_and_buffer(current_state[state_db])
        # Update the monitor variable if necessary
            if (mon['filter_cavity/PID_action']['data'] != True):
                mon['filter_cavity/PID_action']['new'] = True
                mon['filter_cavity/PID_action']['data'] = True
                db['filter_cavity/PID_action'].write_record_and_buffer({'Action':True})
# If unlocked -------------------------------------------------------
    else:
        '''The current state has failed the lock tests. The PID controller is
        then broght into a known state, and the DAQ is used to find the lock
        point.'''
    # Reset the PID controller ----------------------------
        settings_list = [
                {'pid_action':False},
                {'upper_output_limit':STATES[state_db][current_state[state_db]['state']]['settings'][device_db]['upper_output_limit'],
                 'lower_output_limit':STATES[state_db][current_state[state_db]['state']]['settings'][device_db]['lower_output_limit']}]
        update_device_settings(device_db, settings_list)
        settings_list = [
                {'y_min_limit':STATES[state_db][current_state[state_db]['state']]['settings']['filter_cavity/device_HV']['y_min_limit'],
                 'y_max_limit':STATES[state_db][current_state[state_db]['state']]['settings']['filter_cavity/device_HV']['y_max_limit']},
                 {'y_voltage':STATES[state_db][current_state[state_db]['state']]['settings']['filter_cavity/device_HV']['y_voltage']}]
        if thread['get_hv_data'].ident != None:
        # Wait for the monitor thread to complete
            thread['get_hv_data'].join()
        update_device_settings('filter_cavity/device_HV', settings_list)
    # Reinitialize threshold variables --------------------
        v_high = (1-v_range_threshold)*dev[device_db]['driver'].upper_limit + v_range_threshold*dev[device_db]['driver'].lower_limit
        v_low = (1-v_range_threshold)*dev[device_db]['driver'].lower_limit + v_range_threshold*dev[device_db]['driver'].upper_limit
    # Reset the piezo hysteresis --------------------------
        dev[device_db]['driver'].manual_output(v_low)
    # Queue the DAQ ---------------------------------------
        daq_db = 'filter_cavity/device_DAQ_Vout_vs_reflect'
        dev[daq_db]['queue'].queue_and_wait(priority=True)
    # Get lock point data ---------------------------------
        x = np.linspace(v_low, v_high, 200)
        y = np.copy(x)
        w = np.copy(x)
        for ind, x_val in enumerate(x):
        # Touch queue (prevent timeout) ---------
            dev[device_db]['queue'].touch()
            dev[daq_db]['queue'].touch()
        # Change position and trigger DAQ -------
            dev[device_db]['driver'].manual_output(x_val)
            data = dev[daq_db]['driver'].read_point()
            # Average and Std ---------
            y[ind] = np.mean(data)
            w[ind] = 1/np.std(data)
        # Release and remove the DAQ from queue -
        dev[daq_db]['driver'].reserve_point(False)
        dev[daq_db]['queue'].remove()
        # Reset the piezo hysteresis ------------
        dev[device_db]['driver'].manual_output(x[0])
        # Update monitor DB ---------------------
        mon['filter_cavity/DAQ_Vout_vs_reflect']['new'] = True
        mon['filter_cavity/DAQ_Vout_vs_reflect']['data'] = np.array([x, y])
        db['filter_cavity/DAQ_Vout_vs_reflect'].write_record_and_buffer({'V_out':x.tolist(), 'V_ref':y.tolist()})
    # Estimate the lock point -----------------------------
        #Coarse Estimate ------------------------
        min_index = np.argmin(y)
        output_coarse = x[min_index]
        #Fine Estimate --------------------------
        try:
            spline = UnivariateSpline(x, y, w=w)
            min_result = minimize(spline, output_coarse)
            new_output = min_result['x'][0]
        except:
            log.log_exception(__name__, 'find_lock')
            new_output = output_coarse
    # Get Lock --------------------------------------------
        if (new_output > v_low) and (new_output < v_high):
            '''If the new lock point is within the acceptable range between
            the upper and lower hardware limits, attempt to lock.'''
            log_str = 'Estimated voltage setpoint = {:.3f}, locking.'.format(new_output)
            log.log_info(__name__, 'find_lock', log_str)
        # Update deivice settings ---------------
            settings_list = [{'manual_output':new_output,
                              'offset_action':True,
                              'offset':new_output},
                             {'pid_action':True}] #TODO: add delay?
            update_device_settings(device_db, settings_list)
        # Remove the SRS PID controller from queue
            dev[device_db]['queue'].remove()
        # Update lock timer ---------------------
            timer['find_lock:locked'] = time.time()
        else:
            '''If not, something is wrong. This could be that the temperature
            control is not on, the temperature has not settled at the setpoint,
            or the temperature setpoint needs adjustment. Either way, there is
            no method to adjust those parameters'''
            log_setpoint_error_condition = ((time.time() - timer['find_lock:log_setpoint_error']) > log_setpoint_error_interval)
            if log_setpoint_error_condition:
                log_str = 'Estimated voltage setpoint = {:.3f}, lock unobtainable.'.format(new_output)
                log.log_critical(__name__, 'find_lock', log_str)
            # Update timer
                timer['find_lock:log_setpoint_error'] = time.time()

def transfer_to_manual(state_db):
# Queue the SRS PID controller --------------------------------------
    if thread['get_srs_data'].ident != None:
    # Wait for the monitor thread to complete
        thread['get_srs_data'].join()
    device_db = 'filter_cavity/device_PID'
    dev[device_db]['queue'].queue_and_wait()
# Check if the PID controller is on ---------------------------------
    if dev[device_db]['driver'].pid_action():
    # Get current output
        v_out = dev[device_db]['driver'].output_monitor()
    # Bumpless transfer to manual
        settings_list = [
                {'manual_output':v_out},
                {'pid_action':False}]
        update_device_settings(device_db, settings_list)
# Remove SRS PID from queue -----------------------------------------
    dev[device_db]['queue'].remove()
# Update state variable
    current_state[state_db]['compliance'] = True
    db[state_db].write_record_and_buffer(current_state[state_db])

# Maintain Functions ----------------------------------------------------------
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''
v_std_threshold = 5 # standard deviations
lock_age_threshold = 30.0 #s
def keep_lock(state_db):
    locked = True
# Evaluate conditions
    new_output_condition = mon['filter_cavity/PID_output']['new']
    lock_age_condition = ((time.time() - timer['find_lock:locked']) > lock_age_threshold)
    no_new_limits_condition = not(mon['filter_cavity/PID_output_limits']['new'])
# Get most recent values --------------------------------------------
    if new_output_condition:
        current_output = mon['filter_cavity/PID_output']['data'][-1]
    current_limits = mon['filter_cavity/PID_output_limits']['data']
    # Lock threshold
    v_high = (1-v_range_threshold)*current_limits['max'] + v_range_threshold*current_limits['min']
    v_low = (1-v_range_threshold)*current_limits['min'] + v_range_threshold*current_limits['max']
    # Clear 'new' data flags
    mon['filter_cavity/PID_output']['new'] = False
    mon['filter_cavity/PID_output_limits']['new'] = False
# Check if the PID controller is on ---------------------------------
    if (mon['filter_cavity/PID_action']['data'] != True):
    # It is not locked
        locked = False
# Check if the output is outside the acceptable range ---------------
    elif new_output_condition:
        if (current_output < v_low) or (current_output > v_high):
        # It is not locked
            locked = False
    # TODO: check error signal std
# If not locked -----------------------------------------------------
    if not(locked):
    # Update state variable
        current_state[state_db]['compliance'] = False
        db[state_db].write_record_and_buffer(current_state[state_db])
    # Check if quick relock is possible
        if (lock_age_condition and no_new_limits_condition):
        # Calculate the expected output voltage
            data = mon['filter_cavity/PID_output']['data'][:-1]
            v_avg = np.mean(data)
            v_avg_slope = np.mean(np.diff(data))/(len(data)-1)
            v_expected = v_avg + v_avg_slope*len(data)/2
        # Remove the last point from the local monitor
            mon['filter_cavity/PID_output']['data'] = data
        # Attempt a quick relock
            find_lock(state_db, last_good_position=v_expected)
# If locked ---------------------------------------------------------
    else:
    # If the system is at a new lock point, reinitialize the local monitors
        if (not(lock_age_condition) and not(no_new_limits_condition)):
        # Reinitialize the output voltage monitor
            mon['filter_cavity/PID_output']['data'] = np.array([])
            mon['filter_cavity/PID_output']['new'] = False
    # If the system is at a stable lock point, adjust the hardware voltage limits
        elif (lock_age_condition and new_output_condition):
        # Calculate the new limit thresholds
            data = mon['filter_cavity/PID_output']['data']
            v_avg = np.mean(data)
            v_avg_slope = np.mean(np.diff(data))/(len(data)-1)
            v_expected = v_avg + v_avg_slope*len(data)/2
            v_std = np.std(data - v_avg_slope*np.arange(len(data)))
            new_upper_limit = round(v_expected + (v_std_threshold*v_std)/(1-2*v_range_threshold),2)
            new_lower_limit = round(v_expected - (v_std_threshold*v_std)/(1-2*v_range_threshold),2)
            if (new_upper_limit - new_lower_limit) < 0.5: #TODO: determine optimal thresholds
                new_upper_limit = round(v_expected + 0.25,2)
                new_lower_limit = round(v_expected - 0.25,2)
        # Restrict the limits
            device_db = 'filter_cavity/device_PID'
            state_limits = {
                    'upper_output_limit':STATES[state_db][current_state[state_db]['state']]['settings'][device_db]['upper_output_limit'],
                    'lower_output_limit':STATES[state_db][current_state[state_db]['state']]['settings'][device_db]['lower_output_limit']}
            if (new_upper_limit > state_limits['upper_output_limit']):
                new_upper_limit = state_limits['upper_output_limit']
            if (new_lower_limit < state_limits['lower_output_limit']):
                new_lower_limit = state_limits['lower_output_limit']
        # Determine if limits should be updated
            new_v_high = (1-v_range_threshold)*new_upper_limit + v_range_threshold*new_lower_limit
            new_v_low = (1-v_range_threshold)*new_lower_limit + v_range_threshold*new_upper_limit
            update_upper = False
            update_lower = False
            if new_v_high > current_limits['max']:
                update_upper = True
            if new_v_low < current_limits['min']:
                update_lower = True
            if new_upper_limit < v_high:
                update_upper = True
            if new_lower_limit > v_low:
                update_lower = True
            if (new_upper_limit == current_limits['max']):
                update_upper = False
            if (new_lower_limit == current_limits['min']):
                update_lower = False
            if new_upper_limit == new_lower_limit:
                update_upper = False
                update_lower = False
        # Update the hardware limits
            if (update_upper or update_lower):
            # Update the limits
                if not(update_lower):
                    settings_list = {'upper_output_limit':new_upper_limit}
                elif not(update_upper):
                    settings_list = {'lower_output_limit':new_lower_limit}
                else:
                    settings_list = {
                            'upper_output_limit':new_upper_limit,
                            'lower_output_limit':new_lower_limit}
                if thread['get_srs_data'].ident != None:
                # Wait for the monitor thread to complete
                    thread['get_srs_data'].join()
                update_device_settings(device_db, settings_list, write_log=False)
            # Update the voltage limit monitor
                mon['filter_cavity/PID_output_limits']['new'] = True
                mon['filter_cavity/PID_output_limits']['data'] = {'min':new_lower_limit, 'max':new_upper_limit}
                db['filter_cavity/PID_output_limits'].write_record_and_buffer({'min':new_lower_limit, 'max':new_upper_limit})

def lock_disabled(state_db):
    if (mon['filter_cavity/PID_action']['data'] != False):
    # Update state variable
        current_state[state_db]['compliance'] = False
        db[state_db].write_record_and_buffer(current_state[state_db])


# Operate Functions -----------------------------------------------------------
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
                        'value':<desired value>},...],
                    'necessary':[{...},...],
                    'optional':[{...}]}}
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
                the instrument's data collection state is active.'''
STATES = {
        'filter_cavity/state':{
                'lock':{
                        'settings':{
                                'filter_cavity/device_PID':{
                                        'proportional_action':True, 'integral_action':True,
                                        'derivative_action':False,
                                        'proportional_gain':-0.2, 'integral_gain':1.0e2,
                                        'upper_output_limit':2.00, 'lower_output_limit':0.00},
                                'filter_cavity/device_HV':{
                                        'y_min_limit':0.00, 'y_max_limit':150.00, 'y_voltage':99.1}},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor, 'search':find_lock,
                                'maintain':keep_lock, 'operate':nothing}},
                'manual':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor, 'search':transfer_to_manual,
                                'maintain':nothing, 'operate':nothing}},
                'safe':{
                        'settings':{'filter_cavity/device_PID':{'pid_action':False}},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor, 'search':transfer_to_manual,
                                'maintain':lock_disabled, 'operate':nothing}},
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

# %% STATE MACHINE ============================================================

'''The code after this section operates the state machine. This section
    should not require any alteration. Changes to this section changes the
    operation of the state machine logic'''

# Initialize state machine timer ----------------------------------------------
main_loop_interval = 0.5 # seconds
main_loop_timer = get_lap(main_loop_interval)+1

# Initialize failed prereq log timers -----------------------------------------
'''These are set so that the logs do not become cluttered with repetitions of
    the same failure. The timer values are used in the check_prerequisites
    function.'''
log_failed_prereqs_interval = 60*10 #s
log_failed_prereqs_timer = {}
for state_db in STATE_DBs:
    log_failed_prereqs_timer[state_db] = {}
    for state in STATES[state_db]:
        log_failed_prereqs_timer[state_db][state] = {}
        log_failed_prereqs_timer[state_db][state]['critical'] = 0
        log_failed_prereqs_timer[state_db][state]['necessary'] = 0
        log_failed_prereqs_timer[state_db][state]['optional'] = 0
# Run the main loop -----------------------------------------------------------
'''Where the magic happens.'''
loop = True
while loop:
# Get the Current State -------------------------------------------------------
    current_state = {}
    for state_db in STATE_DBs:
        current_state[state_db] = db[state_db].read_buffer()
    
# Check the Critical Prerequisites --------------------------------------------
    for state_db in STATE_DBs:
        critical_pass = check_prereqs(
                state_db,
                current_state[state_db]['state'],
                'critical', log_failures=True)
    # Place into safe state if critical prereqs fail
        if not critical_pass:
            setup_state(state_db, 'safe')

# Monitor the Current State ---------------------------------------------------
    for state_db in STATE_DBs:
        STATES[state_db][current_state[state_db]['state']]['routines']['monitor'](state_db)

# Maintain the Current State --------------------------------------------------
    for state_db in STATE_DBs:
    # If compliant,
        if current_state[state_db]['compliance'] == True:
        # If necessary, check the optional prerequisites
            if current_state[state_db]['prerequisites']['optional'] == False:
                optional_pass = check_prereqs(
                    state_db,
                    current_state[state_db]['state'],
                    'optional')
                if optional_pass == True:
                # Update the state variable
                    current_state[state_db]['prerequisites']['optional'] = optional_pass
                    db[state_db].write_record_and_buffer(current_state[state_db])
        # Maintain compliance
            STATES[state_db][current_state[state_db]['state']]['routines']['maintain'](state_db)
    # If out of compliance, 
        else:
        # Check necessary and optional prerequisites
            necessary_pass = check_prereqs(
                    state_db,
                    current_state[state_db]['state'],
                    'necessary')
            optional_pass = check_prereqs(
                    state_db,
                    current_state[state_db]['state'],
                    'optional')
            necessary_prereq_changed = (current_state[state_db]['prerequisites']['necessary'] != necessary_pass)
            optional_prereq_changed = (current_state[state_db]['prerequisites']['optional'] != optional_pass)
            if (necessary_prereq_changed or optional_prereq_changed):
            # If necessary, update the state variable
                current_state[state_db]['prerequisites']['necessary'] = necessary_pass
                current_state[state_db]['prerequisites']['optional'] = optional_pass
                db[state_db].write_record_and_buffer(current_state[state_db])
        # Search for the compliant state
            if necessary_pass:
                STATES[state_db][current_state[state_db]['state']]['routines']['search'](state_db)
    # Set the state initialization if necessary
        if not(current_state[state_db]['initialized']):
        # Update the state variable
            current_state[state_db]['initialized'] = True
            db[state_db].write_record_and_buffer(current_state[state_db])
    
# Operate the Current State ---------------------------------------------------
    for state_db in STATE_DBs:
    # If compliant,
        if current_state[state_db]['compliance'] == True:
            STATES[state_db][current_state[state_db]['state']]['routines']['operate'](state_db)

# Check the Communications Queue ----------------------------------------------
    for message in range(len(comms.get_queue())):
    # Parse the message
        message = comms.pop()
        parse_message(message)
                        
# Check Desired State ---------------------------------------------------------
    for state_db in STATE_DBs:
        if current_state[state_db]['state'] != current_state[state_db]['desired_state']:
        # Check the prerequisites of the desired states
            critical_pass = check_prereqs(
                    state_db,
                    current_state[state_db]['desired_state'],
                    'critical')
            necessary_pass = check_prereqs(
                    state_db,
                    current_state[state_db]['desired_state'],
                    'necessary')
            optional_pass = check_prereqs(
                    state_db,
                    current_state[state_db]['desired_state'],
                    'optional')
            if critical_pass:
            # Initialize the transition into the desired state
                setup_state(
                        state_db,
                        current_state[state_db]['desired_state'],
                        critical=critical_pass,
                        necessary=necessary_pass,
                        optional=optional_pass)

# Pause -----------------------------------------------------------------------
    pause = (main_loop_timer+1)*main_loop_interval - time.time()
    if pause > 0:
        time.sleep(pause)
        main_loop_timer += 1
    else:
        log_str = "Execution time exceeded the set loop interval {:}s by {:.2g}s".format(main_loop_interval, abs(pause))
        log.log_info(__name__, 'main_loop', log_str)
        main_loop_timer = get_lap(main_loop_interval)+1

