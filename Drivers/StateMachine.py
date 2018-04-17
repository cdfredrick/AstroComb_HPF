# -*- coding: utf-8 -*-
"""
Created on Tue Apr 10 11:04:24 2018

@author: cdf1
"""

# %% Modules ==================================================================
import numpy as np
import time
import datetime

import sys
import traceback
import gc

import threading
from functools import wraps

import logging
from Drivers.Logging import EventLog as log

from Drivers.Database import MongoDB
from Drivers.Database import CouchbaseDB


# %% Helper Functions =========================================================

'''The following are helper functionss that increase the readablity of code in
    this script.'''

# Update a 1D circular buffer -------------------------------------------------
@log.log_this()
def update_buffer(buffer, new_data, length):
    '''Use this function to update a 1D rolling buffer, as typically found in
    the monitor variables.
    '''
    length = int(abs(length))
    buffer = np.append(buffer, new_data)
    if buffer.size > length:
        buffer = buffer[-length:]
    return buffer

# Periodic Timer --------------------------------------------------------------
@log.log_this()
def get_lap(time_interval):
    '''Use this function to get an incrementing integer linked to the system
    clock.
    '''
    return int(time.time() // time_interval)


# %% Threading Error Handling
class ThreadFactory():
    @log.log_this()
    def __init__(self, group=None, target=None, name=None, args=[], kwargs={}, daemon=True):
        '''The ThreadFactory works similarly to a standard threading.Thread(), 
        but with added routines to catch thread errors and start new threads
        without having to reinitialize a new object.
        '''
        self.group = group
        self.target = target
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.daemon = daemon
        self.thread_errors = {}
        self.error_lock = threading.Lock()
        self.new_thread()
    
    @log.log_this()
    def handle_thread(self, func):
        """A function decorator that handles exceptions that occur during thread
        execution. Only errors from the most recent thread are held in memory
        and are accessible through "check_thread".
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapped function"""
            try:
                ident = threading.get_ident()
                self.thread_errors[ident] = None
                result = func(*args, **kwargs)
            except:
                with self.error_lock:
                    if (self.thread.ident in self.thread_errors):
                        self.thread_errors[ident] = sys.exc_info()
                raise
            else:
                return result
        return wrapper
    
    @log.log_this()
    def new_thread(self):
        '''Initialzes a new threading.Thread() object
        '''
        self.thread = threading.Thread(group=self.group,
                                       target=self.handle_thread(self.target),
                                       name=self.name,
                                       args=self.args,
                                       kwargs=self.kwargs,
                                       daemon=self.daemon)
    
    @log.log_this()
    def start(self):
        '''Starts a new thread, creating one if need be.
        '''
    # Check for old thread
        if (self.thread.ident != None):
        # Forget old errors
            with self.error_lock:
                if (self.thread.ident in self.thread_errors):
                   self.thread_errors.pop(self.thread.ident)
        # Initialize new thread
            self.new_thread()
    # Start thread
        self.thread.start()
    
    @log.log_this()
    def join(self):
        '''Blocks until the thread has completed execution.
        '''
        self.thread.join()
    
    @log.log_this()
    def is_alive(self):
        return self.thread.is_alive()
    
    @log.log_this()
    def check_thread(self):
        '''Checks whether the thread is alive and whether any erros have
        occured during its execution.
        '''
        alive = self.thread.is_alive()
        error = None
        if not(alive):
            with self.error_lock:
                if (self.thread.ident in self.thread_errors):
                    error = self.thread_errors[self.thread.ident]
        return (alive, error)


# %% State Machine ============================================================
class Machine():
    @log.log_this()
    def __init__(self, log_error_interval=100):
        '''Initialize the machine. The "__init__" function only instantiates a
        collection of internal variables used by the machine. For a full 
        initialization the following functions must also be called:
            init_comms
            init_master_DB_names
            init_read_DB_names
            init_default_settings
            init_DBs
            init_device_drivers_and_settings
            init_monitors
            init_states
        '''
        self.timer = {}
        self.thread = {}
        self.event = {}
        self.error = {}
        self.error_interval = log_error_interval # seconds

# Communications queue --------------------------------------------------------
    @log.log_this()
    def init_comms(self, COMMS):
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
        self.COMMS = COMMS
        self.comms = CouchbaseDB.PriorityQueue(self.COMMS)

# Internal database names -----------------------------------------------------
    @log.log_this()
    def init_master_DB_names(self, STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB):
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
        self.STATE_DBs = STATE_DBs
        self.DEVICE_DBs = DEVICE_DBs
        self.MONITOR_DBs = MONITOR_DBs
        self.LOG_DB = LOG_DB
        self.CONTROL_DB = CONTROL_DB
        self.MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]

# External database names -----------------------------------------------------
    @log.log_this()
    def init_read_DB_names(self, R_STATE_DBs, R_DEVICE_DBs, R_MONITOR_DBs):
        '''This is a list of all databases external to this control script that are 
        needed to check prerequisites
        '''
        self.R_STATE_DBs = R_STATE_DBs
        self.R_DEVICE_DBs = R_DEVICE_DBs
        self.R_MONITOR_DBs = R_MONITOR_DBs
        self.READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs
        
# Default settings ------------------------------------------------------------
    @log.log_this()
    def init_default_settings(self, STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS):
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
        self.STATE_SETTINGS = STATE_SETTINGS
        self.DEVICE_SETTINGS = DEVICE_SETTINGS
        self.CONTROL_PARAMS = CONTROL_PARAMS
        if not(self.CONTROL_DB in self.CONTROL_PARAMS):
            self.CONTROL_PARAMS[self.CONTROL_DB] = {}
        self.CONTROL_PARAMS[self.CONTROL_DB]['main_loop'] = {'value':True,'type':'bool'}
        self.SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))

# Connect to MongoDB ----------------------------------------------------------
    @log.log_this()
    def init_DBs(self, db={}):
        '''Creates a client and connects to all defined databases
        '''
        self.mongo_client = MongoDB.MongoClient()
        self.db = db
        for database in self.MASTER_DBs:
            if database in self.LOG_DB:
                self.db[database] = MongoDB.LogMaster(self.mongo_client, database)
            else:
                self.db[database] = MongoDB.DatabaseMaster(self.mongo_client, database)
        for database in self.READ_DBs:
            self.db[database] = MongoDB.DatabaseRead(self.mongo_client, database)

# Start Logging ---------------------------------------------------------------
    def init_logging(self, database_object=None, logger_level=logging.DEBUG, log_buffer_handler_level=logging.DEBUG, log_handler_level=logging.WARNING):
        '''Initializes logging for this script. If the logging database is unset then
            all logs will be output to the stout. When the logging database is set
            there are two logging handlers, one logs lower threshold events to the log 
            buffer and the other logs warnings and above to the permanent log database.
            The threshold for the base logger, and the two handlers, may be set in the
            following command.'''
        log.start_logging(logger_level=logger_level, log_buffer_handler_level=log_buffer_handler_level, log_handler_level=log_handler_level, database=database_object)

# Initialize all Devices and Settings -----------------------------------------
    @log.log_this()
    def _init_device_drivers_and_settings(self, dev={}, local_settings={}):
        '''This initializes all device drivers and checks that all settings
        (as listed in SETTINGS) exist within the databases. Any missing
        settings are populated with the default values.
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
    # Device Drivers
        self.dev = dev
        for device_db in self.DEVICE_DBs:
            self.dev[device_db] = {
                    'driver':self.send_args(self.DEVICE_SETTINGS[device_db]['driver'],
                                       self.DEVICE_SETTINGS[device_db]['__init__']),
                    'queue':CouchbaseDB.PriorityQueue(self.DEVICE_SETTINGS[device_db]['queue'])}
        gc.collect() # garbage collect old references
    # Settings
        self.local_settings = local_settings
        for database in self.SETTINGS:
            device_db_condition = (database in self.DEVICE_DBs)
            control_db_condition = (database in self.CONTROL_DB)
            self.local_settings[database] = self.db[database].read_buffer()
        # Check all SETTINGS
            db_initialized = True
            settings_list = []
            for setting in self.SETTINGS[database]:
                update_device_condition = (device_db_condition and (setting != 'driver') and (setting != 'queue') and (setting != '__init__'))
            # Check that there is anything at all
                if (self.local_settings[database]==None):
                    self.local_settings[database]={}
            # Check that the key exists in the database
                if not(setting in self.local_settings[database]):
                    db_initialized = False
                    if device_db_condition:
                        if setting == 'driver':
                            self.local_settings[database][setting] = str(self.SETTINGS[database][setting])
                        else:
                            self.local_settings[database][setting] = self.SETTINGS[database][setting]
                        if update_device_condition:
                            settings_list.append({setting:self.SETTINGS[database][setting]})
                    else:
                        self.local_settings[database][setting] = self.SETTINGS[database][setting]
                elif (device_db_condition and update_device_condition):
                    settings_list.append({setting:None})
                if (control_db_condition and setting == 'main_loop'):
                    if self.local_settings[database][setting]['value'] !=True:
                        db_initialized = False
                        self.local_settings[database][setting]['value'] = True
            if device_db_condition:
            # Update the device values
                self.update_device_settings(database, settings_list)
            elif not(db_initialized):
            # Update the database values if necessary
                self.db[database].write_record_and_buffer(self.local_settings[database])
    
    @log.log_this()
    def init_device_drivers_and_settings(self, dev={}, local_settings={}):
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
        self.dev = dev
        self.local_settings = local_settings
        thread_name = self.init_device_drivers_and_settings.__name__
        self.thread[thread_name] = ThreadFactory(
                target=self._init_device_drivers_and_settings,
                kwargs={'dev':self.dev,'local_settings':self.local_settings})
        self.thread_to_completion(thread_name)

# Initialize Local Copy of Monitors -------------------------------------------
    @log.log_this()
    def init_monitors(self, mon={}):
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
        self.mon = mon
        # External Read Databases------------------------
        for database in self.R_MONITOR_DBs:
            cursor = self.db[database].read_buffer(tailable_cursor=True, no_cursor_timeout=True)
            self.mon[database] = {
                    'data':np.array([]),
                    'cursor':self.exhaust_cursor(cursor),
                    'new':False}

# Initialize States -----------------------------------------------------------
    @log.log_this()
    def init_states(self, STATES):
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
        self.STATES = STATES

# Run the main loop -----------------------------------------------------------
    @log.log_this()
    def operate_machine(self, current_state={}, main_loop_interval=0.5):
        mod_name = __name__
        func_name = self.operate_machine.__name__
        log_str = " Operating state machine"
        log.log_info(mod_name, func_name, log_str)
    # Current state -----------------------------------------------------------
        self.current_state = current_state
        for state_db in self.STATE_DBs:
            self.current_state[state_db] = self.db[state_db].read_buffer()
        
    # Initialize "current_state" locks ----------------------------------------
        '''These are used so that changes to the current state in one thread do
        not overwrite changes made in another.
        '''
        self.lock = {}
        for state_db in self.STATE_DBs:
            self.lock[state_db] = threading.Lock()
        
    # Initialize failed prereq log timers -------------------------------------
        '''These are set so that the logs do not become cluttered with
        repetitions of the same failure. The timer values are used in the
        check_prerequisites function.
        '''
        self.log_failed_prereqs_timer = {}
        for state_db in self.STATE_DBs:
            self.log_failed_prereqs_timer[state_db] = {}
            for state in self.STATES[state_db]:
                self.log_failed_prereqs_timer[state_db][state] = {}
                for level in self.STATES[state_db][state]['prerequisites']:
                    self.log_failed_prereqs_timer[state_db][state][level] = {}
        
    # Initialize state machine timer ------------------------------------------
        '''The main loop timers are used to coordinate the threads of the main
        loop. Threads are expected to execute within this time interval. This
        is also the interval in which the main loop checks on its threads.
        '''
        self.main_loop_interval = main_loop_interval # seconds
        self.main_loop_timer = {}
        self.main_loop_timer['main'] = get_lap(self.main_loop_interval)+1
        for state_db in self.STATE_DBs:
            self.main_loop_timer[state_db] = get_lap(self.main_loop_interval)+1
        self.main_loop_timer['check_for_messages'] = get_lap(self.main_loop_interval)+1
        
    # Initialize thread events ------------------------------------------------
        for state_db in self.STATE_DBs:
            self.event[state_db] = threading.Event()
        self.event[self.COMMS] = threading.Event()
    # Initialize threads ------------------------------------------------------
        for state_db in self.STATE_DBs:
            self.thread[state_db] = ThreadFactory(target=self.state_machine, args=[state_db])
        self.thread[self.COMMS] = ThreadFactory(target=self.check_for_messages)
    # Main Loop ---------------------------------------------------------------
        while self.local_settings[self.CONTROL_DB]['main_loop']['value']:
        # Maintain threads ----------------------------------------------------
            errors = []
            for state_db in self.STATE_DBs:
                errors.append(self.maintain_thread(state_db))
            errors.append(self.maintain_thread(self.COMMS))
        # Check for errors ----------------------------------------------------
            error_caught = bool(len([error for error in errors if (error!=None)]))
            if error_caught:
                error_str = [''.join(traceback.format_exception_only(error[0], error[1])).strip() for error in errors if (error!=None)]
                log_str = '\n'.join([" Exeception detected, reinitializing threads.",*error_str])
                log.log_info(mod_name, func_name, log_str)
            # Trigger shutdown events
                for state_db in self.STATE_DBs:
                    self.event[state_db].set()
                self.event[self.COMMS].set()
            # Join all threads
                for state_db in self.STATE_DBs:
                    self.thread[state_db].join()
                self.thread[self.COMMS].join()
            # Update the state variables
                for state_db in self.STATE_DBs:
                    with self.lock[state_db]:
                        if self.current_state[state_db]['initialized'] != False:
                            self.current_state[state_db]['initialized'] = False
                            self.db[state_db].write_record_and_buffer(self.current_state[state_db])
            # Reinitialize the devices and settings
                self.init_device_drivers_and_settings(dev=self.dev, local_settings=self.local_settings)
            # Reset shutdown trigger
                for state_db in self.STATE_DBs:
                    self.event[state_db].clear()
                self.event[self.COMMS].clear()
        # Pause ---------------------------------------------------------------
            pause = (self.main_loop_timer['main']+1)*self.main_loop_interval - time.time()
            if pause > 0:
                time.sleep(pause)
                self.main_loop_timer['main'] += 1
            else:
                log_str = " Execution time exceeded the set loop interval {:}s by {:.2g}s".format(self.main_loop_interval, abs(pause))
                log.log_info(mod_name, func_name, log_str)
                self.main_loop_timer['check_for_messages'] = get_lap(self.main_loop_interval)+1
    # Main Loop has exited ----------------------------------------------------
        log_str = " Shut down command accepted. Exiting the control script."
        log.log_info(mod_name, func_name, log_str)
        # Trigger shutdown events
        for state_db in self.STATE_DBs:
            self.event[state_db].set()
        self.event[self.COMMS].set()
        # Join all threads
        for state_db in self.STATE_DBs:
            self.thread[state_db].join()
        self.thread[self.COMMS].join()
        log_str = " Shutdown complete."
        log.log_info(mod_name, func_name, log_str)
        

    @log.log_this()
    def state_machine(self, state_db):
        '''This runs the state machine routines. Each state_db should have
        a separate thread of execution.
        '''
        mod_name = __name__
        func_name = '.'.join([self.state_machine.__name__, state_db])
        while not(self.event[state_db].is_set()):
        # Check the Critical Prerequisites ------------------------------------
            critical_pass = self.check_prereqs(
                    state_db,
                    self.current_state[state_db]['state'],
                    'critical', log_all_failures=True)
            # Place into safe state if critical prereqs fail
            if not critical_pass:
                self.setup_state(state_db, 'safe')
    
        # Monitor the Current State -------------------------------------------
            self.STATES[state_db][self.current_state[state_db]['state']]['routines']['monitor'](state_db)
    
        # Maintain the Current State ------------------------------------------
            # If compliant,
            if self.current_state[state_db]['compliance'] == True:
            # If necessary, check the optional prerequisites
                if self.current_state[state_db]['prerequisites']['optional'] == False:
                    optional_pass = self.check_prereqs(
                        state_db,
                        self.current_state[state_db]['state'],
                        'optional')
                    if optional_pass == True:
                    # Update the state variable
                        with self.lock[state_db]:
                            self.current_state[state_db]['prerequisites']['optional'] = optional_pass
                            self.db[state_db].write_record_and_buffer(self.current_state[state_db])
            # Maintain compliance
                self.STATES[state_db][self.current_state[state_db]['state']]['routines']['maintain'](state_db)
            # If out of compliance, 
            else:
            # Check necessary and optional prerequisites
                necessary_pass = self.check_prereqs(
                        state_db,
                        self.current_state[state_db]['state'],
                        'necessary')
                optional_pass = self.check_prereqs(
                        state_db,
                        self.current_state[state_db]['state'],
                        'optional')
                necessary_prereq_changed = (self.current_state[state_db]['prerequisites']['necessary'] != necessary_pass)
                optional_prereq_changed = (self.current_state[state_db]['prerequisites']['optional'] != optional_pass)
                if (necessary_prereq_changed or optional_prereq_changed):
                # If necessary, update the state variable
                    with self.lock[state_db]:
                        self.current_state[state_db]['prerequisites']['necessary'] = necessary_pass
                        self.current_state[state_db]['prerequisites']['optional'] = optional_pass
                        self.db[state_db].write_record_and_buffer(self.current_state[state_db])
            # Search for the compliant state
                if necessary_pass:
                    self.STATES[state_db][self.current_state[state_db]['state']]['routines']['search'](state_db)
        
        # State initialized ---------------------------------------------------
            with self.lock[state_db]:
                if not(self.current_state[state_db]['initialized']):
            # Update the state variable
                    self.current_state[state_db]['initialized'] = True
                    self.db[state_db].write_record_and_buffer(self.current_state[state_db])
        
        # Operate the Current State -------------------------------------------
            # If compliant,
            if self.current_state[state_db]['compliance'] == True:
                self.STATES[state_db][self.current_state[state_db]['state']]['routines']['operate'](state_db)
                            
        # Check Desired State -------------------------------------------------
            with self.lock[state_db]:
                if self.current_state[state_db]['state'] != self.current_state[state_db]['desired_state']:
                # Check the prerequisites of the desired states
                    critical_pass = self.check_prereqs(
                            state_db,
                            self.current_state[state_db]['desired_state'],
                            'critical')
                    necessary_pass = self.check_prereqs(
                            state_db,
                            self.current_state[state_db]['desired_state'],
                            'necessary')
                    optional_pass = self.check_prereqs(
                            state_db,
                            self.current_state[state_db]['desired_state'],
                            'optional')
                    if critical_pass:
                    # Initialize the transition into the desired state
                        self.setup_state(
                                state_db,
                                self.current_state[state_db]['desired_state'],
                                critical=critical_pass,
                                necessary=necessary_pass,
                                optional=optional_pass)
        
        # Write Heartbeat to Buffer -----------------------------------------------
            with self.lock[state_db]:
                self.current_state[state_db]['heartbeat'] = datetime.datetime.utcnow()
                self.db[state_db].write_buffer(self.current_state[state_db])
        
        # Pause ---------------------------------------------------------------
            pause = (self.main_loop_timer[state_db]+1)*self.main_loop_interval - time.time()
            if pause > 0:
                time.sleep(pause)
                self.main_loop_timer[state_db] += 1
            else:
                log_str = " Execution time exceeded the set loop interval {:}s by {:.2g}s".format(self.main_loop_interval, abs(pause))
                log.log_info(mod_name, func_name, log_str)
                self.main_loop_timer[state_db] = get_lap(self.main_loop_interval)+1

# Check the Communications Queue ----------------------------------------------
    @log.log_this()
    def check_for_messages(self):
        '''This checks for and parses new messages in the communications queue.
        '''
        mod_name = __name__
        func_name = self.check_for_messages.__name__
        while not(self.event[self.COMMS].is_set()):
        # Parse the message ---------------------------------------------------
            for message in range(len(self.comms.get_queue())):
                message = self.comms.pop()
                self.parse_message(message)
        # Pause ---------------------------------------------------------------
            pause = (self.main_loop_timer['check_for_messages']+1)*self.main_loop_interval - time.time()
            if pause > 0:
                time.sleep(pause)
                self.main_loop_timer['check_for_messages'] += 1
            else:
                log_str = " Execution time exceeded the set loop interval {:}s by {:.2g}s".format(self.main_loop_interval, abs(pause))
                log.log_info(mod_name, func_name, log_str)
                self.main_loop_timer['check_for_messages'] = get_lap(self.main_loop_interval)+1

# Check the Prerequisites of a Given State ------------------------------------
    @log.log_this()
    def check_prereqs(self, state_db, state, level, log_all_failures=None):
        '''A helper function to automate the process of checking prerequisites.
        '''
        prereqs_pass = True
        if level in self.STATES[state_db][state]['prerequisites']:
            for prereq in self.STATES[state_db][state]['prerequisites'][level]:
                prereq_value = self.from_keys(self.db[prereq['db']].read_buffer(),prereq['key'])
                prereq_status = prereq['test'](prereq_value)
                if not(prereq_status):
                    if log_all_failures == None:
                    # Check the error timer
                        if (str(prereq) in self.log_failed_prereqs_timer[state_db][state][level]):
                        # If the failure has been caught before, wait for the timer
                            log_failure = ((time.time() - self.log_failed_prereqs_timer[state_db][state][level][str(prereq)]) > self.log_error_interval)
                        else:
                        # Catch the failure for the first time
                            log_failure = True
                        if (log_failure == True):
                        # Update the error timer
                            self.log_failed_prereqs_timer[state_db][state][level][str(prereq)] = time.time()
                    else:
                    # If "log_all_failures" is set, use it.
                        log_failure = log_all_failures
                    if log_failure:
                        mod_name = __name__
                        func_name = self.check_prereqs.__name__
                        if (level=='critical'):
                            log_str = 'Critical prerequisite failure:\n state_db:\t{:}\n state:\t\t{:}\n prereq:\t{:}\n current:\t{:}'.format(state_db, state, prereq, prereq_value)
                            log.log_critical(mod_name,func_name,log_str)
                        elif (level=='necessary'):
                            log_str = 'Necessary prerequisite failure:\n state_db:\t{:}\n state:\t\t{:}\n prereq:\t{:}\n current:\t{:}'.format(state_db, state, prereq, prereq_value)
                            log.log_warning(mod_name,func_name,log_str)
                        elif (level=='optional'):
                            log_str = 'Optional prerequisite failure:\n state_db:\t{:}\n state:\t\t{:}\n prereq:\t{:}\n current:\t{:}'.format(state_db, state, prereq, prereq_value)
                            log.log_warning(mod_name,func_name,log_str)
                # Propogate prereq status
                prereqs_pass *= prereq_status
        return prereqs_pass
    
# Update Device Settings ------------------------------------------------------
    @log.log_this()
    def update_device_settings(self, device_db, settings_list, write_log=True):
        '''A helper function to automate the process of updating the settings
        of a single device.
        '''
        mod_name = __name__
        func_name = self.update_device_settings.__name__
        updated = False
    # Check settings_list type
        if isinstance(settings_list, dict):
        # If settings_list is a dictionary then use only one settings_group
            settings_list = [settings_list]
    # Wait for queue
        queued = self.dev[device_db]['queue'].queue_and_wait()
    # Push device settings
        for settings_group in settings_list:
            for setting in settings_group:
            # Log the device, method, and arguments
                if write_log:
                    prologue_str = ' device: {:}\n method: {:}\n   args: {:}'.format(device_db, setting, settings_group[setting])
                    log.log_info(mod_name, func_name, prologue_str)
            # Try sending the command to the device
                result = self.send_args(getattr(self.dev[device_db]['driver'], setting),settings_group[setting])
            # Update the local copy if it exists in the device settings
                if (setting in self.local_settings[device_db]):
                    if settings_group[setting] == None:
                    # A setting was read from the device
                        new_setting = result
                    else:
                    # A new setting was applied to the device
                        new_setting = settings_group[setting]
                    if (self.local_settings[device_db][setting] != new_setting):
                        updated = True
                        self.local_settings[device_db][setting] = new_setting
            # Log the returned result if stringable
                try:
                    epilogue_str = ' Returned: {:}'.format(str(result))
                except:
                    epilogue_str = ' Returned successfully, but result was not stringable'
                if write_log:
                    log.log_info(mod_name, func_name, epilogue_str)
            # Touch queue (prevent timeout)
                self.dev[device_db]['queue'].touch()
    # Remove from queue
        if not(queued):
        # Remove from queue if it wasn't there to begin with.
            self.dev[device_db]['queue'].remove()
    # Update the database if the local copy changed
        if updated:
            self.db[device_db].write_record_and_buffer(self.local_settings[device_db])
    
# Setup the Transition to a New State -----------------------------------------
    @log.log_this()
    def setup_state(self, state_db, state, critical=True, necessary=True, optional=True):
        '''A helper function to automate the process of setting up new states.
        '''
    # Update the device settings
        for device_db in self.STATES[state_db][state]['settings']:
            self.update_device_settings(device_db, self.STATES[state_db][state]['settings'][device_db])
    # Update the state variable
        with self.lock[state_db]:
            self.current_state[state_db]['state'] = state
            self.current_state[state_db]['prerequisites'] = {
                    'critical':critical,
                    'necessary':necessary,
                    'optional':optional}
            self.current_state[state_db]['compliance'] = False
            self.db[state_db].write_record_and_buffer(self.current_state[state_db]) # The desired state should be left unaltered
    
# Parse Messages from the Communications Queue --------------------------------
    @log.log_this()
    def parse_message(self, message):
        '''A helper function to automate the parsing messages from the
        communications queue. The communications queue is a couchbase queue
        that serves as the intermediary between this script and others. The 
        entries in this queue are parsed as commands in this script:
            Requesting to change state:
                {'state': {<state DB path>:{'state':<state>},...}}
            Requesting to change device settings:
                {'device_setting': {<device driver DB path>:{<method name>:<args>,...},...}}
            Requesting to change a control parameter:
                {'control_parameter': {<parameter name>:<value>,...}}
        -Commands are sent into the queue by setting the "message" keyword 
        argument within the CouchbaseDB queue.push() method. 
        -Commands are read from the queue with the queue.pop() method.
        -If the DB path given does not exist in the defined STATE_DBs and
        DEVICE_DBs, or the given method and parameter does not exist in 
        CONTROL_PARAMS, no attempt is made to excecute the command.
        -All commands are caught and logged at the INFO level.
        -Multiple commands may be input simultaneously by nesting single
        commands within the 'state', 'device_setting', and 'control_parameter'
        keys:
            message = {
                'state':{<state DB path>:{'state':<state>},...},
                'device_setting':{<device driver DB path>:{<method name>:<args>,...},...},
                'control_parameter':{<parameter name>:<value>,...}}
        '''
        mod_name = __name__
        func_name = self.parse_message.__name__
        if ('message' in message):
            message = message['message']
            log_str = 'Incoming message:\n {:}'.format(message)
            log.log_info(mod_name, func_name, log_str)
        # If requesting to change states,
            if ('state' in message):
                for state_db in message['state']:
                    if ('state' in message['state'][state_db]):
                        desired_state = message['state'][state_db]['state']
                        if (desired_state in self.STATES[state_db]):
                            with self.lock[state_db]:
                                if self.current_state[state_db]['desired_state'] != desired_state:
                            # Update the state variable
                                    self.current_state[state_db]['desired_state'] = desired_state
                                    self.db[state_db].write_record_and_buffer(self.current_state[state_db])
        # If requesting to change device settings,
            if ('device_setting' in message):
                for device_db in message['device_setting']:
                # Update the device settings
                    if (device_db in self.DEVICE_DBs):
                        self.update_device_settings(device_db, message['device_setting'][device_db])
        # If requesting to change control parameters,
            if ('control_parameter' in message):
                updated = False
                for parameter in message['control_parameter']:
                # Update the control parameter
                    if (parameter in self.local_settings[self.CONTROL_DB]):
                    # Convert new parameter to the correct type
                        parameter_type = self.local_settings[self.CONTROL_DB][parameter]['type']
                        try:
                            result = self.convert_type(message['control_parameter'][parameter], parameter_type)
                        except:
                            result_str = ' Could not convert {:} to {:} for control parameter {:}'.format(message['control_parameter'][parameter], parameter_type, parameter)
                            log.log_info(mod_name, func_name, result_str)
                        else:
                            if (self.local_settings[self.CONTROL_DB][parameter]['value'] != result):
                        # Update the local copy
                                updated = True
                                self.local_settings[self.CONTROL_DB][parameter]['value'] = result
            # Update the database if the local copy changed
                if updated:
                    self.db[self.CONTROL_DB].write_record_and_buffer(self.local_settings[self.CONTROL_DB])
    
# Convert Type from a "type string" -------------------------------------------
    @log.log_this()
    def convert_type(self, obj, type_str):
        '''A helper function to convert an object to a specific type.
        '''
        valid_types = {'bool':bool, 'complex':complex,
                       'float':float, 'int':int, 'str':str}
        obj = valid_types[type_str](obj)
        return obj

# Exhaust a MongoDB Cursor to Queue up the Most Recent Values -----------------
    @log.log_this()
    def exhaust_cursor(self, cursor):
        '''A helper fuction to queue new values from a MongoDB capped
        collection.
        '''
        for doc in cursor:
            pass
        return cursor

# Get Values from Nested Dictionary -------------------------------------------
    @log.log_this()
    def from_keys(self, nested_dict, key_list):
        '''A helper function which parses nested dictionaries given a list of
        keys.
        '''
        if isinstance(key_list, list):
            for key in key_list:
                nested_dict = nested_dict[key]
        else:
            nested_dict = nested_dict[key_list]
        return nested_dict

# Parse and Send Arguments to Functions ---------------------------------------
    @log.log_this()
    def send_args(self, func, obj=None):
        '''Single arguments should be entered as is:
            obj = arg
        Place multiple arguments in a list containing a list of positional
        arguments and a dictionary of keyword arguments:
            obj = [[<args>], {<kwargs>}]
            obj = [[<args>]]
            obj = [{<kwargs>}]
        '''
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
    
# Threading Functions ---------------------------------------------------------
    @log.log_this()
    def thread_to_completion(self, thread_name):
        '''A helper function that blocks until a thread has sucessfully
        completed its execution. It automatically retries the thread if it
        catches errors.
        '''
        completed = False
        loop_count = 0
        while not(completed):
            loop_count += 1
            self.thread[thread_name].start()
            self.thread[thread_name].join()
            (alive, error) = self.thread[thread_name].check_thread()
            if (error != None):
                mod_name = __name__
                func_name = self.thread[thread_name].target.__name__
                err_str = thread_name+''.join(traceback.format_exception(*error))
                if (err_str in self.error):
                    if (time.time() - self.error[err_str]) > self.error_interval:
                        log.log_exception_info(mod_name, func_name, error)
                else:
                    self.error[err_str] = time.time()
                    log.log_exception_info(mod_name, func_name, error)
            else:
                completed = True
                if loop_count > 1:
                    log_str = 'Returned successfully after {:} iterations.'.format(loop_count)
                    log.log_error(mod_name, func_name, log_str)
    
    @log.log_this()
    def maintain_thread(self, thread_name):
        '''A helper function that can be used to maintain the operation of a
        thread. The method checks if the thread is still alive, restarting the 
        thread or returning error messages if it has stopped.
        '''
        (alive, error) = self.thread[thread_name].check_thread()
        if (error != None):
            mod_name = __name__
            func_name = self.thread[thread_name].target.__name__
            err_str = thread_name+''.join(traceback.format_exception(*error))
            if (err_str in self.error):
                if (time.time() - self.error[err_str]) > self.error_interval:
                    log.log_exception_info(mod_name, func_name, error)
            else:
                self.error[err_str] = time.time()
                log.log_exception_info(mod_name, func_name, error)
        elif (alive == False):
            self.thread[thread_name].start()
        return error
