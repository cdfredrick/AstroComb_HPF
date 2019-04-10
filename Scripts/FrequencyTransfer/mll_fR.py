# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:51:36 2017

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

from Drivers.VISA.SRS import SIM960
from Drivers.VISA.ILXLightwave import TECModule
from Drivers.VISA.Thorlabs import MDT639B

from Drivers.DAQ.Tasks import AiTask


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
are parsed as commands in this script
'''
COMMS = 'mll_fR'
sm.init_comms(COMMS)


# Internal database names -----------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function.
'''
STATE_DBs = [
    'mll_fR/state',
    ]
DEVICE_DBs =[
    'mll_fR/device_TEC', 'mll_fR/device_PID',
    'mll_fR/device_HV', 'mll_fR/device_DAQ_Vout_vs_freq',
    ]
MONITOR_DBs = [
    'mll_fR/TEC_temperature', 'mll_fR/TEC_current',  'mll_fR/TEC_event_status',
    'mll_fR/PID_output', 'mll_fR/PID_output_limits',
    'mll_fR/HV_output', 'mll_fR/DAQ_Vout_vs_freq',
    ]
LOG_DB = 'mll_fR'
CONTROL_DB = 'mll_fR/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]
sm.init_master_DB_names(STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB)

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = ['mll_fR/DAQ_error_signal']
READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs
sm.init_read_DB_names(R_STATE_DBs, R_DEVICE_DBs, R_MONITOR_DBs)

# Default settings ------------------------------------------------------------
'''A template for all settings used in this script. Upon initialization
these settings are checked against those saved in the database, and
populated if found empty. Each state and device database should be represented.
'''
STATE_SETTINGS = {
    'mll_fR/state':{
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
    # VISA device settings
    'mll_fR/device_TEC':{
        'driver':TECModule,
        'queue':'GPIB0::20',
        '__init__':[['GPIB0::20::INSTR', 1]],
        'tec_off_triggers':None, 'tec_gain':100,
        'tec_current_limit':0.400, 'tec_temperature_limit':45.0, 'tec_mode':'R',
        'tec_output':True, 'tec_resistance_setpoint':None},
    'mll_fR/device_PID':{
        'driver':SIM960,
        'queue':'ASRL1',
        '__init__':[['ASRL1::INSTR', 1]],
        'proportional_action':True, 'integral_action':True,
        'derivative_action':False, 'offset_action':None, 'offset':None,
        'proportional_gain':-3.0e0, 'integral_gain':5.0e2, 'pid_action':None,
        'external_setpoint_action':False, 'internal_setpoint':0.000,
        'ramp_action':False, 'manual_output':None, 'upper_output_limit':8.00,
        'lower_output_limit':0.00, 'power_line_frequency':60},
    'mll_fR/device_HV':{
        'driver':MDT639B,
        'queue':'ASRL30',
        '__init__':[['ASRL30::INSTR']], 'master_scan_action':False,
        'x_min_limit':0.00, 'x_max_limit':60.00, 'x_voltage':0.00},
    # DAQ settings
    'mll_fR/device_DAQ_Vout_vs_freq':{
        'driver':AiTask,
        'queue':'DAQ_ai',
        '__init__':[
            [[{'physical_channel':'Dev1/ai0', 'terminal_config':'NRSE',
               'min_val':-1.0, 'max_val':1.0}],
             100e3,
             int(100e3*0.2)
            ],
            {'timeout':5.0}],
        'reserve_cont':False, 'reserve_point':False}}
CONTROL_PARAMS = {CONTROL_DB:{}}
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))
sm.init_default_settings(STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS)

# %% Initialize Databases, Devices, and Settings ==============================

# Connect to MongoDB ----------------------------------------------------------
'''Creates a client and connects to all defined databases'''
sm.init_DBs()

# Start Logging ---------------------------------------------------------------
'''Initializes logging for this script.'''
sm.init_logging(
    database_object=sm.db[LOG_DB],
    logger_level=logging.INFO,
    log_buffer_handler_level=logging.DEBUG,
    log_handler_level=logging.WARNING)

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
sm.init_device_drivers_and_settings()

# Initialize Local Copy of Monitors -------------------------------------------
'''Monitors should associate the monitor databases with the local, circular
buffers of the monitored data. Monitors should indicate when they have
recieved new data.
'''
sm.init_monitors()


# %% State Functions ==========================================================

# Global Variables ------------------------------------------------------------
timer = {}
array = {}
thread = {}


# %% Monitor Functions -----------------------------------------------------------
'''This section is for defining the methods needed to monitor the system.'''

# SRS Data --------------------------------------------------------------------
array['srs:v_out'] = []
srs_record_interval = 10 # seconds
timer['srs:record'] = sm.get_lap(srs_record_interval)
def get_srs_data():
# Get lap number
    new_record_lap = sm.get_lap(srs_record_interval)
# Pull data from SRS ----------------------------------
    device_db = 'mll_fR/device_PID'
    # Wait for queue
    sm.dev[device_db]['queue'].queue_and_wait()
    # Get values
        # Current output voltage
    v_out = sm.dev[device_db]['driver'].output_monitor()
        # Output voltage limits
    v_min = sm.dev[device_db]['driver'].lower_limit
    v_max = sm.dev[device_db]['driver'].upper_limit
        # PID action
    settings_list = [{'pid_action':None}]
    sm.update_device_settings(device_db, settings_list, write_log=False)
    # Remove from queue
    sm.dev[device_db]['queue'].remove()
    # Update buffers and databases ----------
    # Output voltage ----------
    monitor_db = 'mll_fR/PID_output'
    array_id = 'srs:v_out'
    data = v_out
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = sm.update_buffer(
                sm.mon[monitor_db]['data'],
                data, 500)
        sm.db[monitor_db].write_buffer({'V':data})
        # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer['srs:record']:
            array[array_id] = np.array(array[array_id])
            # Record statistics
            sm.db[monitor_db].write_record({
                    'V':array[array_id].mean(),
                    'std':array[array_id].std(),
                    'n':array[array_id].size})
            # Empty the array
            array[array_id] = []
    # Voltage limits ----------
    monitor_db = 'mll_fR/PID_output_limits'
    with sm.lock[monitor_db]:
        if (sm.mon[monitor_db]['data'] != {'min':v_min, 'max':v_max}):
            sm.mon[monitor_db]['new'] = True
            sm.mon[monitor_db]['data'] = {'min':v_min, 'max':v_max}
            sm.db[monitor_db].write_record_and_buffer({'min':v_min, 'max':v_max})
    # Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer['srs:record']:
        timer['srs:record'] = new_record_lap
thread['get_srs_data'] = ThreadFactory(target=get_srs_data)

# ILX Data --------------------------------------------------------------------
array['ilx:tec_temp'] = []
array['ilx:tec_curr'] = []
ilx_record_interval = 100 # seconds
timer['ilx:record'] = sm.get_lap(ilx_record_interval)
def get_ilx_data():
# Get lap number
    new_record_lap = sm.get_lap(ilx_record_interval)
# Pull data from ILX Lightwave ------------------------
    device_db = 'mll_fR/device_TEC'
    # Wait for queue
    sm.dev[device_db]['queue'].queue_and_wait()
    # Get values
    sm.dev[device_db]['driver'].open_tec()
    tec_temp = sm.dev[device_db]['driver'].tec_resistance()
    sm.dev[device_db]['queue'].touch()
    tec_curr = sm.dev[device_db]['driver'].tec_current()
    sm.dev[device_db]['queue'].touch()
    tec_events = sm.dev[device_db]['driver'].tec_events()
    sm.dev[device_db]['queue'].touch()
    sm.dev[device_db]['driver'].close_tec()
    # Remove from queue
    sm.dev[device_db]['queue'].remove()
    # Update buffers and databases -----------
    # TEC temp ----------------
    monitor_db = 'mll_fR/TEC_temperature'
    array_id = 'ilx:tec_temp'
    data = tec_temp
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = sm.update_buffer(
                sm.mon[monitor_db]['data'],
                data, 100)
        sm.db[monitor_db].write_buffer({'kOhm':data})
                # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer['ilx:record']:
            array[array_id] = np.array(array[array_id])
            # Record statistics
            sm.db[monitor_db].write_record({
                    'kOhm':array[array_id].mean(),
                    'std':array[array_id].std(),
                    'n':array[array_id].size})
            # Empty the array
            array[array_id] = []
    # TEC current -------------
    monitor_db = 'mll_fR/TEC_current'
    array_id = 'ilx:tec_curr'
    data = tec_curr
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = sm.update_buffer(
                sm.mon[monitor_db]['data'],
                data, 100)
        sm.db[monitor_db].write_buffer({'A':data})
                # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer['ilx:record']:
            array[array_id] = np.array(array[array_id])
            # Record statistics
            sm.db[monitor_db].write_record({
                    'A':array[array_id].mean(),
                    'std':array[array_id].std(),
                    'n':array[array_id].size})
            # Empty the array
            array[array_id] = []
    # TEC Events --------------
    monitor_db = 'mll_fR/TEC_event_status'
    data = tec_events
    with sm.lock[monitor_db]:
        if (sm.mon[monitor_db]['data'] != data):
            sm.mon[monitor_db]['new'] = True
            sm.mon[monitor_db]['data'] = data
            sm.db[monitor_db].write_record_and_buffer({'events':data})
    # Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer['ilx:record']:
        timer['ilx:record'] = new_record_lap
thread['get_ilx_data'] = ThreadFactory(target=get_ilx_data)

# HV Data ---------------------------------------------------------------------
array['hv:v_out'] = []
hv_record_interval = 10 # seconds
timer['hv:record'] = sm.get_lap(hv_record_interval)
def get_HV_data():
# Get lap number
    new_record_lap = sm.get_lap(hv_record_interval)
# Pull data from Thorlabs 3-axis piezo controller -----
    device_db = 'mll_fR/device_HV'
    # Wait for queue
    sm.dev[device_db]['queue'].queue_and_wait()
    # Get values
    hv_out = sm.dev[device_db]['driver'].x_voltage()
    # Remove from queue
    sm.dev[device_db]['queue'].remove()
    # Update buffers and databases ----------
    monitor_db = 'mll_fR/HV_output'
    array_id = 'hv:v_out'
    data = hv_out
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = sm.update_buffer(
                sm.mon[monitor_db]['data'],
                data, 100)
        sm.db[monitor_db].write_buffer({'V':data})
        # Append to the record array
        array[array_id].append(data)
        if new_record_lap > timer['hv:record']:
            array[array_id] = np.array(array[array_id])
            # Record statistics
            sm.db[monitor_db].write_record({
                    'V':array[array_id].mean(),
                    'std':array[array_id].std(),
                    'n':array[array_id].size})
            # Empty the array
            array[array_id] = []
    # Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer['hv:record']:
        timer['hv:record'] = new_record_lap
thread['get_HV_data'] = ThreadFactory(target=get_HV_data)

# Monitor ---------------------------------------------------------------------
control_interval = 0.5 # s
passive_interval = 1.0 # s
timer['monitor:control'] = sm.get_lap(control_interval)
timer['monitor:passive'] = sm.get_lap(passive_interval)
def monitor(state_db):
# Get lap number
    new_control_lap = sm.get_lap(control_interval)
    new_passive_lap = sm.get_lap(passive_interval)
# Update control loop variables -------------------------------------
    if (new_control_lap > timer['monitor:control']):
    # Pull data from SRS ----------------------------------
        thread_name = 'get_srs_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Pull data from external databases -------------------
        monitor_db = 'mll_fR/DAQ_error_signal'
        new_data = []
        for doc in sm.mon[monitor_db]['cursor']:
            new_data.append(doc['std'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            with sm.lock[monitor_db]:
                sm.mon[monitor_db]['new'] = True
                sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    new_data, 500, extend=True)
    # Propogate lap numbers ---------------------------------------------
        timer['monitor:control'] = new_control_lap
# Update passive monitoring variables -------------------------------
    if (new_passive_lap > timer['monitor:passive']):
    # Pull data from ILX Lightwave ------------------------
        thread_name = 'get_ilx_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Pull data from Thorlabs 3-axis piezo controller -----
        thread_name = 'get_HV_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Propogate lap numbers ---------------------------------------------
        timer['monitor:passive'] = new_passive_lap


# %% Search Functions ------------------------------------------------------------
'''This section is for defining the methods needed to bring the system into
    its defined states.'''

# Find Lock -------------------------------------------------------------------
from scipy.optimize import curve_fit
v_range_threshold = 0.1 #(limit-threshold)/(upper - lower limits)
t_setpoint_threshold = 0.02 #kOhm
tec_adjust_interval = 1.0 #s
lock_hold_interval = 1.0 #s
timer['find_lock:locked'] = time.time()
timer['find_lock:tec_adjust'] = time.time()
def find_lock(state_db, last_good_position=None):
    mod_name = __name__
    func_name = find_lock.__name__
# Queue the SRS PID controller --------------------------------------
    device_db = 'mll_fR/device_PID'
    sm.dev[device_db]['queue'].queue_and_wait(priority=True)
# Initialize threshold variables ------------------------------------
    v_high = (1-v_range_threshold)*sm.dev[device_db]['driver'].upper_limit + v_range_threshold*sm.dev[device_db]['driver'].lower_limit
    v_low = (1-v_range_threshold)*sm.dev[device_db]['driver'].lower_limit + v_range_threshold*sm.dev[device_db]['driver'].upper_limit
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
                {'pid_action':True}]
        sm.update_device_settings(device_db, settings_list)
    # Update lock timer -----------------------------------
        timer['find_lock:locked'] = time.time()
        with sm.lock['mll_fR/DAQ_error_signal']:
            sm.mon['mll_fR/DAQ_error_signal']['new'] = False
        locked = True
# Check if locked ---------------------------------------------------
    elif sm.dev[device_db]['driver'].pid_action():
        '''This is the main logic used to determine if the current state is
        locked. The main check is that the current output is within the
        accepted range between the upper and lower hardware limits.'''
    # PID is enabled
        current_output = sm.dev[device_db]['driver'].output_monitor()
        if (current_output < v_low) or (current_output > v_high):
        # Output is beyond voltage thresholds
            locked = False
            log_str = " mll_fR lock failed, PID output was outside the acceptable range"
            log.log_error(mod_name, func_name, log_str)
        else:
        # Lock is holding
            locked = True
    else:
    # PID is disabled
        locked = False
        log_str = ' mll_fR lock failed, PID disabled'
        log.log_info(mod_name, func_name, log_str)
# If locked ---------------------------------------------------------
    if locked:
        '''If the current state passed the previous tests the control script
        holds off on making a final judgement until the specified interval has
        passed since lock acquisition.'''
    # Remove the SRS PID controller from queue ------------
        sm.dev[device_db]['queue'].remove()
    # Check lock interval ---------------------------------
        if (time.time() - timer['find_lock:locked']) > lock_hold_interval:
            if sm.mon['mll_fR/DAQ_error_signal']['new']:
                if (sm.mon['mll_fR/DAQ_error_signal']['data'][-1] > 0.2):
                    locked = False
                    log_str = ' mll_fR lock failed, RMS error signal too high'
                    log.log_info(mod_name, func_name, log_str)
            if locked:
                log_str = ' mll_fR lock successful'
                log.log_info(mod_name, func_name, log_str)
            # Lock is succesful, update state variable
                with sm.lock[state_db]:
                    sm.current_state[state_db]['compliance'] = True
                    sm.db[state_db].write_record_and_buffer(
                            sm.current_state[state_db],
                            timestamp=datetime.datetime.utcfromtimestamp(timer['find_lock:locked']))
# If unlocked -------------------------------------------------------
    else:
        '''The current state has failed the lock tests. The PID controller is
        then broght into a known state, and the DAQ is used to find the lock
        point.'''
    # Reset the PID controller ----------------------------
        settings_list = [
                {'pid_action':False},
                {'upper_output_limit':STATES[state_db][sm.current_state[state_db]['state']]['settings'][device_db]['upper_output_limit'],
                 'lower_output_limit':STATES[state_db][sm.current_state[state_db]['state']]['settings'][device_db]['lower_output_limit']}]
        sm.update_device_settings(device_db, settings_list)
    # Reinitialize threshold variables --------------------
        v_high = (1-v_range_threshold*2)*sm.dev[device_db]['driver'].upper_limit + v_range_threshold*2*sm.dev[device_db]['driver'].lower_limit
        v_low = (1-v_range_threshold*2)*sm.dev[device_db]['driver'].lower_limit + v_range_threshold*2*sm.dev[device_db]['driver'].upper_limit
    # Reset the piezo hysteresis --------------------------
        sm.dev[device_db]['driver'].manual_output(v_low)
    # Queue the DAQ ---------------------------------------
        daq_db = 'mll_fR/device_DAQ_Vout_vs_freq'
        sm.dev[daq_db]['queue'].queue_and_wait(priority=True)
    # Get lock point data ---------------------------------
        to_fit = lambda v, v0, s: s*np.abs(v-v0)
        x = np.linspace(v_low, v_high, 5)
        y = np.copy(x)
        for ind, x_val in enumerate(x):
        # Touch queue (prevent timeout) ---------
            sm.dev[device_db]['queue'].touch()
            sm.dev[daq_db]['queue'].touch()
        # Change position and trigger DAQ -------
            sm.dev[device_db]['driver'].manual_output(x_val)
            data = sm.dev[daq_db]['driver'].read_point()
            # Find peak frequency -----
            han_win = np.hanning(sm.dev[daq_db]['driver'].buffer_size)
            freqs = sm.dev[daq_db]['driver'].rate*np.fft.rfftfreq(sm.dev[daq_db]['driver'].buffer_size)
            amps = np.abs(np.fft.rfft(han_win*data))
            peak_ind = np.argmax(amps)
            y[ind] = freqs[peak_ind]
        # Release and remove the DAQ from queue -
        sm.dev[daq_db]['driver'].reserve_point(False)
        sm.dev[daq_db]['queue'].remove()
        # Reset the piezo hysteresis ------------
        sm.dev[device_db]['driver'].manual_output(x[0])
        # Update monitor DB ---------------------
        with sm.lock['mll_fR/DAQ_Vout_vs_freq']:
            sm.mon['mll_fR/DAQ_Vout_vs_freq']['new'] = True
            sm.mon['mll_fR/DAQ_Vout_vs_freq']['data'] = np.array([x, y])
            sm.db['mll_fR/DAQ_Vout_vs_freq'].write_record_and_buffer({'V':x.tolist(), 'Hz':y.tolist()})
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
            log.log_exception(mod_name, func_name)
            # Failure may be because the frequency response was too flat?
            # The middle is a safe place to go (no TEC adjustment)
            new_output = sm.dev[device_db]['driver'].center
    # Get Lock --------------------------------------------
        if (new_output > v_low) and (new_output < v_high):
            '''If the new lock point is within the acceptable range between
            the upper and lower hardware limits, attempt to lock.'''
            log_str = ' Estimated voltage setpoint = {:.3f}, locking.'.format(new_output)
            log.log_info(mod_name, func_name, log_str)
        # Update deivice settings ---------------
            settings_list = [{'manual_output':new_output,
                              'offset_action':True,
                              'offset':new_output},
                             {'pid_action':True}]
            sm.update_device_settings(device_db, settings_list)
        # Remove the SRS PID controller from queue
            sm.dev[device_db]['queue'].remove()
        # Update lock timer ---------------------
            timer['find_lock:locked'] = time.time()
            with sm.lock['mll_fR/DAQ_error_signal']:
                sm.mon['mll_fR/DAQ_error_signal']['new'] = False
        else:
            '''If not, try to determine why. This could be that the temperature
            control is not on, the temperature has not settled at the setpoint,
            or the temperature setpoint needs adjustment.'''
        # Remove the SRS PID controller from queue
            sm.dev[device_db]['queue'].remove()
        # Queue the ILX TEC controller ----------
            device_db = 'mll_fR/device_TEC'
            thread_name = 'get_ilx_data'
            thread[thread_name].join() # needed because releasing is too slow for the queue
            sm.dev[device_db]['queue'].queue_and_wait(priority=True)
            sm.dev[device_db]['driver'].open_tec()
        # Check TEC settings --------------------
            if sm.dev[device_db]['driver'].tec_output():
            # If TEC is on ------------
                t_setpoint = sm.dev[device_db]['driver'].tec_resistance_setpoint()
                t_meas = sm.dev[device_db]['driver'].tec_resistance()
                setpoint_condition = (abs(t_setpoint - t_meas) < t_setpoint_threshold)
                adjustment_interval_condition = ((time.time()-timer['find_lock:tec_adjust']) > tec_adjust_interval)
                if (setpoint_condition and adjustment_interval_condition):
                # Adjust timer
                    timer['find_lock:tec_adjust'] = time.time()
                # Adjust the setpoint
                    if (new_output < sm.dev['mll_fR/device_PID']['driver'].center):
                        log_str = ' Estimated voltage setpoint = {:.3f}, raising the resistance setpoint'.format(new_output)
                        log.log_info(mod_name, func_name, log_str)
                    # Raise the resistance setpoint
                        sm.dev[device_db]['driver'].tec_step(+1)
                    elif new_output > sm.dev['mll_fR/device_PID']['driver'].center:
                        log_str = ' Estimated voltage setpoint = {:.3f}, lowering the resistance setpoint.'.format(new_output)
                        log.log_info(mod_name, func_name, log_str)
                    # Lower the resistance setpoint
                        sm.dev[device_db]['driver'].tec_step(-1)
                else:
                # TEC has not settled, wait
                    log_str = ' Estimated voltage setpoint = {:.3f}, but TEC has not yet settled'.format(new_output)
                    log.log_debug(mod_name, func_name, log_str)
            else:
            # TEC output is off, renable
                sm.update_device_settings(device_db, [{'tec_mode':'R'}, {'tec_output':True}])
        # Remove the ILX TEC controller from queue ------------
            sm.dev[device_db]['driver'].close_tec()
            sm.dev[device_db]['queue'].remove()

# Transfer to Manual ----------------------------------------------------------
def transfer_to_manual(state_db):
    mod_name = __name__
    func_name = transfer_to_manual.__name__
# Queue the SRS PID controller --------------------------------------
    device_db = 'mll_fR/device_PID'
    sm.dev[device_db]['queue'].queue_and_wait()
# Check if the PID controller is on ---------------------------------
    if sm.dev[device_db]['driver'].pid_action():
    # Get current output
        v_out = sm.dev[device_db]['driver'].output_monitor()
    # Bumpless transfer to manual
        settings_list = [
                {'manual_output':v_out},
                {'pid_action':False}]
        sm.update_device_settings(device_db, settings_list)
# Remove SRS PID from queue -----------------------------------------
    sm.dev[device_db]['queue'].remove()
# Update state variable
    with sm.lock[state_db]:
        sm.current_state[state_db]['compliance'] = True
        sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
    log_str = ' Transfer to manual successful'
    log.log_info(mod_name, func_name, log_str)


# %% Maintain Functions ----------------------------------------------------------
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''

# Keep Lock -------------------------------------------------------------------
v_std_threshold = 5 # standard deviations
lock_age_threshold = 30.0 #s
def keep_lock(state_db):
    mod_name = keep_lock.__module__
    func_name = keep_lock.__name__
    locked = True
# Get most recent values --------------------------------------------
    with sm.lock['mll_fR/PID_output']:
        new_output_condition = sm.mon['mll_fR/PID_output']['new']
        sm.mon['mll_fR/PID_output']['new'] = False
        output_data = sm.mon['mll_fR/PID_output']['data'][:-1]
        if new_output_condition:
            current_output = sm.mon['mll_fR/PID_output']['data'][-1]
    with sm.lock['mll_fR/DAQ_error_signal']:
        new_daq_err_signal_condition = sm.mon['mll_fR/DAQ_error_signal']['new']
        sm.mon['mll_fR/DAQ_error_signal']['new'] = False
        if new_daq_err_signal_condition:
            current_err_sig = sm.mon['mll_fR/DAQ_error_signal']['data'][-1]
    with sm.lock['mll_fR/PID_output_limits']:
        no_new_limits_condition = not(sm.mon['mll_fR/PID_output_limits']['new'])
        sm.mon['mll_fR/PID_output_limits']['new'] = False
        if no_new_limits_condition:
            current_limits = {'max':sm.local_settings['mll_fR/device_PID']['upper_output_limit'],
                              'min':sm.local_settings['mll_fR/device_PID']['lower_output_limit']}
        else:
            current_limits = sm.mon['mll_fR/PID_output_limits']['data']
    lock_age_condition = ((time.time() - timer['find_lock:locked']) > lock_age_threshold)
    # Lock threshold
    v_high = (1-v_range_threshold)*current_limits['max'] + v_range_threshold*current_limits['min']
    v_low = (1-v_range_threshold)*current_limits['min'] + v_range_threshold*current_limits['max']
    # Temperature adjustment threshold
    v_high2 = (1-2*v_range_threshold)*current_limits['max'] + 2*v_range_threshold*current_limits['min']
    v_low2 = (1-2*v_range_threshold)*current_limits['min'] + 2*v_range_threshold*current_limits['max']
# Check if the PID controller is on ---------------------------------
    if (sm.local_settings['mll_fR/device_PID']['pid_action'] != True):
    # It is not locked
        locked = False
        log_str = " mll_fR lock lost, PID controller was disabled"
        log.log_error(mod_name, func_name, log_str)
# Check if the output is outside the acceptable range ---------------
    if new_output_condition:
        if (current_output < v_low) or (current_output > v_high):
        # It is not locked
            locked = False
            log_str = " mll_fR lock lost, PID output was outside the acceptable range"
            log.log_error(mod_name, func_name, log_str)
# Check DAQ error signal --------------------------------------------
    if new_daq_err_signal_condition:
        if (current_err_sig > 0.2):
        # It is not locked
            locked = False
            log_str = " mll_fR lock lost, RMS error signal too high"
            log.log_error(mod_name, func_name, log_str)
# If not locked -----------------------------------------------------
    if not(locked):
    # Update state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = False
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
    # Check if quick relock is possible
        if (lock_age_condition and no_new_limits_condition):
        # Calculate the expected output voltage
            v_avg = np.mean(output_data)
            v_avg_slope = np.mean(np.diff(output_data))/(len(output_data)-1)
            v_expected = v_avg + v_avg_slope*len(output_data)/2
        # Remove the last point from the local monitor
            with sm.lock['mll_fR/PID_output']:
                sm.mon['mll_fR/PID_output']['data'] = output_data
        # Attempt a quick relock
            log_str = " Attempting quick relock"
            log.log_info(mod_name, func_name, log_str)
            find_lock(state_db, last_good_position=v_expected)
# If locked ---------------------------------------------------------
    else:
    # If the system is at a new lock point, reinitialize the local monitors
        if (not(lock_age_condition) and not(no_new_limits_condition)):
        # Reinitialize the output voltage monitor
            with sm.lock['mll_fR/PID_output']:
                sm.mon['mll_fR/PID_output']['data'] = []
                sm.mon['mll_fR/PID_output']['new'] = False
    # If the system is at a stable lock point, adjust the temperature if necessary
        elif (lock_age_condition and new_output_condition):
            update = False
            upper_limit_condition = (current_output > v_high2)
            lower_limit_condition = (current_output < v_low2)
            if upper_limit_condition or lower_limit_condition:
                update = True
        # Update the temperature setpoint
            if not(update):
                pass
            else:
            # If approaching the state limits, adjust the temperature setpoint
                adjustment_interval_condition = ((time.time()-timer['find_lock:tec_adjust']) > tec_adjust_interval)
                if (adjustment_interval_condition and (upper_limit_condition or lower_limit_condition)):
                # Queue the ILX TEC controller ----------
                    device_db = 'mll_fR/device_TEC'
                    thread_name = 'get_ilx_data'
                    thread[thread_name].join() # needed because releasing is too slow for the queue
                    sm.dev[device_db]['queue'].queue_and_wait(priority=True)
                    sm.dev[device_db]['driver'].open_tec()
                # Adjust timer
                    timer['find_lock:tec_adjust'] = time.time()
                # Adjust the setpoint
                    if lower_limit_condition:
                        log_str = ' Voltage = {:.3f}, raising the resistance setpoint'.format(current_output)
                        log.log_info(mod_name, func_name, log_str)
                    # Raise the resistance setpoint
                        settings_list = [{'tec_step':+1}, {'tec_resistance_setpoint':None}]
                        sm.update_device_settings(device_db, settings_list)
                    elif upper_limit_condition:
                        log_str = ' Voltage = {:.3f}, lowering the resistance setpoint'.format(current_output)
                        log.log_info(mod_name, func_name, log_str)
                    # Lower the resistance setpoint
                        settings_list = [{'tec_step':-1}, {'tec_resistance_setpoint':None}]
                        sm.update_device_settings(device_db, settings_list)
                # Remove the ILX TEC controller from queue ------------
                    sm.dev[device_db]['driver'].close_tec()
                    sm.dev[device_db]['queue'].remove()

# Lock Disabled ---------------------------------------------------------------
def lock_disabled(state_db):
    mod_name = __name__
    func_name = lock_disabled.__name__
# Check if the PID controller is on ---------------------------------
    if (sm.local_settings['mll_fR/device_PID']['pid_action'] != False):
    # Update state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = False
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
        log_str = " Lock enabled detected, transfering to manual"
        log.log_info(mod_name, func_name, log_str)


# %% Operate Functions -----------------------------------------------------------
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
                                        'x_min_limit':0.00, 'x_max_limit':60.00, 'x_voltage':0.00}},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor, 'search':find_lock,
                                'maintain':keep_lock, 'operate':sm.nothing}},
                'manual':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor, 'search':transfer_to_manual,
                                'maintain':sm.nothing, 'operate':sm.nothing}},
                'safe':{
                        'settings':{'mll_fR/device_PID':{'pid_action':False}},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor, 'search':transfer_to_manual,
                                'maintain':lock_disabled, 'operate':sm.nothing}},
                'engineering':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}}
                        }
        }
sm.init_states(STATES)

# %% STATE MACHINE ============================================================

'''Operates the state machine.'''
sm.operate_machine(main_loop_interval=0.5)


