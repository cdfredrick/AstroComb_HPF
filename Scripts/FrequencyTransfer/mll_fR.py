# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:51:36 2017

@author: Connor
"""

# %% Import Moduless ==========================================================

import numpy as np
import time
import logging

from Drivers.Logging import EventLog as log

from Drivers.Database import MongoDB
from Drivers.Database import CouchbaseDB

from Drivers.VISA.SRS import SIM960
from Drivers.VISA.ILXLightwave import TECModule
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
def update_device_settings(device_db, settings_list):
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
            args = obj
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
            args = obj
            kwargs = {}
    else:
    # Check if no input
        if obj == None:
            args = []
            kwargs = {}
        else:
            args = obj
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
COMMS = 'mll_fR'

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
            compliance. In general, data for use in control loops should have
            an updated value every 0.2 seconds. Data for passive monitoring
            should have a relaxed 1.0 second or longer update period.
        log:
            -This should be a single database that serves as the repository of
            all logs generated by this script.
        control:
            -This should be a single database that contains all control loop 
            variables accessible to commands from the comms queue.'''
STATE_DBs = [
    'mll_fR/state']
DEVICE_DBs =[
    'mll_fR/device_TEC', 'mll_fR/device_PID',
    'mll_fR/device_HV', 'mll_fR/device_DAQ_error_frequency']
MONITOR_DBs = [
    'mll_fR/TEC_temperature', 'mll_fR/TEC_current', 'mll_fR/PID_voltage',
    'mll_fR/PID_voltage_limits', 'mll_fR/HV_output', 'mll_fR/DAQ_error_frequency',
    'mll_fR/TEC_event_status']
LOG_DB = 'mll_fR/log'
CONTROL_DB = 'mll_fR/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are 
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = ['mll_fR/DAQ_error_signal']
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
        'mll_fR/state':{
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
        'mll_fR/device_TEC':{
                '__init__':[['visa address', 'channel']],
                'tec_off_triggers':None, 'tec_gain':100, 
                'tec_current_limit':0.400, 'tec_temperature_limit':45.0, 'tec_mode':'R',
                'tec_output':True, 'tec_resistance_setpoint':None},
        'mll_fR/device_PID':{
                '__init__':[['visa address', 'port']],
                'proportional_action':True, 'integral_action':True,
                'derivative_action':False, 'offset_action':None, 'offset':None,
                'proportional_gain':-3.0e0, 'integral_gain':5.0e2, 'pid_action':None,
                'external_setpoint_action':False, 'internal_setpoint':0.000,
                'ramp_action':False, 'manual_output':None, 'upper_output_limit':8.00,
                'lower_output_limit':0.00, 'power_line_frequency':60},
        'mll_fR/device_HV':{
                '__init__':'<visa address>', 'master_scan_action':False,
                'x_min':0.00, 'x_max':60.00, 'x_voltage':0.00},
        # DAQ settings
        'mll_fR/device_DAQ_error_frequency':{
                '__init__':[
                    [[{'physical_channel':'Dev1/ai0', 'terminal_config':'NRSE',
                       'min_val':-1.0, 'max_val':1.0}],
                        100e3, int(100e3*0.1)],{'timeout':5.0}],
                'reserve_cont':False, 'reserve_point':False}}
CONTROL_PARAMS = {
        'mll_fR/control':{ }}
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
log.start_logging(logger_level=logging.DEBUG) #database=db[LOG_DB])

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
dev['mll_fR/device_TEC'] = {
        'driver':send_args(TECModule, DEVICE_SETTINGS['mll_fR/device_TEC']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('<visa address>')}
dev['mll_fR/device_PID'] = {
        'driver':send_args(SIM960, DEVICE_SETTINGS['mll_fR/device_PID']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('<visa address>')}
dev['mll_fR/device_HV'] = {
        'driver':send_args(MDT639B, DEVICE_SETTINGS['mll_fR/device_HV']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('<visa address>')}
    # DAQ drivers
dev['mll_fR/device_DAQ_error_frequency'] = {
        'driver':send_args(AiTask, DEVICE_SETTINGS['mll_fR/device_DAQ_error_frequency']['__init__']),
        'queue':CouchbaseDB.PriorityQueue('<daq type and/or channels>')}

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
    # ILX -----------------------------
mon['mll_fR/TEC_temperature'] = {
        'data':np.array([]),
        'device':dev['mll_fR/device_TEC'],
        'new':False}
mon['mll_fR/TEC_current'] = {
        'data':np.array([]),
        'device':dev['mll_fR/device_TEC'],
        'new':False}
mon['mll_fR/TEC_event_status'] = {
        'data':np.array([]),
        'device':dev['mll_fR/device_TEC'],
        'new':False}
    # SRS -----------------------------
mon['mll_fR/PID_voltage'] = {
        'data':np.array([]),
        'device':dev['mll_fR/device_PID'],
        'new':False}
mon['mll_fR/PID_voltage_limits'] = {
        'data':np.array([]),
        'device':dev['mll_fR/device_PID'],
        'new':False}
    # HV Piezo ------------------------
mon['mll_fR/HV_output'] = {
        'data':np.array([]),
        'device':dev['mll_fR/device_HV'],
        'new':False}
    # DAQ -----------------------------
mon['mll_fR/DAQ_error_frequency'] = {
        'data':np.array([]),
        'device':dev['mll_fR/device_DAQ_error_frequency'],
        'new':False}
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

# Global Timing Variable ------------------------------------------------------
timer = {}

# Do nothing function ---------------------------------------------------------
'''A functional placeholder for cases where nothing should happen.'''
@log.log_this()
def nothing(state_db):
    pass

# Monitor Functions -----------------------------------------------------------
'''This section is for defining the methods needed to monitor the system.'''
control_interval = 0.2 # s
passive_interval = 1.0 # s
timer['monitor:control'] = get_lap(control_interval)
timer['monitor:passive'] = get_lap(passive_interval)
def monitor(state_db):
# Get lap number
    new_control_lap = get_lap(control_interval)
    new_passive_lap = get_lap(passive_interval)
# Update control loop variables -------------------------------------
    if (new_control_lap > timer['monitor:control']):
    # Pull data from SRS ----------------------------------
        device_db = 'mll_fR/device_PID'
        # Wait for queue
        dev[device_db]['queue'].queue_and_wait()
        # Get values
        new_v_out = dev[device_db]['driver'].new_output_monitor()
        if new_v_out:
            v_out = dev[device_db]['driver'].output_monitor()
        v_min = dev[device_db]['driver'].lower_limit
        v_max = dev[device_db]['driver'].upper_limit
        # Remove from queue
        dev[device_db]['queue'].remove()
        # Update buffers and databases ----------
            # Output voltage ----------
        if new_v_out:
            mon['mll_fR/PID_voltage']['new'] = True
            mon['mll_fR/PID_voltage']['data'] = update_buffer(
                    mon['mll_fR/PID_voltage']['data'],
                    v_out, 500)
            db['mll_fR/PID_voltage'].write_record_and_buffer({'V':v_out})
            # Voltage limits ----------
        if (mon['mll_fR/PID_voltage_limits']['data'] != {'min':v_min, 'max':v_max}):
            mon['mll_fR/PID_voltage_limits']['new'] = True
            mon['mll_fR/PID_voltage_limits']['data'] = {'min':v_min, 'max':v_max}
            db['mll_fR/PID_voltage_limits'].write_record_and_buffer({'min':v_min, 'max':v_max})
    # Pull data from external databases -------------------
        new_data = []
        for doc in mon['mll_fR/DAQ_error_signal']['cursor']:
            new_data.append(doc['std'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            mon['mll_fR/DAQ_error_signal']['new'] = True
            mon['mll_fR/DAQ_error_signal']['data'] = update_buffer(
                mon['mll_fR/DAQ_error_signal']['data'],
                new_data, 500)
# Update passive monitoring variables -------------------------------
    if (new_passive_lap > timer['monitor:passive']):
    # Pull data from ILX Lightwave ------------------------
        device_db = 'mll_fR/device_TEC'
        # Wait for queue
        dev[device_db]['queue'].queue_and_wait()
        # Get values
        tec_temp = dev[device_db]['driver'].tec_resistance()
        tec_curr = dev[device_db]['driver'].tec_current()
        tec_events = dev[device_db]['driver'].tec_events()
        # Remove from queue
        dev[device_db]['queue'].remove()
        # Update buffers and databases -----------
            # TEC temp ----------------
        mon['mll_fR/TEC_temperature']['new'] = True
        mon['mll_fR/TEC_temperature']['data'] = update_buffer(
                mon['mll_fR/TEC_temperature']['data'],
                tec_temp, 100)
        db['mll_fR/TEC_temperature'].write_record_and_buffer({'kOhm':tec_temp})
            # TEC current -------------
        mon['mll_fR/TEC_current']['new'] = True
        mon['mll_fR/TEC_current']['data'] = update_buffer(
                mon['mll_fR/TEC_current']['data'],
                tec_curr, 100)
        db['mll_fR/TEC_current'].write_record_and_buffer({'A':tec_curr})
            # TEC Events --------------
        if (mon['mll_fR/TEC_event_status']['data'] != tec_events):
            mon['mll_fR/TEC_event_status']['new'] = True
            mon['mll_fR/TEC_event_status']['data'] = tec_events
            db['mll_fR/TEC_event_status'].write_record_and_buffer({'events':tec_events})
    # Pull data from Thorlabs 3-axis piezo controller -----
        device_db = 'mll_fR/device_HV'
        # Wait for queue
        dev[device_db]['queue'].queue_and_wait()
        # Get values
        hv_out = dev[device_db]['driver'].x_voltage()
        # Remove from queue
        dev[device_db]['queue'].remove()
        # Update buffers and databases ----------
        mon['mll_fR/HV_output']['new'] = True
        mon['mll_fR/HV_output']['data'] = update_buffer(
                mon['mll_fR/HV_output']['data'],
                hv_out, 300)
        db['mll_fR/HV_output'].write_record_and_buffer({'V':hv_out})
# Propogate lap numbers ---------------------------------------------
    timer['monitor:control'] = new_control_lap
    timer['monitor:passive'] = new_passive_lap

# Search Functions ------------------------------------------------------------
'''This section is for defining the methods needed to bring the system into
    its defined states.'''
from scipy.optimize import curve_fit
v_range_threshold = 0.1 #(limit-threshold)/(upper - lower limits)
t_setpoint_threshold = 0.02 #kOhm
tec_adjust_interval = 0.5 #s
lock_hold_interval = 1.0 #s
timer['find_lock:locked'] = time.time()
timer['find_lock:tec_adjust'] = time.time()
def find_lock(state_db, last_good_position=None):
# Queue the SRS PID controller --------------------------------------
    device_db = 'mll_fR/device_PID'
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
        # TODO: elif rms error signal is high -> locked = False
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
    # Reinitialize threshold variables --------------------
        v_high = (1-v_range_threshold)*dev[device_db]['driver'].upper_limit + v_range_threshold*dev[device_db]['driver'].lower_limit
        v_low = (1-v_range_threshold)*dev[device_db]['driver'].lower_limit + v_range_threshold*dev[device_db]['driver'].upper_limit
    # Reset the piezo hysteresis --------------------------
        dev[device_db]['driver'].manual_output(v_low)
    # Queue the DAQ ---------------------------------------
        daq_db = 'mll_fR/DAQ_error_frequency'
        dev[daq_db]['queue'].queue_and_wait(priority=True)
    # Get lock point data ---------------------------------
        to_fit = lambda v, v0, s: s*np.abs(v-v0)
        x = np.linspace(v_low, v_high, 5)
        y = np.copy(x)
        for ind, x_val in enumerate(x):
        # Touch queue (prevent timeout) ---------
            dev[device_db]['queue'].touch()
            dev[daq_db]['queue'].touch()
        # Change position and trigger DAQ -------
            dev[device_db]['driver'].manual_output(x_val)
            data = dev[daq_db]['driver'].read_point()
            # Find peak frequency -----
            han_win = np.hanning(dev[daq_db]['driver'].buffer_size)
            freqs = dev[daq_db]['driver'].rate*np.fft.rfftfreq(dev[daq_db]['driver'].buffer_size)
            amps = np.abs(np.fft.rfft(han_win*data))
            peak_ind = np.argmax(amps)
            y[ind] = freqs[peak_ind]
        # Release and remove the DAQ from queue -
        dev[daq_db]['driver'].reserve_point(False)
        dev[daq_db]['queue'].remove()
        # Reset the piezo hysteresis ------------
        dev[device_db]['driver'].manual_output(x[0])
        # Update monitor DB ---------------------
        mon['mll_fR/DAQ_error_frequency']['new'] = True
        mon['mll_fR/DAQ_error_frequency']['data'] = np.array([x, y])
        db['mll_fR/DAQ_error_frequency'].write_record_and_buffer({'V':x.tolist(), 'Hz':y.tolist()})
    # Estimate the lock point -----------------------------
        #Coarse Estimate ------------------------
        slopes = np.diff(y)/np.diff(x)
        slope_ind = np.argmax(np.abs(slopes))
        output_coarse = -y[slope_ind]/slopes[slope_ind] + x[slope_ind]
        slope_coarse = np.abs(slopes[slope_ind])
        #Fine Estimate --------------------------
        try:
            new_output = curve_fit(to_fit, x, y, [output_coarse, slope_coarse])[0][0]
        except:
            log.log_exception(__name__, 'find_lock')
            # Failure may be because the frequency response was too flat?
            # The middle is a safe place to go (no TEC adjustment)
            new_output = dev[device_db]['driver'].center
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
            '''If not, try to determine why. This could be that the temperature
            control is not on, the temperature has not settled at the setpoint,
            or the temperature setpoint needs adjustment.'''
        # Remove the SRS PID controller from queue
            dev[device_db]['queue'].remove()
        # Queue the ILX TEC controller ----------
            device_db = 'mll_fR/device_TEC'
            dev[device_db]['queue'].queue_and_wait(priority=True)
        # Check TEC settings --------------------
            if dev[device_db]['driver'].tec_output():
            # If TEC is on ------------
                t_setpoint = dev[device_db]['driver'].tec_resistance_setpoint()
                t_meas = dev[device_db]['driver'].tec_resistance()
                setpoint_condition = (abs(t_setpoint - t_meas) < t_setpoint_threshold)
                adjustment_interval_condition = ((time.time()-timer['find_lock:tec_adjust']) > tec_adjust_interval)
                if (setpoint_condition and adjustment_interval_condition):
                # Adjust timer
                    timer['find_lock:tec_adjust'] = timer.time()
                # Adjust the setpoint
                    if (new_output < dev[device_db]['driver'].center):
                        log_str = 'Estimated voltage setpoint = {:.3f}, raising the resistance setpoint'.format(new_output)
                        log.log_info(__name__, 'find_lock', log_str)
                    # Raise the resistance setpoint
                        dev[device_db]['driver'].tec_step(+1)
                    elif new_output > dev[device_db]['driver'].center:
                        log_str = 'Estimated voltage setpoint = {:.3f}, lowering the resistance setpoint.'.format(new_output)
                        log.log_info(__name__, 'find_lock', log_str)
                    # Lower the resistance setpoint
                        dev[device_db]['driver'].tec_step(-1)
                else:
                # TEC has not settled, wait
                    log_str = 'Estimated voltage setpoint = {:.3f}, but TEC has not yet settled'.format(new_output)
                    log.log_debug(__name__, 'find_lock', log_str)
            else:
            # TEC output is off, renable
                update_device_settings(device_db, [{'tec_mode':'R'}, {'tec_output':True}])
        # Remove the ILX TEC controller from queue ------------
            dev[device_db]['queue'].remove()

def transfer_to_manual(state_db):
# Queue the SRS PID controller --------------------------------------
    device_db = 'mll_fR/device_PID'
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
lock_age_threshold = 10.0 #s
def keep_lock(state_db):
    locked = True
# Queue the SRS PID controller --------------------------------------
    device_db = 'mll_fR/device_PID'
    dev[device_db]['queue'].queue_and_wait()
# Evaluate conditions
    new_output_condition = mon['mll_fR/PID_voltage']['new']
    lock_age_condition = ((time.time() - timer['find_lock:locked']) > lock_age_threshold)
    no_new_limits_condition = not(mon['mll_fR/PID_voltage_limits']['new'])
# Get most recent values --------------------------------------------
    if new_output_condition:
        current_output = mon['mll_fR/PID_voltage']['data'][-1]
    current_limits = mon['mll_fR/PID_voltage_limits']['data']
    v_high = (1-v_range_threshold)*current_limits['max'] + v_range_threshold*current_limits['min']
    v_low = (1-v_range_threshold)*current_limits['min'] + v_range_threshold*current_limits['max']
    state_limits = {
            'upper_output_limit':STATES[state_db][current_state[state_db]['state']]['settings'][device_db]['upper_output_limit'],
            'lower_output_limit':STATES[state_db][current_state[state_db]['state']]['settings'][device_db]['lower_output_limit']}
# Clear 'new' data flags
    mon['mll_fR/PID_voltage']['new'] = False
    mon['mll_fR/PID_voltage_limits']['new'] = False
# Check if the PID controller is on ---------------------------------
    if not(dev[device_db]['driver'].pid_action()):
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
    # Remove SRS PID controller from queue
        dev[device_db]['queue'].remove()
    # Update state variable
        current_state[state_db]['compliance'] = False
        db[state_db].write_record_and_buffer(current_state[state_db])
    # Check if quick relock is possible
        if (lock_age_condition and no_new_limits_condition):
        # Calculate the expected output voltage
            data = mon['mll_fR/PID_voltage']['data'][:-1]
            v_avg = np.mean(data)
            v_avg_slope = np.mean(np.diff(data))/(len(data)-1)
            v_expected = v_avg + v_avg_slope*len(data)/2
        # Remove the last point from the local monitor
            mon['mll_fR/PID_voltage']['data'] = data
        # Attempt a quick relock
            find_lock(state_db, last_good_position=v_expected)
# If locked ---------------------------------------------------------
    else:
    # If the system is at a new lock point, reinitialize the local monitors
        if (not(lock_age_condition) and not(no_new_limits_condition)):
        # Remove SRS PID controller from queue
            dev[device_db]['queue'].remove()
        # Reinitialize the output voltage monitor
            mon['mll_fR/PID_voltage']['data'] = np.array([])
            mon['mll_fR/PID_voltage']['new'] = False
    # If the system is at a stable lock point, adjust the hardware voltage limits
        elif (lock_age_condition and new_output_condition):
        # Calculate the new limit thresholds
            data = mon['mll_fR/PID_voltage']['data']
            v_avg = np.mean(data)
            v_avg_slope = np.mean(np.diff(data))/(len(data)-1)
            v_expected = v_avg + v_avg_slope*len(data)/2
            v_std = np.std(data - v_avg_slope*np.arange(len(data)))
            upper_limit = v_expected + (v_std_threshold*v_std)/(1-2*v_range_threshold)
            lower_limit = v_expected - (v_std_threshold*v_std)/(1-2*v_range_threshold)
        # Restrict the results
            update = True
            if upper_limit == lower_limit:
                update = False
            elif (upper_limit >= state_limits['upper_output_limit']) and (lower_limit <= state_limits['lower_output_limit']):
                update = False
            elif (upper_limit > state_limits['upper_output_limit']):
                upper_limit = state_limits['upper_output_limit']
            elif (lower_limit < state_limits['lower_output_limit']):
                lower_limit = state_limits['lower_output_limit']
            if (upper_limit == current_limits['max']) and (lower_limit == current_limits['min']):
                update = False
        # Update the hardware limits
            if not(update):
            # Remove SRS PID controller from queue
                dev[device_db]['queue'].remove()
            else:
            # Update the limits
                settings_list = {
                        'upper_output_limit':upper_limit,
                        'lower_output_limit':lower_limit}
                update_device_settings(device_db, settings_list)
            # Remove SRS PID controller from queue
                dev[device_db]['queue'].remove()
            # Update the voltage limit monitor
                mon['mll_fR/PID_voltage_limits']['new'] = True
                mon['mll_fR/PID_voltage_limits']['data'] = {'min':lower_limit, 'max':upper_limit}
                db['mll_fR/PID_voltage_limits'].write_record_and_buffer({'min':lower_limit, 'max':upper_limit})
            # If approaching the state limits, adjust the temperature setpoint
                adjustment_interval_condition = ((time.time()-timer['find_lock:tec_adjust']) > tec_adjust_interval)
                upper_limit_condition = (upper_limit == state_limits['upper_output_limit'])
                lower_limit_condition = (lower_limit == state_limits['lower_output_limit'])
                if (adjustment_interval_condition and (upper_limit_condition or lower_limit_condition)):
                # Queue the ILX TEC controller --------------------------------------
                    device_db = 'mll_fR/device_TEC'
                    dev[device_db]['queue'].queue_and_wait()
                # Adjust timer
                    timer['find_lock:tec_adjust'] = timer.time()
                # Adjust the setpoint
                    if lower_limit_condition:
                        log_str = 'Lower voltage limit = {:.3f}, raising the resistance setpoint'.format(lower_limit)
                        log.log_info(__name__, 'keep_lock', log_str)
                    # Raise the resistance setpoint
                        dev[device_db]['driver'].tec_step(+1)
                    elif upper_limit_condition:
                        log_str = 'Upper voltage limit = {:.3f}, lowering the resistance setpoint'.format(upper_limit)
                        log.log_info(__name__, 'keep_lock', log_str)
                    # Lower the resistance setpoint
                        dev[device_db]['driver'].tec_step(-1)
                # Remove the ILX TEC controller from queue ------------
                    dev[device_db]['queue'].remove()

def lock_disabled(state_db):
# Queue the SRS PID controller --------------------------------------
    device_db = 'mll_fR/device_PID'
    dev[device_db]['queue'].queue_and_wait()
# Check if the PID controller is on ---------------------------------
    if dev[device_db]['driver'].pid_action():
    # Turn off
        dev[device_db]['driver'].pid_action(False)
# Remove SRS PID from queue -----------------------------------------
    dev[device_db]['queue'].remove()


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
        'mll_fR/state':{
                'lock':{
                        'settings':{
                                'mll_fR/device_TEC':[
                                        {'tec_mode':'R'}, {'tec_output':True}],
                                'mll_fR/device_PID':{
                                        'proportional_action':True, 'integral_action':True,
                                        'derivative_action':False,
                                        'proportional_gain':-3.0e0, 'integral_gain':5.0e2,
                                        'upper_output_limit':8.00, 'lower_output_limit':0.00},
                                'mll_fR/device_HV':{
                                        'x_min':0.00, 'x_max':60.00, 'x_voltage':0.00}},
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
                        'settings':{'mll_fR/device_PID':{'pid_action':False}},
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

# Initialize failed prereq log timers -----------------------------------------
'''These are set so that the logs do not become cluttered with repetitions of
    the same failure. The timer values are used in the check_prerequisites
    function.'''
log_failed_prereqs_interval = 60*10 #s
log_failed_prereqs_timer = {}
for state_db in STATE_DBs:
    for state in STATES[state_db]:
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
    STATES[state_db][current_state[state_db]]['routines']['monitor'](state_db)

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
            STATES[state_db][current_state[state_db]]['routines']['maintain'](state_db)
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
                STATES[state_db][current_state[state_db]]['routines']['search'](state_db)
    # Set the state initialization if necessary
        if not(current_state[state_db]['initialized']):
        # Update the state variable
            current_state[state_db]['initialized'] = True
            db[state_db].write_record_and_buffer(current_state[state_db])
    
# Operate the Current State ---------------------------------------------------
    for state_db in STATE_DBs:
    # If compliant,
        if current_state[state_db]['compliance'] == True:
            STATES[state_db][current_state[state_db]]['routines']['operate'](state_db)

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


