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

import os
import sys
sys.path.append(os.getcwd())

from Drivers.Logging import EventLog as log

from Drivers.StateMachine import ThreadFactory, Machine

from Drivers.Thorlabs.APT import KDC101_PRM1Z8, KPZ101, TNA001

from modules.optimizer import Minimizer


# %% Helper Functions =========================================================

'''The following are helper functions that increase the readablity of code in
    this script. These functions are defined by the user and should not
    directly appear in the main loop of the state machine.'''


# %% Initialization ===========================================================

sm = Machine()


# %% Databases and Settings ===================================================

#--- Communications queue -----------------------------------------------------
'''The communications queue is a couchbase queue that serves as the
intermediary between this script and others.
'''
COMMS = 'broadening_stage'
sm.init_comms(COMMS)


#--- Internal database names --------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function
'''
piezos = ['piezo_x_in', 'piezo_y_in', 'piezo_z_in',
          'piezo_x_out', 'piezo_y_out', 'piezo_z_out']
nanotracks = ['nanotrack_in', 'nanotrack_out']

STATE_DBs = [
    'broadening_stage/state_2nd_stage',
    ]

DEVICE_DBs =[
    'broadening_stage/device_rotation_mount',
    ]
for piezo in piezos:
    dev_db = 'broadening_stage/device_' + piezo
    DEVICE_DBs.append(dev_db)
for nt in nanotracks:
    dev_db = 'broadening_stage/device_' + nt
    DEVICE_DBs.append(dev_db)

MONITOR_DBs = [
    'broadening_stage/rot_stg_position',
    'broadening_stage/rot_stg_velocity',
    'broadening_stage/rot_stg_status',
    'broadening_stage/2nd_stage_z_in_optimizer',
    'broadening_stage/2nd_stage_z_out_optimizer',
    ]
for piezo in piezos:
    mon_db = 'broadening_stage/'+piezo+'_HV_output'
    MONITOR_DBs.append(mon_db)
for nt in nanotracks:
    monitors = ['_position', '_TIA', '_status']
    for monitor in monitors:
        mon_db = 'broadening_stage/' + nt + monitor
        MONITOR_DBs.append(mon_db)

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
sm.init_DBs()

#--- Start Logging ------------------------------------------------------------
'''Initializes logging for this script. If the logging database is unset then
all logs will be output to the stout.
'''
sm.init_logging(
    database_object=sm.db[LOG_DB],
    logger_level=logging.INFO,
    log_buffer_handler_level=logging.DEBUG,
    log_handler_level=logging.WARNING)

#--- Initialize All Devices and Settings --------------------------------------
'''This initializes all device drivers and checks that all settings
(as listed in SETTINGS) exist within the databases. Any missing
settings are populated with the default values.
-Each device database will be associated with a driver and a queue. The
format is as follows:
    dev[<device database path>] = {
            'driver':<driver object>,
            'queue':<queue objecct>}
'''
sm.init_device_drivers_and_settings()

#--- Initialize Local Copy of Monitors ----------------------------------------
'''Monitors should associate the monitor databases with the local, circular
buffers of the monitored data. Monitors should indicate when they have
recieved new data.
- Monitors from the internal databases should be associated with the
          device that they pull data from::

            {<database path>:{
                'data':<local data copy>,
                'new':<bool>}}

        - Monitors from the read database should have their cursors exhausted so
          that only their most recent values are accessible::

            {<database path>:{
                'data':<local data copy>,
                'cursor':<tailable cursor object>,
                'new':<bool>}}

        - Only the read databases are automatically populated. The monitors for the
          internal databases must be entered manually into `Machine.mon`.
'''
sm.init_monitors()


# %% State Functions ==========================================================
'''This section is for defining the helper functions, threads, and constants
used by the state routines.'''

#-- Global Variables ----------------------------------------------------------
timer = {}
thread = {}
array = {}
warning = {}

rot_stg_min_pwr = 58 # degrees
rot_stg_limits = {"min":16, "max":45}
piezo_limits = {"min":0, "max":75}


#--- Monitor Functions --------------------------------------------------------

# Get Rotation Mount Data -----------------------------------------------------
array['rot_stg:pos'] = []
array['rot_stg:vel'] = []
rot_mount_record_interval = 10.0 # seconds
timer['rot_stg:record'] = sm.get_lap(rot_mount_record_interval)
def get_rotation_mount_data():
    # Get lap number
    new_record_lap = sm.get_lap(rot_mount_record_interval)

    #--- Get data ---------------------------------------------------------
    # Device DB
    device_db = 'broadening_stage/device_rotation_mount'
    # Wait for queue
    sm.dev[device_db]['queue'].queue_and_wait()
    # Get status
    status = sm.dev[device_db]['driver'].status()
    # Remove from Queue
    sm.dev[device_db]['queue'].remove()

    #--- Record position --------------------------------------------------
    mon_db = 'broadening_stage/rot_stg_position'
    array_id = "rot_stg:pos"
    timer_id = "rot_stg:record"
    data = status["position"] # degrees
    with sm.lock[mon_db]:
        sm.mon[mon_db]['new'] = True
        sm.mon[mon_db]['data'] = sm.update_buffer(
            sm.mon[mon_db]['data'],
            data, 500)
        sm.db[mon_db].write_buffer({'deg':data})
        # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer[timer_id]:
            array[array_id] = np.array(array[array_id])
            # Record statistics
            sm.db[mon_db].write_record(
                {'deg':array[array_id].mean(),
                 'std':array[array_id].std(),
                 'n':array[array_id].size})
            # Empty the array
            array[array_id] = []

    #--- Record velocity --------------------------------------------------
    mon_db = 'broadening_stage/rot_stg_velocity'
    array_id = "rot_stg:vel"
    timer_id = "rot_stg:record"
    data = status["velocity"] # degrees/s
    with sm.lock[mon_db]:
        sm.mon[mon_db]['new'] = True
        sm.mon[mon_db]['data'] = sm.update_buffer(
            sm.mon[mon_db]['data'],
            data, 500)
        sm.db[mon_db].write_buffer({'deg/s':data})
        # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer[timer_id]:
            array[array_id] = np.array(array[array_id])
            # Record statistics
            sm.db[mon_db].write_record(
                {'deg/s':array[array_id].mean(),
                 'std':array[array_id].std(),
                 'n':array[array_id].size})
            # Empty the array
            array[array_id] = []

    #--- Record status flags ----------------------------------------------
    mon_db = 'broadening_stage/rot_stg_status'
    timer_id = "rot_stg:record"
    data = status["flags"] # status flags
    with sm.lock[mon_db]:
        if sm.mon[mon_db]['data'] != data:
            sm.mon[mon_db]['new'] = True
            sm.mon[mon_db]['data'] = data
            sm.db[mon_db].write_record_and_buffer(data)

    #--- Propogate lap numbers --------------------------------------------
    if new_record_lap > timer[timer_id]:
        timer[timer_id] = new_record_lap

# Initialize thread
thread['get_rotation_mount_data'] = ThreadFactory(target=get_rotation_mount_data)


# Get 2nd Stage Piezo Data ----------------------------------------------------
piezo_record_interval = 10.0 # seconds
for piezo in piezos:
    array[piezo+':HV'] = []
    timer[piezo+':record'] = sm.get_lap(piezo_record_interval)
def get_piezo_data(device):
    # Get lap number
    new_record_lap = sm.get_lap(piezo_record_interval)

    #--- Get data ---------------------------------------------------------
    # Device DB
    device_db = 'broadening_stage/device_'+device
    # Wait for queue
    sm.dev[device_db]['queue'].queue_and_wait()
    # Get status
    voltage = sm.dev[device_db]['driver'].voltage()
    # Remove from Queue
    sm.dev[device_db]['queue'].remove()

    #--- Record voltage ---------------------------------------------------
    mon_db = 'broadening_stage/'+device+'_HV_output'
    array_id = device+':HV'
    timer_id = device+':record'
    data = voltage # volts
    with sm.lock[mon_db]:
        sm.mon[mon_db]['new'] = True
        sm.mon[mon_db]['data'] = sm.update_buffer(
            sm.mon[mon_db]['data'],
            data, 500)
        sm.db[mon_db].write_buffer({'V':data})
        # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer[timer_id]:
            array[array_id] = np.array(array[array_id])
            # Record statistics
            sm.db[mon_db].write_record(
                {'V':array[array_id].mean(),
                 'std':array[array_id].std(),
                 'n':array[array_id].size})
            # Empty the array
            array[array_id] = []

    #--- Propogate lap numbers --------------------------------------------
    if new_record_lap > timer[timer_id]:
        timer[timer_id] = new_record_lap

# Initialize threads
for piezo in piezos:
    thread['get_piezo_data:'+piezo] = ThreadFactory(
        target=get_rotation_mount_data,
        args=[piezo])


# Get 2nd Stage NanoTrack Data ------------------------------------------------
nanotrack_record_interval = 10.0 # seconds
for nt in nanotracks:
    array[nt+':pos'] = []
    array[nt+':tia'] = []
    timer[nt+':record'] = sm.get_lap(nanotrack_record_interval)
def get_nanotrack_data(device):
    # Get lap number
    timer_id = device+':record'
    new_record_lap = sm.get_lap(nanotrack_record_interval)

    #--- Get data ---------------------------------------------------------
    # Device DB
    device_db = 'broadening_stage/device_'+device
    # Wait for queue
    sm.dev[device_db]['queue'].queue_and_wait()
    # Connect
    sm.dev[device_db]['driver'].open_port()
    # Get position
    position = sm.dev[device_db]['driver'].position()
    # Get tia reading
    tia_reading = sm.dev[device_db]['driver'].tia_reading()
    # Get position
    status = sm.dev[device_db]['driver'].status()
    # Disconnect
    sm.dev[device_db]['driver'].close_port()
    # Remove from Queue
    sm.dev[device_db]['queue'].remove()

    #--- Record Position --------------------------------------------------
    mon_db = 'broadening_stage/'+device+'_position'
    array_id = device+':pos'
    data = [position["x"], position["y"]] # {"x":x, "y":y}
    with sm.lock[mon_db]:
        sm.mon[mon_db]['new'] = True
        sm.mon[mon_db]['data'] = sm.update_buffer(
            sm.mon[mon_db]['data'],
            data, 500)
        sm.db[mon_db].write_buffer(data)
        # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer[timer_id]:
            array[array_id] = np.array(array[array_id]).T
            # Record statistics
            sm.db[mon_db].write_record(
                {'x':       array[array_id][0].mean(),
                 'x_std':   array[array_id][0].std(),
                 'x_n':     array[array_id][0].size,
                 'y':       array[array_id][1].mean(),
                 'y_std':   array[array_id][1].std(),
                 'y_n':     array[array_id][1].size})
            # Empty the array
            array[array_id] = []

    #--- Record TIA Reading -----------------------------------------------
    mon_db = 'broadening_stage/'+device+'_TIA'
    timer_id = device+':record'
    data = [
        tia_reading["abs reading"],
        tia_reading["rel reading"],
        tia_reading["range"],
        tia_reading["under over"]
        ]
    with sm.lock[mon_db]:
        sm.mon[mon_db]['new'] = True
        sm.mon[mon_db]['data'] = sm.update_buffer(
            sm.mon[mon_db]['data'],
            data, 500)
        sm.db[mon_db].write_buffer(data)
        # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer[timer_id]:
            array[array_id] = np.array(array[array_id]).T
            n = array[array_id][0].size
            norm_read = n - np.count_nonzero(array[array_id][3] - TNA001.NORM_READ)
            under_read = n - np.count_nonzero(array[array_id][3] - TNA001.UNDER_READ)
            over_read = n - np.count_nonzero(array[array_id][3] - TNA001.OVER_READ)
            # Record statistics
            sm.db[mon_db].write_record(
                {'A':           array[array_id][0].mean(),
                 'A_std':       array[array_id][0].std(),
                 'n':           array[array_id][0].size,
                 'rel':         array[array_id][1].mean(),
                 'rel_std':     array[array_id][1].std(),
                 'range':       array[array_id][2].mean(),
                 'range_std':   array[array_id][2].std(),
                 'norm read':   norm_read,
                 'under read':  under_read,
                 'over read':   over_read,
                 })
            # Empty the array
            array[array_id] = []

    #--- Record Status Flags ----------------------------------------------
    mon_db = 'broadening_stage/'+device+'_status'
    data = status # status flags
    with sm.lock[mon_db]:
        if sm.mon[mon_db]['data'] != data:
            sm.mon[mon_db]['new'] = True
            sm.mon[mon_db]['data'] = data
            sm.db[mon_db].write_record_and_buffer(data)

    #--- Propogate lap numbers --------------------------------------------
    if new_record_lap > timer[timer_id]:
        timer[timer_id] = new_record_lap

# Initialize threads
for nt in nanotracks:
    thread['get_nanotrack_data:'+nt] = ThreadFactory(
        target=get_rotation_mount_data,
        args=[nt])


#--- Optimization Functions ---------------------------------------------------

# Optimize Z Coupling ---------------------------------------------------------
def optimize_z_coupling(pz_db, nt_db, mon_db, sig, scan_range=10., max_iter=None):
    # Info
    mod_name = __name__
    func_name = optimize_z_coupling.__name__
    log_str = ' Beginning z pizeo optimization'
    log.log_info(mod_name, func_name, log_str)
    start_time = time.time()

    #--- Queue and wait ---------------------------------------------------
    sm.dev[nt_db]['queue'].queue_and_wait()
    sm.dev[pz_db]['queue'].queue_and_wait()

    #--- Setup optimizer --------------------------------------------------
    current_position = sm.dev[pz_db]['driver'].voltage()
    start_scan = current_position - scan_range/2
    stop_scan = current_position + scan_range/2
    if start_scan < piezo_limits["min"]:
        start_scan = piezo_limits["min"]
        stop_scan = start_scan + scan_range
    if stop_scan > piezo_limits["max"]:
        stop_scan = piezo_limits["max"]
        start_scan = stop_scan - scan_range
    bounds = [(start_scan, stop_scan)]

    #--- Initialize optimizer ---------------------------------------------
    optimizer = Minimizer(
        bounds,
        n_initial_points=5, sig=sig,
        abs_bounds=[(piezo_limits["min"], piezo_limits["max"])])

    #--- Optimize ---------------------------------------------------------
    converged = False
    search = True
    new_x = [current_position]
    while search:
        #--- Ensure queues
        sm.dev[nt_db]['queue'].touch()
        sm.dev[pz_db]['queue'].touch()

        #--- Measure new point
        tia_reading = sm.dev[nt_db]['driver'].tia_reading()["abs reading"]

        #--- Update Model
        new_y = -np.log10(tia_reading) # maximize the tia_reading
        opt_x, diag = optimizer.tell(new_x, new_y, diagnostics=True)

        #--- Write Intermediate Result to Buffer
        with sm.lock[mon_db]:
            sm.mon[mon_db]['new'] = True
            sm.mon[mon_db]['data'] = {
                "V":np.array(optimizer.x).flatten().tolist(), # Volts
                "A":np.power(10., -np.array(optimizer.y)).tolist(), # Amps
                "model":{
                    "opt x":opt_x,
                    "x":optimizer.x, # Volts
                    "y":optimizer.y, # -log10(Amps)
                    "diagnostics":diag,
                    "n obs":optimizer.n_obs,
                    "target sig":optimizer.sig,
                    "time":time.time() - start_time
                    }
                }
            sm.db[mon_db].write_buffer(sm.mon[mon_db]['data'])

        #--- Check convergence
        if optimizer.convergence_count >= 3:
            #--- End the search
            converged = True
            search = False
        elif max_iter:
            if optimizer.n_obs >= max_iter:
                converged = False
                search = False
                opt_x = [current_position]
                log_str = ' Model did not converge to {:} sig after {:} samples, returning to initial point.'.format(
                    optimizer.sig,
                    optimizer.n_obs)
                warning_id = 'piezo z optimization'
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > sm.warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)

        #--- Get new point
        if search:
            #--- Ask for new point
            new_x = optimizer.ask()
            #--- Move to new point
            sm.dev[pz_db]['driver'].voltage(new_x[0])
            # System settle time
            time.sleep(1)
    # Optimum output
    new_position = opt_x[0]
    stop_time = time.time()

    #--- Implement result -------------------------------------------------
    sm.dev[pz_db]['driver'].voltage(new_position)

    #--- Remove from queue ------------------------------------------------
    sm.dev[nt_db]['queue'].remove()
    sm.dev[pz_db]['queue'].remove()

    #--- Log Result -------------------------------------------------------
    if converged:
        log_str = ' Z piezo optimized at {:.3f}V'.format(new_position)
        log.log_info(mod_name, func_name, log_str)
        log_str = ' {:} sig after {:.3g}s and {:} observations'.format(
            optimizer.sig,
            stop_time - start_time,
            optimizer.n_obs)
        log.log_info(mod_name, func_name, log_str)

    #--- Record result ----------------------------------------------------
    with sm.lock[mon_db]:
        sm.mon[mon_db]['new'] = True
        sm.mon[mon_db]['data'] = {
            "V":np.array(optimizer.x).flatten().tolist(), # Volts
            "A":np.power(10., -np.array(optimizer.y)).tolist(), # Amps
            "model":{
                "opt x":opt_x,
                "x":optimizer.x, # Volts
                "y":optimizer.y, # -log10(Amps)
                "diagnostics":diag,
                "n obs":optimizer.n_obs,
                "target sig":optimizer.sig,
                "time":stop_time - start_time,
                "converged":converged
                }
            }
        sm.db[mon_db].write_record_and_buffer(sm.mon[mon_db]['data'])
    return new_position


# %% Monitor Routines =========================================================
'''This section is for defining the methods needed to monitor the system.'''

# Monitor 2nd Stage -----------------------------------------------------------
passive_interval = 1.0 # s
timer['monitor_2nd_stage:passive'] = sm.get_lap(passive_interval)
def monitor_2nd_stage(state_db):
    # Get lap number
    new_passive_lap = sm.get_lap(passive_interval)
    #--- Update Passive Monitors ------------------------------------------
    if (new_passive_lap > timer['monitor_2nd_stage:passive']):
        #--- Rotation Stage Data ------------------------------------------
        thread_name = 'get_rotation_mount_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
            # Start new thread
            thread[thread_name].start()

        #--- Piezo Data ---------------------------------------------------
        for piezo in piezos:
            thread_name = 'get_piezo_data:'+piezo
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            if not(alive):
                # Start new thread
                thread[thread_name].start()

        #--- NanoTrack Data ------------------------------------------------
        for nt in nanotracks:
            thread_name = 'get_nanotrack_data:'+nt
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            if not(alive):
                # Start new thread
                thread[thread_name].start()

        # Propogate lap numbers -------------------------------------------
        timer['monitor_2nd_stage:passive'] = new_passive_lap


# %% Search Routines ==========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''

def minimize_power(state_db):
    # Device DB
    device_db = 'broadening_stage/device_rotation_mount'
    # Check if homed
    mon_db = 'broadening_stage/rot_stg_status'
    with sm.lock[mon_db]:
        if sm.mon[mon_db]['new']:
            sm.mon[mon_db]['new'] = False
            homed = sm.mon[mon_db]['homed']
        else:
            homed = False
    if homed:
        # Move to minimum transmission
        settings_list = [{'position':rot_stg_min_pwr}]
        sm.update_device_settings(device_db, settings_list, write_log=True)
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = True
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])

def track_2nd_stage(state_db):
    mod_name = __name__
    func_name = track_2nd_stage.__name__
    # Device DB
    device_db = 'broadening_stage/device_rotation_mount'
    #--- Track if homed -------------------------------------------------------
    mon_db = 'broadening_stage/rot_stg_status'
    with sm.lock[mon_db]:
        if sm.mon[mon_db]['new']:
            sm.mon[mon_db]['new'] = False
            homed = sm.mon[mon_db]['homed']
        else:
            homed = False
    if homed:
        # Check if rotation stage is minimized
        if sm.dev[device_db]['position'] > rot_stg_limits['max']:
            # Move to baseline minimum power (small, but measurable)
            settings_list = [{'position':rot_stg_limits['max']}]
            sm.update_device_settings(device_db, settings_list, write_log=True)

        #--- Enable input tracking ----------------------------------------
        device_db = 'broadening_stage/device_nanotrack_in'
        settings_list = [{'track_mode':TNA001.TRACK_MODE}]
        sm.update_device_settings(device_db, settings_list, write_log=True)
        time.sleep(2)

        #--- Enable output tracking ---------------------------------------
        device_db = 'broadening_stage/device_nanotrack_out'
        settings_list = [{'track_mode':TNA001.TRACK_MODE}]
        sm.update_device_settings(device_db, settings_list, write_log=True)
        time.sleep(2)

        #--- Optimize input coupling --------------------------------------
        # Device dbs
        nt_db = "broadening_stage/device_nanotrack_in"
        pz_db = "broadening_stage/device_piezo_z_in"

        # Monitor db
        mon_db = 'broadening_stage/2nd_stage_z_in_optimizer'

        # Optimize
        sig = 3.
        new_output = optimize_z_coupling(pz_db, nt_db, mon_db, sig)

        # Log Result
        log_str = ' Input coupling optimized at z = {:.3f}V'.format(new_output)
        log.log_info(mod_name, func_name, log_str)

        #--- Optimize output coupling -------------------------------------
        # Device dbs
        nt_db = "broadening_stage/device_nanotrack_out"
        pz_db = "broadening_stage/device_piezo_z_out"

        # Monitor db
        mon_db = 'broadening_stage/2nd_stage_z_out_optimizer'

        # Optimize
        sig = 3.
        new_output = optimize_z_coupling(pz_db, nt_db, mon_db, sig)

        # Log Result
        log_str = ' Output coupling optimized at z = {:.3f}V'.format(new_output)
        log.log_info(mod_name, func_name, log_str)

        #--- Update state db ----------------------------------------------
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = True
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])


# %% Maintenance Routines ========================================================
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''

def keep_2nd_stage(state_db):
    mod_name = __name__
    func_name = keep_2nd_stage.__name__
    # Check tracking status
    for nt in nanotracks:
        mon_db = 'broadening_stage/'+nt+'_status'
        with sm.lock[mon_db]:
            if sm.mon[mon_db]['new']:
                sm.mon[mon_db]['new'] = False
                tracking = sm.mon[mon_db]['data']["tracking"]
                signal = sm.mon[mon_db]['data']["signal"]
            else:
                tracking = True
                signal = True
        if not(tracking) or not(signal):
            if not tracking:
                log_str = " tracking lost, tracking was disabled"
            elif not signal:
                log_str = " tracking lost, low signal"
            log.log_error(mod_name, func_name, log_str)

            #--- Update state db --------------------------------------
            with sm.lock[state_db]:
                sm.current_state[state_db]['compliance'] = False
                sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])


# %% Operation Routines =======================================================
'''This section is for defining the methods called only when the system is in
    its defined states.'''


# %% States ===================================================================
'''Defined states are composed of collections of settings, prerequisites,
and routines'''

STATES = {
        'broadening_stage/state_2nd_stage':{
                'lock':{
                        'settings':{
                                'broadening_stage/device_nanotrack_in':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}},
                                'broadening_stage/device_nanotrack_out':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}},
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
                                },
                        'prerequisites':{}, #TODO: prereqs are setup and 1st stage properties
                        'routines':{
                                'monitor':monitor_2nd_stage, 'search':track_2nd_stage,
                                'maintain':keep_2nd_stage, 'operate':sm.nothing}
                        },
                'safe':{
                        'settings':{
                                'broadening_stage/device_nanotrack_in':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}},
                                'broadening_stage/device_nanotrack_out':{
                                        'track_mode':TNA001.LATCH_MODE,
                                        'position':{"x":0.5, "y":0.6}},
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
                                },
                        'prerequisites':{},
                        'routines':{
                                'monitor':monitor_2nd_stage, 'search':minimize_power,
                                'maintain':sm.nothing, 'operate':sm.nothing}
                        },
                'engineering':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing},
                        }
                }
        }
sm.init_states(STATES)


# %% STATE MACHINE ============================================================

'''Operates the state machine.'''
sm.operate_machine(main_loop_interval=0.5)
