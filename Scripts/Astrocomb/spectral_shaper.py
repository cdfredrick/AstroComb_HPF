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
from Drivers.Thorlabs.APT import KPZ101
from Drivers.Finisar import WaveShaper

#Import the tkinter module
import tkinter
#Import the Pillow module
from PIL import Image, ImageTk

from modules.optimizer import Minimizer

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
    'spectral_shaper/device_piezo_z_in',
    'spectral_shaper/device_piezo_z_out',
    'spectral_shaper/device_waveshaper'
    ]
MONITOR_DBs = [
    'spectral_shaper/mask', 'spectral_shaper/spectrum',
    'spectral_shaper/DW', 'spectral_shaper/DW_vs_IM_bias',
    'spectral_shaper/DW_vs_waveplate_angle',
    'spectral_shaper/DW_bulk_vs_waveplate_angle',
    'spectral_shaper/2nd_stage_z_in_optimizer',
    'spectral_shaper/2nd_stage_z_out_optimizer',
    'spectral_shaper/optical_phase_optimizer'
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
    'broadening_stage/rot_stg_position',
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
        'queue':'COM10',
        '__init__':[
            ['COM10'],
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
    'spectral_shaper/device_piezo_z_in':{
        'driver':KPZ101,
        'queue':"COM18",
        '__init__':[["COM18"],
                    {'timeout':5,
                     'serial_number':29501649}]
        },
    'spectral_shaper/device_piezo_z_out':{
        'driver':KPZ101,
        'queue':'COM17', 
        '__init__':[['COM17'], 
                    {'timeout':5,
                     'serial_number':29501638}]
        },
    'spectral_shaper/device_waveshaper':{
        'driver':WaveShaper.WS1000A,
        'queue':'192.168.0.5',
        '__init__':[['192.168.0.5']]
        }
    }
CONTROL_PARAMS = {
    CONTROL_DB:{
        'setpoint_optimization':{'value':tomorrow_at_noon(),'type':'float'},
        'DW_setpoint':{'value':-45.5,'type':'float'},
        'run_optimizer':{'value':{}, 'type':'dict'},
        'abort_optimizer':{'value':False, 'type':'bool'}
        }
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
reset = {}
thread = {}
array = {}
warning = {}
warning_interval = 100 # seconds

IM_bias_limits = {'max':5.5, 'min':0.5}
rot_stg_limits = {"min":16, "max":45}
piezo_limits = {"min":0, "max":75}

#--- Monitor Functions --------------------------------------------------------

# Get Spectrum from OSA -------------------------------------------------------
array['spectrum'] = []
array['DW'] = []
spectrum_record_interval = 1000 # seconds
timer['spectrum:record'] = sm.get_lap(spectrum_record_interval)
reset['spectrum:record'] = False
def get_spectrum():
    # Get lap number
    new_record_lap = sm.get_lap(spectrum_record_interval)
    timer_id = 'spectrum:record'
    reset_id = 'spectrum:record'
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
        if not reset[reset_id]:
            array[array_id].append(data)
        if (new_record_lap > timer[timer_id]) or reset[reset_id]:
            if len(array[array_id]):
                np_array = np.array(array[array_id])
                np_array = np.power(10, np_array/10)*1e-3
                # Record statistics ---------------------
                sm.db[monitor_db].write_record({
                    'W':np_array.mean(),
                    'W_std':np_array.std(),
                    'dBm':10*np.log10(1e3*np_array.mean()),
                    'dBm_std':10/(np_array.mean() * np.log(10)) * np_array.std(),
                    'n':np_array.size})
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
        if not reset[reset_id]:
            array[array_id].append(osa_trace['data']['y'])
        if (new_record_lap > timer[timer_id]) or reset[reset_id]:
            if len(array[array_id]):
                np_array = np.array(array[array_id])
                np_array = np.power(10, np_array/10)*1e-3
                # Record statistics ---------------------
                y_mean = np_array.mean(axis=0)
                y_std = np_array.std(axis=0)
                y_n = np_array.shape[0]
                osa_trace['data']['W'] = y_mean.tolist()
                osa_trace['data']['W_std'] = y_std.tolist()
                osa_trace['data']['W_n'] = y_n
                osa_trace['data']['y'] = (10*np.log10(y_mean*1e3)).tolist()
                osa_trace['data']['y_std'] = (10/(y_mean*np.log(10))*y_std).tolist()
                osa_trace['data']['y_n'] = y_n
                sm.db[monitor_db].write_record(osa_trace)
                # Empty the array
                array[array_id] = []
            # Update reset flag
            reset[reset_id] = False
# Propogate lap numbers ---------------------------------------------
    if new_record_lap > timer[timer_id]:
        timer[timer_id] = new_record_lap

# Initialize threads
thread['get_spectrum'] = ThreadFactory(target=get_spectrum)
thread['get_new_single'] = ThreadFactory(target=sm.dev['spectral_shaper/device_OSA']['driver'].get_new_single)
thread['get_new_single_quick'] = ThreadFactory(target=sm.dev['spectral_shaper/device_OSA']['driver'].get_new_single, kwargs={'get_parameters':False})


#--- Optimization Functions ---------------------------------------------------

# Optimize DW Setpoint --------------------------------------------------------
def optimize_DW_setpoint(sig=3, max_iter=None):
    # Info
    mod_name = __name__
    func_name = optimize_DW_setpoint.__name__
    log_str = ' Beginning DW setpoint optimization'
    log.log_info(mod_name, func_name, log_str)
    start_time = time.time()

    #--- Databases --------------------------------------------------------
    mon_db = 'spectral_shaper/DW_bulk_vs_waveplate_angle'
    osa_db = 'spectral_shaper/device_OSA'
    rot_db = 'spectral_shaper/device_rotation_mount'

    #--- Queue and wait ---------------------------------------------------
    sm.dev[osa_db]['queue'].queue_and_wait()
    sm.dev[rot_db]['queue'].queue_and_wait()

    #--- Setup  Optimizer -------------------------------------------------
    angle_scan_range = 4 # 4 degree range, +-2 degree
    current_angle = sm.dev[rot_db]['driver'].position()
    start_scan = current_angle - angle_scan_range/2
    stop_scan = current_angle + angle_scan_range/2
    if start_scan < rot_stg_limits["min"]:
        start_scan = rot_stg_limits["min"]
        stop_scan = start_scan + angle_scan_range
    if stop_scan > rot_stg_limits["max"]:
        stop_scan = rot_stg_limits["max"]
        start_scan = stop_scan - angle_scan_range
    bounds = [(start_scan, stop_scan)]

    #--- Initialize optimizer ---------------------------------------------
    optimizer = Minimizer(
        bounds,
        n_initial_points=10, sig=sig,
        abs_bounds=[(rot_stg_limits["min"], rot_stg_limits["max"])])

    #--- Setup OSA --------------------------------------------------------
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['short']
    sm.update_device_settings(osa_db, settings_list, write_log=False)

    #--- Optimize DW Setpoint ---------------------------------------------
    converged = False
    search = True
    new_x = [current_angle]
    DWs = []
    while search:
        #--- Ensure queues
        sm.dev[osa_db]['queue'].touch()
        sm.dev[rot_db]['queue'].touch()

        #--- Measure new OSA trace
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

        #--- Update Model
        new_y = -current_bulk # maximize the bulk spectrum (dBm)
        opt_x, diag = optimizer.tell(new_x, new_y, diagnostics=True)
        # Save dispersive wave amplitude
        DWs.append(current_DW)

        #--- Calculate Optimal DW Amplitude
        dw_model = Minimizer.new_model(optimizer.x, DWs, optimizer.dims)
        opt_DW, opt_DW_std = dw_model.predict(opt_x, return_std=True)

        #--- Write Intermediate Result to Buffer
        with sm.lock[mon_db]:
            sm.mon[mon_db]['new'] = True
            sm.mon[mon_db]['data'] = {
                'deg':np.array(optimizer.x).flatten().tolist(),
                'bulk_dBm':(-np.array(optimizer.y)).tolist(),
                'DW_dBm':DWs,
                "bulk_model":{
                    "opt x":opt_x,
                    "x":optimizer.x, # deg
                    "y":optimizer.y, # -dBm
                    "diagnostics":diag,
                    "n obs":optimizer.n_obs,
                    "target sig":optimizer.sig,
                    "time":time.time() - start_time
                    },
                "DW_model":{
                    "opt x":opt_x,
                    "x":dw_model.x, # Volts
                    "y":dw_model.y, # dBm
                    "diagnostics":dw_model.fitness(test_x=opt_x),
                    "n obs":dw_model.n_obs,
                    "target sig":dw_model.sig,
                    "time":time.time() - start_time
                    }
                }
            sm.db[mon_db].write_buffer(sm.mon[mon_db]['data'])

        #--- Check abort flag
        with sm.lock[CONTROL_DB]:
            abort_optimization = sm.local_settings[CONTROL_DB]['abort_optimizer']['value']
            if abort_optimization:
                sm.local_settings[CONTROL_DB]['abort_optimizer']['value'] = False
                sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])

        #--- Check convergence or end search
        if optimizer.convergence_count >= 3:
            converged = True
            search = False
        elif max_iter:
            if optimizer.n_obs >= max_iter:
                converged = False
                search = False
                opt_x = [current_angle]
                log_str = ' Model did not converge to {:} sig after {:} samples. Returning to initial point.'.format(
                    optimizer.sig,
                    optimizer.n_obs)
                warning_id = 'DW optimization'
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)
        elif abort_optimization:
            log_str = ' Optimization aborted, returning to initial point.'
            log.log_info(mod_name, func_name, log_str)
            converged = False
            search = False
            opt_x = [current_angle]

        #--- Get new point
        if search:
            if not (optimizer.n_obs % 5):
                print(" {:} observations, {:.2f} significance, {:.3g}s".format(optimizer.n_obs, diag["significance"], time.time()-start_time))
            #--- Ask for new point
            new_x = optimizer.ask()
            #--- Move to new point
            sm.dev[rot_db]['driver'].position(new_x[0])
            #--- Settle time
            time.sleep(.1)
            moving = True
            while moving:
                #--- Ensure queues
                sm.dev[osa_db]['queue'].touch()
                sm.dev[rot_db]['queue'].touch()
                # Check if moving
                flags = sm.dev[rot_db]['driver'].status()['flags']
                if (not flags["moving forward"]) or (not flags["moving reverse"]):
                    moving = False

    # Optimum output
    new_angle = opt_x[0]
    stop_time = time.time()

    #--- Implement result -------------------------------------------------
    sm.dev[rot_db]['driver'].position(new_angle)

    #--- Remove from queue ------------------------------------------------
    sm.dev[osa_db]['queue'].remove()
    sm.dev[rot_db]['queue'].remove()

    #--- Log Result -------------------------------------------------------
    if converged:
        log_str = ' Bulk spectrum optimized at {:.2f} deg'.format(new_angle)
        log.log_info(mod_name, func_name, log_str)

    #--- Update DW Setpoint -----------------------------------------------
    if converged:
        with sm.lock[CONTROL_DB]:
            log_str = ' Optimal DW = {:.3g}+-{:.2g} dBm'.format(opt_DW, opt_DW_std)
            log.log_info(mod_name, func_name, log_str)
            log_str = ' >{:} sig after {:.3g}s and {:} observations'.format(
                optimizer.sig,
                stop_time - start_time,
                optimizer.n_obs)
            log.log_info(mod_name, func_name, log_str)
            sm.local_settings[CONTROL_DB]['DW_setpoint']['value'] = opt_DW
            sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])


    #--- Record result ----------------------------------------------------
    with sm.lock[mon_db]:
        sm.mon[mon_db]['new'] = True
        sm.mon[mon_db]['data'] = {
            'deg':np.array(optimizer.x).flatten().tolist(),
            'bulk_dBm':(-np.array(optimizer.y)).tolist(),
            'DW_dBm':DWs,
            "bulk_model":{
                "opt x":opt_x,
                "x":optimizer.x, # deg
                "y":optimizer.y, # -dBm
                "diagnostics":diag,
                "n obs":optimizer.n_obs,
                "target sig":optimizer.sig,
                "time":stop_time - start_time,
                "converged":converged,
                },
            "DW_model":{
                "opt x":opt_x,
                "x":dw_model.x, # Volts
                "y":dw_model.y, # dBm
                "diagnostics":dw_model.fitness(test_x=opt_x),
                "n obs":dw_model.n_obs,
                "target sig":dw_model.sig,
                "time":stop_time - start_time,
                "converged":converged,
                }
            }
        sm.db[mon_db].write_record_and_buffer(sm.mon[mon_db]['data'])
    return new_angle, opt_DW, opt_DW_std


# Optimize 2nd Stage Z Coupling -----------------------------------------------
def optimize_z_coupling(sig=3, max_iter=None, stage="in"):
    # Info
    mod_name = __name__
    func_name = optimize_z_coupling.__name__
    log_str = ' Beginning z pizeo optimization'
    log.log_info(mod_name, func_name, log_str)
    start_time = time.time()

    #--- Databases --------------------------------------------------------
    osa_db = 'spectral_shaper/device_OSA'
    if stage=="in":
        pz_db = 'spectral_shaper/device_piezo_z_in'
        mon_db = 'spectral_shaper/2nd_stage_z_in_optimizer'
    elif stage=="out":
        pz_db = 'spectral_shaper/device_piezo_z_out'
        mon_db = 'spectral_shaper/2nd_stage_z_out_optimizer'

    #--- Queue and wait ---------------------------------------------------
    sm.dev[osa_db]['queue'].queue_and_wait()
    sm.dev[pz_db]['queue'].queue_and_wait()

    #--- Setup optimizer --------------------------------------------------
    current_position = sm.dev[pz_db]['driver'].voltage()
    scan_range = 5 # 5V, +- 2.5 V
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
        n_initial_points=10, sig=sig,
        abs_bounds=[(piezo_limits["min"], piezo_limits["max"])])

    #--- Setup OSA --------------------------------------------------------
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['DW']
    sm.update_device_settings(osa_db, settings_list, write_log=False)

    #--- Optimize ---------------------------------------------------------
    converged = False
    search = True
    new_x = [current_position]
    while search:
        #--- Ensure queues
        sm.dev[osa_db]['queue'].touch()
        sm.dev[pz_db]['queue'].touch()

        #--- Measure new OSA trace
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
            sm.dev[pz_db]['queue'].touch()
        # Get Result
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        else:
            osa_trace = thread[thread_name].result
        # Get DW
        current_DW = np.max(osa_trace['data']['y'])

        #--- Update Model
        new_y = -current_DW # maximize the DW (dBm)
        opt_x, diag = optimizer.tell(new_x, new_y, diagnostics=True)

        #--- Write Intermediate Result to Buffer
        with sm.lock[mon_db]:
            sm.mon[mon_db]['new'] = True
            sm.mon[mon_db]['data'] = {
                "V":np.array(optimizer.x).flatten().tolist(), # Volts
                "dBm":(-np.array(optimizer.y)).tolist(), # dBm
                "model":{
                    "opt x":opt_x,
                    "x":optimizer.x, # Volts
                    "y":optimizer.y, # -dBm
                    "diagnostics":diag,
                    "n obs":optimizer.n_obs,
                    "target sig":optimizer.sig,
                    "time":time.time() - start_time
                    }
                }
            sm.db[mon_db].write_buffer(sm.mon[mon_db]['data'])

        #--- Check abort flag
        with sm.lock[CONTROL_DB]:
            abort_optimization = sm.local_settings[CONTROL_DB]['abort_optimizer']['value']
            if abort_optimization:
                sm.local_settings[CONTROL_DB]['abort_optimizer']['value'] = False
                sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])

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
        elif abort_optimization:
            log_str = ' Optimization aborted, returning to initial point.'
            log.log_info(mod_name, func_name, log_str)
            converged = False
            search = False
            opt_x = [current_position]

        #--- Get new point
        if search:
            if not (optimizer.n_obs % 5):
                print(" {:} observations, {:.2f} significance, {:.3g}s".format(optimizer.n_obs, diag["significance"], time.time()-start_time))
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
    sm.dev[osa_db]['queue'].remove()
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
            "dBm":(-np.array(optimizer.y)).tolist(), # dBm
            "model":{
                "opt x":opt_x,
                "x":optimizer.x, # Volts
                "y":optimizer.y, # -dBm
                "diagnostics":diag,
                "n obs":optimizer.n_obs,
                "target sig":optimizer.sig,
                "time":stop_time - start_time,
                "converged":converged
                }
            }
        sm.db[mon_db].write_record_and_buffer(sm.mon[mon_db]['data'])
    return new_position


# Optimize IM Bias ------------------------------------------------------------
def optimize_IM_bias(sig=3, max_iter=None):
    # Info
    mod_name = __name__
    func_name = optimize_IM_bias.__name__
    log_str = ' Beginning IM bias optimization'
    log.log_info(mod_name, func_name, log_str)
    start_time = time.time()

    #--- Databases --------------------------------------------------------
    mon_db = 'spectral_shaper/DW_vs_IM_bias'
    osa_db = 'spectral_shaper/device_OSA'
    IM_db = 'spectral_shaper/device_IM_bias'

    #--- Queue and wait ---------------------------------------------------
    sm.dev[osa_db]['queue'].queue_and_wait()
    sm.dev[IM_db]['queue'].queue_and_wait()

    #--- Setup  Optimizer -------------------------------------------------
    IM_scan_range = 0.100 # 100mV range, +-50mV
    current_bias = sm.dev[IM_db]['driver'].voltage_setpoint()
    start_scan = current_bias - IM_scan_range/2
    stop_scan = current_bias + IM_scan_range/2
    if start_scan < IM_bias_limits["min"]:
        start_scan = IM_bias_limits["min"]
        stop_scan = start_scan + IM_scan_range
    if stop_scan > IM_bias_limits["max"]:
        stop_scan = IM_bias_limits["max"]
        start_scan = stop_scan - IM_scan_range
    bounds = [(start_scan, stop_scan)]

    #--- Initialize optimizer ---------------------------------------------
    optimizer = Minimizer(
        bounds,
        n_initial_points=10, sig=sig,
        abs_bounds=[(IM_bias_limits["min"], IM_bias_limits["max"])])

    #--- Setup OSA --------------------------------------------------------
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['DW']
    sm.update_device_settings(osa_db, settings_list, write_log=False)

    #--- Optimize IM Bias -------------------------------------------------
    converged = False
    search = True
    new_x = [current_bias]
    while search:
        #--- Ensure queues
        sm.dev[osa_db]['queue'].touch()
        sm.dev[IM_db]['queue'].touch()

        #--- Measure new OSA trace
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

        #--- Update Model
        new_y = -current_DW # maximize the DW (dBm)
        opt_x, diag = optimizer.tell(new_x, new_y, diagnostics=True)

        #--- Write Intermediate Result to Buffer
        with sm.lock[mon_db]:
            sm.mon[mon_db]['new'] = True
            sm.mon[mon_db]['data'] = {
                'V':np.array(optimizer.x).flatten().tolist(),
                'dBm':(-np.array(optimizer.y)).tolist(),
                "model":{
                    "opt x":opt_x,
                    "x":optimizer.x, # Volts
                    "y":optimizer.y, # -dBm
                    "diagnostics":diag,
                    "n obs":optimizer.n_obs,
                    "target sig":optimizer.sig,
                    "time":time.time() - start_time
                    }
                }
            sm.db[mon_db].write_buffer(sm.mon[mon_db]['data'])

        #--- Check abort flag
        with sm.lock[CONTROL_DB]:
            abort_optimization = sm.local_settings[CONTROL_DB]['abort_optimizer']['value']
            if abort_optimization:
                sm.local_settings[CONTROL_DB]['abort_optimizer']['value'] = False
                sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])

        #--- Check convergence
        if optimizer.convergence_count >= 3:
            #--- End the search
            converged = True
            search = False
        elif max_iter:
            if optimizer.n_obs >= max_iter:
                converged = False
                search = False
                opt_x = [current_bias]
                log_str = ' Model did not converge to {:} sig after {:} samples, returning to initial point.'.format(
                    optimizer.sig,
                    optimizer.n_obs)
                warning_id = 'bias optimization'
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)
        elif abort_optimization:
            log_str = ' Optimization aborted, returning to initial point.'
            log.log_info(mod_name, func_name, log_str)
            converged = False
            search = False
            opt_x = [current_bias]

        #--- Get new point
        if search:
            if not (optimizer.n_obs % 5):
                print(" {:} observations, {:.2f} significance, {:.3g}s".format(optimizer.n_obs, diag["significance"], time.time()-start_time))
            #--- Ask for new point
            new_x = optimizer.ask()
            #--- Move to new point
            sm.dev[IM_db]['driver'].voltage_setpoint(new_x[0])
    # Optimum output
    new_bias = opt_x[0]
    stop_time = time.time()

    #--- Implement result -------------------------------------------------
    sm.dev[IM_db]['driver'].voltage_setpoint(new_bias)

    #--- Remove from queue ------------------------------------------------
    sm.dev[osa_db]['queue'].remove()
    sm.dev[IM_db]['queue'].remove()

    #--- Log Result -------------------------------------------------------
    if converged:
        log_str = ' IM bias optimized at {:.3f}V'.format(new_bias)
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
            'V':np.array(optimizer.x).flatten().tolist(),
            'dBm':(-np.array(optimizer.y)).tolist(),
            "model":{
                "opt x":opt_x,
                "x":optimizer.x, # Volts
                "y":optimizer.y, # -dBm
                "diagnostics":diag,
                "n obs":optimizer.n_obs,
                "target sig":optimizer.sig,
                "time":stop_time - start_time,
                "converged":converged
                }
            }
        sm.db[mon_db].write_record_and_buffer(sm.mon[mon_db]['data'])
    return new_bias


# Optimize Finisar Waveshaper Phase -------------------------------------------
def optimize_optical_phase(sig=3, max_iter=None):
    # Info
    mod_name = __name__
    func_name = optimize_optical_phase.__name__
    log_str = ' Beginning optical phase optimization'
    log.log_info(mod_name, func_name, log_str)
    start_time = time.time()

    #--- Databases --------------------------------------------------------
    mon_db = 'spectral_shaper/optical_phase_optimizer'
    osa_db = 'spectral_shaper/device_OSA'
    ws_db = 'spectral_shaper/device_waveshaper'

    #--- Queue and wait ---------------------------------------------------
    sm.dev[osa_db]['queue'].queue_and_wait()
    sm.dev[ws_db]['queue'].queue_and_wait()

    #--- Setup  Optimizer -------------------------------------------------
    opt_orders = 7
    current_phase = sm.dev[ws_db]['driver'].phase_profile()
    freqs = sm.dev[ws_db]['driver'].freq
    frq_smp = (freqs > WaveShaper.SPEED_OF_LIGHT_NM_THZ/1070) & (freqs < WaveShaper.SPEED_OF_LIGHT_NM_THZ/1058)
    current_polyfit = np.polynomial.Legendre.fit(freqs[frq_smp], current_phase[frq_smp], 1+opt_orders)
    current_coefs = current_polyfit.coef[2:].tolist()
    coefs_scan_range = 0.05 * (2*np.pi)
    bounds = []
    for idx, coef in enumerate(current_coefs):
        bounds.append((coef - coefs_scan_range/(2+idx/2), coef + coefs_scan_range/(2+idx/2)))
    abs_bounds = []
    for bound in bounds:
        c_scan_range = bound[1] - bound[0]
        # Limit total scan range for faster model convergence
        abs_bounds.append((bound[0]-c_scan_range, bound[1]+c_scan_range))

    #--- Initialize optimizer ---------------------------------------------
    optimizer = Minimizer(
        bounds, abs_bounds=abs_bounds,
        n_initial_points=10, sig=sig)

    #--- Setup OSA --------------------------------------------------------
    settings_list = STATES['spectral_shaper/state_optimizer']['optimal']['settings']['DW']
    sm.update_device_settings(osa_db, settings_list, write_log=False)

    #--- Optimize Phase Profile -------------------------------------------
    converged = False
    search = True
    new_x = current_coefs
    while search:
        #--- Ensure queues
        sm.dev[osa_db]['queue'].touch()
        sm.dev[ws_db]['queue'].touch()

        #--- Measure new OSA trace
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
            sm.dev[ws_db]['queue'].touch()
        # Get Result
        (alive, error) = thread[thread_name].check_thread()
        if error != None:
            raise error[1].with_traceback(error[2])
        else:
            osa_trace = thread[thread_name].result
        # Get DW
        current_DW = np.max(osa_trace['data']['y'])

        #--- Update Model
        new_y = -current_DW # maximize the DW (dBm)
        opt_x, diag = optimizer.tell(new_x, new_y, diagnostics=True)

        #--- Write Intermediate Result to Buffer
        with sm.lock[mon_db]:
            sm.mon[mon_db]['new'] = True
            sm.mon[mon_db]['data'] = {
                'coefs':optimizer.x,
                'domain':current_polyfit.domain.tolist(),
                'dBm':(-np.array(optimizer.y)).tolist(),
                "model":{
                    "opt x":opt_x,
                    "x":optimizer.x, # 2nd order and above coefs
                    "y":optimizer.y, # -dBm
                    "diagnostics":diag,
                    "n obs":optimizer.n_obs,
                    "target sig":optimizer.sig,
                    "time":time.time() - start_time
                    }
                }
            sm.db[mon_db].write_buffer(sm.mon[mon_db]['data'])

        #--- Check abort flag
        with sm.lock[CONTROL_DB]:
            abort_optimization = sm.local_settings[CONTROL_DB]['abort_optimizer']['value']
            if abort_optimization:
                sm.local_settings[CONTROL_DB]['abort_optimizer']['value'] = False
                sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])

        #--- Check convergence
        if optimizer.convergence_count >= 3:
            #--- End the search
            converged = True
            search = False
        elif max_iter:
            if optimizer.n_obs >= max_iter:
                converged = False
                search = False
                opt_x = current_coefs
                log_str = ' Model did not converge to {:} sig after {:} samples, returning to initial point'.format(
                    optimizer.sig,
                    optimizer.n_obs)
                warning_id = 'optical phase optimization'
                if (warning_id in warning):
                    if (time.time() - warning[warning_id]) > warning_interval:
                        log.log_warning(mod_name, func_name, log_str)
                else:
                    warning[warning_id] = time.time()
                    log.log_warning(mod_name, func_name, log_str)
        elif abort_optimization:
            log_str = ' Optimization aborted, returning to initial point.'
            log.log_info(mod_name, func_name, log_str)
            converged = False
            search = False
            opt_x = current_coefs

        #--- Get new point
        if search:
            if not (optimizer.n_obs % 5):
                print(" {:} observations, {:.2f} significance, {:.3g}s".format(optimizer.n_obs, diag["significance"], time.time()-start_time))
            #--- Ask for new coefs
            new_x = optimizer.ask()
            #--- Calculate phase profile
            new_poly_fit = np.polynomial.Legendre([0,0]+new_x, domain=current_polyfit.domain)
            #--- Send new phase profile
            sm.dev[ws_db]['driver'].phase_profile(new_poly_fit(freqs)) # send phase for the entire waveshaper range
    # Optimum output
    new_coefs = opt_x
    stop_time = time.time()

    #--- Implement result -------------------------------------------------
    # Calculate phase profile
    new_poly_fit = np.polynomial.Legendre([0,0]+new_coefs, domain=current_polyfit.domain)
    # Send new phase profile
    sm.dev[ws_db]['driver'].phase_profile(new_poly_fit(freqs)) # send phase for the entire waveshaper range
    new_phase = sm.dev[ws_db]['driver'].phase_profile()

    #--- Remove from queue ------------------------------------------------
    sm.dev[osa_db]['queue'].remove()
    sm.dev[ws_db]['queue'].remove()

    #--- Log Result -------------------------------------------------------
    if converged:
        log_str = ' Optical phase optimized with {:}'.format(new_poly_fit)
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
            'filter profile':{
                'freq':sm.dev[ws_db]['driver'].freq.tolist(),
                'attn':sm.dev[ws_db]['driver'].attn.tolist(),
                'phase':sm.dev[ws_db]['driver'].phase.tolist(),
                'port':sm.dev[ws_db]['driver'].port.tolist(),
                },
            'coefs':optimizer.x,
            'domain':current_polyfit.domain.tolist(),
            'dBm':(-np.array(optimizer.y)).tolist(),
            "model":{
                "opt x":opt_x,
                "x":optimizer.x, # 2nd order and above coefs
                "y":optimizer.y, # -dBm
                "diagnostics":diag,
                "n obs":optimizer.n_obs,
                "target sig":optimizer.sig,
                "time":stop_time - start_time,
                "converged":converged
                }
            }
        sm.db[mon_db].write_record_and_buffer(sm.mon[mon_db]['data'])
    return new_phase


# %% Monitor Routines =========================================================
'''This section is for defining the methods needed to monitor the system.'''

## Initialize monitor
#monitor_db = 'broadening_stage/rot_stg_position'
# # Update buffers -----------------------
#with sm.lock[monitor_db]:
#    sm.mon[monitor_db]['new'] = True
#    sm.mon[monitor_db]['data'] = update_buffer(
#        sm.mon[monitor_db]['data'],
#        sm.db[monitor_db].read_buffer()['deg'], 500)

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
        monitor_db = 'broadening_stage/rot_stg_position'
        for doc in sm.mon[monitor_db]['cursor']:
            new_data.append(doc['deg'])
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


# %% Search Routines ==========================================================
'''This section is for defining the methods needed to bring the system into
    its defined states.'''

# Apply Mask ------------------------------------------------------------------
def apply_mask(state_db):
    mod_name = apply_mask.__module__
    func_name = apply_mask.__name__
    # Reset spectrum record
    reset['spectrum:record'] = True
    # Apply mask
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
minimum_angle = rot_stg_limits["min"] # degrees
maximum_angle = rot_stg_limits["max"] # degrees
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
        # Update Monitor
        monitor_db = 'broadening_stage/rot_stg_position'
        with sm.lock[monitor_db]:
            sm.mon[monitor_db]['data'].append(current_angle)


# %% Maintain Routines ========================================================
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
                mon_db = 'broadening_stage/rot_stg_position'
                with sm.lock[mon_db]:
                    sm.mon[mon_db]['new'] = False
                    current_angle = sm.mon[mon_db]['data'][-1]
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


# %% Operate Routines =========================================================
'''This section is for defining the methods called only when the system is in
    its defined states.'''
optimizer_functions = [
    "optimize_DW_setpoint",
    "optimize_z_in_coupling",
    "optimize_z_out_coupling",
    "optimize_IM_bias",
    "optimize_optical_phase",
    ]
# Optimize setpoints ----------------------------------------------------------
def optimize_setpoints(state_db):
    if (datetime.datetime.now().timestamp() > sm.local_settings[CONTROL_DB]['setpoint_optimization']['value']):
        optimize_z_coupling(sig=3, stage="in")
        optimize_z_coupling(sig=3, stage="out")
        optimize_IM_bias(sig=3)
        optimize_optical_phase(sig=3)
        optimize_DW_setpoint(sig=3)
        # Schedule next optimization
        with sm.lock[CONTROL_DB]:
            sm.local_settings[CONTROL_DB]['setpoint_optimization']['value'] = tomorrow_at_noon()
            sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])
    # Check if optimizer requested
    with sm.lock[CONTROL_DB]:
        run_optimizer = {}
        if sm.local_settings[CONTROL_DB]['run_optimizer']['value']:
            run_optimizer = sm.local_settings[CONTROL_DB]['run_optimizer']['value']
            # Reset "run_optimizer"
            sm.local_settings[CONTROL_DB]['run_optimizer']['value'] = {}
            sm.db[CONTROL_DB].write_record_and_buffer(sm.local_settings[CONTROL_DB])
    if 'target' in run_optimizer:
        if 'sig' in run_optimizer:
            sig = run_optimizer['sig']
        else:
            sig = 3
        target = run_optimizer['target']
        if target in optimizer_functions:
            if target == "optimize_DW_setpoint":
                optimize_DW_setpoint(sig=sig)
            elif target == "optimize_z_in_coupling":
                optimize_z_coupling(sig=sig, stage="in")
            elif target == "optimize_z_out_coupling":
                optimize_z_coupling(sig=sig, stage="out")
            elif target == "optimize_IM_bias":
                optimize_IM_bias(sig=sig)
            elif target == "optimize_optical_phase":
                optimize_optical_phase(sig=sig)


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


