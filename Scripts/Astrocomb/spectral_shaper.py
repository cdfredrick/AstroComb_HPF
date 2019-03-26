# -*- coding: utf-8 -*-
"""
Created on Wed Apr 25 13:15:58 2018

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

from Drivers.StateMachine import ThreadFactory, Machine

from Drivers.Thorlabs.APT import KDC101_PRM1Z8
from Drivers.VISA.Yokogawa import OSA
from Drivers.VISA.Keysight import E36103A

#Import the tkinter module
import tkinter
#Import the Pillow module
from PIL import Image, ImageTk


# %% Initialization ===========================================================

sm = Machine()


# %% Helper Functions =========================================================

'''The following are helper functionss that increase the readablity of code in
    this script. These functions are defined by the user and should not
    directly appear in the main loop of the state machine.'''

# Tomorrow at Noon ------------------------------------------------------------
def tomorrow_at_noon():
    tomorrow = datetime.date.today()+datetime.timedelta(days=1)
    noon = datetime.time(hour=12)
    return datetime.datetime.combine(tomorrow,noon).timestamp()

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

# Full Screen -----------------------------------------------------------------
image_dir = ['']
class FullScreen():
    def __init__(self, dimensions=None, position=None, auto_scale=False):
        self.auto_scale = auto_scale
    # Initialize Tk -----------------------------------------------------------
        self.root = tkinter.Tk()
    # Initialize the Window ---------------------------------------------------
        # Window Geometry
        if (dimensions==None):
            self.w = self.root.winfo_screenwidth() # screen width
            self.h = self.root.winfo_screenheight() # screen height
        else:
            self.w = dimensions['w']
            self.h = dimensions['h']
        if (position==None):
            self.x = 0 # horizontal position
            self.y = 0 # vertical position
        else:
            self.x = position['x']
            self.y = position['y']
        # Window Display Settings
        self.root.overrideredirect(1) # remove Window's window manager decorations
        self.root.attributes("-topmost", True) # always on top
        self.root.configure(cursor='pirate') # skull and crossbones cursor
        self.root.geometry("{0:}x{1:}+{2:}+{3:}".format(self.w, self.h, self.x, self.y)) # set the window geometry
    # Initialize the Canvas ---------------------------------------------------
        self.canvas = tkinter.Canvas(self.root,width=self.w,height=self.h)
        self.canvas.configure(background="black") # set background color
        self.canvas.configure(highlightthickness=0) # remove border
        self.canvas.pack()

    def load_image(self, image_path):
        image_dir[0] = image_path
        self.pilImage = Image.open(image_path)
        if self.auto_scale:
        # Scale the Image if Too Large
            imgWidth, imgHeight = self.pilImage.size
            if imgWidth > self.w or imgHeight > self.h:
                ratio = min(self.w/imgWidth, self.h/imgHeight)
                imgWidth = int(imgWidth*ratio)
                imgHeight = int(imgHeight*ratio)
                self.pilImage = self.pilImage.resize((imgWidth,imgHeight), Image.ANTIALIAS)
        # Convert to Tk
        self.image = ImageTk.PhotoImage(self.pilImage)

    def draw(self):
    # Draw the image
        self.canvas.create_image(self.w/2,self.h/2,image=self.image)
    # Bring to front ----------------------------------------------------------
        self.root.lift()
    # Display -------------------------------------------------------------
        self.root.update()

    def destroy(self):
        self.root.destroy()

# Queue Worker ----------------------------------------------------------------
def tkinter_worker(dimensions={'w':1920, 'h':1152}, position={'x':-1920, 'y':-1152}, auto_scale=False):
    '''Run this function in a thread and use the associated queue object to
    pass new images.

    The tk interface can only be called from a single thread per interpreter
    session. If the thread that it is running in fails, it cannot be started
    again in the same interpreter session.
    '''
    tk_obj = FullScreen(dimensions=dimensions, position=position, auto_scale=auto_scale)
    loop = True
    while loop:
        try:
            item = tkinter_queue.get(block=False)
        except queue.Empty:
            time.sleep(0.1) # don't hog the CPU
        else:
            tk_obj.load_image(item)
            tk_obj.draw()
            tkinter_queue.task_done()
tkinter_thread = threading.Thread(target=tkinter_worker)
tkinter_thread.start()
tkinter_queue = queue.Queue()


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
COMMS = 'spectral_shaper'
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
        'spectral_shaper/state_SLM', 'spectral_shaper/state_optimizer']
DEVICE_DBs =['spectral_shaper/device_OSA',
             'spectral_shaper/device_rotation_mount',
             'spectral_shaper/device_IM_bias']
MONITOR_DBs = [
        'spectral_shaper/mask', 'spectral_shaper/spectrum',
        'spectral_shaper/DW', 'spectral_shaper/DW_vs_IM_bias',
        'spectral_shaper/DW_vs_waveplate_angle',
        'spectral_shaper/DW_bulk_vs_waveplate_angle']
LOG_DB = 'spectral_shaper'
CONTROL_DB = 'spectral_shaper/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]
sm.init_master_DB_names(STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB)

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = ['broadening_stage/device_rotation_mount',
                 'comb_generator/device_IM_bias']
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
        'spectral_shaper/state_SLM':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'flat',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()},
        'spectral_shaper/state_optimizer':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'optimal',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()}}
DEVICE_SETTINGS = {
        'spectral_shaper/device_rotation_mount':{
                'driver':KDC101_PRM1Z8,
                'queue':'27251608',
                '__init__':[[''], #TODO: add COM port
                            {'timeout':5,
                             'serial_number':27251608}]},
        'spectral_shaper/device_OSA':{
                'driver':OSA,
                'queue':'GPIB0::27',
                '__init__':[['GPIB0::27::INSTR']]},
        'spectral_shaper/device_IM_bias':{
                'driver':E36103A,
                'queue':'IM_bias',
                '__init__':[['USB0::0x2A8D::0x0702::MY57427460::INSTR']]}}
CONTROL_PARAMS = {
        CONTROL_DB:{
                'setpoint_optimization':{'value':tomorrow_at_noon(),'type':'float'},
                'DW_setpoint':{'value':-45.5,'type':'float'}}}
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
mon['spectral_shaper/mask'] = {
        'data':{'path':''},
        'device':None,
        'new':False,
        'lock':threading.Lock()}
mon['spectral_shaper/spectrum'] = {
        'data':{},
        'device':dev['spectral_shaper/device_OSA'],
        'new':False,
        'lock':threading.Lock()}
mon['spectral_shaper/DW'] = {
        'data':np.array([]),
        'device':dev['spectral_shaper/device_OSA'],
        'new':False,
        'lock':threading.Lock()}
mon['spectral_shaper/DW_vs_IM_bias'] = {
        'data':np.array([]),
        'device':None,
        'new':False,
        'lock':threading.Lock()}
mon['spectral_shaper/DW_vs_waveplate_angle'] = {
        'data':np.array([]),
        'device':None,
        'new':False,
        'lock':threading.Lock()}
mon['spectral_shaper/DW_bulk_vs_waveplate_angle'] = {
        'data':np.array([]),
        'device':None,
        'new':False,
        'lock':threading.Lock()}
    # External ------------------------
sm.init_monitors(mon=mon)


# %% State Functions ==========================================================

# Global Timing Variable ------------------------------------------------------
timer = {}
thread = {}
array = {}
warning = {}
warning_interval = 100 # seconds

# Do nothing function ---------------------------------------------------------
'''A functional placeholder for cases where nothing should happen.'''
@log.log_this()
def nothing(state_db):
    pass


# %% Monitor Functions ========================================================
'''This section is for defining the methods needed to monitor the system.'''

# Initialize monitor
monitor_db = 'broadening_stage/device_rotation_mount'
 # Update buffers -----------------------
with mon[monitor_db]['lock']:
    mon[monitor_db]['new'] = True
    mon[monitor_db]['data'] = update_buffer(
        mon[monitor_db]['data'],
        db[monitor_db].read_buffer()['position'], 500)

# Get Spectrum from OSA -------------------------------------------------------
array['spectrum'] = np.array([])
array['DW'] = np.array([])
spectrum_record_interval = 1000 # seconds
timer['spectrum:record'] = get_lap(spectrum_record_interval)
def get_spectrum():
# Get lap number
    new_record_lap = get_lap(spectrum_record_interval)
# Device DB
    device_db = 'spectral_shaper/device_OSA'
# Wait for queue
    dev[device_db]['queue'].queue_and_wait()
# Setup OSA
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['full']
    sm.update_device_settings(device_db, settings_list, write_log=False)
# Get New Trace
    thread_name = 'get_new_single'
    (alive, error) = thread[thread_name].check_thread()
    if error != None:
        raise error[1].with_traceback(error[2])
    if not(alive):
    # Start new thread
        thread[thread_name].start()
# Check Progress
    while thread[thread_name].is_alive():
        time.sleep(0.1)
        dev[device_db]['queue'].touch()
# Remove from Queue
    dev[device_db]['queue'].remove()
# Get Result
    (alive, error) = thread[thread_name].check_thread()
    if error != None:
        raise error[1].with_traceback(error[2])
    else:
        osa_trace = thread[thread_name].result
# Update buffers and databases --------------------------------------
    # Dispersive Wave -------------------------------------
    monitor_db = 'spectral_shaper/DW'
    array_id = 'DW'
    dw_ind = ((np.array(osa_trace['data']['x']) < 740) * (np.array(osa_trace['data']['x']) > 690)).astype(np.bool)
    data = np.max(np.array(osa_trace['data']['y'])[dw_ind])
    with mon[monitor_db]['lock']:
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = update_buffer(
                mon[monitor_db]['data'],
                data, 100)
    db[monitor_db].write_buffer({'dBm':data})
        # Append to the record array
    array[array_id] = np.append(array[array_id], data)
    if (new_record_lap > timer['spectrum:record']):
        # Record statistics ---------------------
        db[monitor_db].write_record({
                'dBm':array[array_id].mean(),
                'std':array[array_id].std(),
                'n':array[array_id].size})
        # Empty the array
        array[array_id] = np.array([])
    # Spectrum -----MUST BE LAST!!!------------------------
    monitor_db = 'spectral_shaper/spectrum'
    array_id = 'spectrum'
    with mon[monitor_db]['lock']:
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = osa_trace
    db[monitor_db].write_buffer(osa_trace)
        # Append to the record array
    if (array[array_id].size == 0):
        array[array_id] = np.array(osa_trace['data']['y'])
    else:
        array[array_id] = np.vstack([array[array_id], osa_trace['data']['y']])
    if new_record_lap > timer['spectrum:record']:
        # Record statistics ---------------------
        y_mean = array[array_id].mean(axis=0).tolist()
        y_std = array[array_id].std(axis=0).tolist()
        y_n = array[array_id].shape[0]
        osa_trace['data']['y'] = y_mean
        osa_trace['data']['y_std'] = y_std
        osa_trace['data']['y_n'] = y_n
        db[monitor_db].write_record(osa_trace)
        # Empty the array
        array[array_id] = np.array([])
# Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer['spectrum:record']:
        timer['spectrum:record'] = new_record_lap
thread['get_spectrum'] = ThreadFactory(target=get_spectrum)
thread['get_new_single'] = ThreadFactory(target=dev['spectral_shaper/device_OSA']['driver'].get_new_single)
thread['get_new_single_quick'] = ThreadFactory(target=dev['spectral_shaper/device_OSA']['driver'].get_new_single, kwargs={'get_parameters':False})

# Record Spectrum -------------------------------------------------------------
control_interval = 0.5 # s
spectrum_interval = 100.0 # s
timer['monitor_spectrum:control'] = get_lap(control_interval)
timer['monitor_spectrum:spectrum'] = get_lap(spectrum_interval)
def monitor_spectrum(state_db):
# Get lap number
    new_control_lap = get_lap(control_interval)
    new_spectrum_lap = get_lap(spectrum_interval)
# Update control loop variables -------------------------------------
    if (new_control_lap > timer['monitor_spectrum:control']):
# Pull data from external databases -----------------------
    # Rotation Mount
        new_data = []
        monitor_db = 'broadening_stage/device_rotation_mount'
        for doc in mon[monitor_db]['cursor']:
            new_data.append(doc['position'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            with mon[monitor_db]['lock']:
                mon[monitor_db]['new'] = True
                mon[monitor_db]['data'] = update_buffer(
                    mon[monitor_db]['data'],
                    new_data, 500)
    # Intensity Modulator Bias
        new_data = []
        monitor_db = 'comb_generator/device_IM_bias'
        for doc in mon[monitor_db]['cursor']:
            new_data.append(doc['voltage_setpoint'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            with mon[monitor_db]['lock']:
                mon[monitor_db]['new'] = True
                mon[monitor_db]['data'] = update_buffer(
                    mon[monitor_db]['data'],
                    new_data, 500)
    # Propogate lap numbers -------------------------------
        timer['monitor_spectrum:control'] = new_control_lap
# Update spectrum ---------------------------------------------------
    if (new_spectrum_lap > timer['monitor_spectrum:spectrum']):
    # Get Spectrum ----------------------------------------
        thread_name = 'get_spectrum'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Propogate lap numbers -------------------------------
        timer['monitor_spectrum:spectrum'] = new_spectrum_lap


# %% Search Functions =========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''

# Apply Mask ------------------------------------------------------------------
def apply_mask(state_db):
    mod_name = apply_mask.__module__
    func_name = apply_mask.__name__
    mask_path = STATES[state_db][current_state[state_db]['state']]['settings']['mask']
    tkinter_queue.put(mask_path, block=False)
    tkinter_queue.join()
    # Update the state variable
    with sm.lock[state_db]:
        current_state[state_db]['compliance'] = True
        db[state_db].write_record_and_buffer(current_state[state_db])
    # Update Monitor
    monitor_db = 'spectral_shaper/mask'
    with mon[monitor_db]['lock']:
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = {'path':mask_path}
    db[monitor_db].write_record_and_buffer({'path':mask_path})
    # Log
    log_str = ' Mask successfully changed to "{:}"'.format(mask_path)
    log.log_info(mod_name, func_name, log_str)

# Adjust Chip Input Power (Fast) ----------------------------------------------
DW_limits = 2. #4.5 #{'max':-41, 'min':-50}
DW_range_threshold = 1. # 3.5/9 #  3.5/9 for -44.5 and -46.5 soft limits :: 1/3.6 for -43.5 and -47.5 soft limits
minimum_angle = 20 # degrees
maximum_angle = 52 # degrees
def adjust_quick(state_db):
    mod_name = adjust_quick.__module__
    func_name = adjust_quick.__name__
    osa_db = 'spectral_shaper/device_OSA'
    rot_db = 'spectral_shaper/device_rotation_mount'
# DW threshold
    DW_high = local_settings[CONTROL_DB]['DW_setpoint']['value']+DW_range_threshold # (1-DW_range_threshold)*DW_limits['max'] + DW_range_threshold*DW_limits['min']
    DW_low = local_settings[CONTROL_DB]['DW_setpoint']['value']-DW_range_threshold # (1-DW_range_threshold)*DW_limits['min'] + DW_range_threshold*DW_limits['max']
# Wait for OSA queue
    dev[osa_db]['queue'].queue_and_wait()
# Setup OSA
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['DW']
    sm.update_device_settings(osa_db, settings_list, write_log=False)
# Adjust 2nd Stage Power
    dev[rot_db]['queue'].queue_and_wait()
    continue_adjusting_angle = True
    DWs = []
    angles = []
    while continue_adjusting_angle:
    # Ensure Queues
        dev[osa_db]['queue'].queue_and_wait()
        dev[rot_db]['queue'].queue_and_wait()
    # Get New Trace
        thread_name = 'get_new_single_quick'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Check Progress
        while thread[thread_name].is_alive():
            time.sleep(0.1)
            dev[osa_db]['queue'].touch()
            dev[rot_db]['queue'].touch()
    # Get Result
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        else:
            osa_trace = thread[thread_name].result
    # Get DW
        current_DW = np.max(osa_trace['data']['y'])
        DWs.append(current_DW)
    # Get Rotation Mount Position
        current_angle = dev[rot_db]['driver'].position()
        angles.append(current_angle)
    # Minimum angle condition
        lower_angle_condition = (current_angle < minimum_angle)
    # Check compliance
        DW_diff = current_DW - local_settings[CONTROL_DB]['DW_setpoint']['value']
        upper_limit_condition = (current_DW > DW_high)
        lower_limit_condition = (current_DW < DW_low)
    # Adjust the setpoint
        if lower_limit_condition:
            if lower_angle_condition:
                warning_id = 'low_angle_fast'
                log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, but 2nd stage power is already at maximum'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'])
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)
                continue_adjusting_angle = False
            else:
                log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, raising the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                log.log_info(mod_name, func_name, log_str)
            # Raise the 2nd stage power
                settings_list = [{'position':current_angle-0.1}]
                sm.update_device_settings(rot_db, settings_list, write_log=False)
        elif upper_limit_condition:
            log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, lowering the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
            log.log_info(mod_name, func_name, log_str)
        # Lower the 2nd stage power
            settings_list = [{'position':current_angle+0.1}]
            sm.update_device_settings(rot_db, settings_list, write_log=False)
        else:
        # Good to go
            continue_adjusting_angle = False
# Remove from Queue
    dev[osa_db]['queue'].remove()
    dev[rot_db]['queue'].remove()
# Record Movement
    monitor_db = 'spectral_shaper/DW_vs_waveplate_angle'
    with mon[monitor_db]['lock']:
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = np.array([angles, DWs])
    db[monitor_db].write_record_and_buffer({'deg':angles, 'dBm':DWs})
# Update State Variable
    if not(upper_limit_condition or lower_limit_condition):
        with sm.lock[state_db]:
            current_state[state_db]['compliance'] = True
            db[state_db].write_record_and_buffer(current_state[state_db])
        # Log
        log_str = ' Spectrum successfully optimized at {:}deg'.format(current_angle)
        log.log_info(mod_name, func_name, log_str)


# %% Maintain Functions =======================================================
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''

# Check Mask ------------------------------------------------------------------
def check_mask(state_db):
    mod_name = check_mask.__module__
    func_name = check_mask.__name__
    mask_path = STATES[state_db][current_state[state_db]['state']]['settings']['mask']
    #current_mask = mon['spectral_shaper/mask']['data']['path']
    current_mask = image_dir[0]
    if (current_mask != mask_path):
        # Update the state variable
        with sm.lock[state_db]:
            current_state[state_db]['compliance'] = False
            db[state_db].write_record_and_buffer(current_state[state_db])
        # Log
        log_str = ' Current mask "{:}", switching to "{:}"'.format(current_mask, mask_path)
        log.log_info(mod_name, func_name, log_str)
        # Call apply_mask
        apply_mask(state_db)

# Adjust Chip Input Power (Slow) ----------------------------------------------
def adjust_slow(state_db):
    mod_name = adjust_slow.__module__
    func_name = adjust_slow.__name__
    compliant = True
# Get most recent values --------------------------------------------
    with mon['spectral_shaper/DW']['lock']:
        new_DW_condition = mon['spectral_shaper/DW']['new']
        mon['spectral_shaper/DW']['new'] = False
        if new_DW_condition:
            current_DW = mon['spectral_shaper/DW']['data'][-1]
    # DW threshold
    DW_high = local_settings[CONTROL_DB]['DW_setpoint']['value']+DW_range_threshold # (1-DW_range_threshold)*DW_limits['max'] + DW_range_threshold*DW_limits['min']
    DW_low = local_settings[CONTROL_DB]['DW_setpoint']['value']-DW_range_threshold # (1-DW_range_threshold)*DW_limits['min'] + DW_range_threshold*DW_limits['max']
# Check if the output is outside the acceptable range ---------------
    if new_DW_condition:
        if (current_DW < local_settings[CONTROL_DB]['DW_setpoint']['value']-DW_limits) or (current_DW > local_settings[CONTROL_DB]['DW_setpoint']['value']+DW_limits):
        # Spectrum is not optimized
            compliant = False
            log_str = " Spectrum not optimized, DW amplitude outside the acceptable range"
            log.log_error(mod_name, func_name, log_str)
# If not optimized --------------------------------------------------
    if not(compliant):
    # Update state variable
        with sm.lock[state_db]:
            current_state[state_db]['compliance'] = False
            db[state_db].write_record_and_buffer(current_state[state_db])
# If optimized ------------------------------------------------------
    else:
    # If the system is at a stable point, adjust the 2nd stage input power if necessary
        if (new_DW_condition):
            update = False
            DW_diff = current_DW - local_settings[CONTROL_DB]['DW_setpoint']['value']
            power_too_low = (DW_diff < 0)
            power_is_close = np.isclose(DW_diff, 0, atol=0.1)
            upper_limit_condition = (current_DW > DW_high)
            lower_limit_condition = (current_DW < DW_low)
            if not(power_is_close) or upper_limit_condition or lower_limit_condition:
                update = True
        # Update the temperature setpoint
            if not(update):
                pass
            else:
            # If approaching the state limits, adjust the 2nd stage power setpoint
                with mon['broadening_stage/device_rotation_mount']['lock']:
                    mon['broadening_stage/device_rotation_mount']['new'] = False
                    current_angle = mon['broadening_stage/device_rotation_mount']['data'][-1]
                    lower_angle_condition = (current_angle < minimum_angle)
                if lower_angle_condition and power_too_low:
                    warning_id = 'low_angle_slow'
                    log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, but 2nd stage power is already at maximum'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'])
                    if (warning_id in warning):
                        if (time.time() - warning[warning_id]) > warning_interval:
                            log.log_warning(mod_name, func_name, log_str)
                    else:
                        warning[warning_id] = time.time()
                        log.log_warning(mod_name, func_name, log_str)
                else:
                # Adjust the setpoint
                    device_db = 'spectral_shaper/device_rotation_mount'
                    if lower_limit_condition:
                        log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, raising the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                        log.log_info(mod_name, func_name, log_str)
                    # Raise the 2nd stage power
                        settings_list = [{'position':current_angle-0.1}]
                        sm.update_device_settings(device_db, settings_list, write_log=False)
                    elif upper_limit_condition:
                        log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, lowering the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                        log.log_info(mod_name, func_name, log_str)
                    # Lower the 2nd stage power
                        settings_list = [{'position':current_angle+0.1}]
                        sm.update_device_settings(device_db, settings_list, write_log=False)
                    else:
                        step_size = 0.05 + (0.1-0.05) * abs(DW_diff)/DW_range_threshold
                        if power_too_low:
                            log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, raising the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                            log.log_info(mod_name, func_name, log_str)
                        # Raise the 2nd stage power
                            settings_list = [{'position':current_angle-step_size}]
                            sm.update_device_settings(device_db, settings_list, write_log=False)
                        else:
                            log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, lowering the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                            log.log_info(mod_name, func_name, log_str)
                        # Lower the 2nd stage power
                            settings_list = [{'position':current_angle+step_size}]
                            sm.update_device_settings(device_db, settings_list, write_log=False)


# %% Operate Functions ========================================================
'''This section is for defining the methods called only when the system is in
    its defined states.'''

# Optimize IM Bias ------------------------------------------------------------
def optimize_IM_bias(state_db):
# Info
    mod_name = optimize_IM_bias.__module__
    func_name = optimize_IM_bias.__name__
    log_str = ' Beginning IM bias optimization'
    log.log_info(mod_name, func_name, log_str)
# Parameters
    IM_bias_limits = {'max':5.5, 'min':0.5}
    IM_scan_range = 0.100 # 100mV range, +-50mV
    IM_scan_offsets = IM_scan_range*np.linspace(-0.5, +0.5, 20) # 5mV step size
# Device Databases
    osa_db = 'spectral_shaper/device_OSA'
    IM_db = 'spectral_shaper/device_IM_bias'
# Wait for OSA queue
    dev[osa_db]['queue'].queue_and_wait()
# Setup OSA
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['DW']
    sm.update_device_settings(osa_db, settings_list, write_log=False)
# Wait for IM Bias Queue
    dev[IM_db]['queue'].queue_and_wait()
# Adjust IM Bias
    continue_adjusting_IM = True
    biases = []
    DWs = []
    while continue_adjusting_IM:
    # Get Voltage Setpoint
        current_bias = dev[IM_db]['driver'].voltage_setpoint()
        v_setpoints = current_bias + IM_scan_offsets
    # Dither IM Bias
        for v_setpoint in v_setpoints:
        # Ensure Queues
            dev[osa_db]['queue'].queue_and_wait()
            dev[IM_db]['queue'].queue_and_wait()
        # Adjust the setpoint
            biases.append(v_setpoint)
            settings_list = [{'voltage_setpoint':v_setpoint}]
            sm.update_device_settings(IM_db, settings_list, write_log=False)
        # Get New Trace
            thread_name = 'get_new_single_quick'
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            if not(alive):
            # Start new thread
                thread[thread_name].start()
        # Check Progress
            while thread[thread_name].is_alive():
                time.sleep(0.1)
                dev[osa_db]['queue'].touch()
                dev[IM_db]['queue'].touch()
        # Get Result
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            else:
                osa_trace = thread[thread_name].result
        # Get DW
            current_DW = np.max(osa_trace['data']['y'])
            DWs.append(current_DW)
    # Return to Original Setpoint
        settings_list = [{'voltage_setpoint':current_bias}]
        sm.update_device_settings(IM_db, settings_list, write_log=False)
    # Find Maximum DW
        # Quadratic Fit
        poly_coef = np.polyfit(np.array(biases)-current_bias, DWs, 2)
        poly_fit = np.poly1d(poly_coef)
        stationary_point = poly_fit.deriv().roots
        maximum_found = False
        within_range = False
        if stationary_point.size:
        # is it a maximum?
            max_stationary_point = stationary_point[poly_fit(stationary_point).argmax()]
            maximum_found = (poly_fit(max_stationary_point) > poly_fit(np.min(biases)-current_bias)) and (poly_fit(max_stationary_point) > poly_fit(np.max(biases)-current_bias))
            within_range = (np.min(biases) <= max_stationary_point+current_bias <= np.max(biases))
            within_limits = (IM_bias_limits['min'] <= max_stationary_point+current_bias <= IM_bias_limits['max'])
        if (maximum_found and within_range and within_limits):
            new_setpoint = max_stationary_point+current_bias
            continue_adjusting_IM = False
            # Update IM bias
            settings_list = [{'voltage_setpoint':new_setpoint}]
            sm.update_device_settings(IM_db, settings_list, write_log=True)
            log_str = ' IM bias optimized at {:}V'.format(new_setpoint)
            log.log_info(mod_name, func_name, log_str)
        else:
        # Is the result sensible?
            bounds_equal_condition = np.isclose(poly_fit(IM_scan_offsets[0]), poly_fit(IM_scan_offsets[-1]))
            if bounds_equal_condition:
                continue_adjusting_IM = False
                warning_id = 'undetermined bias'
                log_str = ' Unable to determine IM bias adjustment'
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)
            else:
            # Maximum at low or high V?
                if maximum_found:
                    high_max_condition = (max_stationary_point+current_bias > np.max(biases))
                else:
                    high_max_condition = (poly_fit(np.min(biases)-current_bias) < poly_fit(np.max(biases)-current_bias))
                if high_max_condition:
                    new_setpoint = np.max(biases)
                else:
                    new_setpoint = np.min(biases)
                within_limits = (IM_bias_limits['min'] <= new_setpoint <= IM_bias_limits['max'])
                if not(within_limits):
                    continue_adjusting_IM = False
                    warning_id = 'bias limited'
                    log_str = ' Unable to optimize IM bias, new value of {:}V is outside the acceptable limits'.format(new_setpoint)
                    if (warning_id in warning):
                        if (time.time() - warning[warning_id]) > warning_interval:
                            log.log_warning(mod_name, func_name, log_str)
                    else:
                        warning[warning_id] = time.time()
                        log.log_warning(mod_name, func_name, log_str)
                else:
                # Adjust and repeat
                    settings_list = [{'voltage_setpoint':new_setpoint}]
                    sm.update_device_settings(IM_db, settings_list, write_log=False)
                    log_str = ' Moving IM bias to {:.5f}V'.format(new_setpoint)
                    log.log_info(mod_name, func_name, log_str)
# Remove from Queue
    dev[osa_db]['queue'].remove()
    dev[IM_db]['queue'].remove()
# Record Data
    monitor_db = 'spectral_shaper/DW_vs_IM_bias'
    with mon[monitor_db]['lock']:
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = np.array([biases, DWs])
    db[monitor_db].write_record_and_buffer({'V':biases, 'dBm':DWs})

# Optimize DW Setpoint --------------------------------------------------------
def optimize_DW_setpoint(state_db):
# Info
    mod_name = optimize_DW_setpoint.__module__
    func_name = optimize_DW_setpoint.__name__
    log_str = ' Beginning DW setpoint optimization'
    log.log_info(mod_name, func_name, log_str)
# Parameters
    angle_scan_range = 4 # 4 degree range, +-2 degree
    angle_scan_offsets = angle_scan_range*np.linspace(-0.5, +0.5, 20) # 0.2 deg step size
# Device Databases
    osa_db = 'spectral_shaper/device_OSA'
    rot_db = 'spectral_shaper/device_rotation_mount'
# Wait for OSA queue
    dev[osa_db]['queue'].queue_and_wait()
# Setup OSA
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['short']
    sm.update_device_settings(osa_db, settings_list, write_log=False)
# Wait for Rotation Stage Queue
    dev[rot_db]['queue'].queue_and_wait()
# Adjust Rotation Stage
    continue_adjusting_angle = True
    angles = []
    DWs = []
    bulks = []
    current_angle = mon['broadening_stage/device_rotation_mount']['data'][-1]
    while continue_adjusting_angle:
    # Get Angle Setpoints
        angle_setpoints = current_angle + angle_scan_offsets
    # Dither Angles
        for angle_setpoint in angle_setpoints:
        # Ensure Queues
            dev[osa_db]['queue'].queue_and_wait()
            dev[rot_db]['queue'].queue_and_wait()
        # Adjust the setpoint
            angles.append(angle_setpoint)
            settings_list = [{'position':angle_setpoint}]
            sm.update_device_settings(rot_db, settings_list, write_log=False)
        # Get New Trace
            thread_name = 'get_new_single_quick'
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            if not(alive):
            # Start new thread
                thread[thread_name].start()
        # Check Progress
            while thread[thread_name].is_alive():
                time.sleep(0.1)
                dev[osa_db]['queue'].touch()
                dev[rot_db]['queue'].touch()
        # Get Result
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            else:
                osa_trace = thread[thread_name].result
        # Get DW
            spectrum = np.array(osa_trace['data']['y'])
            wavelengths = np.array(osa_trace['data']['x'])
            current_DW = spectrum[wavelengths<740].max()
            current_bulk = spectrum[wavelengths>800].max()
            DWs.append(current_DW)
            bulks.append(current_bulk)
    # Return to Original Setpoint
        settings_list = [{'position':current_angle}]
        sm.update_device_settings(rot_db, settings_list, write_log=False)
    # Find Maximum DW
        # Fit
        DW_poly_fit = np.poly1d(np.polyfit(np.array(angles)-current_angle, DWs, 2))
        bulk_poly_fit = np.poly1d(np.polyfit(np.array(angles)-current_angle, bulks, 3))
        stationary_points = bulk_poly_fit.deriv().roots
        maximum_found = False
        within_range = False
        within_limits = False
        if stationary_points.size:
        # is it a maximum?
            max_stationary_point = stationary_points[bulk_poly_fit(stationary_points).argmax()]
            maximum_found = (bulk_poly_fit.deriv(2)(max_stationary_point) < 0)
            maximum_found = (bulk_poly_fit(max_stationary_point) > bulk_poly_fit(np.min(angles)-current_angle)) and (bulk_poly_fit(max_stationary_point) > bulk_poly_fit(np.max(angles)-current_angle))
            within_range = (np.min(angles) <= max_stationary_point+current_angle <= np.max(angles))
            within_limits = (minimum_angle <= max_stationary_point+current_angle <= maximum_angle)
        if (maximum_found and within_range and within_limits):
            new_setpoint = max_stationary_point
            continue_adjusting_angle = False
            # Move to optimal angular position
            settings_list = [{'position':current_angle+new_setpoint}]
            sm.update_device_settings(rot_db, settings_list, write_log=False)
            # Change DW setpoint
            new_DW_setpoint = DW_poly_fit(new_setpoint)
            with sm.lock[CONTROL_DB]:
                log_str = ' DW setpoint optimized at {:.3f}dBm'.format(new_DW_setpoint)
                log.log_info(mod_name, func_name, log_str)
                local_settings[CONTROL_DB]['DW_setpoint']['value'] = new_DW_setpoint
                db[CONTROL_DB].write_record_and_buffer(local_settings[CONTROL_DB])
        else:
        # Is the result sensible?
            bounds_equal_condition = np.isclose(bulk_poly_fit(np.min(angle_scan_offsets)), bulk_poly_fit(np.max(angle_scan_offsets)))
            if bounds_equal_condition:
                continue_adjusting_angle = False
                warning_id = 'undetermined DW setpoint'
                log_str = ' Unable to determine optimal DW setpoint'
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)
            else:
            # Maximum at low or high angle?
                if maximum_found:
                    high_max_condition = (max_stationary_point+current_angle > np.max(angles))
                else:
                    high_max_condition = (bulk_poly_fit(np.min(angles)-current_angle) < bulk_poly_fit(np.max(angles)-current_angle))
                if high_max_condition:
                    new_setpoint = np.max(angles)
                else:
                    new_setpoint = np.min(angles)
                within_limits = (minimum_angle <= new_setpoint <= maximum_angle)
                if not(within_limits):
                    continue_adjusting_angle = False
                    warning_id = 'angle limited'
                    log_str = ' Unable to optimize DW setpoint, new rotation stage angle of {:} deg is outside the acceptable limits'.format(new_setpoint)
                    if (warning_id in warning):
                        if (time.time() - warning[warning_id]) > warning_interval:
                            log.log_warning(mod_name, func_name, log_str)
                    else:
                        warning[warning_id] = time.time()
                        log.log_warning(mod_name, func_name, log_str)
                else:
                # Adjust offsets and repeat
                    angle_scan_offsets = angle_scan_offsets + (new_setpoint - current_angle) # center new scan at adjusted offset
# Remove from Queue
    dev[osa_db]['queue'].remove()
    dev[rot_db]['queue'].remove()
# Record Data
    monitor_db = 'spectral_shaper/DW_bulk_vs_waveplate_angle'
    with mon[monitor_db]['lock']:
        mon[monitor_db]['new'] = True
        mon[monitor_db]['data'] = np.array([angles, bulks, DWs])
    db[monitor_db].write_record_and_buffer({'deg':angles, 'bulk_dBm':bulks, 'DW_dBm':DWs})

# Optimize setpoints ----------------------------------------------------------
def optimize_setpoints(state_db):
    if (datetime.datetime.now().timestamp() > local_settings[CONTROL_DB]['setpoint_optimization']['value']):
        optimize_IM_bias(state_db)
        optimize_DW_setpoint(state_db)
    # Schedule next optimization
        with sm.lock[CONTROL_DB]:
            local_settings[CONTROL_DB]['setpoint_optimization']['value'] = tomorrow_at_noon()
            db[CONTROL_DB].write_record_and_buffer(local_settings[CONTROL_DB])

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
            or
            'settings':{
                <NOT device database path>:<something general>}
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
        'spectral_shaper/state_SLM':{
                'flat':{
                        'settings':{'mask':"flat_18-04-26_06-50.bmp"},
                        'prerequisites':{},
                        'routines':{
                                'monitor':nothing, 'search':apply_mask,
                                'maintain':check_mask, 'operate':nothing}
                        },
                'top':{
                        'settings':{'mask':"top_18-04-26_07-15.bmp"},
                        'prerequisites':{},
                        'routines':{
                                'monitor':nothing, 'search':apply_mask,
                                'maintain':check_mask, 'operate':nothing}
                        },
                'safe':{
                        'settings':{},
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
                                'maintain':nothing, 'operate':nothing}
                                }
                        },
        'spectral_shaper/state_optimizer':{
                'optimal':{
                        'settings':{
                                'spectral_shaper/device_OSA':{},
                                'DW':[
                                        {'fix_all':True},
                                        {'active_trace':'TRA'},
                                        {'trace_type':[[{'mode':'WRIT', 'avg':1}]],
                                         'sensitivity':[[{'sense':'HIGH1', 'chop':'OFF'}]],
                                         'wvl_range':[[{'start':690, 'stop':740}]],
                                         'resolution':2, 'level_scale':'LOG'}
                                        ],
                                'short':[
                                        {'fix_all':True},
                                        {'active_trace':'TRA'},
                                        {'trace_type':[[{'mode':'WRIT', 'avg':1}]],
                                         'sensitivity':[[{'sense':'HIGH1', 'chop':'OFF'}]],
                                         'wvl_range':[[{'start':690, 'stop':825}]],
                                         'resolution':2, 'level_scale':'LOG'}
                                        ],
                                'full':[
                                        {'fix_all':True},
                                        {'active_trace':'TRA'},
                                        {'trace_type':[[{'mode':'WRIT', 'avg':1}]],
                                         'sensitivity':[[{'sense':'HIGH1', 'chop':'OFF'}]],
                                         'wvl_range':[[{'start':690, 'stop':1320}]],
                                         'resolution':2, 'level_scale':'LOG'}
                                        ]
                                },
                        'prerequisites':{
                                'necessary':[
                                        {'db':'spectral_shaper/state_SLM',
                                         'key':'state',
                                         'test':(lambda state: ((state=='flat') or (state=='top'))),
                                         'doc':"lambda state: ((state=='flat') or (state=='top'))"},
                                        {'db':'spectral_shaper/state_SLM',
                                         'key':'compliance',
                                         'test':(lambda comp: (comp==True)),
                                         'doc':"lambda comp: (comp==True)"}
                                        ],
                                'critical':[
                                        {'db':'spectral_shaper/state_SLM',
                                         'key':'initialized',
                                         'test':(lambda init: (init==True)),
                                         'doc':"lambda init: (init==True)"}]
                                },
                        'routines':{
                                'monitor':monitor_spectrum, 'search':adjust_quick,
                                'maintain':adjust_slow, 'operate':optimize_setpoints}
                },
                'safe':{
                        'settings':{},
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
                                'maintain':nothing, 'operate':nothing}
                        }
                },
        }
sm.init_states(STATES)


# %% STATE MACHINE ============================================================

'''Operates the state machine.'''
current_state={}
sm.operate_machine(current_state=current_state, main_loop_interval=0.5)


