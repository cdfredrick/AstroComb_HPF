# -*- coding: utf-8 -*-
"""
Created on Thu Dec 14 13:12:10 2017

@author: National Institute
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
import threading

from Drivers.VISA.SRS import SIM940


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
COMMS = 'rf_oscillators'
sm.init_comms(COMMS)

# Internal database names --------------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function.
'''
STATE_DBs = [
        'rf_oscillators/state_Rb_clock', 'rf_oscillators/state_PLOs']
DEVICE_DBs =[
        'rf_oscillators/device_Rb_clock']
MONITOR_DBs = [
        # Control Loop
        'rf_oscillators/Rb_status',
        # Passive
        'rf_oscillators/Rb_OCXO_control', 'rf_oscillators/Rb_detected_signals',
        'rf_oscillators/Rb_frequency_offset', 'rf_oscillators/Rb_magnetic_read',
        'rf_oscillators/Rb_time_tag',
        # DAC
        'rf_oscillators/Rb_dac_0', 'rf_oscillators/Rb_dac_1', 'rf_oscillators/Rb_dac_2',
        'rf_oscillators/Rb_dac_3', 'rf_oscillators/Rb_dac_4', 'rf_oscillators/Rb_dac_5',
        'rf_oscillators/Rb_dac_6', 'rf_oscillators/Rb_dac_7',
        # ADC
        'rf_oscillators/Rb_adc_0', 'rf_oscillators/Rb_adc_1', 'rf_oscillators/Rb_adc_2',
        'rf_oscillators/Rb_adc_3', 'rf_oscillators/Rb_adc_4', 'rf_oscillators/Rb_adc_5',
        'rf_oscillators/Rb_adc_6', 'rf_oscillators/Rb_adc_7', 'rf_oscillators/Rb_adc_8',
        'rf_oscillators/Rb_adc_9', 'rf_oscillators/Rb_adc_10', 'rf_oscillators/Rb_adc_11',
        'rf_oscillators/Rb_adc_12', 'rf_oscillators/Rb_adc_13', 'rf_oscillators/Rb_adc_14',
        'rf_oscillators/Rb_adc_15', 'rf_oscillators/Rb_adc_16', 'rf_oscillators/Rb_adc_17',
        'rf_oscillators/Rb_adc_18', 'rf_oscillators/Rb_adc_19']
LOG_DB = 'rf_oscillators'
CONTROL_DB = 'rf_oscillators/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]
sm.init_master_DB_names(STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB)

# External database names -----------------------------------------------------
'''This is a list of all databases external to this control script that are
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = ['rf_oscillators/1GHz_phase_lock', 'rf_oscillators/100MHz_phase_lock']
READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs
sm.init_read_DB_names(R_STATE_DBs, R_DEVICE_DBs, R_MONITOR_DBs)

# Default settings ------------------------------------------------------------
'''A template for all settings used in this script. Upon initialization
these settings are checked against those saved in the database, and
populated if found empty. Each state and device database should be represented.
'''
STATE_SETTINGS = {
        'rf_oscillators/state_Rb_clock':{
                'state':'engineering',
                'prerequisites':{
                        'critical':False,
                        'necessary':False,
                        'optional':False},
                'compliance':False,
                'desired_state':'lock',
                'initialized':False,
                'heartbeat':datetime.datetime.utcnow()},
        'rf_oscillators/state_PLOs':{
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
        'rf_oscillators/device_Rb_clock':{
                'driver':SIM940,
                'queue':'ASRL1',
                '__init__':[['ASRL1::INSTR', 7]],
                'lock_mode':1, 'lock_Rb':True, 'set_slope':None,
                'time_constant_Rb':None, 'phase':None, 'set_parameters':None,
                'magnetic_switching':True, 'magnetic_offset':None, 'time_slope':None,
                'lock_1pps':True, 'time_constant_1pps':None, 'stability_factor_1pps':None,
                }}
CONTROL_PARAMS = {CONTROL_DB:{}}
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(CONTROL_PARAMS.items()))
sm.init_default_settings(STATE_SETTINGS, DEVICE_SETTINGS, CONTROL_PARAMS)


# %% Initialize Databases, Devices, and Settings ==============================

# Connect to MongoDB ----------------------------------------------------------
'''Creates a client and connects to all defined databases'''
sm.init_DBs()

# Start Logging ---------------------------------------------------------------
'''Initializes logging for this script.
'''
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
'''Monitors should associate the monitor databases with the local, circular
buffers of the monitored data. Monitors should indicate when they have
recieved new data.
'''
sm.init_monitors()


# %% State Functions ==========================================================

# Global Timing Variable ------------------------------------------------------
timer = {}
array = {}
thread = {}


# %% Monitor Functions ========================================================
'''This section is for defining the methods needed to monitor the system.'''

# Get Rb clock data -----------------------------------------------------------
    # Arrays
array['rf_oscillators/Rb_OCXO_control'+'high'] = []
array['rf_oscillators/Rb_OCXO_control'+'low'] = []
array['rf_oscillators/Rb_detected_signals'+'mod'] = []
array['rf_oscillators/Rb_detected_signals'+'2mod'] = []
array['rf_oscillators/Rb_time_tag'] = []
    # Timers
control_interval = 0.5 # seconds
record_interval = 10 # seconds
timer['Rb:control'] = sm.get_lap(control_interval)
timer['Rb:record'] = sm.get_lap(record_interval)
def get_Rb_clock_data():
    device_db = 'rf_oscillators/device_Rb_clock'
# Get lap number
    new_control_lap = sm.get_lap(control_interval)
    new_record_lap = sm.get_lap(record_interval)
# Update control loop variables -------------------------------------
    if (new_control_lap > timer['Rb:control']):
    # Wait for queue
        sm.dev[device_db]['queue'].queue_and_wait()
    # Optimize I/O
        sm.dev[device_db]['driver'].open_port()
    # Get values
        # Status Bytes: 'rf_oscillators/Rb_status'
        status_bytes = sm.dev[device_db]['driver'].status()
            # Ignore "No 1pps Input" Warning
        status_bytes['5']['7'] = None
        # Time tag: 'rf_oscillators/Rb_time_tag'
        tm_tag = sm.dev[device_db]['driver'].time_tag()
        # Select other monitor
        if ((new_control_lap % 2)==0):
            selector= new_control_lap // 2
            if ((selector % 2) == 0):
                # OCXO parameters: 'rf_oscillators/Rb_OCXO_control'
                ocxo_ctrl = sm.dev[device_db]['driver'].OCXO_control()
            else:
                # Detected signals: 'rf_oscillators/Rb_detected_signals'
                dtc_sig = sm.dev[device_db]['driver'].detected_signals()
        else:
            selector = new_control_lap // 2
            if ((selector % 2)==0):
                # ADC: 'rf_oscillators/Rb_adc_{:}'
                selector = selector // 2
                adc_port = int(selector % 16)
                adc_v = sm.dev[device_db]['driver'].adc(adc_port)
            else:
                selector = selector // 2
                if ((selector % 2)==0):
                    # DAC: 'rf_oscillators/Rb_dac_{:}
                    selector = selector // 2
                    dac_port = int(selector % 8)
                    dac_byte = sm.dev[device_db]['driver'].dac(dac_port)
                else:
                    selector = selector // 2
                    if ((selector % 2)==0):
                        # ADC: 'rf_oscillators/Rb_adc_{:}'
                        selector = selector // 2
                        adc_port = int(16 + (selector % 4))
                        adc_v = sm.dev[device_db]['driver'].adc(adc_port)
                    else:
                        selector = selector // 2
                        if ((selector % 2)==0):
                            # Frequency offset: 'rf_oscillators/Rb_frequency_offset'
                            frq_offset = sm.dev[device_db]['driver'].frequency_offset()
                        else:
                            # Magnetic reading: 'rf_oscillators/Rb_magnetic_read'
                            mag_read = sm.dev[device_db]['driver'].magnetic_read()
# Dequeue -----------------------------------------------------------
    # Return to normal I/O
        sm.dev[device_db]['driver'].close_port()
    # Remove from queue
        sm.dev[device_db]['queue'].remove()
# Update buffers (and records) --------------------------------------
    # Status Bytes: --------------------------------------------
        monitor_db = 'rf_oscillators/Rb_status'
        with sm.lock[monitor_db]:
            if (sm.mon[monitor_db]['data'] != status_bytes):
                sm.mon[monitor_db]['new'] = True
                sm.mon[monitor_db]['data'] = status_bytes
                sm.db[monitor_db].write_record_and_buffer(status_bytes)
        # Raise warnings
        status_warnings(status_bytes)
    # Time tag: ------------------------------------------------
        monitor_db = 'rf_oscillators/Rb_time_tag'
        if (tm_tag != None):
            with sm.lock[monitor_db]:
                sm.mon[monitor_db]['new'] = True
                sm.mon[monitor_db]['data'] = sm.update_buffer(
                        sm.mon[monitor_db]['data'],
                        tm_tag, 500)
                sm.db[monitor_db].write_buffer({'ns':tm_tag})
                # Append to the record array
                array[monitor_db].append(tm_tag)
    # Select other monitor
        if ((new_control_lap % 2)==0):
            selector= new_control_lap // 2
            if ((selector % 2) == 0):
            # OCXO parameters: ---------------------------------
                monitor_db = 'rf_oscillators/Rb_OCXO_control'
                data = ocxo_ctrl
                keys = data.keys()
                with sm.lock[monitor_db]:
                    sm.mon[monitor_db]['new'] = True
                    sm.mon[monitor_db]['data'] = sm.update_buffer(
                            sm.mon[monitor_db]['data'],
                            list(data.values()), 500)
                    sm.db[monitor_db].write_buffer(data)
                    for key in keys:
                        # Append to the record array
                        array[monitor_db+key].append(data[key])
            else:
            # Detected signals: --------------------------------
                monitor_db = 'rf_oscillators/Rb_detected_signals'
                data = dtc_sig
                keys = data.keys()
                with sm.lock[monitor_db]:
                    sm.mon[monitor_db]['new'] = True
                    sm.mon[monitor_db]['data'] = sm.update_buffer(
                            sm.mon[monitor_db]['data'],
                            list(data.values()), 500)
                    sm.db[monitor_db].write_buffer(data)
                    for key in keys:
                        # Append to the record array
                        array[monitor_db+key].append(data[key])
        else:
            selector = new_control_lap // 2
            if ((selector % 2)==0):
            # ADC (0-15): --------------------------------------
                monitor_db = 'rf_oscillators/Rb_adc_{:}'.format(adc_port)
                with sm.lock[monitor_db]:
                    sm.mon[monitor_db]['new'] = True
                    sm.mon[monitor_db]['data'] = sm.update_buffer(
                            sm.mon[monitor_db]['data'],
                            adc_v, 500)
                    sm.db[monitor_db].write_record_and_buffer({'V':adc_v})
            else:
                selector = selector // 2
                if ((selector % 2)==0):
                # DAC (0-7): -----------------------------------
                    monitor_db = 'rf_oscillators/Rb_dac_{:}'.format(dac_port)
                    with sm.lock[monitor_db]:
                        sm.mon[monitor_db]['new'] = True
                        sm.mon[monitor_db]['data'] = sm.update_buffer(
                                sm.mon[monitor_db]['data'],
                                dac_byte, 500)
                        sm.db[monitor_db].write_record_and_buffer({'DAC':dac_byte})
                else:
                    selector = selector // 2
                    if ((selector % 2)==0):
                    # ADC (16-19): -----------------------------
                        monitor_db = 'rf_oscillators/Rb_adc_{:}'.format(adc_port)
                        with sm.lock[monitor_db]:
                            sm.mon[monitor_db]['new'] = True
                            sm.mon[monitor_db]['data'] = sm.update_buffer(
                                    sm.mon[monitor_db]['data'],
                                    adc_v, 500)
                            sm.db[monitor_db].write_record_and_buffer({'V':adc_v})
                    else:
                        selector = selector // 2
                        if ((selector % 2)==0):
                        # Frequency offset: --------------------
                            monitor_db = 'rf_oscillators/Rb_frequency_offset'
                            with sm.lock[monitor_db]:
                                sm.mon[monitor_db]['new'] = True
                                sm.mon[monitor_db]['data'] = sm.update_buffer(
                                        sm.mon[monitor_db]['data'],
                                        frq_offset, 500)
                                sm.db[monitor_db].write_record_and_buffer({'1e-12':frq_offset})
                        else:
                        # Magnetic reading: --------------------
                            monitor_db = 'rf_oscillators/Rb_magnetic_read'
                            with sm.lock[monitor_db]:
                                sm.mon[monitor_db]['new'] = True
                                sm.mon[monitor_db]['data'] = sm.update_buffer(
                                        sm.mon[monitor_db]['data'],
                                        mag_read, 500)
                                sm.db[monitor_db].write_record_and_buffer({'DAC':mag_read})
    # Propogate lap numbers ------------------------------------
        timer['Rb:control'] = new_control_lap
# Update records ----------------------------------------------------
    if (new_record_lap > timer['Rb:record']):
    # Time tag: ------------------------------------------------
        monitor_db = 'rf_oscillators/Rb_time_tag'
        with sm.lock[monitor_db]:
            # Record statistics
            if len(array[monitor_db]):
                array[monitor_db] = np.array(array[monitor_db])
                sm.db[monitor_db].write_record({
                        'ns':array[monitor_db].mean(),
                        'std':array[monitor_db].std(),
                        'n':array[monitor_db].size})
                # Empty the array
                array[monitor_db] = []
    # OCXO parameters: -----------------------------------------
        monitor_db = 'rf_oscillators/Rb_OCXO_control'
        with sm.lock[monitor_db]:
            # Record statistics
            record = {}
            update = False
            keys = ['high','low']
            for key in keys:
                if len(array[monitor_db+key]):
                    array[monitor_db+key] = np.array(array[monitor_db+key])
                    record[key] = array[monitor_db+key].mean()
                    record[key+'_std'] = array[monitor_db+key].std()
                    record[key+'_n'] = array[monitor_db+key].size
                    # Empty the array
                    update = True
                    array[monitor_db+key] = []
            if update:
                sm.db[monitor_db].write_record(record)
    # Detected signals: ----------------------------------------
        monitor_db = 'rf_oscillators/Rb_detected_signals'
        with sm.lock[monitor_db]:
            # Record statistics
            record = {}
            update = False
            keys = ['mod','2mod']
            for key in keys:
                if len(array[monitor_db+key]):
                    array[monitor_db+key] = np.array(array[monitor_db+key])
                    record[key] = array[monitor_db+key].mean()
                    record[key+'_std'] = array[monitor_db+key].std()
                    record[key+'_n'] = array[monitor_db+key].size
                    # Empty the array
                    update = True
                    array[monitor_db+key] = []
            if update:
                sm.db[monitor_db].write_record(record)
    # Propogate lap numbers -------------------------------------
        timer['Rb:record'] = new_record_lap
thread['get_Rb_clock_data'] = ThreadFactory(target=get_Rb_clock_data)

# Monitor Rb Clock ------------------------------------------------------------
def monitor_Rb_clock(state_db):
    new_control_lap = sm.get_lap(control_interval)
    if (new_control_lap > timer['Rb:control']):
    # Pull data from SRS ----------------------------------
        thread_name = 'get_Rb_clock_data'
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        if not(alive):
        # Start new thread
            thread[thread_name].start()

# Status Warnings -------------------------------------------------------------
for byte in range(1,6+1):
    for bit in range(8):
        timer['Rb_status_{:}_{:}'.format(byte, bit)] = 0
warning_interval = 100 #s
def status_warnings(status_bytes):
    mod_name = status_warnings.__module__
    func_name = status_warnings.__name__
# ST1 : Power supplies and Discharge Lamp
    byte = '1'
    byte_str = ' ST1 : Power supplies and Discharge Lamp'
    bit = '0'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'+24 for electronics < +22 Vdc','Increase supply voltage'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '1'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'+24 for electronics > +30 Vdc','Decrease supply voltage'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '2'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'+24 for heaters <+22 Vdc','Increase supply voltage'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '3'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'+24 for heaters > +30 Vdc','Decrease supply voltage'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '4'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Lamp light level too low','Wait; check SD2 setting'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '5'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Lamp light level too high','Check SD2 setting'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '6'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Gate voltage too low','Wait; check SD2 setting'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '7'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Gate voltage too high','Check SD2 setting'])
            log.log_warning(mod_name, func_name, log_str)
# ST2: RF Synthesizer
    byte = '2'
    byte_str = ' ST2: RF Synthesizer'
    bit = '0'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'RF synthesizer PLL unlocked','Query SP? verify values'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '1'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'RF crystal varactor too low','Query SP? verify values'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '2'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'RF crystal varactor too high','Query SP? verify values'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '3'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'RF VCO control too low','Query SP? verify values'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '4'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'RF VCO control too high','Query SP? verify values'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '5'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'RF AGC control too low','Check SD0? values'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '6'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'RF AGC control too high','Check SD0? values'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '7'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Bad PLL parameter','Query SP? verify values'])
            log.log_warning(mod_name, func_name, log_str)
# ST3: Temperature Controllers
    byte = '3'
    byte_str = ' ST3: Temperature Controllers'
    bit = '0'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Lamp temp below set point','Wait for warm-up'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '1'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Lamp temp above set point','Check SD3, ambient'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '2'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Crystal temp below set point','Wait for warm-up'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '3'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Crystal temp above set point','Check SD4, ambient'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '4'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Cell temp below set point','Wait for warm-up'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '5'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Cell temp above set point','Check SD5, ambient'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '6'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Case temperature too low','Wait for warm-up'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '7'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Case temperature too high','Reduce ambient'])
            log.log_warning(mod_name, func_name, log_str)
# ST4: Frequency Lock-Loop Control
    byte = '4'
    byte_str = ' ST4: Frequency Lock-Loop Control'
    bit = '0'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Frequency lock control is off','Wait for warm-up'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '1'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Frequency lock is disabled','Enable w/LO1 command'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '2'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'10 MHz EFC is too high','SD4,SP,10MHz cal,Tamb'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '3'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'10 MHz EFC is too low','SP, 10 MHz cal'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '4'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Analog cal voltage > 4.9 V','Int cal. pot, ext cal. volt'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '5'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Analog cal voltage < 0.1','Int cal. pot, ext cal. volt'])
            log.log_warning(mod_name, func_name, log_str)
# ST5: Frequency Lock to External 1pps
    byte = '5'
    byte_str = ' ST5: Frequency Lock to External 1pps'
    bit = '0'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'PLL disabled','Send PL 1 to enable'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '1'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'< 256 good 1pps inputs','Provide stable 1pps inputs'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '2'
    if not(status_bytes[byte][bit]):
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'PLL is inactive', 'Wait; check other ST5'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '3'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'> 256 bad 1pps inputs','Provide stable 1pps inputs'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '4'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Excessive time interval','Provide accurate 1pps'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '5'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'PLL restarted','Provide stable 1pps inputs'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '6'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'f control saturated','Wait; check 1pps inputs'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '7'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'No 1pps input','Provide 1pps input'])
            log.log_debug(mod_name, func_name, log_str)
# ST6: System Level Events
    byte = '6'
    byte_str = ' ST6: System Level Events'
    bit = '0'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Lamp restart'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '1'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Watchdog time-out and reset'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '2'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Bad interrupt vector'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '3'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'EEPROM write failure'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '4'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'EEPROM data corruption'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '5'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Bad command syntax'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '6'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Bad command parameter'])
            log.log_warning(mod_name, func_name, log_str)
    bit = '7'
    if status_bytes[byte][bit]:
        if ((time.time() - timer['Rb_status_{:}_{:}'.format(byte, bit)]) >= warning_interval):
            timer['Rb_status_{:}_{:}'.format(byte, bit)] = time.time()
            log_str = '\n '.join([byte_str,'Unit has been reset'])
            log.log_warning(mod_name, func_name, log_str)

# Monitor PLOs ----------------------------------------------------------------
for monitor_db in ['rf_oscillators/1GHz_phase_lock','rf_oscillators/100MHz_phase_lock']:
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = False
        sm.mon[monitor_db]['data'] = {}
        sm.mon[monitor_db]['data']['bit'] = []
        sm.mon[monitor_db]['data']['flips'] = []
plo_control_interval = 0.5 # seconds
timer['PLO:control'] = sm.get_lap(plo_control_interval)
def monitor_PLOs(state_db):
    new_control_lap = sm.get_lap(plo_control_interval)
    if (new_control_lap > timer['PLO:control']):
# Pull data from external databases -------------------
        for monitor_db in ['rf_oscillators/1GHz_phase_lock','rf_oscillators/100MHz_phase_lock']:
            new_bits = []
            new_flips = []
            for doc in sm.mon[monitor_db]['cursor'].read():
                new_bits.append(doc['bit'])
                new_flips.append(doc['flips'])
             # Update buffers -----------------------
            if len(new_bits) > 0:
                with sm.lock[monitor_db]:
                    sm.mon[monitor_db]['new'] = True
                    sm.mon[monitor_db]['data']['bit'].extend(new_bits)
                    sm.mon[monitor_db]['data']['flips'].extend(new_flips)


# %% Search Functions =========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''

# wait_for_locks --------------------------------------------------------------
def wait_for_locks(state_db):
    mod_name = wait_for_locks.__module__
    func_name = wait_for_locks.__name__
    monitor_db = 'rf_oscillators/Rb_status'
    with sm.lock[monitor_db]:
        if sm.mon[monitor_db]['new']:
            locked_Rb = not(sm.mon[monitor_db]['data']['4']['0'])
            locked_1pps = sm.mon[monitor_db]['data']['5']['2']
            sm.mon[monitor_db]['new'] = False
            if (locked_Rb and locked_1pps):
            # Everything is locked
                # Update the state variable
                with sm.lock[state_db]:
                    sm.current_state[state_db]['compliance'] = True
                    sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
                log_str = ' Rb and 1pps locks engaged'
                log.log_info(mod_name, func_name, log_str)

# wait_for_PLOs --------------------------------------------------------------
def wait_for_PLOs(state_db):
    mod_name = wait_for_PLOs.__module__
    func_name = wait_for_PLOs.__name__
    monitor_db = 'rf_oscillators/1GHz_phase_lock'
    with sm.lock[monitor_db]:
        new_1GHz = sm.mon[monitor_db]['new']
        if new_1GHz:
            locked_1GHz = sm.mon[monitor_db]['data']['bit'][-1]
    monitor_db = 'rf_oscillators/100MHz_phase_lock'
    with sm.lock[monitor_db]:
        new_100MHz = sm.mon[monitor_db]['new']
        if new_100MHz:
            locked_100MHz = sm.mon[monitor_db]['data']['bit'][-1]
    if (new_1GHz and new_100MHz):
    # Locked?
        if (locked_1GHz and locked_100MHz):
        # Update state variable
            with sm.lock[state_db]:
                sm.current_state[state_db]['compliance'] = True
                sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
                log_str = ' 1GHz and 100MHz phase locks engaged'
                log.log_info(mod_name, func_name, log_str)
        for monitor_db in ['rf_oscillators/1GHz_phase_lock','rf_oscillators/100MHz_phase_lock']:
            with sm.lock[monitor_db]:
                sm.mon[monitor_db]['new'] = False
                sm.mon[monitor_db]['data']['bit'] = []
                sm.mon[monitor_db]['data']['flips'] = []


# %% Maintain Functions =======================================================
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''

# Check Locks -----------------------------------------------------------------
def check_locks(state_db):
    mod_name = check_locks.__module__
    func_name = check_locks.__name__
    monitor_db = 'rf_oscillators/Rb_status'
    with sm.lock[monitor_db]:
        if sm.mon[monitor_db]['new']:
            locked_Rb = not(sm.mon[monitor_db]['data']['4']['0'])
            locked_1pps = sm.mon[monitor_db]['data']['5']['2']
            sm.mon[monitor_db]['new'] = False
            if not(locked_Rb and locked_1pps):
            # Something is unlocked
                # Update the state variable
                with sm.lock[state_db]:
                    sm.current_state[state_db]['compliance'] = False
                    sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
                if not(locked_Rb) and not(locked_1pps):
                    log_str = ' Rb and 1pps locks not engaged'
                elif not(locked_Rb):
                    log_str = ' Rb lock not engaged'
                elif not(locked_1pps):
                    log_str = ' 1pps lock not engaged'
                log.log_info(mod_name, func_name, log_str)


# Check Locks -----------------------------------------------------------------
def check_PLOs(state_db):
    mod_name = check_PLOs.__module__
    func_name = check_PLOs.__name__
    monitor_db = 'rf_oscillators/Rb_status'
    monitor_db = 'rf_oscillators/1GHz_phase_lock'
    with sm.lock[monitor_db]:
        new_1GHz = sm.mon[monitor_db]['new']
        if new_1GHz:
            locked_1GHz = sm.mon[monitor_db]['data']['bit'][-1]
            flipped_1GHz = np.sum(sm.mon[monitor_db]['data']['flips'])
    monitor_db = 'rf_oscillators/100MHz_phase_lock'
    with sm.lock[monitor_db]:
        new_100MHz = sm.mon[monitor_db]['new']
        if new_100MHz:
            locked_100MHz = sm.mon[monitor_db]['data']['bit'][-1]
            flipped_100MHz = np.sum(sm.mon[monitor_db]['data']['flips'])
    if (new_1GHz and new_100MHz):
    # Locked?
        if (not(locked_1GHz and locked_100MHz) or (flipped_1GHz or flipped_100MHz)):
        # Something is unlocked
            # Update the state variable
            with sm.lock[state_db]:
                sm.current_state[state_db]['compliance'] = False
                sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
            if not(locked_1GHz) and not(locked_100MHz):
                lock_log_str = ' 1GHz and 100MHz locks not engaged'
            elif not(locked_1GHz):
                lock_log_str = ' 1GHz lock not engaged'
            elif not(locked_100MHz):
                lock_log_str = ' 100MHz lock not engaged'
            else:
                lock_log_str = ''
            if not(flipped_1GHz) and not(flipped_100MHz):
                flip_log_str = ' 1GHz and 100MHz locks unstable'
            elif not(flipped_1GHz):
                flip_log_str = ' 1GHz lock unstable'
            elif not(flipped_100MHz):
                flip_log_str = ' 100MHz lock unstable'
            else:
                flip_log_str = ''
            if (len(lock_log_str) and len(flip_log_str)):
                log_str = '\n'.join([lock_log_str,flip_log_str])
            elif len(lock_log_str):
                log_str = lock_log_str
            elif len(flip_log_str):
                log_str = flip_log_str
            log.log_info(mod_name, func_name, log_str)
        # Clear monitors
        for monitor_db in ['rf_oscillators/1GHz_phase_lock','rf_oscillators/100MHz_phase_lock']:
            with sm.lock[monitor_db]:
                sm.mon[monitor_db]['new'] = False
                sm.mon[monitor_db]['data']['bit'] = []
                sm.mon[monitor_db]['data']['flips'] = []


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
        'rf_oscillators/state_Rb_clock':{
                'lock':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor_Rb_clock, 'search':wait_for_locks,
                                'maintain':check_locks, 'operate':sm.nothing}},
                'safe':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor_Rb_clock, 'search':sm.nothing,
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
        'rf_oscillators/state_PLOs':{
                'lock':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor_PLOs, 'search':wait_for_PLOs,
                                'maintain':check_PLOs, 'operate':sm.nothing}},
                'safe':{
                        'settings':{},
                        'prerequisites':{
                                'critical':[],
                                'necessary':[],
                                'optional':[]},
                        'routines':{
                                'monitor':monitor_PLOs, 'search':sm.nothing,
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


