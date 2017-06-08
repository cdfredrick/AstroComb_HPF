# -*- coding: utf-8 -*-
"""
Created on Tue May 13 10:58:42 2014

@author: NIST
"""

from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from PyDAQmx import DAQError

from scipy.signal import blackmanharris
from numpy.fft import rfft, fftfreq
from scipy import stats

import visa
from mongologger import *
import logging

import time
from datetime import datetime

logging.basicConfig(filename = 'd:\\KeepCombLocked.txt', level = logging.ERROR)

FREP_CENTER_VOLTS = 5.0 # resting value for frep

# Define function to retry when an query_ascii_values times out
def safe_query_ascii_values(inst, arg):
    tries = 5
    retry = True
    while tries > 0 and retry:
        retry = False
        tries =- 1
        try:                  
            values  =  inst.query_ascii_values(arg)
        except visa.VisaIOError as e:            
            logging.log(0,'Caught VisIOError', e)
            retry = True
    if retry == False:
        return values
    else:
        logging.log(0,'Caught 5 consecutive VisIOErrors; aborting.')
        raise visa.VisaIOError(e.error_code)


class srs_actions:
    def __init__(self, srs_visa_id = 'ASRL2::INSTR', rm = None):
        print datetime.now().strftime('%c')+' - '+"Initializing srs_actions script"
        if rm is None:
            rm = visa.ResourceManager()
        self.srs = rm.get_instrument(srs_visa_id)
        self.f0channel = 3
        self.frchannel = 7
        self.fr_open_cmd = 'CONN '+str(self.frchannel)+',"xyz"\n'
        self.f0_open_cmd = 'CONN '+str(self.f0channel)+',"xyz"\n'
        print datetime.now().strftime('%c')+' - '+"srs_actions initialized"
        
    def srs_turn_off_fr(self):
        self.srs.write(self.fr_open_cmd)
        self.srs.write("AMAN 0\n")
        self.srs.query('xyz*IDN?\n')
    
    def srs_turn_on_fr(self):
        self.srs.write(self.fr_open_cmd)
        # For smooth turn on of the rep rate servo, start with P gain only, pause,
        # then enable I
        self.srs.write("ICTL 0\n")
        self.srs.write("AMAN 1\n")
        time.sleep(1)
        self.srs.write("ICTL 1\n")
        self.srs.query('xyz*IDN?\n')
    def srs_outputstate_fr(self):
        self.srs.write(self.fr_open_cmd)
        state = self.srs.query_ascii_values("AMAN?\n")[0]
        self.srs.query('xyz*IDN?\n')
        return state
    def srs_turn_off_f0(self):
        self.srs.write(self.f0_open_cmd)
        self.srs.write("AMAN 0\n")
        self.srs.query('xyz*IDN?\n')
        time.sleep(10)
    
    def srs_turn_on_f0(self):
        self.srs.write(self.f0_open_cmd)
        self.srs.write("AMAN 1\n")
        self.srs.query('xyz*IDN?\n')
    def srs_outputstate_f0(self):
        self.srs.write(self.f0_open_cmd)
        state = self.srs.query_ascii_values("AMAN?\n")[0]
        self.srs.query('xyz*IDN?\n')
        return state
    def get_frep_lims(self):
        self.srs.write(self.fr_open_cmd)
        ulim = self.srs.query_ascii_values('ULIM?\n')
        llim = self.srs.query_ascii_values('LLIM?\n')
        self.srs.query('xyz*IDN?\n')
        return (ulim[0], llim[0])
    def get_frep_P(self):
        self.srs.write(self.fr_open_cmd)
        pgain = self.srs.query_ascii_values('GAIN?\n')
        self.srs.query('xyz*IDN?\n')
        return pgain
        
    def get_f0_lims(self):
        self.srs.write(self.f0_open_cmd)
        ulim = self.srs.query_ascii_values('ULIM?\n')
        llim = self.srs.query_ascii_values('LLIM?\n')
        self.srs.query('xyz*IDN?\n')
        return (ulim[0], llim[0])
    
    def get_f0_volts(self):
        self.srs.write(self.f0_open_cmd)
        level = self.srs.query_ascii_values('OMON?\n')
        self.srs.query('xyz*IDN?\n')
        return level[0]
        
    def get_fr_volts(self):
        self.srs.write(self.fr_open_cmd)
        level = self.srs.query_ascii_values('OMON?\n')
        self.srs.query('xyz*IDN?\n')
        return level[0]

class servo_locker:
    
    f0_lock_test_counter = 0
    fR_lock_test_counter = 0
    f0_volts = 0
    fr_volts = 0
    fr_iter_count = 0
    fr_recent_f = []

    # f0_states
    F_LOCKED    = 0
    F_TESTING   = 1
    F_SEARCHING = 2
    F0_STATE_DESC = ['Locked', 'Testing', 'Searching']
    
    
    def __init__(self, f0_lock_fr, fR_lock_fr, mongologger_instance,
                       srs_visa_id = 'ASRL2::INSTR'):
        print datetime.now().strftime('%c')+' - '+"Initializing servo_locker script"
        # Constants -----------------------------------------------------------
        self.fr_searching = False        
        self.f0_search_dir = 5 #was 5. changed 03.25.16 by RCT
        self.fr_search_dir = 1
        self.hunt_multiplier = 1
        self.f0_is_settled = True
        self.fr_is_settled = True
        self.ML= mongologger_instance
        self.f0_lock_fr = f0_lock_fr
        self.fR_lock_fr = fR_lock_fr
        self.f0_state = self.F_LOCKED
        self.fR_state = self.F_LOCKED
        
        # Instruments ---------------------------------------------------------
        self.rm = visa.ResourceManager()
        #print self.rm.list_resources()
        self.comb = self.rm.get_instrument('ASRL1::INSTR', baud_rate=115200)
        self.rfsa = self.rm.get_instrument('USB0::0x0957::0xFFEF::CN03480546::INSTR')
        self.srs_comms = srs_actions(srs_visa_id, rm = self.rm)
        
        # RFSA ----------------------------------------------------------------
        # set start / stop frequencies
        self.rfsa_start = self.fR_lock_fr * 0.
        self.rfsa_stop = self.fR_lock_fr * 1.
        self.rfsa.write(":SENS:FREQ:STAR {:.2e}".format(self.rfsa_start))
        self.rfsa.write(":SENS:FREQ:STOP {:.2e}".format(self.rfsa_stop))

        startf = safe_query_ascii_values(self.rfsa,":SENS:FREQ:STAR?")[0]
        endf = safe_query_ascii_values(self.rfsa,":SENS:FREQ:STOP?")[0]
        self.fr_pgain = self.srs_comms.get_frep_P()
        
        # NOTE: Expect peaks between f_r and 2*f_r at
        # f_r + deltaf and 2*f_r - deltaf
        self.leftPeakF = self.rfsa_start + (self.fR_lock_fr - self.f0_lock_fr)
        self.rightPeakF = self.rfsa_stop - (self.fR_lock_fr - self.f0_lock_fr)        
        self.rfsa_sweep_time = float(self.rfsa.query(":SENS:SWE:TIME?"))
        rfsadata = safe_query_ascii_values(self.rfsa,":TRAC:DATA?")
                
        self.freqs = np.linspace(startf,endf,len(rfsadata))

        self.f0_snr_threshold = 20   # Peak detection threshold (dB)
        self.capture_limit = 3e6    # capture range for f0 (Hz)
        
        # DAC (for DAC-based fR search) ---------------------------------------
        self.NSAMPS = 50000
        self.read = int32()
        self.DACdata = np.zeros( (self.NSAMPS,), dtype = np.float64)
        self.t = Task()
        self.t.CreateAIVoltageChan('Dev6320_1/ai0', "", DAQmx_Val_Diff,
                                   -1.0,1.0, DAQmx_Val_Volts, None)
        self.t_f0locked = Task()
        self.t_f0locked.CreateAIVoltageChan('Dev6320_1/ai1', "", DAQmx_Val_Diff,
                                   -10.0,10.0, DAQmx_Val_Volts, None)                                   
        self.t.CfgSampClkTiming("", 250000.0, DAQmx_Val_Rising, 
                                    DAQmx_Val_FiniteSamps, self.NSAMPS)
        
        self.frep_rms_threshold = 0.010 # rms value on fr error signal above which fr is
                               # not really locked.

        # PID Control ---------------------------------------------------------
        # Find the "rails" for f0
        ulim_f0, llim_f0 = self.srs_comms.get_f0_lims()
        self.f0_center = (0.5*(ulim_f0+llim_f0))
        self.ulim_f0 = self.f0_center + 0.5*(ulim_f0-llim_f0) * 0.9
        self.llim_f0 = self.f0_center - 0.5*(ulim_f0-llim_f0) * 0.9
        
        # Find the "rails" for frep
        ulim_fr, llim_fr = self.srs_comms.get_frep_lims()
        self.fr_center = (0.5*(ulim_fr+llim_fr))
        self.ulim_fr = self.fr_center + 0.5*(ulim_fr-llim_fr) * 0.9
        self.llim_fr = self.fr_center - 0.5*(ulim_fr-llim_fr) * 0.9
        
        # Set Hysterysis
        self.f0_hyst = (ulim_f0-llim_f0)/3.  # hystersis for f0 servo
        self.fr_hyst =  (ulim_fr-llim_fr)/4. # hystersis for fR servo


        print datetime.now().strftime('%c')+' - '+"servo_locker initialized"
        # /Setup


# =============================================================================
# Lock f0 =====================================================================
    def move_f0(self):
        try:
            logging.debug('Entering move f0. State is '+self.F0_STATE_DESC[self.f0_state]+'.')
            self.f0_is_settled = False
            self.f0_volts = self.srs_comms.get_f0_volts()

            # if f0 output state is manual then set to SEARCHING
            if (not self.f0_state is self.F_SEARCHING) and (self.srs_comms.srs_outputstate_f0() == 0):
                # Update Lock State
                print datetime.now().strftime('%c')+' - '+'f0 unlocked, search queued'
                self.f0_state = self.F_SEARCHING
                self.ML.logData(self.f0_state, "Lock_state/f0")
                self.ML.logData(max([self.f0_state,self.fR_state]),  "Lock_state/lock_state")


# Get Counter Values ----------------------------------------------------------
        # if f0 is LOCKED, get counter values
            if self.f0_state is self.F_LOCKED:
                try:
                    last_lock_time = self.ML.getMostRecentData("Comb/f0_lock_test_begun")['_time']
                    f0_counter_value = self.ML.getMostRecentData("Countf0/f0_str")['_value']
                    f0_counter_value = float(f0_counter_value)
                    f0_counter_time  = self.ML.getMostRecentData("Countf0/f0_str")['_time']                        
                except TypeError:
                    logging.warning('last lock time was NoneType. Using 0')
                    self.ML.logText('last lock time was NoneType.', 'Comb/ScriptTextLog')
                    last_lock_time = 0
                    f0_counter_value = self.f0_lock_fr / 8.0
                    f0_counter_time = 1
                
                quality_counter_time = f0_counter_time-last_lock_time
                #print f0_counter_value
                #print self.f0_lock_fr
                f0_err   = abs(self.f0_lock_fr - 8.0 * f0_counter_value)


# SEARCHING for f0 ------------------------------------------------------------
        # If SEARCHING, perform motor move before aquiring RFSA data.
        # This order ensures that the logic in place to escape
        # bad locks actually executes.
            if self.f0_state is self.F_SEARCHING:
                logging.debug('Talking to comb.')
                # If the motor position > 10000, bounce around
                self.comb.open()
                pos = float(self.comb.query(':TMC428:POS4?\n'))
                self.comb.close()
                good_loc = 2500
                if pos > good_loc+2500:
                    self.f0_search_dir = -abs(self.f0_search_dir)
                elif pos < good_loc-2500:
                    self.f0_search_dir = abs(self.f0_search_dir)
        
            # searching and not lock testing, then move the motor
            # self.hunt_multiplier is used to give a larger step size upon 
            #detection of unlock. This is to eject the locking logic from 
            # pseudo-locked states where the sign of the P gain is incorrect, but
            # where this causes oscillation (the root cause is the digital
            # divider, which gives a noisy peak centered at the RF bandpass filter
            # divided by 8 )

                logging.debug('Talking to comb.')
                msg = ':TMC428:MOVE4 ' + str(self.f0_search_dir * self.hunt_multiplier) + '\n'
                self.comb.open()
                self.comb.write(msg)
                self.comb.close()                
                self.ML.logData(str(pos), "Comb/TMC428/POS4")
                print datetime.now().strftime('%c')+' - '+"Moving motor " + str(self.f0_search_dir * self.hunt_multiplier) +", was at " + str(pos)
                logging.debug("Moving motor " + str(self.f0_search_dir * self.hunt_multiplier) +", was at " + str(pos))
                self.hunt_multiplier = 1


# Get RFSA Data ---------------------------------------------------------------
        # If SEARCHING or TESTING, collect data from RFSA
            if (self.f0_state is self.F_SEARCHING) or\
                self.f0_state is self.F_TESTING:

                self.ML.logText('entering f0 search logic', 'Comb/ScriptTextLog')
            # Find peaks    
                datas = []
                nMeasPerCycle = 1
                logging.debug('Attempting to talking to RFSA...')
                self.rfsa.write(":SENS:FREQ:STAR {:.2e}".format(self.rfsa_start))
                self.rfsa.write(":SENS:FREQ:STOP {:.2e}".format(self.rfsa_stop))
                for i in range(nMeasPerCycle):
                    datas.append(safe_query_ascii_values(self.rfsa,":TRAC:DATA?"))
                    time.sleep(self.rfsa_sweep_time)
                logging.debug('Success')
                dataAvg = []
                if nMeasPerCycle == 1:
                    dataAvg = datas[0]
                else:
                    for i in range(len(datas[0])):
                        dataSlice = []
                        for j in range(len(datas)):
                            dataSlice.append(datas[j][i])
                        dataAvg.append(np.average(dataSlice))

                peaksF = []
                peaksA = []
                noise_floor, counts = stats.stats.mode(dataAvg)
                for i in range(len(dataAvg)):
                    if dataAvg[i] > noise_floor + self.f0_snr_threshold:
                        peaksA.append(dataAvg[i]) # amplitude
                        peaksF.append(self.freqs[i])    # frequency
                
            # Check if peaks are in appropriate places
                dataAvg = np.array(dataAvg)
            
                left_filter = (self.freqs > (self.rfsa_start + 10e6)) * (self.freqs < self.rfsa_start + self.fR_lock_fr/2.)
                left_peak_idx = np.argmax( dataAvg[ left_filter ] )
                left_peak_freq = self.freqs[ left_filter ][left_peak_idx]
            
                right_filter = (self.freqs > (self.rfsa_stop - self.fR_lock_fr/2.)) * (self.freqs < (self.rfsa_stop - 10e6))
                right_peak_idx = np.argmax( dataAvg[right_filter] )
                right_peak_freq = self.freqs[right_filter][right_peak_idx]
            
                foundLeftPeak = False
                foundRightPeak = False        
            
                if abs(left_peak_freq - self.leftPeakF) < self.capture_limit:
                    foundLeftPeak = True
                if abs(right_peak_freq - self.rightPeakF) < self.capture_limit:
                    foundRightPeak = True
                      
                self.ML.logData([left_peak_freq, right_peak_freq], "Comb/TMC428/POS4/f0_beat_freqs")


# Keep SEARCHING for f0? ------------------------------------------------------
            if self.f0_state is self.F_SEARCHING:
                print datetime.now().strftime('%c')+' - '+'f0 peaks found at {0:.2f} & {1:.2f}MHz'.format(left_peak_freq*1e-6,right_peak_freq*1e-6)
                if foundLeftPeak and foundRightPeak:
                    # Lock and start TESTING
                    self.srs_comms.srs_turn_on_f0()
                    self.ML.logData(True, "Comb/f0_lock_test_begun")
                    time.sleep(2)
                    self.ML.logText("Testing a f0 lock.", "Comb/TMC428/POS4")                
                    print datetime.now().strftime('%c')+' - '+"f0 corrected, enabling PID controller and beginning tests."
                    logging.info("Testing a f0 lock.")
                    # Update Lock State
                    self.f0_state = self.F_TESTING
                    self.ML.logData(self.f0_state, "Lock_state/f0")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    self.f0_lock_test_counter = 3
                    return
                else:
                    # Continue SEARCHING
                    self.ML.logData(self.f0_state, "Lock_state/f0")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    return


# TESTING f0 lock -------------------------------------------------------------
        # If TESTING the f0 lock, see how it's doing
            if self.f0_state is self.F_TESTING:
                if self.f0_lock_test_counter > 1:
                    if self.f0_volts > self.ulim_f0 or self.f0_volts < self.llim_f0:
                        # PID voltages outside of threshold, begin SEARCHING
                        f0_locked = False
                        if self.f0_volts >= self.ulim_f0:
                            print datetime.now().strftime('%c')+' - '+'f0 voltage is ',str(self.f0_volts),\
                            ' and above threshold value of ',str(self.ulim_f0)
                        if self.f0_volts <= self.llim_f0:
                            print datetime.now().strftime('%c')+' - '+'f0 voltage is ',str(self.f0_volts),\
                            ' and below threshold value of ',str(self.llim_f0) 
                    elif not foundRightPeak:
                        # incorrect f0 peak, begin SEARCHING
                        f0_locked = False
                        print datetime.now().strftime('%c')+' - '+"f0 is {0:.2f}MHz, and outside the capturing limit {1:.2}MHz".format(right_peak_freq*1e-6, self.capture_limit*1e-6)
                    else:
                        # lock succeded, continue TESTING
                        f0_locked = True

                # Lock pass/fail?
                    if f0_locked is False:
                        # Lock failed, continue SEARCHING
                        print datetime.now().strftime('%c')+' - '+"f0 lock failed, continuing search"
                        self.f0_lock_test_counter = 0
                        self.hunt_multiplier = 10.0
                        logging.debug("Lock failed, continuing search")
                        # Update Lock State
                        self.f0_state = self.F_SEARCHING
                        self.ML.logData(self.f0_state, "Lock_state/f0")
                        self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                        self.srs_comms.srs_turn_off_f0()
                        return
                    else: 
                        # lock succeeded, continue TESTING
                        self.f0_lock_test_counter -= 1
                        # Update Lock State
                        self.ML.logData(self.f0_state, "Lock_state/f0")
                        self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                        time.sleep(1)
                        return

            # Lock tests succeeded, f0 is LOCKED
                elif self.f0_lock_test_counter == 1:
                    self.comb.open()
                    pos = self.comb.query(':TMC428:POS4?\n').strip()
                    self.comb.close()
                    self.ML.logText("f0 lock succeeded, ending search.", "Comb/TMC428/POS4")
                    print datetime.now().strftime('%c')+' - '+"f0 Lock succeeded, ending search"
                    print "f0: Position {0:}, PID {1:.2E}V, RFSA Error {2:.2E}Hz".format(pos, self.f0_volts, right_peak_freq-self.rightPeakF)
                    logging.debug("f0 Lock succeeded, ending search. Position {0:}, PID V {1:.2E}".format(pos, self.f0_volts))
                    self.f0_lock_test_counter = 0
                    # Update Lock State
                    self.f0_state = self.F_LOCKED
                    self.ML.logData(self.f0_state, "Lock_state/f0")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    return         


# Checking f0 LOCKED state ----------------------------------------------------
        # if f0 is LOCKED, check PID limits and Counter values
            if self.f0_state is self.F_LOCKED:
                ###### if we're at the rails try relocking by toggling PI on & off.
                # This is only expected to be used in the first cycles of the program
                if self.f0_volts > self.ulim_f0 or self.f0_volts < self.llim_f0:
                    self.f0_is_settled = False
                    # try to relock by toggling the servo, then repeat TESTING
                    self.ML.logText('Attempting to relock f0 by servo toggle', "Comb/TMC428/POS4")
                    logging.info('Attempting to relock f0 by servo toggle')
                    # Update Lock State
                    self.f0_state = self.F_SEARCHING
                    self.ML.logData(self.f0_state, "Lock_state/f0")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    self.srs_comms.srs_turn_off_f0()
                    time.sleep(2)
                    self.srs_comms.srs_turn_on_f0()
                    # Update Lock State
                    self.f0_state = self.F_TESTING
                    self.ML.logData(self.f0_state, "Lock_state/f0")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    self.f0_lock_test_counter = 3
                    return
                # if the counter reads a frequency > 500 kHz from lock point, force
                #   a relock with a big kick
#                if  f0_err > 500e3 and quality_counter_time > 120:
#                    self.hunt_multiplier = 20
#                    print datetime.now().strftime('%c')+' - '+"f0 counter failed. searching."
#                    logging.info("f0 counter failed. searching.")
#                    # Update Lock State
#                    self.f0_state = self.F_SEARCHING
#                    self.ML.logData(self.f0_state, "Lock_state/f0")
#                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
#                    self.srs_comms.srs_turn_off_f0()
#                    return
            
                ###### Otherwise, if voltage output of f0 servo is less than f0_hyst.
                #   enable frep lock scheme by setting f0_is_settled = true
                if abs(self.f0_volts-self.f0_center) < self.f0_hyst:
                    self.f0_is_settled = True
                    return
                else:
                    # Update Lock State
                    self.ML.logData(self.f0_state, "Lock_state/f0")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    # PID voltage marginal, adjust slighty, then repeat TESTING
                    print datetime.now().strftime('%c')+' - '+"f0 PID voltage marginal, adjusting slighty"
                    self.f0_is_settled = False
                    # Update Lock State to TESTING
                    self.f0_state = self.F_TESTING
                    self.ML.logData(self.f0_state, "Lock_state/f0")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    self.f0_lock_test_counter = 3
                    # try a small adjustment
                    old_f0_volts = self.f0_volts
                    msg = ':TMC428:MOVE4 {:}\n'.format(np.sign(self.f0_search_dir)*2)
                    logging.debug('Talking to comb.')
                    self.comb.open()
                    self.comb.write(msg)
                    time.sleep(0.1)
                    pos = self.comb.query(':TMC428:POS4?\n').strip()
                    self.comb.close()
                    time.sleep(1.)
                    self.f0_volts = self.srs_comms.get_f0_volts()
                    self.ML.logData(self.f0_volts, "Comb/TMC428/f0_volts")
                    self.ML.logData(pos, "Comb/TMC428/POS4")
                    # change search direction?
                    if abs(self.f0_volts-self.f0_center) > abs(old_f0_volts-self.f0_center):
                        self.f0_search_dir *= -1 # Switch directions
                    #print "moved f0: Position {0:}, PID V {1:.2E}".format(pos, self.f0_volts)
                    return


# Error Handling --------------------------------------------------------------
        except DAQError as err:
            print datetime.now().strftime('%c')+' - '+'DAQ error: %s.'%err
            self.t_f0locked.ClearTask()
            return


# =============================================================================
# Lock fR =====================================================================
    def move_fr(self):
        try:
            logging.debug('Entering move fr. State is '+self.F0_STATE_DESC[self.fR_state]+'.')
            self.fr_volts = self.srs_comms.get_fr_volts()
        
            # if fR PID output state is manual then set status to SEARCHING
            if (not self.fR_state is self.F_SEARCHING) and (self.srs_comms.srs_outputstate_fr() == 0):
                # Update Lock State
                print datetime.now().strftime('%c')+' - '+'fR unlocked, search queued.'
                self.fR_state = self.F_SEARCHING
                self.ML.logData(self.fR_state, "Lock_state/fR")
                self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
            # if fR PID rails while adjusting f0, set to SEARCHING
            elif (not self.f0_is_settled) and ((self.fr_volts >= self.ulim_fr) or (self.fr_volts <= self.llim_fr)):
                # Update Lock State
                print datetime.now().strftime('%c')+' - '+'fR lock lost, search queued.'
                self.fR_state = self.F_SEARCHING
                self.ML.logData(self.fR_state, "Lock_state/fR")
                self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                self.srs_comms.srs_turn_off_fr()
            # if f0 is SEARCHING, return to move_f0()
            if not self.f0_is_settled:
                return


# Get DAC Frequency Data ------------------------------------------------------
        # If SEARCHING, or TESTING, get frep difference frequency from DAC
            if (self.fR_state is self.F_SEARCHING) or\
                self.fR_state is self.F_TESTING:
            
                self.t.StartTask()
                self.t.ReadAnalogF64(self.NSAMPS, 10.0, DAQmx_Val_GroupByChannel, 
                                     self.DACdata, self.NSAMPS, 
                                     byref(self.read), None)
                self.t.StopTask()
                # Test lock independently of PID controller by making sure there
                #   is a low RMS value on the error signal
                rms_error = np.sum(np.sqrt(self.DACdata**2)) / float(self.NSAMPS)\
                                                     / self.fr_pgain
                self.ML.logData(rms_error[0], 'Comb/TMC428/POS6/frep_rms_error')
        

# Keep SEARCHING for fR? ------------------------------------------------------
            if self.fR_state is self.F_SEARCHING:
                self.srs_comms.srs_turn_off_fr()
                self.fr_is_settled = False
                       
                windowed = self.DACdata * blackmanharris(len(self.DACdata))
                f = rfft(windowed)
            
                freqs = fftfreq(len(windowed), d=1./250000.)
            
                i = np.argmax(abs(f))
                cur_f = freqs[i]

            # Stop SEARCHING if we're within 150 Hz of the desired frequency (previously 60 Hz)
                if cur_f <= 150:
                    print datetime.now().strftime('%c')+' - '+'error frequency: ',cur_f
                    # Start TESTING
                    self.ML.logText("Concluding DAC-based frep search. Begining tests.", "Comb/TMC428/POS6")
                    print datetime.now().strftime('%c')+' - '+"fR corrected, enabling PID controller and beginning tests."
                    self.fr_searching = False
                    self.fr_iter_count = 0
                    self.srs_comms.srs_turn_on_fr()
                    # Update Lock State
                    self.fR_state = self.F_TESTING
                    self.ML.logData(self.fR_state, "Lock_state/fR")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    self.fR_lock_test_counter = 3
                    return
                else:
                    # Continue SEARCHING
                    # Calc how far we've gone since we started moving this direction
                    # Moving window average
                    self.fr_recent_f.append(cur_f) # Push
                    if len(self.fr_recent_f) >= 3:
                        self.fr_recent_f = self.fr_recent_f[1:] # Pop from beginning
                    if len(self.fr_recent_f) > 1:
#                        delta_f = np.average(np.array(self.fr_recent_f[1:]) -\
#                                np.array(self.fr_recent_f[0:len(self.fr_recent_f)-1]))
                        delta_fs = np.diff(self.fr_recent_f)
                        delta_f = delta_fs[-1]
                        delta_f_avg = np.mean(delta_fs)
                        fr_hunt_mult = int(round(cur_f/300.))
                        if not fr_hunt_mult:
                            fr_hunt_mult = 1
                        self.fr_search_dir = np.sign(self.fr_search_dir)*fr_hunt_mult
                    else:
                        delta_f = 0
                        delta_f_avg = 0
                    print datetime.now().strftime('%c')+' - '+"error frequency: "+str(cur_f)+" Hz, change: " + str(delta_f) + " Hz"
                    logging.info("fr error frequency: "+str(cur_f)+" change:" + str(delta_f) + " Hz")
                    # If we're going the wrong way (want to drive f -> 0)
                    # then switch directions
                    if delta_f_avg > 0 and self.fr_iter_count > 5:
                        self.fr_search_dir *= -1 # Switch directions
                        self.fr_iter_count = 0 # Try another set of test iterations                    
                    # Separate conditional allows instantialization to work right
                    if self.fr_iter_count == 0:
                        self.fr_recent_f = []
                                    
                    # Move the motor
                    logging.debug('Talking to comb.')                
                    msg = ":TMC428:MOVE6 " + str(self.fr_search_dir) + "\n"
                    self.comb.open()
                    self.comb.write(msg)
                    time.sleep(0.1)
                    pos = self.comb.query(':TMC428:POS6?\n').strip()
                    self.comb.close()   
                    print datetime.now().strftime('%c')+' - '+"Driving frep: " + str(pos)
                    self.ML.logData(pos, "Comb/TMC428/POS6")        
                    self.fr_iter_count += 1
                    # Update Lock State
                    self.ML.logData(self.fR_state, "Lock_state/fR")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    return


# TESTING fR lock -------------------------------------------------------------
        # If TESTING the lock fR, see how it's doing
            if self.fR_state is self.F_TESTING:
                if self.fR_lock_test_counter > 1:
                    if rms_error > self.frep_rms_threshold:
                        # rms error above threshold, begin SEARCHING
                        fr_locked = False
                        print datetime.now().strftime('%c')+' - '+'RMS error is {0:.2E} Hz, and above threshold value of {1:.3E} Hz'.format(rms_error[0],self.frep_rms_threshold)
                    elif self.fr_volts >= self.ulim_fr or self.fr_volts <= self.llim_fr:
                        # PID voltages outside of threshold, begin SEARCHING
                        fr_locked = False
                        if self.fr_volts >= self.ulim_fr:
                            print datetime.now().strftime('%c')+' - '+'fr voltage is ',str(self.fr_volts),\
                            ' and above threshold value of ',str(self.ulim_fr)
                        if self.fr_volts <= self.llim_fr:
                            print datetime.now().strftime('%c')+' - '+'fr voltage is ',str(self.fr_volts),\
                            ' and below threshold value of ',str(self.llim_fr) 
                    else:
                        # lock succeeded, continue TESTING
                        fr_locked = True
                
                # Lock pass/fail?
                    if fr_locked is False:
                        # lock failed, begin SEARCHING
                        self.fR_lock_test_counter = 0
                        self.ML.logText("Lock failed, starting DAC-based frep search.", "Comb/TMC428/POS6")    
                        self.fr_is_settled = False
                        self.fr_searching = True
                        # Update Lock State
                        self.fR_state = self.F_SEARCHING
                        self.ML.logData(self.fR_state, "Lock_state/fR")
                        self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                        self.srs_comms.srs_turn_off_fr()
                        
                        # Move the motor
                        logging.debug('Talking to comb.')                
                        msg = ":TMC428:MOVE6 " + str(self.fr_search_dir) + "\n"
                        self.comb.open()
                        self.comb.write(msg)
                        time.sleep(0.1)
                        pos = self.comb.query(':TMC428:POS6?\n').strip()
                        self.comb.close()   
                        print datetime.now().strftime('%c')+' - '+"Driving frep: " + str(pos)
                        self.ML.logData(pos, "Comb/TMC428/POS6")        
                        self.fr_iter_count += 1
                        return
                    else:
                        # lock succeeded, continue TESTING
                        self.fR_lock_test_counter -= 1
                        # Update Lock State
                        self.ML.logData(self.fR_state, "Lock_state/fR")
                        self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                        return

            # Lock tests succeeded, fR is LOCKED
                elif self.fR_lock_test_counter == 1:
                    self.comb.open()
                    pos = self.comb.query(':TMC428:POS6?\n').strip()
                    self.comb.close()
                    self.ML.logText("fR lock succeeded, ending search.", "Comb/TMC428/POS6")
                    print datetime.now().strftime('%c')+' - '+"fR Lock succeeded, ending search."
                    print "fR: Position {0:}, PID {1:.2E}V, RMS Error {2:.2E}Hz".format(pos, self.fr_volts, rms_error[0])
                    logging.debug("fR Lock succeeded, ending search. Mean DAQ was {:.2E}".format(np.mean(self.DACdata)))
                    self.fR_lock_test_counter = 0
                    # Update Lock State            
                    self.fR_state = self.F_LOCKED
                    self.ML.logData(self.fR_state, "Lock_state/fR")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    return


# Checking fR LOCKED state ----------------------------------------------------
            if self.fR_state is self.F_LOCKED:
                if abs(self.fr_volts-self.fr_center) < self.fr_hyst:
                    self.fr_is_settled = True
                    return
                else:
                    # Update Lock State
                    self.ML.logData(self.fR_state, "Lock_state/fR")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    # PID voltage marginal, adjust slighty then repeat TESTING
                    print datetime.now().strftime('%c')+' - '+"fR PID voltage marginal, adjusting slighty"
                    self.fr_is_settled = False
                    # Update Lock State to TESTING
                    self.fR_state = self.F_TESTING
                    self.ML.logData(self.fR_state, "Lock_state/fR")
                    self.ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")
                    self.fR_lock_test_counter = 3
                    # try a small adjustment
                    old_fr_volts = self.fr_volts
                    msg = ':TMC428:MOVE6 {:}\n'.format(self.fr_search_dir)
                    logging.info('Talkiing to comb.')
                    self.comb.open()
                    self.comb.write(msg)
                    time.sleep(0.1)
                    pos = self.comb.query(':TMC428:POS6?\n').strip()
                    self.comb.close()
                    logging.info('Success.')
                    time.sleep(1.)
                    self.fr_volts = self.srs_comms.get_fr_volts()
                    self.ML.logData(pos, "Comb/TMC428/POS6")
                    # change serach direction?
                    if abs(self.fr_volts-self.fr_center) > abs(old_fr_volts-self.fr_center):
                        # if voltage is worse, try again to make sure
                        logging.info('Talking to comb.')
                        self.comb.open()
                        self.comb.write(msg)
                        time.sleep(0.1)
                        pos = self.comb.query(':TMC428:POS6?\n').strip()
                        self.comb.close()
                        logging.info('Success.')
                        time.sleep(1.)
                        self.fr_volts = self.srs_comms.get_fr_volts()
                        if abs(self.fr_volts-self.fr_center) > abs(old_fr_volts-self.fr_center):
                            # if still bad, move back to previous position, switch serach direction
                            self.fr_search_dir *= -1 # Switch directions
                            msg = ':TMC428:MOVE6 {:}\n'.format(self.fr_search_dir)
                            logging.info('Talking to comb.')
                            self.comb.open()
                            self.comb.write(msg)
                            time.sleep(0.1)
                            pos = self.comb.query(':TMC428:POS6?\n').strip()
                            self.comb.close()
                            logging.info('Success.')
                    #print "moved fR: Position {0:}, PID V {1:.2E}".format(pos, self.fr_volts)
                    return

# Error Handling --------------------------------------------------------------
        except DAQError as err:
            print datetime.now().strftime('%c')+' - '+'DAQ error: %s.'%err
            self.t.ClearTask()
            return


# =============================================================================
# Log LOCKED States ===========================================================
    def log_LOCKED_state(self, log_period):
        if (self.f0_state is self.F_LOCKED) and (self.fR_state is self.F_LOCKED):
            try:
                now = time.mktime(time.localtime())
                # f0 ----------------------------------------------------------
                last_log_f0 = ML.getMostRecentData("Lock_state/f0")
                if last_log_f0:
                    log_time_f0 = float(last_log_f0['_time'])
                else:
                    log_time_f0 = 0
                if ((now - log_time_f0) > log_period):
                    ML.logData(self.f0_state, "Lock_state/f0")
                # fR ----------------------------------------------------------
                last_log_fR = ML.getMostRecentData("Lock_state/fR")
                if last_log_fR:
                    log_time_fR = float(last_log_fR['_time'])
                else:
                    log_time_fR = 0
                if ((now - log_time_fR) > log_period):
                    ML.logData(self.fR_state, "Lock_state/fR")
                # Comb --------------------------------------------------------
                last_log_comb = ML.getMostRecentData("Lock_state/comb")
                if last_log_comb:
                    log_time_comb = float(last_log_comb['_time'])
                else:
                    log_time_comb = 0
                if ((now - log_time_comb) > log_period):
                    ML.logData(max([self.f0_state,self.fR_state]), "Lock_state/comb")

# Error Handling --------------------------------------------------------------
            except TypeError as err:
                print err
                #pass # if something doesn't work, just keep going


# =============================================================================
# Script ======================================================================
# Start MongoLogger
print datetime.now().strftime('%c')+' - '+'Connecting to Mongo Logger...'
ML = MongoLogger()

log_rate = 100
log_counter = 0
log_period = 60*30 # in seconds

f0 = 160e6 # 160 MHz
fR = 250e6 # 250 MHz

locker = servo_locker(f0, fR, ML) # lock frequency

restart = True
print datetime.now().strftime('%c')+' - '+"restarted \n \n"
while True:
    # Lock fR
    time.sleep(0.5)
    locker.move_fr()
    # Lock f0
    time.sleep(0.5)
    locker.move_f0()
    # Log PID Voltages
    if np.mod(log_counter, log_rate) == 0:
        ML.logData(locker.f0_volts, "Srs/f0")
        ML.logData(locker.fr_volts, "Srs/fr")
    log_counter += 1
    # Log LOCKED state
    locker.log_LOCKED_state(log_period)

