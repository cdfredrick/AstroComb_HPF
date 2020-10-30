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

from Drivers.StateMachine import ThreadFactory, Machine

from Drivers.DAQ.Tasks import AiTask
from Drivers.DAQ.Tasks import DiTask


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
COMMS = 'monitor_DAQ'
sm.init_comms(COMMS)

# Internal database names --------------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function.
'''
STATE_DBs = [
        'monitor_DAQ/state_analog', 'monitor_DAQ/state_digital']
DEVICE_DBs =[
        'monitor_DAQ/device_DAQ_analog_in', 'monitor_DAQ/device_DAQ_digital_in']
MONITOR_DBs = [
    # Analog In
        'mll_fR/DAQ_error_signal',
        'filter_cavity/DAQ_error_signal', 'filter_cavity/heater_temperature',
        'ambience/box_temperature_0', 'ambience/box_temperature_1', 'ambience/rack_temperature_0',
        #'dc_power/12V_0', 'dc_power/12V_1', 'dc_power/12V_2', 'dc_power/12V_3',
        #'dc_power/8V_0', 'dc_power/15V_0', 'dc_power/24V_0', 'dc_power/24V_1',
    # Digital In
        'rf_oscillators/1GHz_phase_lock','rf_oscillators/100MHz_phase_lock'#,'rf_oscillators/10GHz_phase_lock',
        #'chiller/system_alarm', 'chiller/pump_alarm'
        ]
LOG_DB = 'monitor_DAQ'
CONTROL_DB = 'monitor_DAQ/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]
sm.init_master_DB_names(STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB)

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = []
READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs
sm.init_read_DB_names(R_STATE_DBs, R_DEVICE_DBs, R_MONITOR_DBs)

# Default settings ------------------------------------------------------------
'''A template for all settings used in this script. Upon initialization
these settings are checked against those saved in the database, and
populated if found empty. Each state and device database should be
represented.
'''
STATE_SETTINGS = {
        'monitor_DAQ/state_analog':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'read',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()},
        'monitor_DAQ/state_digital':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'read',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()}}
DEVICE_SETTINGS = {
        # DAQ settings
        'monitor_DAQ/device_DAQ_analog_in':{
                'driver':AiTask,
                'queue':'DAQ_ai',
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
                'reserve_cont':False, 'reserve_point':False},
        'monitor_DAQ/device_DAQ_digital_in':{
                'driver':DiTask,
                'queue':'DAQ_di',
                '__init__':[
                    [[{'physical_channel':'Dev1/port0/line0'}, # 'rf_osc/1GHz_phase_lock'
                      {'physical_channel':'Dev1/port0/line1'}]], # 'rf_osc/100MHz_phase_lock'
#                      {'physical_channel':'Dev1/port0/line2'}, # 'rf_osc/10GHz_phase_lock'
#                      {'physical_channel':'Dev1/port0/line3'}, # 'chiller/system_alarm'
#                      {'physical_channel':'Dev1/port0/line4'}]], # 'chiller/pump_alarm'
                      {'timeout':5.0}],
                'reserve_cont':False, 'reserve_point':False}}
CONTROL_PARAMS = {CONTROL_DB:{}}
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))
sm.init_default_settings(STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS)

ai_map = {'mll_fR/DAQ_error_signal':0,
          'filter_cavity/DAQ_error_signal':1,
          'filter_cavity/heater_temperature':[2,3],
          'ambience/box_temperature_0':4,
          'ambience/box_temperature_1':5,
          'ambience/rack_temperature_0':6}
di_map = {'rf_oscillators/1GHz_phase_lock':0,
          'rf_oscillators/100MHz_phase_lock':1}


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
settings are populated with the default values.
'''
sm.init_device_drivers_and_settings()

# Initialize Local Copy of Monitors -------------------------------------------
'''This initializes all device drivers and checks that all settings
(as listed in SETTINGS) exist within the databases. Any missing
settings are populated with the default values.
'''
sm.init_monitors()


# %% State Functions ==========================================================

# Global Variables ------------------------------------------------------------
timer = {}
array = {}
thread = {}
fifo_q = {}
for state_db in STATE_DBs:
    timer[state_db] = {}


# %% Monitor Functions ========================================================
'''This section is for defining the methods needed to monitor the system.'''


# %% Search Functions =========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''

# Queue and Reserve -----------------------------------------------------------
def queue_and_reserve(state_db):
    mod_name = queue_and_reserve.__module__
    func_name = queue_and_reserve.__name__
    if (state_db == 'monitor_DAQ/state_analog'):
        device_db ='monitor_DAQ/device_DAQ_analog_in'
        queue_position = sm.dev[device_db]['queue'].position()
        if (queue_position < 0):
            queue_size = len(sm.dev[device_db]['queue'].get_queue())
        # Add to queue
            sm.dev[device_db]['queue'].push()
        elif (queue_position == 0):
            queue_size = len(sm.dev[device_db]['queue'].get_queue())
            if (queue_size == 1):
            # Reserve and start the DAQ
                sm.dev[device_db]['driver'].reserve_cont(True)
            # Update the state variable
                with sm.lock[state_db]:
                    sm.current_state[state_db]['compliance'] = True
                    sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
                log_str = " Reserving ai DAQ"
                log.log_info(mod_name, func_name, log_str)
            else:
            # Start over if something else is in the queue
                sm.dev[device_db]['queue'].remove()
    elif (state_db == 'monitor_DAQ/state_digital'):
        device_db ='monitor_DAQ/device_DAQ_digital_in'
        queue_position = sm.dev[device_db]['queue'].position()
        if (queue_position < 0):
            queue_size = len(sm.dev[device_db]['queue'].get_queue())
        # Add to queue
            sm.dev[device_db]['queue'].push()
        elif (queue_position == 0):
            queue_size = len(sm.dev[device_db]['queue'].get_queue())
            if (queue_size == 1):
            # Read single
                read_di_DAQ_single()
            # Reserve and start the DAQ
                sm.dev[device_db]['driver'].reserve_cont(True)
            # Update the state variable
                with sm.lock[state_db]:
                    sm.current_state[state_db]['compliance'] = True
                    sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
                log_str = " Reserving di DAQ"
                log.log_info(mod_name, func_name, log_str)
            else:
            # Start over if something else is in the queue
                sm.dev[device_db]['queue'].remove()

# Read di single --------------------------------------------------------------
last_value = {}
def read_di_DAQ_single():
    device_db = 'monitor_DAQ/device_DAQ_digital_in'
# Double check queue
    sm.dev[device_db]['queue'].queue_and_wait()
# Get values
    multi_channel_reading = sm.dev[device_db]['driver'].read_point()
# Update buffers and databases -----------------------------
# port0/line0, 'rf_oscillators/1GHz_phase_lock' ----------------------
    monitor_db = 'rf_oscillators/1GHz_phase_lock'
    channel_index = di_map[monitor_db] # 0
    last_value[monitor_db] = [multi_channel_reading[channel_index]]
# port0/line1, 'rf_oscillators/100MHz_phase_lock' ----------------------
    monitor_db = 'rf_oscillators/100MHz_phase_lock'
    channel_index = di_map[monitor_db] # 1
    last_value[monitor_db] = [multi_channel_reading[channel_index]]


# %% Maintain Functions =======================================================
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''

# Touch -----------------------------------------------------------------------
touch_interval = 1 # second
for state_db in STATE_DBs:
    timer[state_db]['touch'] = sm.get_lap(touch_interval)
def touch(state_db):
    mod_name = touch.__module__
    func_name = touch.__name__
    if (state_db == 'monitor_DAQ/state_analog'):
        device_db ='monitor_DAQ/device_DAQ_analog_in'
        queue_size = len(sm.dev[device_db]['queue'].get_queue())
        if (queue_size != 1):
        # Other scripts want to use the DAQ
        # Unreserve and dequeue DAQ
            sm.dev[device_db]['driver'].reserve_cont(False)
            sm.dev[device_db]['queue'].remove()
        # Update state variable
            with sm.lock[state_db]:
                sm.current_state[state_db]['compliance'] = False
                sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
            log_str = " Releasing ai DAQ, other processes waiting in the queue"
            log.log_info(mod_name, func_name, log_str)
        elif not(sm.dev[device_db]['driver'].reserve_cont()):
        # Continuous aquisition has not been reserved
        # Dequeue
            sm.dev[device_db]['queue'].remove()
        # Update state variable
            with sm.lock[state_db]:
                sm.current_state[state_db]['compliance'] = False
                sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
            log_str = " Releasing ai DAQ, continuous acquisition has not been reserved"
            log.log_info(mod_name, func_name, log_str)
        else:
        # Touch queue (prevent timeout)
            touch_lap = sm.get_lap(touch_interval)
            if touch_lap > timer[state_db]['touch']:
                timer[state_db]['touch'] = touch_lap
                sm.dev[device_db]['queue'].touch()
    if (state_db == 'monitor_DAQ/state_digital'):
        device_db ='monitor_DAQ/device_DAQ_digital_in'
        queue_size = len(sm.dev[device_db]['queue'].get_queue())
        if (queue_size != 1):
        # Other scripts want to use the DAQ
        # Unreserve and dequeue DAQ
            sm.dev[device_db]['driver'].reserve_cont(False)
            sm.dev[device_db]['queue'].remove()
        # Update state variable
            with sm.lock[state_db]:
                sm.current_state[state_db]['compliance'] = False
                sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
            log_str = " Releasing di DAQ, other processes waiting in the queue"
            log.log_info(mod_name, func_name, log_str)
        elif not(sm.dev[device_db]['driver'].reserve_cont()):
        # Continuous aquisition has not been reserved
        # Dequeue
            sm.dev[device_db]['queue'].remove()
        # Update state variable
            with sm.lock[state_db]:
                sm.current_state[state_db]['compliance'] = False
                sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
            log_str = " Releasing di DAQ, continuous acquisition has not been reserved"
            log.log_info(mod_name, func_name, log_str)
        else:
        # Touch queue (prevent timeout)
            touch_lap = sm.get_lap(touch_interval)
            if touch_lap > timer[state_db]['touch']:
                timer[state_db]['touch'] = touch_lap
                sm.dev[device_db]['queue'].touch()


# %% Operate Functions ========================================================
'''This section is for defining the methods called only when the system is in
    its defined states.'''

# Queue Worker ----------------------------------------------------------------
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
# Analog In
fifo_q['daq:ai_buffer'] = queue.Queue()
thread['daq:ai_buffer'] = ThreadFactory(target=queue_worker, args=['daq:ai_buffer'])
fifo_q['daq:ai_record'] = queue.Queue()
thread['daq:ai_record'] = ThreadFactory(target=queue_worker, args=['daq:ai_record'])
# Digital In
fifo_q['daq:di_buffer'] = queue.Queue()
thread['daq:di_buffer'] = ThreadFactory(target=queue_worker, args=['daq:di_buffer'])
fifo_q['daq:di_record'] = queue.Queue()
thread['daq:di_record'] = ThreadFactory(target=queue_worker, args=['daq:di_record'])

# Buffer Ai -------------------------------------------------------------------
def buffer_ai(monitor_db, data_mean, data_std, data_n, timestamp, channel_identifiers=None):
    with sm.lock[monitor_db]:
        if (channel_identifiers == None):
            sm.mon[monitor_db]['new'] = True
            sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    data_mean, 500)
            sm.db[monitor_db].write_buffer({'V':data_mean, 'std':data_std, 'n':data_n}, timestamp=timestamp)
        elif (type(channel_identifiers) == list):
            data_buffer = {}
            sm.mon[monitor_db]['new'] = True
            sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    data_mean, 500)
            for ind, name in enumerate(channel_identifiers):
                data_buffer[name+'_V'] = data_mean[ind]
                data_buffer[name+'_std'] = data_std[ind]
                data_buffer[name+'_n'] = data_n
            sm.db[monitor_db].write_buffer(data_buffer, timestamp=timestamp)

# Record Ai -------------------------------------------------------------------
array['daq:ai0'] = []
array['daq:ai1'] = []
array['daq:ai2'] = []
array['daq:ai3'] = []
array['daq:ai4'] = []
array['daq:ai5'] = []
array['daq:ai6'] = []
daq_record_interval = 10 # seconds
timer['daq:record_ai'] = sm.get_lap(daq_record_interval)
def record_ai(monitor_db, data, timestamp, write_record, array_identifier, channel_identifiers=None):
    with sm.lock[monitor_db]:
        if (channel_identifiers == None):
            # Append to record array ----------------
            array[array_identifier].extend(data)
            if write_record:
                if len(array[array_identifier]):
                    array[array_identifier] = np.array(array[array_identifier])
                    # Record statistics ---------------------
                    sm.db[monitor_db].write_record({
                            'V':array[array_identifier].mean(),
                            'std':array[array_identifier].std(),
                            'n':array[array_identifier].size}, timestamp=timestamp)
                    # Empty the array -----------------------
                    array[array_identifier] = []
        elif (type(channel_identifiers) == list):
            # Append to record arrays ---------------
            array_size = [] # check if data is in arrays
            for ind, name in enumerate(channel_identifiers):
                array[array_identifier[ind]].extend(data[ind])
                array_size.append(len(array[array_identifier[ind]]))
            if write_record:
                data_record = {}
                if np.all(array_size):
            # Record statistics ---------------------
                    for ind, name in enumerate(channel_identifiers):
                        array[array_identifier[ind]] = np.array(array[array_identifier[ind]])
                        data_record[name+'_V'] = array[array_identifier[ind]].mean()
                        data_record[name+'_std'] = array[array_identifier[ind]].std()
                        data_record[name+'_n'] = array[array_identifier[ind]].size
                    sm.db[monitor_db].write_record(data_record, timestamp=timestamp)
            # Empty the arrays ----------------------
                    for ind, name in enumerate(channel_identifiers):
                        array[array_identifier[ind]] = []

# Read Ai ---------------------------------------------------------------------
control_interval = 0.5 # s
for state_db in STATE_DBs:
    timer[state_db]['data'] = sm.get_lap(control_interval)
def read_ai_DAQ(state_db):
# Get lap number
    new_control_lap = sm.get_lap(control_interval)
    new_record_lap = sm.get_lap(daq_record_interval)
# Read DAQ ----------------------------------------------------------
    if (new_control_lap > timer[state_db]['data']):
        device_db = 'monitor_DAQ/device_DAQ_analog_in'
    # Double check queue
        sm.dev[device_db]['queue'].queue_and_wait()
    # Get values
        multi_channel_reading = np.array(sm.dev[device_db]['driver'].read_cont())
        timestamp=datetime.datetime.utcnow()
        sample_size = multi_channel_reading.size
        if sample_size > 0:
            multi_channel_mean = multi_channel_reading.mean(axis=1)
            multi_channel_std = multi_channel_reading.std(axis=1)
            multi_channel_n = multi_channel_reading.shape[1]
            multi_channel_reading = multi_channel_reading.tolist()
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
            data = [multi_channel_reading[channel_index] for channel_index in channel_indicies]
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
            thread_name = 'daq:ai_buffer'
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            if not(alive):
            # Start new thread
                thread[thread_name].start()
            thread_name = 'daq:ai_record'
            (alive, error) = thread[thread_name].check_thread()
            if error != None:
                raise error[1].with_traceback(error[2])
            if not(alive):
            # Start new thread
                thread[thread_name].start()
        # Propogate lap numbers -------------------------------------
            if write_record:
                timer['daq:record_ai'] = new_record_lap
    # Propogate lap numbers -----------------------------------------
        timer[state_db]['data'] = new_control_lap

# Buffer Di -------------------------------------------------------------------
def buffer_di(monitor_db, current_value, flips, timestamp, channel_identifiers=None):
    with sm.lock[monitor_db]:
        if (channel_identifiers == None):
            sm.mon[monitor_db]['new'] = True
            sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    current_value, 500)
            sm.db[monitor_db].write_buffer({'bit':bool(current_value), 'flips':int(flips)},
                                          timestamp=timestamp)
        elif (type(channel_identifiers) == list):
            data_buffer = {}
            sm.mon[monitor_db]['new'] = True
            sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    current_value, 500)
            for ind, name in enumerate(channel_identifiers):
                data_buffer[name+'_bit'] = bool(current_value[ind])
                data_buffer[name+'_flips'] = int(flips[ind])
            sm.db[monitor_db].write_buffer(data_buffer, timestamp=timestamp)

# Record Di -------------------------------------------------------------------
array['daq:port0/line0'] = []
array['daq:port0/line1'] = []
timer['daq:record_di'] = sm.get_lap(daq_record_interval)
def record_di(monitor_db, data, timestamp, write_record, array_identifier, channel_identifiers=None):
    with sm.lock[monitor_db]:
        if (channel_identifiers == None):
            # Append to record array ----------------
            array[array_identifier].extend(data)
            if write_record:
                if len(array[array_identifier]):
            # Record statistics ---------------------
                    sm.db[monitor_db].write_record({
                            'bit':bool(array[array_identifier][-1]),
                            'flips':int(np.sum(np.diff(array[array_identifier])))},
                            timestamp=timestamp)
            # Empty the array -----------------------
                    array[array_identifier] = [array[array_identifier][-1]]
        elif (type(channel_identifiers) == list):
            # Append to record arrays ---------------
            array_size = []
            for ind, name in enumerate(channel_identifiers):
                array[array_identifier[ind]].extend(data[ind])
                array_size.append(len(array[array_identifier[ind]]))
            if write_record:
                data_record = {}
                if np.all(array_size):
            # Record statistics ---------------------
                    for ind, name in enumerate(channel_identifiers):
                        data_record[name+'_bit'] = bool(array[array_identifier[ind]][-1])
                        data_record[name+'_flips'] = int(np.sum(np.diff(array[array_identifier[ind]])))
                    sm.db[monitor_db].write_record(data_record, timestamp=timestamp)
            # Empty the arrays ----------------------
                    for ind, name in enumerate(channel_identifiers):
                        array[array_identifier[ind]] = [array[array_identifier[ind]][-1]]

# Read Di ---------------------------------------------------------------------
def read_di_DAQ(state_db):
# Get lap number
    new_control_lap = sm.get_lap(control_interval)
    new_record_lap = sm.get_lap(daq_record_interval)
    write_record = (new_record_lap > timer['daq:record_di'])
# Read DAQ ----------------------------------------------------------
    if (new_control_lap > timer[state_db]['data']):
        device_db = 'monitor_DAQ/device_DAQ_digital_in'
    # Double check queue
        sm.dev[device_db]['queue'].queue_and_wait()
    # Get values
        multi_channel_reading = sm.dev[device_db]['driver'].read_cont()
        timestamp=datetime.datetime.utcnow()
    # Update buffers and databases -----------------------------
    # port0/line0, 'rf_oscillators/1GHz_phase_lock' ----------------------
        channel = 'daq:port0/line0'
        monitor_db = 'rf_oscillators/1GHz_phase_lock'
        channel_index = di_map[monitor_db] # 0
        data = last_value[monitor_db] + multi_channel_reading[channel_index]
        last_value[monitor_db] = [data[-1]]
        flips = int(np.sum(np.diff(data)))
        # Update buffer
        args = [monitor_db, last_value[monitor_db], flips, timestamp]
        item = threading.Thread(target=buffer_di, args=args, daemon=True)
        fifo_q['daq:di_buffer'].put(item, block=False)
        # Update record
        args = [monitor_db, data, timestamp, write_record, channel]
        item = threading.Thread(target=record_di, args=args, daemon=True)
        fifo_q['daq:di_record'].put(item, block=False)
    # port0/line1, 'rf_oscillators/100MHz_phase_lock' ----------------------
        channel = 'daq:port0/line1'
        monitor_db = 'rf_oscillators/100MHz_phase_lock'
        channel_index = di_map[monitor_db] # 1
        data = last_value[monitor_db] + multi_channel_reading[channel_index]
        last_value[monitor_db] = [data[-1]]
        flips = int(np.sum(np.diff(data)))
        # Update buffer
        args = [monitor_db, last_value[monitor_db], flips, timestamp]
        item = threading.Thread(target=buffer_di, args=args, daemon=True)
        fifo_q['daq:di_buffer'].put(item, block=False)
        # Update record
        args = [monitor_db, data, timestamp, write_record, channel]
        item = threading.Thread(target=record_di, args=args, daemon=True)
        fifo_q['daq:di_record'].put(item, block=False)
    # Check threads ---------------------------------------------
        thread_name = 'daq:di_buffer'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
        thread_name = 'daq:di_record'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()
    # Propogate lap numbers -------------------------------------
        if write_record:
            timer['daq:record_di'] = new_record_lap
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
        'monitor_DAQ/state_analog':{
                'read':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':sm.nothing, 'search':queue_and_reserve,
                                'maintain':touch, 'operate':read_ai_DAQ}},
                'safe':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}},
                'engineering':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}}
                        },
        'monitor_DAQ/state_digital':{
                'read':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':sm.nothing, 'search':queue_and_reserve,
                                'maintain':touch, 'operate':read_di_DAQ}},
                'safe':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}},
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


