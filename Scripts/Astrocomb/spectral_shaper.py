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

#--- Communications queue -----------------------------------------------------
'''The communications queue is a couchbase queue that serves as the
intermediary between this script and others.
'''
COMMS = 'spectral_shaper'
sm.init_comms(COMMS)


#--- Internal database names --------------------------------------------------
'''The following are all of the databases that this script directly
controls. Each of these databases are initialized within this script.
The databases should be grouped by function
'''
STATE_DBs = [
    'spectral_shaper/state_SLM',
    'spectral_shaper/state_optimizer',
    ]
DEVICE_DBs =[
    'spectral_shaper/device_OSA',
    'spectral_shaper/device_rotation_mount',
    'spectral_shaper/device_IM_bias',
    ]
MONITOR_DBs = [
    'spectral_shaper/mask', 'spectral_shaper/spectrum',
    'spectral_shaper/DW', 'spectral_shaper/DW_vs_IM_bias',
    'spectral_shaper/DW_vs_waveplate_angle',
    'spectral_shaper/DW_bulk_vs_waveplate_angle',
    ]
LOG_DB = 'spectral_shaper'
CONTROL_DB = 'spectral_shaper/control'
MASTER_DBs = STATE_DBs + DEVICE_DBs + MONITOR_DBs + [LOG_DB] + [CONTROL_DB]
sm.init_master_DB_names(STATE_DBs, DEVICE_DBs, MONITOR_DBs, LOG_DB, CONTROL_DB)


#--- External database names --------------------------------------------------
'''This is a list of all databases external to this control script that are
    needed to check prerequisites'''
R_STATE_DBs = []
R_DEVICE_DBs =[]
R_MONITOR_DBs = [
    'broadening_stage/device_rotation_mount',
    'comb_generator/device_IM_bias',
    ]
READ_DBs = R_STATE_DBs + R_DEVICE_DBs + R_MONITOR_DBs
sm.init_read_DB_names(R_STATE_DBs, R_DEVICE_DBs, R_MONITOR_DBs)


#--- Default settings ---------------------------------------------------------
'''A template for all settings used in this script. Upon initialization
these settings are checked against those saved in the database, and
populated if found empty. Each state and device database should be represented.
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
        'heartbeat':datetime.datetime.utcnow()
        },
    'spectral_shaper/state_optimizer':{
        'state':'engineering',
        'prerequisites':{
            'critical':False,
            'necessary':False,
            'optional':False},
        'compliance':False,
        'desired_state':'optimal',
        'initialized':False,
        'heartbeat':datetime.datetime.utcnow()
        },
    }
DEVICE_SETTINGS = {
    'spectral_shaper/device_rotation_mount':{
        'driver':KDC101_PRM1Z8,
        'queue':'27251608',
        '__init__':[
            [''], #TODO: add COM port
            {'timeout':5,
             'serial_number':27251608}
            ]
        },
    'spectral_shaper/device_OSA':{
        'driver':OSA,
        'queue':'GPIB0::27',
        '__init__':[['GPIB0::27::INSTR']]
        },
    'spectral_shaper/device_IM_bias':{
        'driver':E36103A,
        'queue':'IM_bias',
        '__init__':[['USB0::0x2A8D::0x0702::MY57427460::INSTR']]
        },
    }
CONTROL_PARAMS = {
    CONTROL_DB:{
        'setpoint_optimization':{'value':tomorrow_at_noon(),'type':'float'},
        'DW_setpoint':{'value':-45.5,'type':'float'}}
    }

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

#--- Initialize all Devices and Settings --------------------------------------
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
'''
sm.init_monitors()


# %% State Functions ==========================================================

#--- Global Variables ---------------------------------------------------------
timer = {}
thread = {}
array = {}
warning = {}
warning_interval = 100 # seconds


# %% Monitor Functions ========================================================
'''This section is for defining the methods needed to monitor the system.'''

## Initialize monitor
#monitor_db = 'broadening_stage/device_rotation_mount'
# # Update buffers -----------------------
#with sm.lock[monitor_db]:
#    sm.mon[monitor_db]['new'] = True
#    sm.mon[monitor_db]['data'] = update_buffer(
#        sm.mon[monitor_db]['data'],
#        sm.db[monitor_db].read_buffer()['position'], 500)

# Get Spectrum from OSA -------------------------------------------------------
array['spectrum'] = []
array['DW'] = []
spectrum_record_interval = 1000 # seconds
timer['spectrum:record'] = sm.get_lap(spectrum_record_interval)
def get_spectrum():
    # Get lap number
    new_record_lap = sm.get_lap(spectrum_record_interval)
    timer_id = 'spectrum:record'
    #--- Get Data ---------------------------------------------------------
    # Device DB
    device_db = 'spectral_shaper/device_OSA'
    # Wait for queue
    sm.dev[device_db]['queue'].queue_and_wait()
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
        sm.dev[device_db]['queue'].touch()
    # Remove from Queue
    sm.dev[device_db]['queue'].remove()
    # Get Result
    (alive, error) = thread[thread_name].check_thread()
    if error != None:
        raise error[1].with_traceback(error[2])
    else:
        osa_trace = thread[thread_name].result
    #--- Record Dispersive Wave -------------------------------------------
    monitor_db = 'spectral_shaper/DW'
    array_id = 'DW'
    dw_ind = ((np.array(osa_trace['data']['x']) < 740) * (np.array(osa_trace['data']['x']) > 690)).astype(np.bool)
    data = np.max(np.array(osa_trace['data']['y'])[dw_ind])
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = sm.update_buffer(
            sm.mon[monitor_db]['data'],
            data, 100)
        sm.db[monitor_db].write_buffer({'dBm':data})
        # Append to the record array
        array[array_id].append(data)
        if (new_record_lap > timer[timer_id]):
            array[array_id] = np.array(array[array_id])
            array[array_id] = np.power(10, array[array_id]/10)*1e-3
            # Record statistics ---------------------
            sm.db[monitor_db].write_record({
                'W':array[array_id].mean(),
                'std':array[array_id].std(),
                'n':array[array_id].size})
            # Empty the array
            array[array_id] = []
    # Spectrum -----MUST BE LAST!!!------------------------
    monitor_db = 'spectral_shaper/spectrum'
    array_id = 'spectrum'
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = osa_trace
        sm.db[monitor_db].write_buffer(osa_trace)
        # Append to the record array
        array[array_id].append(osa_trace['data']['y'])
        if new_record_lap > timer[timer_id]:
            array[array_id] = np.array(array[array_id])
            array[array_id] = np.power(10, array[array_id]/10)*1e-3
            # Record statistics ---------------------
            y_mean = array[array_id].mean(axis=0)
            y_std = array[array_id].std(axis=0)
            y_n = array[array_id].shape[0]
            osa_trace['data']['W'] = y_mean.tolist()
            osa_trace['data']['W_std'] = y_std.tolist()
            osa_trace['data']['W_n'] = y_n
            osa_trace['data']['y'] = (10*np.log10(y_mean*1e3)).tolist()
            osa_trace['data']['y_std'] = (10/(y_mean*np.log(10))*y_std).tolist()
            osa_trace['data']['y_n'] = y_n
            sm.db[monitor_db].write_record(osa_trace)
            # Empty the array
            array[array_id] = []
# Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer[timer_id]:
        timer[timer_id] = new_record_lap

# Initialize threads
thread['get_spectrum'] = ThreadFactory(target=get_spectrum)
thread['get_new_single'] = ThreadFactory(target=sm.dev['spectral_shaper/device_OSA']['driver'].get_new_single)
thread['get_new_single_quick'] = ThreadFactory(target=sm.dev['spectral_shaper/device_OSA']['driver'].get_new_single, kwargs={'get_parameters':False})


# Record Spectrum -------------------------------------------------------------
control_interval = 0.5 # s
spectrum_interval = 100.0 # s
timer['monitor_spectrum:control'] = sm.get_lap(control_interval)
timer['monitor_spectrum:spectrum'] = sm.get_lap(spectrum_interval)
def monitor_spectrum(state_db):
# Get lap number
    new_control_lap = sm.get_lap(control_interval)
    new_spectrum_lap = sm.get_lap(spectrum_interval)
# Update control loop variables -------------------------------------
    if (new_control_lap > timer['monitor_spectrum:control']):
# Pull data from external databases -----------------------
    # Rotation Mount
        new_data = []
        monitor_db = 'broadening_stage/device_rotation_mount'
        for doc in sm.mon[monitor_db]['cursor']:
            new_data.append(doc['position'])
         # Update buffers -----------------------
        if len(new_data) > 0:
            with sm.lock[monitor_db]:
                sm.mon[monitor_db]['new'] = True
                sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    new_data, 500, extend=True)
    # Intensity Modulator Bias
        new_data = []
        monitor_db = 'comb_generator/device_IM_bias'
        for doc in sm.mon[monitor_db]['cursor']:
            new_data.append(doc['voltage_setpoint'])
        # Update buffers -----------------------
        if len(new_data) > 0:
            with sm.lock[monitor_db]:
                sm.mon[monitor_db]['new'] = True
                sm.mon[monitor_db]['data'] = sm.update_buffer(
                    sm.mon[monitor_db]['data'],
                    new_data, 500, extend=True)
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
    mask_path = STATES[state_db][sm.current_state[state_db]['state']]['settings']['mask']
    tkinter_queue.put(mask_path, block=False)
    tkinter_queue.join()
    # Update the state variable
    with sm.lock[state_db]:
        sm.current_state[state_db]['compliance'] = True
        sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
    # Update Monitor
    monitor_db = 'spectral_shaper/mask'
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = {'path':mask_path}
    sm.db[monitor_db].write_record_and_buffer({'path':mask_path})
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
    DW_high = sm.local_settings[CONTROL_DB]['DW_setpoint']['value']+DW_range_threshold # (1-DW_range_threshold)*DW_limits['max'] + DW_range_threshold*DW_limits['min']
    DW_low = sm.local_settings[CONTROL_DB]['DW_setpoint']['value']-DW_range_threshold # (1-DW_range_threshold)*DW_limits['min'] + DW_range_threshold*DW_limits['max']
# Wait for OSA queue
    sm.dev[osa_db]['queue'].queue_and_wait()
# Setup OSA
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['DW']
    sm.update_device_settings(osa_db, settings_list, write_log=False)
# Adjust 2nd Stage Power
    sm.dev[rot_db]['queue'].queue_and_wait()
    continue_adjusting_angle = True
    DWs = []
    angles = []
    while continue_adjusting_angle:
    # Ensure Queues
        sm.dev[osa_db]['queue'].queue_and_wait()
        sm.dev[rot_db]['queue'].queue_and_wait()
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
            sm.dev[osa_db]['queue'].touch()
            sm.dev[rot_db]['queue'].touch()
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
        current_angle = sm.dev[rot_db]['driver'].position()
        angles.append(current_angle)
    # Minimum angle condition
        lower_angle_condition = (current_angle < minimum_angle)
    # Check compliance
        DW_diff = current_DW - sm.local_settings[CONTROL_DB]['DW_setpoint']['value']
        upper_limit_condition = (current_DW > DW_high)
        lower_limit_condition = (current_DW < DW_low)
    # Adjust the setpoint
        if lower_limit_condition:
            if lower_angle_condition:
                warning_id = 'low_angle_fast'
                log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, but 2nd stage power is already at maximum'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'])
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)
                continue_adjusting_angle = False
            else:
                log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, raising the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                log.log_info(mod_name, func_name, log_str)
            # Raise the 2nd stage power
                settings_list = [{'position':current_angle-0.1}]
                sm.update_device_settings(rot_db, settings_list, write_log=False)
        elif upper_limit_condition:
            log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, lowering the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
            log.log_info(mod_name, func_name, log_str)
        # Lower the 2nd stage power
            settings_list = [{'position':current_angle+0.1}]
            sm.update_device_settings(rot_db, settings_list, write_log=False)
        else:
        # Good to go
            continue_adjusting_angle = False
# Remove from Queue
    sm.dev[osa_db]['queue'].remove()
    sm.dev[rot_db]['queue'].remove()
# Record Movement
    monitor_db = 'spectral_shaper/DW_vs_waveplate_angle'
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = np.array([angles, DWs])
        sm.db[monitor_db].write_record_and_buffer({'deg':angles, 'dBm':DWs})
# Update State Variable
    if not(upper_limit_condition or lower_limit_condition):
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = True
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
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
    mask_path = STATES[state_db][sm.current_state[state_db]['state']]['settings']['mask']
    #current_mask = mon['spectral_shaper/mask']['data']['path']
    current_mask = image_dir[0]
    if (current_mask != mask_path):
        # Update the state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = False
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
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
    with sm.lock['spectral_shaper/DW']:
        new_DW_condition = sm.mon['spectral_shaper/DW']['new']
        sm.mon['spectral_shaper/DW']['new'] = False
        if new_DW_condition:
            current_DW = sm.mon['spectral_shaper/DW']['data'][-1]
    # DW threshold
    DW_high = sm.local_settings[CONTROL_DB]['DW_setpoint']['value']+DW_range_threshold # (1-DW_range_threshold)*DW_limits['max'] + DW_range_threshold*DW_limits['min']
    DW_low = sm.local_settings[CONTROL_DB]['DW_setpoint']['value']-DW_range_threshold # (1-DW_range_threshold)*DW_limits['min'] + DW_range_threshold*DW_limits['max']
# Check if the output is outside the acceptable range ---------------
    if new_DW_condition:
        if (current_DW < sm.local_settings[CONTROL_DB]['DW_setpoint']['value']-DW_limits) or (current_DW > sm.local_settings[CONTROL_DB]['DW_setpoint']['value']+DW_limits):
        # Spectrum is not optimized
            compliant = False
            log_str = " Spectrum not optimized, DW amplitude outside the acceptable range"
            log.log_error(mod_name, func_name, log_str)
# If not optimized --------------------------------------------------
    if not(compliant):
    # Update state variable
        with sm.lock[state_db]:
            sm.current_state[state_db]['compliance'] = False
            sm.db[state_db].write_record_and_buffer(sm.current_state[state_db])
# If optimized ------------------------------------------------------
    else:
    # If the system is at a stable point, adjust the 2nd stage input power if necessary
        if (new_DW_condition):
            update = False
            DW_diff = current_DW - sm.local_settings[CONTROL_DB]['DW_setpoint']['value']
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
                with sm.lock['broadening_stage/device_rotation_mount']:
                    sm.mon['broadening_stage/device_rotation_mount']['new'] = False
                    current_angle = sm.mon['broadening_stage/device_rotation_mount']['data'][-1]
                    lower_angle_condition = (current_angle < minimum_angle)
                if lower_angle_condition and power_too_low:
                    warning_id = 'low_angle_slow'
                    log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, but 2nd stage power is already at maximum'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'])
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
                        log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, raising the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                        log.log_info(mod_name, func_name, log_str)
                    # Raise the 2nd stage power
                        settings_list = [{'position':current_angle-0.1}]
                        sm.update_device_settings(device_db, settings_list, write_log=False)
                    elif upper_limit_condition:
                        log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, lowering the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                        log.log_info(mod_name, func_name, log_str)
                    # Lower the 2nd stage power
                        settings_list = [{'position':current_angle+0.1}]
                        sm.update_device_settings(device_db, settings_list, write_log=False)
                    else:
                        step_size = 0.05 + (0.1-0.05) * abs(DW_diff)/DW_range_threshold
                        if power_too_low:
                            log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, raising the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
                            log.log_info(mod_name, func_name, log_str)
                        # Raise the 2nd stage power
                            settings_list = [{'position':current_angle-step_size}]
                            sm.update_device_settings(device_db, settings_list, write_log=False)
                        else:
                            log_str = ' DW is {:.3f}dB from setpoint {:.3f}dBm, lowering the 2nd stage power.\n Current angle {:.3f}deg.'.format(DW_diff, sm.local_settings[CONTROL_DB]['DW_setpoint']['value'], current_angle)
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
    sm.dev[osa_db]['queue'].queue_and_wait()
# Setup OSA
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['DW']
    sm.update_device_settings(osa_db, settings_list, write_log=False)
# Wait for IM Bias Queue
    sm.dev[IM_db]['queue'].queue_and_wait()
# Adjust IM Bias
    continue_adjusting_IM = True
    biases = []
    DWs = []
    while continue_adjusting_IM:
    # Get Voltage Setpoint
        current_bias = sm.dev[IM_db]['driver'].voltage_setpoint()
        v_setpoints = current_bias + IM_scan_offsets
    # Dither IM Bias
        for v_setpoint in v_setpoints:
        # Ensure Queues
            sm.dev[osa_db]['queue'].queue_and_wait()
            sm.dev[IM_db]['queue'].queue_and_wait()
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
                sm.dev[osa_db]['queue'].touch()
                sm.dev[IM_db]['queue'].touch()
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
    sm.dev[osa_db]['queue'].remove()
    sm.dev[IM_db]['queue'].remove()
# Record Data
    monitor_db = 'spectral_shaper/DW_vs_IM_bias'
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = np.array([biases, DWs])
        sm.db[monitor_db].write_record_and_buffer({'V':biases, 'dBm':DWs})


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
    sm.dev[osa_db]['queue'].queue_and_wait()
# Setup OSA
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['short']
    sm.update_device_settings(osa_db, settings_list, write_log=False)
# Wait for Rotation Stage Queue
    sm.dev[rot_db]['queue'].queue_and_wait()
# Adjust Rotation Stage
    continue_adjusting_angle = True
    angles = []
    DWs = []
    bulks = []
    current_angle = sm.mon['broadening_stage/device_rotation_mount']['data'][-1]
    while continue_adjusting_angle:
    # Get Angle Setpoints
        angle_setpoints = current_angle + angle_scan_offsets
    # Dither Angles
        for angle_setpoint in angle_setpoints:
        # Ensure Queues
            sm.dev[osa_db]['queue'].queue_and_wait()
            sm.dev[rot_db]['queue'].queue_and_wait()
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
                sm.dev[osa_db]['queue'].touch()
                sm.dev[rot_db]['queue'].touch()
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
                sm.local_settings[CONTROL_DB]['DW_setpoint']['value'] = new_DW_setpoint
                sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])
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
    sm.dev[osa_db]['queue'].remove()
    sm.dev[rot_db]['queue'].remove()
# Record Data
    monitor_db = 'spectral_shaper/DW_bulk_vs_waveplate_angle'
    with sm.lock[monitor_db]:
        sm.mon[monitor_db]['new'] = True
        sm.mon[monitor_db]['data'] = np.array([angles, bulks, DWs])
        sm.db[monitor_db].write_record_and_buffer({'deg':angles, 'bulk_dBm':bulks, 'DW_dBm':DWs})

# Optimize setpoints ----------------------------------------------------------
def optimize_setpoints(state_db):
    if (datetime.datetime.now().timestamp() > sm.local_settings[CONTROL_DB]['setpoint_optimization']['value']):
        optimize_IM_bias(state_db)
        optimize_DW_setpoint(state_db)
    # Schedule next optimization
        with sm.lock[CONTROL_DB]:
            sm.local_settings[CONTROL_DB]['setpoint_optimization']['value'] = tomorrow_at_noon()
            sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])

# %% States ===================================================================

'''Defined states are composed of collections of settings, prerequisites,
and routines
'''
STATES = {
        'spectral_shaper/state_SLM':{
                'flat':{
                        'settings':{'mask':"flat_18-04-26_06-50.bmp"},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':apply_mask,
                                'maintain':check_mask, 'operate':sm.nothing}
                        },
                'top':{
                        'settings':{'mask':"top_18-04-26_07-15.bmp"},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':apply_mask,
                                'maintain':check_mask, 'operate':sm.nothing}
                        },
                'safe':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}
                        },
                'engineering':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}
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
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}
                        },
                'engineering':{
                        'settings':{},
                        'prerequisites':{},
                        'routines':{
                                'monitor':sm.nothing, 'search':sm.nothing,
                                'maintain':sm.nothing, 'operate':sm.nothing}
                        }
                },
        }
sm.init_states(STATES)


# %% STATE MACHINE ============================================================

'''Operates the state machine.'''
sm.operate_machine(main_loop_interval=0.5)


