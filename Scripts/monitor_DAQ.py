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
import queue

import os
import sys
sys.path.append(os.getcwd())

from Drivers.Logging import EventLog as log

from Drivers.Database import MongoDB
from Drivers.Database import CouchbaseDB

from Drivers.DAQ.Tasks import AiTask
from Drivers.DAQ.Tasks import DiTask


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
COMMS = 'monitor_DAQ'

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
        'monitor_DAQ/state_analog']#, 'monitor_DAQ/state_digital']
DEVICE_DBs =[
        'monitor_DAQ/device_DAQ_analog_in']#, 'monitor_DAQ/device_DAQ_digital_in']
MONITOR_DBs = [
        # Analog In
        'mll_fR/DAQ_error_signal',
        'filter_cavity/DAQ_error_signal', 'filter_cavity/heater_temperature',
        'ambience/box_temperature_0', 'ambience/box_temperature_1', 'ambience/rack_temperature_0']
        #'dc_power/12V_0', 'dc_power/12V_1', 'dc_power/12V_2', 'dc_power/12V_3',
        #'dc_power/8V_0', 'dc_power/15V_0', 'dc_power/24V_0', 'dc_power/24V_1',
        # Digital In
        #'rf_osc/100MHz_alarm', 'rf_osc/1GHz_alarm', 'rf_osc/10GHz_alarm',
        #'chiller/system_alarm', 'chiller/pump_alarm']
LOG_DB = 'monitor_DAQ/log'
CONTROL_DB = 'monitor_DAQ/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are 
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = []
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
        'monitor_DAQ/state_analog':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'read',
                'initialized':False}}
#        'monitor_DAQ/state_digital':{
#                'state':'engineering',
#                'prerequisites':{
#                        'critical':False,
#                        'necessary':False,
#                        'optional':False},
#                'compliance':False,
#                'desired_state':'read',
#                'initialized':False}}
DEVICE_SETTINGS = {
        # DAQ settings
        'monitor_DAQ/device_DAQ_analog_in':{
                '__init__':[
                    [[{'physical_channel':'Dev1/ai0', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'mll_fR/DAQ_error_signal', V
                      {'physical_channel':'Dev1/ai1', 'terminal_config':'NRSE','min_val':0, 'max_val':2.0}, # 'filter_cavity/DAQ_error_signal', V
                      {'physical_channel':'Dev1/ai2', 'terminal_config':'NRSE','min_val':0, 'max_val':2.0}, # 'filter_cavity/heater_temperature', V_act
                      {'physical_channel':'Dev1/ai3', 'terminal_config':'NRSE','min_val':0, 'max_val':2.0}, # 'filter_cavity/heater_temperature', V_set
                      {'physical_channel':'Dev1/ai4', 'terminal_config':'NRSE','min_val':0, 'max_val':1.0}, # 'ambience/box_temperature_0'
                      {'physical_channel':'Dev1/ai5', 'terminal_config':'NRSE','min_val':0, 'max_val':1.0}, # 'ambience/box_temperature_1'
                      {'physical_channel':'Dev1/ai6', 'terminal_config':'NRSE','min_val':0, 'max_val':1.0}], # 'ambience/rack_temperature_0'
#                      {'physical_channel':'Dev1/ai7', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0},
#                      {'physical_channel':'Dev1/ai8', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'dc_power/12V_0'
#                      {'physical_channel':'Dev1/ai9', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'dc_power/12V_1'
#                      {'physical_channel':'Dev1/ai10', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'dc_power/12V_2'
#                      {'physical_channel':'Dev1/ai11', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'dc_power/12V_3'
#                      {'physical_channel':'Dev1/ai12', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'dc_power/8V_0'
#                      {'physical_channel':'Dev1/ai13', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'dc_power/15V_0'
#                      {'physical_channel':'Dev1/ai14', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}, # 'dc_power/24V_0'
#                      {'physical_channel':'Dev1/ai15', 'terminal_config':'NRSE','min_val':-1.0, 'max_val':1.0}], # 'dc_power/24V_1'
                    250e3, int(250e3*0.2*3)],{'timeout':5.0}],
                'reserve_cont':False, 'reserve_point':False}}
#        'monitor_DAQ/device_DAQ_digital_in':{
#                '__init__':[
#                    [[{'physical_channel':'Dev1/port0/line0'}, # 'rf_osc/100MHz_alarm'
#                      {'physical_channel':'Dev1/port0/line1'}, # 'rf_osc/1GHz_alarm'
#                      {'physical_channel':'Dev1/port0/line2'}, # 'rf_osc/10GHz_alarm'
#                      {'physical_channel':'Dev1/port0/line3'}, # 'chiller/system_alarm'
#                      {'physical_channel':'Dev1/port0/line4'}]], # 'chiller/pump_alarm'
#                      {'timeout':5.0}],
#                'reserve_cont':False, 'reserve_point':False}}
CONTROL_PARAMS = {
        'monitor_DAQ/control':{ }}
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
    # DAQ drivers
dev['monitor_DAQ/device_DAQ_analog_in'] = {
        'driver':send_args(AiTask, DEVICE_SETTINGS['monitor_DAQ/device_DAQ_analog_in']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('DAQ_ai')}
#dev['monitor_DAQ/device_DAQ_digital_in'] = {
#        'driver':send_args(AiTask, DEVICE_SETTINGS['monitor_DAQ/device_DAQ_digital_in']['__init__']),
#        'queue':CouchbaseDB.PriorityQueue('<daq type and/or channels>')}

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
#        # Digital In
#        'rf_osc/100MHz_alarm', 'rf_osc/1GHz_alarm', 'rf_osc/10GHz_alarm',
#        'chiller/system_alarm', 'chiller/pump_alarm'
    # DAQ analog ----------------------
mon['mll_fR/DAQ_error_signal'] = {
        'data':np.array([]),
        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
        'new':False}
mon['filter_cavity/DAQ_error_signal'] = {
        'data':np.array([]),
        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
        'new':False}
mon['filter_cavity/heater_temperature'] = {
        'data':np.array([]),
        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
        'new':False}
mon['ambience/box_temperature_0'] = {
        'data':np.array([]),
        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
        'new':False}
mon['ambience/box_temperature_1'] = {
        'data':np.array([]),
        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
        'new':False}
mon['ambience/rack_temperature_0'] = {
        'data':np.array([]),
        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
        'new':False}
#mon['dc_power/12V_0'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
#mon['dc_power/12V_1'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
#mon['dc_power/12V_2'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
#mon['dc_power/12V_3'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
#mon['dc_power/8V_0'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
#mon['dc_power/15V_0'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
#mon['dc_power/24V_0'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
#mon['dc_power/24V_1'] = {
#        'data':np.array([]),
#        'device':dev['monitor_DAQ/device_DAQ_analog_in'],
#        'new':False}
    # External ------------------------
for database in R_MONITOR_DBs:
    cursor = db[database].read_buffer(tailable_cursor=True, no_cursor_timeout=True)
    mon[database] = {
            'data':np.array([]),
            'cursor':exhaust_cursor(cursor),
            'new':False}

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


# %% State and Monitor Functions ==============================================

# Global Variables ------------------------------------------------------------
timer = {}
array = {}
thread = {}
fifo_q = {}
for state_db in STATE_DBs:
    timer[state_db] = {}


# Do nothing function ---------------------------------------------------------
'''A functional placeholder for cases where nothing should happen.'''
@log.log_this()
def nothing(state_db):
    pass


# Monitor Functions -----------------------------------------------------------
'''This section is for defining the methods needed to monitor the system.'''


# Search Functions ------------------------------------------------------------
'''This section is for defining the methods needed to bring the system into
    its defined states.'''
def queue_and_reserve(state_db):
# add to queue, loop until the top of the queue (no touch). When queued, reserve cont.
    # have a switch for each state_db, either analog in or diggital in
    if (state_db == 'monitor_DAQ/state_analog'):
        device_db ='monitor_DAQ/device_DAQ_analog_in'
        queue_position = dev[device_db]['queue'].position()
        if (queue_position < 0):
            queue_size = len(dev[device_db]['queue'].get_queue())
        # Add to queue
            dev[device_db]['queue'].push()
        elif (queue_position == 0):
            queue_size = len(dev[device_db]['queue'].get_queue())
            if (queue_size == 1):
            # Reserve and start the DAQ
                dev[device_db]['driver'].reserve_cont(True)
            # Update the state variable
                current_state[state_db]['compliance'] = True
                db[state_db].write_record_and_buffer(current_state[state_db])
            else:
            # Start over if something else is in the queue
                dev[device_db]['queue'].remove()


# Maintain Functions ----------------------------------------------------------
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''
touch_interval = 1 # second
for state_db in STATE_DBs:
    timer[state_db]['touch'] = get_lap(touch_interval)
def touch(state_db):
    if (state_db == 'monitor_DAQ/state_analog'):
        device_db ='monitor_DAQ/device_DAQ_analog_in'
        queue_size = len(dev[device_db]['queue'].get_queue())
        if (queue_size != 1):
        # Other scripts want to use the DAQ
        # Unreserve and dequeue DAQ
            dev[device_db]['driver'].reserve_cont(False)
            dev[device_db]['queue'].remove()
        # Update state variable
            current_state[state_db]['compliance'] = False
            db[state_db].write_record_and_buffer(current_state[state_db])
        elif not(dev[device_db]['driver'].reserve_cont()):
        # Continuous auisition has not been reserved
        # Dequeue
            dev[device_db]['queue'].remove()
        # Update state variable
            current_state[state_db]['compliance'] = False
            db[state_db].write_record_and_buffer(current_state[state_db])
        else:
        # Touch queue (prevent timeout)
            touch_lap = get_lap(touch_interval)
            if touch_lap > timer[state_db]['touch']:
                timer[state_db]['touch'] = touch_lap
                dev[device_db]['queue'].touch()


# Operate Functions -----------------------------------------------------------
'''This section is for defining the methods called only when the system is in
    its defined states.'''
def queue_worker(queue_name):
    loop = True
    while loop:
        try:
            item = fifo_q[queue_name].get(block=False)
        except queue.Empty:
            loop = False
        else:
            item.start()
            item.join()
            fifo_q[queue_name].task_done()
fifo_q['daq:ai_buffer'] = queue.Queue()
thread['daq:ai_buffer'] = threading.Thread(target=queue_worker, args=['daq:ai_buffer'], daemon=True)
fifo_q['daq:ai_record'] = queue.Queue()
thread['daq:ai_record'] = threading.Thread(target=queue_worker, args=['daq:ai_record'], daemon=True)

def buffer_ai(monitor_db, data_mean, data_std, data_n, timestamp, channel_identifiers=None):
    if (channel_identifiers == None):
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = update_buffer(
                mon[monitor_db]['data'],
                data_mean, 500)
        db[monitor_db].write_buffer({'V':data_mean, 'std':data_std, 'n':data_n}, timestamp=timestamp)
    elif (type(channel_identifiers) == list):
        data_buffer = {}
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = update_buffer(
                mon[monitor_db]['data'],
                data_mean, 500*len(channel_identifiers))
        for ind, name in enumerate(channel_identifiers):
            data_buffer[name+'_V'] = data_mean[ind]
            data_buffer[name+'_std'] = data_std[ind]
            data_buffer[name+'_n'] = data_n
        db[monitor_db].write_buffer(data_buffer, timestamp=timestamp)

array['daq:ai0'] = np.array([])
array['daq:ai1'] = np.array([])
array['daq:ai2'] = np.array([])
array['daq:ai3'] = np.array([])
array['daq:ai4'] = np.array([])
array['daq:ai5'] = np.array([])
array['daq:ai6'] = np.array([])
daq_record_interval = 10 # seconds
timer['daq:record_ai'] = get_lap(daq_record_interval)
def record_ai(monitor_db, data, timestamp, write_record, array_identifier, channel_identifiers=None):
    if (channel_identifiers == None):
        # Append to record array ----------------
        array[array_identifier] = np.append(array[array_identifier], data)
        if write_record:
            if (array[array_identifier].size > 0):
        # Record statistics ---------------------
                db[monitor_db].write_record({
                        'V':array[array_identifier].mean(),
                        'std':array[array_identifier].std(),
                        'n':array[array_identifier].size}, timestamp=timestamp)
        # Empty the array -----------------------
                array[array_identifier] = np.array([])
    else:
        # Append to record arrays ---------------
        array_size = []
        for ind, name in enumerate(channel_identifiers):
            array[array_identifier[ind]] = np.append(array[array_identifier[ind]], data[ind])
            array_size.append(array[array_identifier[ind]].size)
        if write_record:
            data_record = {}
            if (np.product(array_size) > 0):
        # Record statistics ---------------------
                for ind, name in enumerate(channel_identifiers):
                    data_record[name+'_V'] = array[array_identifier[ind]].mean()
                    data_record[name+'_std'] = array[array_identifier[ind]].std()
                    data_record[name+'_n'] = array[array_identifier[ind]].size
                db[monitor_db].write_record(data_record, timestamp=timestamp)
        # Empty the arrays ----------------------
                for ind, name in enumerate(channel_identifiers):
                    array[array_identifier[ind]] = np.array([])

control_interval = 0.2 # s
for state_db in STATE_DBs:
    timer[state_db]['data'] = get_lap(control_interval)
def read_ai_DAQ(state_db):
# Get lap number
    new_control_lap = get_lap(control_interval)
    new_record_lap = get_lap(daq_record_interval)
# Read DAQ ----------------------------------------------------------
    if (new_control_lap > timer[state_db]['data']):
        device_db = 'monitor_DAQ/device_DAQ_analog_in'
    # Double check queue
        dev[device_db]['queue'].queue_and_wait()
    # Get values
        multi_channel_reading = np.array(dev[device_db]['driver'].read_cont())
        timestamp=datetime.datetime.utcnow()
        sample_size = multi_channel_reading.size
        if sample_size > 0:
            multi_channel_mean = multi_channel_reading.mean(axis=1)
            multi_channel_std = multi_channel_reading.std(axis=1)
            multi_channel_n = multi_channel_reading.shape[1]
        # Update buffers and databases -----------------------------
            write_record = (new_record_lap > timer['daq:record_ai'])
        # ai0, 'mll_fR/DAQ_error_signal' ----------------------
            channel = 'daq:ai0'
            monitor_db = 'mll_fR/DAQ_error_signal'
            channel_index = 0 # ai0
            data = multi_channel_reading[channel_index]
            # Update buffer
            args = [monitor_db, multi_channel_mean[channel_index],
                    multi_channel_std[channel_index], multi_channel_n,
                    timestamp]
            item = threading.Thread(target=buffer_ai, args=args, daemon=True)
            fifo_q['daq:ai_buffer'].put(item, block=False)
            # Update record
            args = [monitor_db, data, timestamp, write_record, channel]
            item = threading.Thread(target=record_ai, args=args, daemon=True)
            fifo_q['daq:ai_record'].put(item, block=False)
        # ai1, 'filter_cavity/DAQ_error_signal' ---------------
            channel = 'daq:ai1'
            monitor_db = 'filter_cavity/DAQ_error_signal'
            channel_index = 1 # ai1
            data = multi_channel_reading[channel_index]
            # Update buffer
            args = [monitor_db, multi_channel_mean[channel_index],
                    multi_channel_std[channel_index], multi_channel_n,
                    timestamp]
            item = threading.Thread(target=buffer_ai, args=args, daemon=True)
            fifo_q['daq:ai_buffer'].put(item, block=False)
            # Update record
            args = [monitor_db, data, timestamp, write_record, channel]
            item = threading.Thread(target=record_ai, args=args, daemon=True)
            fifo_q['daq:ai_record'].put(item, block=False)
        # ai2, V_set, 'filter_cavity/heater_temperature' ------
        # ai3, V_act, 'filter_cavity/heater_temperature' ------
            channel_set = 'daq:ai2'
            channel_act = 'daq:ai3'
            channels = [channel_set, channel_act]
            monitor_db = 'filter_cavity/heater_temperature'
            channel_index_set = 2 # ai2
            channel_index_act = 3 # ai3
            channel_indicies = [channel_index_set, channel_index_act]
            data = multi_channel_reading[channel_indicies]
            # Update buffer
            args = [monitor_db, multi_channel_mean[channel_indicies],
                    multi_channel_std[channel_indicies], multi_channel_n,
                    timestamp]
            kwargs = {'channel_identifiers':['set', 'act']}
            item = threading.Thread(target=buffer_ai, args=args, kwargs=kwargs, daemon=True)
            fifo_q['daq:ai_buffer'].put(item, block=False)
            # Update record
            args = [monitor_db, data, timestamp, write_record, channels]
            kwargs = {'channel_identifiers':['set', 'act']}
            item = threading.Thread(target=record_ai, args=args, kwargs=kwargs, daemon=True)
            fifo_q['daq:ai_record'].put(item, block=False)
        # ai4, 'ambience/box_temperature_0' -------------------
            channel = 'daq:ai4'
            monitor_db = 'ambience/box_temperature_0'
            channel_index = 4 # ai4
            data = multi_channel_reading[channel_index]
            # Update buffer
            args = [monitor_db, multi_channel_mean[channel_index],
                    multi_channel_std[channel_index], multi_channel_n,
                    timestamp]
            item = threading.Thread(target=buffer_ai, args=args, daemon=True)
            fifo_q['daq:ai_buffer'].put(item, block=False)
            # Update record
            args = [monitor_db, data, timestamp, write_record, channel]
            item = threading.Thread(target=record_ai, args=args, daemon=True)
            fifo_q['daq:ai_record'].put(item, block=False)
        # ai5, 'ambience/box_temperature_1' -------------------
            channel = 'daq:ai5'
            monitor_db = 'ambience/box_temperature_1'
            channel_index = 5 # ai5
            data = multi_channel_reading[channel_index]
            # Update buffer
            args = [monitor_db, multi_channel_mean[channel_index],
                    multi_channel_std[channel_index], multi_channel_n,
                    timestamp]
            item = threading.Thread(target=buffer_ai, args=args, daemon=True)
            fifo_q['daq:ai_buffer'].put(item, block=False)
            # Update record
            args = [monitor_db, data, timestamp, write_record, channel]
            item = threading.Thread(target=record_ai, args=args, daemon=True)
            fifo_q['daq:ai_record'].put(item, block=False)
        # ai6, 'ambience/rack_temperature_0' ------------------
            channel = 'daq:ai6'
            monitor_db = 'ambience/rack_temperature_0'
            channel_index = 6 # ai6
            data = multi_channel_reading[channel_index]
            # Update buffer
            args = [monitor_db, multi_channel_mean[channel_index],
                    multi_channel_std[channel_index], multi_channel_n,
                    timestamp]
            item = threading.Thread(target=buffer_ai, args=args, daemon=True)
            fifo_q['daq:ai_buffer'].put(item, block=False)
            # Update record
            args = [monitor_db, data, timestamp, write_record, channel]
            item = threading.Thread(target=record_ai, args=args, daemon=True)
            fifo_q['daq:ai_record'].put(item, block=False)
        # Check threads ---------------------------------------------
            if not(thread['daq:ai_buffer'].is_alive()):
            # Start new thread
                thread['daq:ai_record'] = threading.Thread(target=queue_worker, args=['daq:ai_record'], daemon=True)
                thread['daq:ai_record'].start()
            if not(thread['daq:ai_record'].is_alive()):
            # Start new thread
                thread['daq:ai_record'] = threading.Thread(target=queue_worker, args=['daq:ai_record'], daemon=True)
                thread['daq:ai_record'].start()
        # Propogate lap numbers -------------------------------------
            if write_record:
                timer['daq:record_ai'] = new_record_lap
    # Propogate lap numbers -----------------------------------------
        timer[state_db]['data'] = new_control_lap
        


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
        'monitor_DAQ/state_analog':{
                'read':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':nothing, 'search':queue_and_reserve,
                                'maintain':touch, 'operate':read_ai_DAQ}},
                'safe':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':nothing, 'search':nothing,
                                'maintain':nothing, 'operate':nothing}},
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
main_loop_interval = 0.2 # seconds
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


