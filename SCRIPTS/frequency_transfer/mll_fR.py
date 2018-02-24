# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:51:36 2017

@author: Connor
"""

# %% Import Packages and Drivers ==============================================
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import time

from Drivers.Database import MongoDB
from Drivers.Logging import EventLog as log
from Drivers.VISA.SRS import SIM960
from Drivers.VISA.ILXLightwave import TECModule
from Drivers.Daq.DaqObjects import DAQAnalogIn
from Drivers.VISA.Thorlabs import MDT639B

# %% Helper Functions =========================================================
def from_keys(nested_dict, key_list):
    if isinstance(key_list, list):
        for key in key_list:
            nested_dict = nested_dict[key]
    else:
        nested_dict = nested_dict[key_list]
    return nested_dict
    

# %% Databases and Settings ===================================================

# Local Database Names --------------------------------------------------------
'''The following are lists of all of the databases originating within this 
    control script. Each of these databases are initialized within this script.
    The databases should be grouped by function.
        state:
            -The entries in state databases should reflect the current state of
                the system and the level of compliance. Other scripts should 
                look to these databases in order to resolve prerequisites.
        device:
            -The entries in visa databases should include the settings for
                each unique device or device/channel combination.
        daq:
            -The entries in the daq databases should include the settings
                needed to generate a task handler. DAQ databases are not for
                storing data retrieved from the device, use monitor databases
                for that purpose. If there are multiple use cases for a single
                channel (same channel, different task handlers), each case
                should have a db.
        monitor:
            -The entries in monitor databases should contain secondary 
                variables used to determine compliance with the state of the
                system, and to determine any actions required to maintain
                compliance.
        log:
            -This should be a single database that serves as the intermediary 
                between this script and others. The entries in the log database
                should be parsed as commands in this script.'''
STATE_DBs = [
    'mll_fR/state']
DEVICE_DBs =[
    'mll_fR/TEC_settings', 'mll_fR/PID_settings', 'mll_fR/HV_settings']
DAQ_DBs = [
    'mll_fR/DAQ_error_frequency', 'mll_fR/DAQ_rms_error']
MONITOR_DBs = [
    'mll_fR/TEC_temperature', 'mll_fR/TEC_current', 'mll_fR/PID_voltage', 
    'mll_fR/HV_output', 'mll_fR/rms_error']
LOG_DB = 'mll_fR/log'
MASTER_DBs = STATE_DBs + DEVICE_DBs + DAQ_DBs + MONITOR_DBs + [LOG_DB]

# External Database Names -----------------------------------------------------
'''This is a list of all databases external to this control script that are 
    needed to check prerequisites'''
READ_DBs = []

# Default Settings ------------------------------------------------------------
'''A template for all settings used in this script. Upon initialization 
    these settings are checked against those saved in the database, and 
    populated if found empty. Each state and device database should be
    represented. Default values are only added to a database if they are found 
    to be undefined within the database.
states:
    -Entries in the state databases are specified as follows:
        <database path>:{'state':<name of the current state>,
         'compliance':<compliance with the current state>
         'desired_state':<name of the desired state>,
         'initialized':<initialization state of the control script>
         }
    -The state name should correspond to one of the defined states.
    -The compliance level should be a simple boolean value that indicates
        whether the system is compliant with the current state.
    -The "desired_state" is mostly for internal use, particularly for cases
        where the state is temporarliy changed. The script should seek to bring
        the current state to the desired state. The script should not change 
        the current state if the desired state is undefined.
    -The "initialized" parameter is a boolean value that indicates that the
        current state is accurate. It should be set to False by the master
        program before the control scripts are loaded, and should only be set
        to True after the control script has determined the current state. In
        order to smoothly connect to the system if the instruments are already
        running, initialization prerequisites should be no higher than 
        "necessary".
devices and daq:
    -Entries in the device and daq databases are specified as follows:
        <database path>:{<method name>:<value>,...},...
    -The entries should include the settings for each unique device or
        device/channel combination. The setting names and parameters should be
        derived from the methods of the drivers for automation purposes.
    -Place multiple arguments in a list, keyword arguments in
        dictionaries, and combinations of the two in tuples, 
        ([args], {kwargs}). Single arguments may be left as is, but single
        arguments that are lists must nested, [[list argument]]. The automation
        checks whether the instance is list, dictionary, or tuple before 
        sending the commands.
'''
STATE_SETTINGS = {
    'mll_fR/state':{
            'state':'free',
            'compliance':False,
            'desired_state':'lock'}}
DEVICE_SETTINGS = {
    'mll_fR/TEC_settings':{
        'tec_off_triggers':[5, 6, 7, 8, 10], 'tec_gain':100, 
        'tec_current_limit':0.400, 'tec_temperature_limit':40.0, 'tec_mode':'R',
        'tec_output':True, 'tec_resistance_setpoint':7.580},
    'mll_fR/PID_settings':{
        'proportional_action':True, 'integral_action':True,
        'derivative_action':False, 'offset_action':False, 
        'proportional_gain':-3.0e0, 'integral_gain':5.0e2, 'pid_action':False,
        'setpoint_action':False, 'internal_setpoint':0.000, 'ramp_action':False,
        'manual_output':0.000, 'upper_output_limit':8.00,
        'lower_output_limit':0.00, 'power_line_frequency':60, 'display':True},
    'mll_fR/HV_settings':{
        'x_min':0.00, 'x_max':60.00, 'x_voltage':0.00}}
DAQ_SETTINGS = {
    'mll_fR/DAQ_error_frequency':{
        'task_handler':{
            'samples':1e3, 'rate':50e3, 'max_v':10., 'min_v':-10.}},
    'mll_fR/DAQ_rms_error':{
        'task_handler':{
            'samples':1e3, 'rate':50e3, 'max_v':10., 'min_v':-10.}}}
    
SETTINGS = dict(list(STATE_SETTINGS.items()) + list(DEVICE_SETTINGS.items()) + list(DAQ_SETTINGS.items()))

# %% Initialize Databases, Devices, and Settings ==============================

# Connect to MongoDB ----------------------------------------------------------
mongo_client = mongoDB.MongoClient()
db = {}
for database in MASTER_DBs:
    db[database] = mongoDB.DatabaseMaster(mongo_client, database)
for database in READ_DBs:
    db[database] = mongoDB.DatabaseRead(mongo_client, database)

# Start Logging ---------------------------------------------------------------
log.start_logging(database=db[LOG_DB])

# Check that all settings (as listed in the defaults) exist in the databases
    # If misssing, populate with the default values

# Initialize Devices ----------------------------------------------------------
'''Each device database should be associated with a device object.'''
dev = {}
dev['mll_fR/TEC_settings'] = TECModule(visa_address, tec_channel)
dev['mll_fR/PID_settings'] = SIM960(visa_address, port)
dev['mll_fR/HV_settings'] = MDT639B(visa_address)

# Initialize DAQ Channels -----------------------------------------------------
daq = {}
daq['mll_fR/DAQ_error_frequency'] = DAQAnalogIn(device_address, chan_num)
daq['mll_fR/DAQ_error_frequency'] = DAQAnalogIn(device_address, chan_num)

# Initialize Local Copy of Device Settings ------------------------------------
# TODO: Get directly from instrument?
local_settings = {}
for database in SETTINGS:
    local_settings[database] = db[database].read_buffer()['entry']

# %% Routines ==================================================================
def nothing():
    pass

# State Routines --------------------------------------------------------------
'''This section is for defining the methods needed to maintain the system in
    its defined states.'''
def monitor_lock():
    pass

def find_lock():
    pass

def keep_lock():
    pass

def locked_disabled():
    pass

# Monitor Functions
'''This section is for defining the methods needed to monitor the system.'''
def rms_error():
    pass

# %% States and Monitors ======================================================
'''Defined states are composed of collections of settings, prerequisites,
    and a routines.
setttings:
    -Only the settings particular to a state need to be listed, and they should
        be in the same format as those in the defaults.
    -The settings listed here should be thought of as stationary prerequisites 
        or as known initialization states that the system should pass through
        to ease the transition to the compliant state. Dynamic settings should
        be dealt with in the state's methods.
    -These settings will be applied when the system is out of compliance.
prerequisites:
    -Prerequisites should be entered as lists of dictionaries that include the 
        database and key:value pair that corresponds to a passing prerequisite
        for the given state:
        [{'db':<database path>, 'key':<entry's key (optional)>, 'value':<desired value>},...]
    -The key is optional, and is only used if specified.
    -Prereqs should be separated by severity.
        critical:
            -A failed critical prereq could jeopardize the health of the
                system if brought into or left in the applied state.
            -Critical prerequisites are continuously monitored.
            -The system is placed into a temporary "safe" state upon failure of
                a critical prereq.
        necessary:
            -Failure of a necessary prereq will cause the system to come out of
                or be unable to reach compliance.
            -Necessary prereqs are checked if the system is out of compliance.
            -The system is prevented from moving to the applied state upon 
                failure of a necessary prereq, and no attempts are made to 
                bring the system into compliance if already in the state.
        optional:
            -Failure of an optional prereq should not cause failure elsewhere, 
                but system performance or specifications can't be guaranteed. 
                It is more "non compulsory" than "optional".
            -Optional prereqs are checked if the system is out of compliance.
            -The system is allowed to move into the applied state upon 
                failure of an optional prereq.
routines:
    -The routines are the functions needed to determine if the state is in 
        compliance, bring the state into compliance, and maintain the current
        state in compliance. Only one function call should be listed for each
        method. The methods themselves may call others.
    -Routines should be entered for the three cases: testing the state, 
        searching for the state, and maintaining the state.
        {'test':<method1>, 'search':<method2>, 'maintain':<method3>}
    -The test methods should return a boolean value indicating the compliance of
        the state. Searching and maintaining methods should not return anything.'''
STATES = {
    'mll_fR/state':{
        'lock':{
            'settings':{
                'mll_fR/TEC_settings':{
                    'tec_mode':'R', 'tec_output':True},
                'mll_fR/PID_settings':{
                    'proportional_action':True, 'integral_action':True,
                    'derivative_action':False, 'offset_action':False,
                    'proportional_gain':-3.0e0, 'integral_gain':5.0e2,},
                'mll_fR/HV_settings':{
                    'x_min':0.00, 'x_max':60.00, 'x_voltage':0.00},
                'mll_fR/DAQ_settings':{
                    'task_handler':{
                        'samples':1e3, 'rate':50e3, 'max_v':2., 'min_v':-2.}}},
            'prerequisites':{
                'critical':[
                    {'db':'', 'key':'entry', 'value':''}],
                'necessary':[],
                'optional':[]},
            'routines':{'test':monitor_lock, 'search':find_lock, 'maintain':keep_lock}},
        'free':{
            'settings':{
                'mll_fR/TEC_settings':{},
                'mll_fR/PID_settings':{},
                'mll_fR/HV_settings':{}},
            'prerequisites':{
                'critical':[],
                'necessary':[],
                'optional':[]},
            'routines':{'test':locked_disabled, 'search':transfer_to_manual, 'maintain':nothing}},
        'safe':{
            'settings':{
                'mll_fR_TEC_settings':{},
                'mll_fR_PID_settings':{'pid_action':False},
                'mll_fR_HV_settings':{}},
            'prerequisites':{
                'critical':[],
                'necessary':[],
                'optional':[]},
            'routines':{}}}}

# Initialize monitors ---------------------------------------------------------
'''
monitors:
    -Monitors should associate the monitor databases with the methods that 
        returns the monitored values, the units, and contain local copies of
        the monitored data for use by state routines:
        {<database path>:{'method':<monitoring function>,'units':<units>, 
                          'data':<placeholder for local data copy>}, ...}'''
mon = {
    'mll_fR/TEC_temperature':{
        'method':gettatr(), 'units':'kOhms', 'data':np.array([])},
    'mll_fR/TEC_current':{
        'method':gettatr(), 'units':'A', 'data':np.array([])},
    'mll_fR/PID_voltage':{
        'method':gettatr(), 'units':'V', 'data':np.array([])},
    'mll_fR/HV_output':{
        'method':gettatr(), 'units':'V', 'data':np.array([])},
    'mll_fR/rmsError':{
        'method':gettatr(), 'units':'V', 'data':np.array([])}}


# %% Main Loop ================================================================
loop = True
while loop:
# Get the current state
    current_state = {}
    for state_db in STATE_DBs:
        current_state[state_db] = db[state_db].read_buffer()['entry']
# Check the critical prerequisites of the current states
    for state_db in STATE_DBs:
        prereqs_pass = True
        for prereq in STATES[state_db][current_state[state_db]['state']]['prerequisites']['critical']:
            critical_prereq = from_keys(db[prereq['db']].read_buffer(),prereq['key'])
            prereqs_pass *= (critical_prereq == prereq['value'])
    # Place into safe state if critical prereqs fail
        if not prereqs_pass:
        # Update the device settings
            for device in STATES[state_db]['safe']['settings']:
                for setting in STATES[state_db]['safe']['settings'][device]:
                # Send command to the device
                    getattr(dev[device], setting)(STATES[state_db]['safe']['settings'][device][setting])
                # Update the device settings' local copy
                    local_settings[device][setting] = STATES[state_db]['safe']['settings'][device][setting]
            # Update the database
                db[device].write_buffer(local_settings[device])
        # Update the state variable
            current_state[state_db]['state'] = 'safe'
            current_state[state_db]['compliance'] = False
            db[state_db].write_buffer(current_state[state_db]) # The desired state should be left unaltered
# Maintain the current state
    # If compliant
        # Check the monitored parameters against requirements of the state
        # Determine compliance
    # If out of compliance, 
        # update the current settings or reinitialize the state if required
        # check necessary and optional prerequisites
        # Bring in to compliance if prereqs pass
    # elif compliant
        # Maintain the state in compliance
# Check the log for new settings, or specified state
    # if a new setting, check if it conflicts with the current state
        # excecute new command if no conflicts
    # if a new state, update the desired state variable
# Check that the current state is the desired state
    for state_db in STATE_DBs:
        if current_state[state_db]['state'] != current_state[state_db]['desired_state']:
        # Check the critical prerequisites of the desired states
            prereqs_pass = True
            for prereq in STATES[state_db][current_state[state_db]['desired_state']]['prerequisites']['critical']:
                critical_prereq = from_keys(db[prereq['db']].read_buffer(),prereq['key'])
                prereqs_pass *= (critical_prereq == prereq['value'])
        # If the critical prerequisites pass, initialize transition into the desired state
            if prereqs_pass:
            # Update the state variable
                current_state[state_db]['state'] = current_state[state_db]['desired_state']
                current_state[state_db]['compliance'] = False # The current state variable should show noncompliance.
                db[state_db].write_buffer(current_state[state_db])
        

# %% OLD STUFF
#==============================================================================
# %% Functions

def start_busy(task):
    started = False
    while not started:
        try:
            task.StartTask()
        except DAQError as daq_err:
            if daq_err.error == -50103: # "The specified resource is reserved."
                pass
            else:
                raise
        else:
            started = True


class ilx_LDC3900:
    def __init__(self, visa_id, channel, rm = None):
        print(time.strftime('%c')+' - Initializing communication with the ILX LDC-3900.')
        if rm is None:
            rm = visa.ResourceManager()
        opened = False
        while not opened:
            try:
                self.ilx = rm.open_resource(visa_id, open_timeout = 5000)
            except visa.VisaIOError as visa_err:
                if visa_err[0] == visa.VisaIOError(visa.constants.VI_ERROR_RSRC_BUSY)[0]:
                    pass
                else:
                    raise
            else:
                opened = True
        self.ilx.close()
        self.las_open_cmd = 'LAS:CHAN {:}'.format(int(channel))
        self.tec_open_cmd = 'TEC:CHAN {:}'.format(int(channel))
        self.tec_settling_time = 30 # seconds
        self.last_tec_change = time.time()
        self.nominal_tec_r = 7.7
        self.safe_tec_range = .2
        print(time.strftime('%c')+' - Initialized.')
    
    def get_resistance(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        res = self.ilx.query('TEC:R?').strip()
        self.ilx.close()
        return float(res)
    
    def set_resistance(self, resistance):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:R {:.3f}'.format(resistance))
        self.ilx.close()
        
    def get_resistance_setpoint(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        res = self.ilx.query('TEC:SET:R?').strip()
        self.ilx.close()
        return float(res)
    
    def set_tec_step(self, step):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:STEP {:}'.format(int(step)))
        self.ilx.close()
    
    def dec_tec(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:DEC')
        self.ilx.close()
    
    def inc_tec(self):
        open_busy(self.ilx)
        self.ilx.write(self.tec_open_cmd)
        self.ilx.write('TEC:INC')
        self.ilx.close()
    
    def change_tec_output(self, direction):
        now = time.time()
        if now - self.last_tec_change > 1:
            old_res = self.get_resistance()
            new_res = old_res
            while abs(new_res - old_res) < .002:
                if direction>0:
                    if new_res - (self.nominal_tec_r+self.safe_tec_range) < 0:
                        self.inc_tec()
                    else:
                        print(time.strftime('%c')+' - at the limit of the safe TEC range. Raising no farther.')
                        return
                elif direction<0:
                    if new_res - (self.nominal_tec_r-self.safe_tec_range) > 0:
                        self.dec_tec()
                    else:
                        print(time.strftime('%c')+' - at the limit of the safe TEC range. Lowering no farther.')
                        return
                time.sleep(.5)
                new_res = self.get_resistance()
            self.last_tec_change = time.time()
        else:
            print(time.strftime('%c')+' - TEC has not settled. {:.3f}s left'.format(now - self.last_tec_change))
        #time.sleep(20) #let the temperature settle


class ni_USB6361:
    def __init__(self, dev_channel_id, low_v = -1, high_v = 1):
        self.NSAMPS = 1000
        self.read = int32()
        self.data = np.zeros( (self.NSAMPS,), dtype = np.float64)
        self.t = Task()
        self.t.CreateAIVoltageChan(dev_channel_id, "", DAQmx_Val_RSE, low_v, high_v, DAQmx_Val_Volts, None)
    
    def read_analog(self):
        start_busy(self.t)
        self.t.ReadAnalogF64(self.NSAMPS, 10.0, DAQmx_Val_GroupByChannel, self.data, self.NSAMPS, byref(self.read), None)
        self.t.StopTask()
    
    def get_peak_freq(self):
        self.read_analog()
        han_win = np.hanning(self.NSAMPS)
        freqs = 1e4*np.fft.rfftfreq(self.NSAMPS)
        amps = np.abs(np.fft.rfft(han_win*self.data))
        peak_ind = np.argmax(amps)
        return freqs[peak_ind]
    
    def get_rms(self):
        self.read_analog()
        rms = np.sqrt(np.mean(np.square(self.data)))
        return rms


class srs_SIM900:
    def __init__(self, visa_id, channel, rm = None, thrsh_1 = .2, thrsh_2 = .05):
        print(time.strftime('%c')+' - Initializing communication with the SRS SIM900.')
        if rm is None:
            rm = visa.ResourceManager()
        opened = False
        while not opened:
            try:
                self.srs = rm.open_resource(visa_id, open_timeout = 5000)
            except visa.VisaIOError as visa_err:
                if visa_err[0] == visa.VisaIOError(visa.constants.VI_ERROR_RSRC_BUSY)[0]:
                    pass
                else:
                    raise
            else:
                opened = True
        self.srs.close()
        self.flush()
        self.open_cmd = 'CONN '+str(channel)+',"xyz"\n'
        # Get settings (from instrument or database?)
        self.ulim, self.llim = self.get_output_lims()
        self.center = np.mean([self.ulim, self.llim])
        self.threshold_1 = (self.ulim - self.llim)*(1.-thrsh_1*2.)/2.
        self.threshold_2 = (self.ulim - self.llim)*(1.-thrsh_2*2.)/2.
        print(time.strftime('%c')+' - Initialized.')
    
    def flush(self):
        open_busy(self.srs)
        self.srs.flush(visa.constants.VI_READ_BUF)
        self.srs.close()
    
    def get_man_output(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        man_output = self.srs.query('MOUT?').strip()
        self.srs.write('xyz')
        self.srs.close()
        return float(man_output)
    
    def set_man_output(self, output):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        self.srs.write('MOUT {:.3f}'.format(output))
        self.srs.write('xyz')
        self.srs.close()
    
    def get_output(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        level = self.srs.query('OMON?\n').strip()
        self.srs.write('xyz')
        self.srs.close()
        return float(level)
    
    def get_output_cond(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        u_lim = self.srs.query('INCR? 1').strip()
        l_lim = self.srs.query('INCR? 2').strip()
        anti_wind = self.srs.query('INCR? 3').strip()
        self.srs.write('xyz')
        self.srs.close()
        return [int(u_lim), int(l_lim), int(anti_wind)]
    
    def get_output_lims(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        ulim = self.srs.query('ULIM?\n').strip()
        llim = self.srs.query('LLIM?\n').strip()
        self.srs.write('xyz')
        self.srs.close()
        return [float(ulim), float(llim)]
    
    def get_pid_state(self):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        state = self.srs.query("AMAN?\n").strip()
        self.srs.write('xyz')
        self.srs.close()
        return int(state)
    
    def set_pid_state(self, state):
        open_busy(self.srs)
        self.srs.write(self.open_cmd)
        self.srs.write("AMAN {:}\n".format(int(state)))
        self.srs.write('xyz')
        self.srs.close()


def get_lock(srs, daq, ilx, last_good_pos = None):
    #Turn off PID servo
    srs.set_pid_state(0)
    srs.set_man_output(srs.center - srs.threshold_2) # reset the hysteresis
    #Try locking at last good position
    if last_good_pos is not None:
        srs.set_man_output(last_good_pos)
        time.sleep(.1)
        srs.set_pid_state(1)
        time.sleep(1)
        current_output = srs.get_output()
        if abs(current_output - srs.center) < srs.threshold_2:
            return
        else:
            srs.set_pid_state(0)
    
    #Find lock point    
    to_fit = lambda v, v0, s: s*np.abs(v-v0)
        #Get Data
    x = np.linspace(srs.center-srs.threshold_2, srs.center+srs.threshold_2, 4)
    y =np.copy(x)
    for ind, x_val in enumerate(x):
        srs.set_man_output(x_val)
        y[ind] = daq.get_peak_freq()
    srs.set_man_output(x[0]) # reset the hysteresis
        #Coarse Estimate
    slopes = np.diff(y)/np.diff(x)
    slope_ind = np.argmax(np.abs(slopes))
    output_coarse = -y[slope_ind]/slopes[slope_ind] + x[slope_ind]
    slope_coarse = np.abs(slopes[slope_ind])
        #Fine Estimate
    try:
        new_output = curve_fit(to_fit, x, y, [output_coarse, slope_coarse])[0][0]
    except:
        print(time.strftime('%c')+' - Curve fit failed')
        new_output = srs.center
    
    #Get Lock
    if abs(new_output - srs.center) < srs.threshold_2:
        print(time.strftime('%c')+' - estimated voltage setpoint = {:.3f}, locking.'.format(new_output))
        srs.set_man_output(new_output)
        time.sleep(.1)
        srs.set_pid_state(1)
    elif new_output < srs.center:
        print(time.strftime('%c')+' - estimated voltage setpoint = {:.3f}, raising the resistance setpoint.'.format(new_output))
        ilx.change_tec_output(+1)
        #time.sleep(30)
    elif new_output > srs.center:
        print(time.strftime('%c')+' - estimated voltage setpoint = {:.3f}, lowering the resistance setpoint.'.format(new_output))
        ilx.change_tec_output(-1)
        #time.sleep(30)


# %% Setup
rm = visa.ResourceManager()

fr_pid = srs_SIM900('ASRL9::INSTR', 1, rm)
fr_err = ni_USB6361('Dev1/ai0')
fr_tec = ilx_LDC3900(u'GPIB0::20::INSTR', 1, rm)

last_good_pos = None

#pid_ulim, pid_llim = fr_pid.get_output_lims()
#
#pid_center = np.mean([pid_ulim, pid_llim])
#pid_hyst = (pid_ulim - pid_llim)*(1.-.2*2.)/2.
#pid_hyst2 = (pid_ulim - pid_llim)*(1.-.01*2.)/2.

# %% Test

test = 0
while test:
    #Begin Test
    if fr_pid.get_pid_state():
        current_output = fr_pid.get_output()
        current_output_cond = fr_pid.get_output_cond()
        current_rms = fr_err.get_rms()
        print current_output
        print current_output_cond
        print current_rms
        if abs(current_output - fr_pid.center) > fr_pid.threshold_2:
            print(time.strftime('%c')+' - lost fR lock')
            get_lock(fr_pid, fr_err, fr_tec, last_good_pos)
        elif abs(current_output - fr_pid.center) > fr_pid.threshold_1:
            if current_output - fr_pid.center > 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, lowering the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(-1)
            elif current_output - fr_pid.center < 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, raising the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(1)
        else:
            last_good_pos = current_output
    else:
        get_lock(fr_pid, fr_err, fr_tec)
    time.sleep(.1)
    #End Test
    test = 0
    


# %% Main Loop

while 1:
    if fr_pid.get_pid_state():
        current_output = fr_pid.get_output()
        current_output_cond = fr_pid.get_output_cond()
        if abs(current_output - fr_pid.center) > fr_pid.threshold_2:
            print(time.strftime('%c')+' - lost fR lock')
            get_lock(fr_pid, fr_err, fr_tec, last_good_pos)
        elif abs(current_output - fr_pid.center) > fr_pid.threshold_1:
            if current_output - fr_pid.center > 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, lowering the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(-1)
            elif current_output - fr_pid.center < 0:
                print(time.strftime('%c')+' - voltage was {:.3f}, raising the resistance setpoint.'.format(current_output))
                fr_tec.change_tec_output(+1)
        else:
            last_good_pos = current_output
    else:
        get_lock(fr_pid, fr_err, fr_tec)


print('temperature setpoint is out of range')


    