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

'''The following are helper functions that increase the readablity of code in
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
        self.result = None
        self.error = None
        self.lock = threading.Lock()
        self.new_thread()

    @log.log_this()
    def _handle_thread(self, func):
        """A function decorator that handles exceptions that occur during thread
        execution. Only errors from the most recent thread are held in memory
        and are accessible through "check_thread" or the "error" attribute.
        """
        @wraps(func)
        def handle_thread(*args, **kwargs):
            """Wrapped function"""
            try:
                ident = threading.get_ident()
                # Execute the function
                result = func(*args, **kwargs)
            except:
                error = sys.exc_info()
                with self.lock:
                # Record the error
                    if (self.thread.ident == ident):
                        self.result = None
                        self.error = error
                raise error[1].with_traceback(error[2])
            else:
                with self.lock:
                # Record the result
                    if (self.thread.ident == ident):
                        self.result = result
                        self.error = None
        return handle_thread

    @log.log_this()
    def new_thread(self):
        '''Initialzes a new threading.Thread() object
        '''
        with self.lock:
            self.thread = threading.Thread(group=self.group,
                                           target=self._handle_thread(self.target),
                                           name=self.name,
                                           args=self.args,
                                           kwargs=self.kwargs,
                                           daemon=self.daemon)
            self.result = None
            self.error = None

    @log.log_this()
    def start(self):
        '''Starts a new thread, creating one if need be.
        '''
    # Check for old thread
        if (self.thread.ident != None):
        # Initialize new thread
            self.new_thread()
    # Start thread
        self.thread.start()

    @log.log_this()
    def join(self):
        '''Blocks until the most recent thread has completed execution.'''
        self.thread.join()

    @log.log_this()
    def is_alive(self):
        '''Returns if the most recent thread is alive'''
        return self.thread.is_alive()

    @log.log_this()
    def check_thread(self):
        '''Checks whether the most recent thread is alive and whether any
        errors have occured during its execution. The error is cleared after
        using this method.
        '''
        alive = self.is_alive()
        error = self.error
        if (error != None):
        # Remove Error
            with self.lock:
                self.error = None
        return (alive, error)


# %% State Machine ============================================================
class Machine():
    '''Initialize the machine.

    Parameters
    ----------
    log_error_interval
        The number of seconds to wait before logging the same error. A larger
        value prevents the logs from being continously flooded by a recurring
        error.

    Notes
    -----
    The `Machine.__init__` function only instantiates a collection of internal
    variables used by the machine. For a full initialization the following
    functions must also be called:
        1. `Machine.init_comms`
        2. `Machine.init_master_DB_names`
        3. `Machine.init_read_DB_names`
        4. `Machine.init_default_settings`
        5. `Machine.init_DBs`
        6. `Machine.init_device_drivers_and_settings`
        7. `Machine.init_monitors`
        8. `Machine.init_states`
    '''

    @log.log_this()
    def __init__(self, log_error_interval=100):
        self.timer = {}
        self.thread = {}
        self.event = {}
        self.error = {}
        self.error_interval = log_error_interval # seconds

# Communications queue --------------------------------------------------------
    @log.log_this()
    def init_comms(self, COMMS):
        '''Initialize the communications queue.

        Parameters
        ----------
        COMMS : str
            The name of the queue associated with this `Machine` instance.

        Notes
        -----
        The communications queue is a couchbase queue that serves as the
        intermediary between this machine and others. The entries in this queue
        are parsed into commands within this class. See `Machine.parse_message`
        for documentation on the message syntax.
        '''
        self.COMMS = COMMS
        self.comms = CouchbaseDB.PriorityQueue(self.COMMS)

# Internal database names -----------------------------------------------------
    @log.log_this()
    def init_master_DB_names(self, STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB):
        '''Initialize the list of master databases.

        This is a list of all databases that this script directly initializes
        and controls. If they do not already exists, these databases are
        initialized within `Machine.init_DBs`.

        Parameters
        ----------
        The databases are grouped by function.

        STATE_DBs : list of str
            - The entries in state databases should reflect the current
              state of the system and the level of compliance. Other
              scripts should look to these databases in order to resolve
              prerequisites.
        DEVICE_DBs : list of str
            - The entries in device databases should include the settings for
              each unique device or device/channel driver interface.
        MONITOR_DBs : list of str
            - The entries in monitor databases should contain secondary
              variables used to determine compliance with the state of the
              system, and to determine any actions required to maintain
              compliance.
            - In general, data for use in control loops should have
              an updated value every 0.2 seconds. Data for passive
              monitoring should have a relaxed 1.0 second or longer update
              period.
        LOG_DB : str
            - This should be a single database that serves as the
              repository of all logs generated by this script.
        CONTROL_DB : str
            - This should be a single database that contains all control
              loop variables accessible to commands from the comms queue.
        '''
        self.STATE_DBs = STATE_DBs
        self.DEVICE_DBs = DEVICE_DBs
        self.MONITOR_DBs = MONITOR_DBs
        self.LOG_DB = LOG_DB
        self.CONTROL_DB = CONTROL_DB
        self.MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]

# External database names -----------------------------------------------------
    @log.log_this()
    def init_read_DB_names(self, STATE_DBs, DEVICE_DBs, MONITOR_DBs):
        '''Initialize the list of read databases.

        This is a list of all databases external to this control script that are
        needed to check prerequisites. These databases must be initialized by
        another instance of `Machine`.
        '''
        self.R_STATE_DBs = STATE_DBs
        self.R_DEVICE_DBs = DEVICE_DBs
        self.R_MONITOR_DBs = MONITOR_DBs
        self.READ_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs

# Default settings ------------------------------------------------------------
    @log.log_this()
    def init_default_settings(self, STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS):
        '''A template for all settings used in this script.

        Upon calling `Machine.init_device_drivers_and_settings` these settings
        are checked against those saved in the database, and populated if found
        empty. Each state and device database declared in
        `Machine.init_master_DB_names` should be represented.

        Only settings which are listed in the defaults are tracked by the
        respective state, device, or control databases.

        Parameters
        ----------
        STATE_SETTINGS : dict of dict
            - Include all states that need to be tracked in the `Machine`::

                {<state database path>:{
                    "state":<name of the current state>,
                    "prerequisites":{
                        "critical":<critical>,
                        "necessary":<necessary>,
                        "optional":<optional>},
                    "compliance":<compliance of current state>,
                    "desired_state":<name of the desired state>,
                    "initialized":<initialization state of the control script>,
                    "heartbeat":<datetime.datetime.utcnow()>},
                ...}
            - The state name should correspond to one of the states defined
              in `Machine.init_states`.
            - The prerequisites are a 3 part dictionary of boolean values
              that indicate whether each category of prerequisites pass for the
              current state. The 3 severity levels are critical, necessary, and
              optional.
            - The compliance level is a boolean value that indicates whether
              the system is compliant with the current state.
            - The "desired_state" is mostly for internal use, particularly for
              cases where the state is temporarliy changed. The script should
              seek to bring the current state to the desired state. The script
              should not change the current state if the desired state is
              undefined.
            - The "initialized" parameter is a boolean value that indicates
              that the current state is accurate. This is useful for cases
              where a master program or watchdog starts the control scripts. It
              should be set to False by the master program before the control
              scripts are executed, and should only be set to True after the
              control scripts have determined the current state. In order to
              smoothly connect to the system if the instruments are already
              running, initialization prerequisites should be either
              "necessary" or "optional" ("critical" would force the "safe"
              state).
            - The "heartbeat" parameter is a datetime.datetime utc timestamp
              that indicates when the control script last checked the state.
              Every time the control script finishes a loop it writes the
              state db to the buffer with a new heartbeat value. This is useful
              to determine if the current state in the database is "stale". The
              heartbeat is only incidentally updated in the record as items are
              written to it in the coarse of normal control script operation.

        DEVICE_SETTINGS : dict of dict
            - Include all settings that need to be tracked in the databases::

                {<device database path>:{
                    "driver":<driver class>,
                    "queue":<queue name>,
                    "__init__":<args>,
                    <method name>:<args>,...},
                ...}
            - The entries should include the settings for each unique device
              or device/channel combination.
            - The "driver" should contain an uninitialized instance of the
              driver class.
            - The "queue" should contain the name of the device queue. The
              queue is needed to coordinate access to the devices. Each
              blocking connection to a device should have a unique queue name.
              If access to one part of an instrument blocks access to other
              parts, that set of parts should all use the same unique queue. A
              good queue name is the instrument address.
            - The "__init__" method should hold all arguments necessary to
              initialize the device driver.
            - For automation purposes, the setting names and parameters should
              be derived from the names of the device driver methods so as to
              be accessible through getattr. See use in
              `Machine.update_device_setting`s.
            - The automated `Machine.send_args` parses and sends the commands.
            - Single arguments should be entered as is::

                  <method name>:<arg>
            - Multiple arguments must be placed in a list containing a list of
              positional arguments and a dictionary of keyword arguments::

                  <method name>:[[<args>], {<kwargs>}]
                  <method name>:[[<args>]]
                  <method name>:[{<kwargs>}]
            - A setting of `None` calls the methods without any arguments.
              Device drivers must reserve these cases for getting the
              current device settings or readings::

                  <method name>:None -> returns current device state

        CONTROL_PARAMS : dict of dict
            - Include all control parameters that must be externally accesible::

                {<control database path>:{
                    <control parameter>:{
                        "value":<value>,
                        "type":<type str>},
                    ...}}
            - Control parameters have both a value and a type. See
              `Machine.convert_type` for details on the valid types.
            - Only include parameters that should have remote access. Only the
              type of the recieved parameter is checked, there is no protection
              against the insertion of bad values.
            - The "main_loop" parameter is reserved for operation of the
              state machine.

        Notes
        -----
        - Default values are only added to a database on initialization if the
          setting keys are not found within the database (if the database has
          not yet been populated with that setting).
        - For device databases, default settings of None are populated with
          values from the device, but set values are written to the device.
          All initialized settings are read from the device at startup.
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

        This method also initializes all thread locks necessary for safely
        accesing the databases.
        '''
        self.mongo_client = MongoDB.MongoClient()
        self.db = db
        self.lock = {}
        for database in self.MASTER_DBs:
            # Initialize "current_state" locks --------------------------------
            self.lock[database] = threading.Lock()
            # Initialize Databases --------------------------------------------
            if database in self.LOG_DB:
                self.db[database] = MongoDB.LogMaster(self.mongo_client, database)
            else:
                self.db[database] = MongoDB.DatabaseMaster(self.mongo_client, database)
        for database in self.READ_DBs:
            self.lock[database] = threading.Lock()
            # Initialize Read Only Databases ----------------------------------
            self.db[database] = MongoDB.DatabaseRead(self.mongo_client, database)

# Start Logging ---------------------------------------------------------------
    def init_logging(self, database_object=None, logger_level=logging.DEBUG, log_buffer_handler_level=logging.DEBUG, log_handler_level=logging.WARNING):
        '''Initializes logging for this script.

        If the logging database is unset then all logs will be output to the
        `stout`. When the logging database is set there are two logging
        handlers, one logs lower threshold events to the log buffer and the
        other logs warnings and above to the permanent log database. The
        threshold for the base logger, and the two handlers, may be set in the
        following command.'''
        log.start_logging(logger_level=logger_level, log_buffer_handler_level=log_buffer_handler_level, log_handler_level=log_handler_level, database=database_object)

# Initialize all Devices and Settings -----------------------------------------
    @log.log_this()
    def _init_device_drivers_and_settings(self, dev={}, local_settings={}):
        '''Initializes all device objects and checks that all settings (as
        listed in `SETTINGS`) exist within the databases. Any missing settings
        are populated with the default values.

        - If the setting does not exist within a device database that setting
          is propogated to the device, otherwise the local settings are read
          from the device.
        - The "driver" settings are saved as strings.
        - The settings for "__init__" methods are are not sent or pulled to
          devices.
        - A local copy of all settings is contained within the local_settings
          dictionary.
        - Each device database will be associated with a driver and a queue::

            dev[<device database path>] = {
                'driver':<driver object>,
                'queue':<queue objecct>}
        '''
    # Logging
        mod_name = self.init_device_drivers_and_settings.__module__
        func_name = self.init_device_drivers_and_settings.__name__
    # Device Drivers
        self.dev = dev
        for device_db in self.DEVICE_DBs:
            log_str = " Initializing device {:}".format(device_db)
            log.log_info(mod_name, func_name, log_str)
        # Release Old References
            if (device_db in self.dev):
                if ('driver' in self.dev[device_db]):
                    if hasattr(self.dev[device_db]['driver'],'_release'):
                        getattr(self.dev[device_db]['driver'],'_release')()
        # Create New Object
            self.dev[device_db] = {
                    'driver':self.send_args(self.DEVICE_SETTINGS[device_db]['driver'],
                                       self.DEVICE_SETTINGS[device_db]['__init__']),
                    'queue':CouchbaseDB.PriorityQueue(self.DEVICE_SETTINGS[device_db]['queue'])}
        gc.collect() # garbage collect old references
    # Settings
        self.local_settings = local_settings
        for database in self.SETTINGS:
            log_str = " Initializing database {:}".format(database)
            log.log_info(mod_name, func_name, log_str)
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
                elif (update_device_condition):
                    settings_list.append({setting:None})
                if (control_db_condition and setting == 'main_loop'):
                    if self.local_settings[database][setting]['value'] !=True:
                        db_initialized = False
                        self.local_settings[database][setting]['value'] = True
                if ((setting == 'driver') or (setting == 'queue') or (setting == '__init__')):
                    if setting == 'driver':
                        if self.local_settings[database][setting] != str(self.SETTINGS[database][setting]):
                            db_initialized = False
                            self.local_settings[database][setting] = str(self.SETTINGS[database][setting])
                    else:
                        if self.local_settings[database][setting] != self.SETTINGS[database][setting]:
                            db_initialized = False
                            self.local_settings[database][setting] = self.SETTINGS[database][setting]
            if device_db_condition:
            # Update the device values
                self.update_device_settings(database, settings_list)
            elif not(db_initialized):
            # Update the database values if necessary
                self.db[database].write_record_and_buffer(self.local_settings[database])

    @log.log_this()
    def init_device_drivers_and_settings(self, dev={}, local_settings={}):
        '''Initializes all device objects and checks that all settings (as
        listed in `SETTINGS`) exist within the databases. Any missing settings
        are populated with the default values. This function automatically
        restarts if an error is encoutered.

        - If the setting does not exist within a device database that setting
          is propogated to the device, otherwise the local settings are read
          from the device.
        - The "driver" settings are saved as strings.
        - The settings for "__init__" methods are are not sent or pulled to
          devices.
        - A local copy of all settings is contained within the local_settings
          dictionary.
        - Each device database will be associated with a driver and a queue::

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
        '''Initialize the local copy of the monitor objects.

        Monitors should associate the monitor databases with the local,
        circular buffers of the monitored data. Monitors should indicate when
        they have recieved new data.

        - Monitors from the internal databases must be entered manually and
          should contain the following::

            {<database path>:{
                'data':<local data copy>,
                'new':<bool>,
                'lock':threading.Lock()},
            ...}

        - Monitors from the read database should have their cursors exhausted so
          that only their most recent values are accessible::

            {<database path>:{
                'data':<local data copy>,
                'cursor':<tailable cursor object>,
                'new':<bool>,
                'lock':threading.Lock(),
            ...}

        Notes
        -----
        - Only the read databases are automatically populated. The monitors for
          the internal databases must be entered manually into `Machine.mon`.
        '''
        self.mon = mon
        # External Read Databases------------------------
        for database in self.R_MONITOR_DBs:
            cursor = self.db[database].read_buffer(tailable_cursor=True, no_cursor_timeout=True)
            self.mon[database] = {
                    'data':np.array([]),
                    'cursor':self.exhaust_cursor(cursor),
                    'new':False,
                    'lock':threading.Lock()}

# Initialize States -----------------------------------------------------------
    @log.log_this()
    def init_states(self, STATES):
        '''Initialize the state machines state parameters.

        Parameters
        ----------
        STATES : dict of dict
            Defined state machines are composed of collections of states,
            settings, prerequisites, routines, and a set of optional keyword
            arguments::

                {<state database path>:{
                    <state>:{
                        "settings":{
                            <device database path>:{
                                <method>:<args>,
                                ...},
                            ...,
                            <not a device database path>:<fixed parameter>,
                            ...},
                        "prerequisites":{
                            "critical":[
                                {"db":<database path>,
                                "key":<entry's key>,
                                "test":<test function>,
                                "doc":<test function docs>},
                                 ...],
                            "necessary":[...],
                            "optional":[...],
                            "exit":[...]},
                        "routines":{
                                "monitor":<function>,
                                "search":<function>,
                                "maintain":<function>,
                                "operate":<function>},
                        "loop_interval":<loop interval (seconds)},
                    ...},
                ...}

            - Each state database represents one `Machine.state_machine`.
            - Each state machine is run in an independent thread within the
              main loop of `Machine.operate_machine`.

            "settings":
                - Device settings will be applied before the system transitions
                  into this state.
                - Only the device settings particular to a state need to be
                  listed, and they should be in the same format as those in
                  `SETTINGS`::

                    "settings":{
                        <device database path>:{
                            <method>:<args>,
                            ...},
                        ...}

                - The device settings listed here should be thought of as
                  stationary prerequisites, or as known initialization states
                  that the system should pass through to ease the transition to
                  the compliant state.
                - Dynamic device settings should be dealt with inside of the
                  state's "search", "maintain", or "operate" methods.
                - Place groups of device settings together in lists if the
                  order of the operations matter. The groups of settings will
                  be applied as ordered in the list::

                      "settings":{
                          <device database path>:[
                              {<first group>},
                              {<second group>},
                              ...],
                          ...}

                - "settings" may also be used as a repository for any
                  non-device associated parameters. The only requirement is
                  that this setting's key is not a device databse::

                      "settings":{
                          <not a device database path>:<some fixed parameter>}

                - These general settings can then be freely referenced within
                  the state's methods.

            "prerequisites":
                - Prerequisites should be entered as lists of dictionaries that
                  include the database, key, and test function that indicates
                  whether the database value corresponds to a passing
                  prerequisite for the given state::

                      "prerequisites":{
                          "critical":[
                              {"db":<database path>,
                              "key":<entry's key>,
                              "test":<test function>,
                              "doc":<test function docs>},
                               ...],
                          "necessary":[...],
                          "optional":[...],
                          "exit":[...]}

                - The "test" should be a function or lambda function that
                  accepts the database value and evaluates to `True` if the
                  prerequisite has passed.
                - The "doc" is a recommended keyword that may be used to store
                  text for more readable prerequisite logs. Since the code of a
                  lambda function is not printable, this key should contain a
                  stringed version of the lambda function, or some other
                  documenation of the test function.
                - A list of keys may be entered in order to access values
                  within nested dictionaries (see `Machine.from_keys`)::

                      "key":[<outermost key>, ..., <innermost key>]

                - Prereqs are separated by severity:
                "critical":
                    - A failed critical prereq could jeopardize the health of
                      the system if brought into or left in the applied state.
                    - Critical prerequisites are continuously monitored.
                    - The system is placed into a temporary "safe" state upon
                      failure of a critical prereq.
                "necessary":
                    - Failure of a necessary prereq will cause the system to
                      come out of, or be unable to reach, compliance.
                    - Necessary prereqs are checked if the system is out
                      of compliance.
                    - The system is allowed to move into the applied state upon
                      failure of a necessary prereq, but no attempts are made
                      to bring the system into compliance.
                "optional":
                    - Failure of an optional prereq should not cause failure
                      elsewhere, but system performance or specifications can't
                      be guaranteed. Think of it more as "non compulsory" than
                      "optional".
                    - Optional prereqs are checked when the system is out of
                      compliance, and when the system is in compliance, but the
                      optional prereqs are listed as failed.
                    - The system is allowed to move into the applied state upon
                      failure of an optional prereq.
                "exit":
                    - The failure of an exit prereq prevents the system from
                      moving away from the current state.
                    - These are only checked during normal operation when
                      the desired state does not equal the current.
                    - Exit prereqs are not checked if the state change is
                      caused by the failure of a critical prereq (critical
                      has priority).
                    - This prereq is most useful for preventing the transfer
                      away from the "safe" state before the actual problem
                      has been resolved.

            "routines":
                - The routines are the functions needed to monitor the state,
                  bring the state into compliance, maintain the state in
                  compliance, and operate any other scripts that require a
                  compliant state.
                - All routines must accept the path of a state DB as an
                  argument for access to the compliance state variable.
                - The compliance state variable is accessible by calling::

                        self.current_state[<state database path>]['compliance']

                - Only one function call should be listed for each method. The
                  methods themselves may call others.
                - Routines should be entered for the 4 cases::

                    "routines":{
                        "monitor":<function>,
                        "search":<function>,
                        "maintain":<function>,
                        "operate":<function>}

                "monitor":
                    - The monitor method should generally update all state
                      parameters necessary for the "search" or "maintain"
                      methods as well as any secondary parameters useful for
                      passive monitoring.
                    - Updating state parameters includes getting new values
                      from connected instruments and pulling new values from
                      connected databases.
                    - New values from instruments should always be saved to
                      their respective databases. The main entry in the
                      database should typically be keyed with the symbols for
                      the units of the measurement (V, Hz, Ohm,...)::

                          self.db[device_db].write_record_and_buffer(
                              {<unit>:<value>})

                    - Suggested refresh times for control loop parameters is
                      0.2 seconds, while a 1.0 second or longer refresh time
                      should be sufficient for passive monitoring parameters.
                    - All values should be stored locally in circular buffers.
                      The sizes of which should be controlled within the
                      "monitor" method.
                "search":
                    - The search method should be able to bring the system into
                      compliance from any noncompliant state.
                    - The most important cases to consider are those starting
                      from the configuration as given in the state's
                      "settings", and the cases where the state has
                      transitioned from a compliant to a noncompliant state.
                    - It is the search method's responsibility to change the
                      state's compliance state variable as the "maintain" and
                      "operate" scripts are only called if the state's
                      compliance variable is set to `True`.
                    - The search method should use testing criteria to
                      determine if the found state is truly in compliance
                      before setting the state's compliance variable.
                    - Any important device setting changes should be propogated
                      to their respective databases.
                "maintain":
                    - The maintain method should observe the state parameters
                      and make any needed adjustments to the state settings in
                      order to maintain the state.
                    - If time series are needed in order to maintain the state,
                      a global variable may be used within the maintain and
                      search methods to indicate when the search method brought
                      the state into compliance. The maintain method may then
                      use that knowledge to selectively pull values from the
                      "monitor" buffers or simply clear the buffers on first
                      pass.
                    - The maintain method is responsible for changing the
                      compliance variable to `False` if it is unable to maintain
                      the state.
                    - Any important device setting changes should be propogated
                      to their respective databases.
                "operate":
                    - The operate method is a catchall function for use cases
                      that are only valid while the state is in compliance. An
                      example is to only read values from an instrument buffer
                      while the instrument's data collection state is active.

            "loop_interval":
                - Specifies the desired loop interval, in seconds, of the state
                  machine. If not provided, each state machine automatically
                  has the same loop interval as the main loop.
                - This is the interval between checks of the prereqs and calls
                  to the state machine's routines.
        '''
        self.STATES = STATES

# Run the main loop -----------------------------------------------------------
    @log.log_this()
    def operate_machine(self, current_state={}, main_loop_interval=0.5):
        mod_name = self.operate_machine.__module__
        func_name = self.operate_machine.__name__
        log_str = " Operating state machine"
        log.log_info(mod_name, func_name, log_str)
        #--- Current State ----------------------------------------------------
        self.current_state = current_state
        for state_db in self.STATE_DBs:
            self.current_state[state_db] = self.db[state_db].read_buffer()
            if self.current_state[state_db]['initialized'] != False:
                self.current_state[state_db]['initialized'] = False
                self.db[state_db].write_record_and_buffer(self.current_state[state_db])

        #--- Initialize Failed Prereq Log Timers ------------------------------
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

        #--- Initialize State Machine Timers ----------------------------------
        '''The main loop timers are used to coordinate the threads of the main
        loop. Threads are expected to execute within this time interval. This
        is also the interval in which the main loop checks on its threads.
        '''
        self.loop_interval = {}
        self.loop_timer = {}
        # Main Loop
        self.loop_interval['main'] = main_loop_interval # seconds
        self.loop_timer['main'] = get_lap(self.loop_interval['main'])+1
        # State Machines
        for state_db in self.STATE_DBs:
            if 'loop_interval' in self.STATES[state_db]:
                self.loop_interval[state_db] = self.STATES[state_db]['loop_interval']
            else:
                self.loop_interval[state_db] = main_loop_interval
            self.loop_timer[state_db] = get_lap(self.loop_interval[state_db])+1
        # Communications
        self.loop_interval['check_for_messages'] = main_loop_interval
        self.loop_timer['check_for_messages'] = get_lap(self.loop_interval['check_for_messages'])+1
        #--- Initialize Thread Events -----------------------------------------
        for state_db in self.STATE_DBs:
            self.event[state_db] = threading.Event()
        self.event[self.COMMS] = threading.Event()
        #--- Initialize Threads -----------------------------------------------
        for state_db in self.STATE_DBs:
            self.thread[state_db] = ThreadFactory(target=self.state_machine, args=[state_db])
        self.thread[self.COMMS] = ThreadFactory(target=self.check_for_messages)
        #--- Main Loop --------------------------------------------------------
        while self.local_settings[self.CONTROL_DB]['main_loop']['value']:
            #--- Maintain Threads ---------------------------------------------
            errors = []
            for state_db in self.STATE_DBs:
                errors.append(self.maintain_thread(state_db))
            errors.append(self.maintain_thread(self.COMMS))
            #--- Check for Errors ---------------------------------------------
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
            # Update log
                log_str = " Operating state machine"
                log.log_info(mod_name, func_name, log_str)
            #--- Pause --------------------------------------------------------
            pause = (self.loop_timer['main']+1)*self.loop_interval['main'] - time.time()
            if pause > 0:
                time.sleep(pause)
                self.loop_timer['main'] += 1
            else:
                log_str = " Execution time exceeded the set loop interval {:}s by {:.2g}s".format(self.loop_interval['main'], abs(pause))
                log.log_info(mod_name, func_name, log_str)
                self.loop_timer['main'] = get_lap(self.loop_interval['main'])+1
        #--- Main Loop has exited ---------------------------------------------
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
        mod_name = self.state_machine.__module__
        func_name = '.'.join([self.state_machine.__name__, state_db])
        log_str = " Operating {:}".format(state_db)
        log.log_info(mod_name, func_name, log_str)
        #--- Main Loop --------------------------------------------------------
        while not(self.event[state_db].is_set()):
            #--- Check the Critical Prerequisites -----------------------------
            critical_pass = self.check_prereqs(
                    state_db,
                    self.current_state[state_db]['state'],
                    'critical', log_all_failures=True)
            # Place into safe state if critical prereqs fail
            if not critical_pass:
                # Update the state variable
                with self.lock[state_db]:
                    self.current_state[state_db]['prerequisites']['critical'] = critical_pass
                    self.db[state_db].write_record_and_buffer(self.current_state[state_db])
                self.setup_state(state_db, 'safe')

            #--- Monitor the Current State ------------------------------------
            self.STATES[state_db][self.current_state[state_db]['state']]['routines']['monitor'](state_db)

            #--- Maintain the Current State -----------------------------------
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

            #--- State initialized --------------------------------------------
            with self.lock[state_db]:
                if not(self.current_state[state_db]['initialized']):
            # Update the state variable
                    self.current_state[state_db]['initialized'] = True
                    self.db[state_db].write_record_and_buffer(self.current_state[state_db])

            #--- Operate the Current State ------------------------------------
            # If compliant,
            if self.current_state[state_db]['compliance'] == True:
                self.STATES[state_db][self.current_state[state_db]['state']]['routines']['operate'](state_db)

            #--- Check Desired State ------------------------------------------
            state = self.current_state[state_db]['state']
            desired_state = self.current_state[state_db]['desired_state']
            if state != desired_state:
                state = self.current_state[state_db]['state']
                desired_state = self.current_state[state_db]['desired_state']
            # Check the prerequisites of the desired states
                if 'critical' in self.STATES[state_db][desired_state]['prerequisites']:
                    critical_pass = self.check_prereqs(
                            state_db,
                            desired_state,
                            'critical')
                else:
                    critical_pass = True
                if 'necessary' in self.STATES[state_db][desired_state]['prerequisites']:
                    necessary_pass = self.check_prereqs(
                            state_db,
                            desired_state,
                            'necessary')
                else:
                    necessary_pass = True
                if 'optional' in self.STATES[state_db][desired_state]['prerequisites']:
                    optional_pass = self.check_prereqs(
                            state_db,
                            desired_state,
                            'optional')
                else:
                    optional_pass = True
            # Check the "exit" prerequisites of the current state
                if 'exit' in self.STATES[state_db][state]['prerequisites']:
                    exit_pass = self.check_prereqs(
                            state_db,
                            state,
                            'exit')
                else:
                    exit_pass = True
            # Update the current state
                if (critical_pass and exit_pass):
                # Initialize the transition into the desired state
                    self.setup_state(
                            state_db,
                            desired_state,
                            critical=critical_pass,
                            necessary=necessary_pass,
                            optional=optional_pass)

            #--- Write Heartbeat to Buffer ------------------------------------
            with self.lock[state_db]:
                self.current_state[state_db]['heartbeat'] = datetime.datetime.utcnow()
                self.db[state_db].write_buffer(self.current_state[state_db])

            #--- Pause --------------------------------------------------------
            pause = (self.loop_timer[state_db]+1)*self.loop_interval[state_db] - time.time()
            if pause > 0:
                time.sleep(pause)
                self.loop_timer[state_db] += 1
            else:
                log_str = " Execution time exceeded the set loop interval {:}s by {:.2g}s".format(self.loop_interval[state_db], abs(pause))
                log.log_info(mod_name, func_name, log_str)
                self.loop_timer[state_db] = get_lap(self.loop_interval[state_db])+1

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
                            log_failure = ((time.time() - self.log_failed_prereqs_timer[state_db][state][level][str(prereq)]) > self.error_interval)
                        else:
                        # Catch the failure for the first time
                            log_failure = True
                    else:
                    # If "log_all_failures" is set, use it.
                        log_failure = log_all_failures
                    if (log_failure == True):
                    # Update the error timer
                        self.log_failed_prereqs_timer[state_db][state][level][str(prereq)] = time.time()
                    # Log failure
                        mod_name = self.check_prereqs.__module__
                        func_name = self.check_prereqs.__name__
                        if (level=='critical'):
                            log_str = '"Critical" prerequisite failure:\n state_db:\t{:}\n state:\t\t{:}\n prereq:\t{:}\n current:\t{:}'.format(state_db, state, prereq, prereq_value)
                            log.log_critical(mod_name,func_name,log_str)
                        elif (level=='necessary'):
                            log_str = '"Necessary" prerequisite failure:\n state_db:\t{:}\n state:\t\t{:}\n prereq:\t{:}\n current:\t{:}'.format(state_db, state, prereq, prereq_value)
                            log.log_warning(mod_name,func_name,log_str)
                        elif (level=='optional'):
                            log_str = '"Optional" prerequisite failure:\n state_db:\t{:}\n state:\t\t{:}\n prereq:\t{:}\n current:\t{:}'.format(state_db, state, prereq, prereq_value)
                            log.log_warning(mod_name,func_name,log_str)
                        elif (level=='exit'):
                            log_str = '"Exit" prerequisite failure:\n state_db:\t{:}\n state:\t\t{:}\n prereq:\t{:}\n current:\t{:}'.format(state_db, state, prereq, prereq_value)
                            log.log_warning(mod_name,func_name,log_str)
                # Propogate prereq status
                prereqs_pass *= prereq_status
        return bool(prereqs_pass)

# Setup the Transition to a New State -----------------------------------------
    @log.log_this()
    def setup_state(self, state_db, state, critical=True, necessary=True, optional=True):
        '''A helper function to automate the process of setting up new states.
        '''
    # Log
        mod_name = self.setup_state.__module__
        func_name = self.setup_state.__name__
        log_str = ' Setting up {:}:{:}'.format(state_db, state)
        log.log_info(mod_name,func_name,log_str)
    # Update the device settings
        for database in self.STATES[state_db][state]['settings']:
            if database in self.DEVICE_DBs:
                self.update_device_settings(database, self.STATES[state_db][state]['settings'][database])
    # Update the state variable
        with self.lock[state_db]:
            self.current_state[state_db]['state'] = state
            self.current_state[state_db]['prerequisites'] = {
                    'critical':critical,
                    'necessary':necessary,
                    'optional':optional}
            self.current_state[state_db]['compliance'] = False
            self.db[state_db].write_record_and_buffer(self.current_state[state_db]) # The desired state should be left unaltered


# Update Device Settings ------------------------------------------------------
    @log.log_this()
    def update_device_settings(self, device_db, settings_list, write_log=True):
        '''A helper function to automate the process of updating the settings
        of a single device.
        '''
        mod_name = self.update_device_settings.__module__
        func_name = self.update_device_settings.__name__
        updated = False
    # Check settings_list type
        if isinstance(settings_list, dict):
        # If settings_list is a dictionary then use only one settings_group
            settings_list = [settings_list]
    # Wait for queue
        queued = self.dev[device_db]['queue'].queue_and_wait()
    # Push device settings
        with self.lock[device_db]:
            for settings_group in settings_list:
                for setting in settings_group:
                # Try sending the command to the device
                    try:
                        result = self.send_args(getattr(self.dev[device_db]['driver'], setting),settings_group[setting])
                    except:
                        error = sys.exc_info()
                        # Log the device, method, and arguments
                        if write_log:
                            prologue_str = ' device: {:}\n method: {:}\n   args: {:}'.format(device_db, setting, settings_group[setting])
                            log.log_info(mod_name, func_name, prologue_str)
                        raise error[1].with_traceback(error[2])
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
                    if write_log:
                        try:
                            epilogue_str = ' device: {:}\n method: {:}\n   args: {:}\n result: {:}'.format(device_db, setting, settings_group[setting], str(result))
                        except:
                            epilogue_str = ' device: {:}\n method: {:}\n   args: {:}\n result: {:}'.format(device_db, setting, settings_group[setting], '<result was not string-able>')
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

# Check the Communications Queue ----------------------------------------------
    @log.log_this()
    def check_for_messages(self):
        '''This checks for and parses new messages in the communications queue.
        '''
        mod_name = self.check_for_messages.__module__
        func_name = self.check_for_messages.__name__
        while not(self.event[self.COMMS].is_set()):
        # Parse the message ---------------------------------------------------
            for message in range(len(self.comms.get_queue())):
                message = self.comms.pop()
                self.parse_message(message)
        # Pause ---------------------------------------------------------------
            pause = (self.loop_timer['check_for_messages']+1)*self.loop_interval['check_for_messages'] - time.time()
            if pause > 0:
                time.sleep(pause)
                self.loop_timer['check_for_messages'] += 1
            else:
                log_str = " Execution time exceeded the set loop interval {:}s by {:.2g}s".format(self.loop_interval['check_for_messages'], abs(pause))
                log.log_info(mod_name, func_name, log_str)
                self.loop_timer['check_for_messages'] = get_lap(self.loop_interval['check_for_messages'])+1

# Parse Messages from the Communications Queue --------------------------------
    @log.log_this()
    def parse_message(self, message):
        '''A helper function to automate the parsing of messages from the
        communications queue.

        The communications queue is a couchbase queue that serves as the
        intermediary between this script and others. The entries in this queue
        are parsed into commands within this class:
            Requesting to change state::

                    message = {"state":{
                                  <state DB path>:{"state":<state>},...}}

            Requesting to change device settings::

                    message = {"device_setting":{
                                  <device driver DB path>:{
                                      <method name>:<args>,...},...}}

            Requesting to change a control parameter::

                    message = {"control_parameter":{
                                  <parameter name>:<value>,...}}

        - Commands are sent into the queue by setting the "message" keyword
          argument within the CouchbaseDB queue.push() method.
        - Commands are read from the queue with the queue.pop() method.
        - If the DB path given does not exist in the defined `STATE_DBs` and
          `DEVICE_DBs`, or the given method and parameter does not exist in
          `CONTROL_PARAMS`, no attempt is made to excecute the command.
        - All commands are caught and logged at the INFO level.
        - Multiple commands may be input simultaneously by nesting single
          commands within the "state", "device_setting", and
          "control_parameter" keys::

            message = {
                "state":{
                    <state DB path>:{"state":<state>},...},
                "device_setting":{
                    <device driver DB path>:{
                        <method name>:<args>,...},...},
                "control_parameter":{
                    <parameter name>:<value>,...}}
        '''
        mod_name = self.parse_message.__module__
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
                                elif self.current_state[state_db]['state'] == desired_state:
                                # Force the state to check compliance
                                    self.current_state[state_db]['compliance'] = False
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
                with self.lock[self.CONTROL_DB]:
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
                mod_name = self.thread[thread_name].target.__module__
                func_name = self.thread[thread_name].target.__name__
                err_str = thread_name+''.join(traceback.format_exception_only(error[0], error[1]))
                if (err_str in self.error):
                    if (time.time() - self.error[err_str]) > self.error_interval:
                        log.log_exception_info(mod_name, func_name, error)
                    else:
                        log.log_info(mod_name, func_name, ' Iteration {:}'.format(loop_count))
                else:
                    self.error[err_str] = time.time()
                    log.log_exception_info(mod_name, func_name, error)
                time.sleep(0.5)
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
            mod_name = self.thread[thread_name].target.__module__
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

    # Do nothing function ---------------------------------------------------------
    def nothing(self, *args, **kwargs):
        '''A functional placeholder for cases where nothing should happen.'''
        pass
