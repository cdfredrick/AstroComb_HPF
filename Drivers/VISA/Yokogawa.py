# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 07:26:32 2017

@authors: AJ Metcalf and Wesley Brand

Module: osa_driver

Requires:
    eventlog.py
    visa_objects.py

Public Function:
    plot_spectrum(array)

Public Class:
    OSA

with Public Methods:

    General:

    __init__(res_name, res_address)
    close()
    reset()

    Query:

    str = query_identity()
    save_n_graph_spectrum()
    dict = query_sweep_parameters() #nm

    Set:

    set_sweep_parameters(center_wl=1064,
                         span_wl=200, res_wl=2, sensitivity=1) #nm
    
    Manual:
    
    manual_spectrum_verify()

"""

# %% Modules ------------------------------------------------------------------

import time

#3rd party imports
import numpy as np
import pyvisa

#Astrocomb imports
from Drivers.VISA import VISAObjects as vo
from Drivers.Logging import ACExceptions as ac_excepts
from Drivers.Logging import EventLog as log


# %% OSA ----------------------------------------------------------------------
class OSA(vo.VISA):
    """Holds Yokogawa OSA's attributes and method library."""
#General Methods
    @log.log_this()
    def __init__(self, res_address):
        super(OSA, self).__init__(res_address)
        if self.resource is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create OSA instrument!', self.__init__)
        self.__set_command_format()
        self.active_trace()
    
    @log.log_this()
    def reset(self):
        """Stops current machine operation and returns OSA to default values"""
        self.write('*RST')
        self.__set_command_format()

#Query Methods
   
    @log.log_this()
    @vo._auto_connect
    def sweep_parameters(self):
        """Returns sweep parameters as a dictionary

        dictionary keys: center_wl, span_wl, res_wl, sensitivity
        wavelengths are in nm

        Sensitivites:
              0     |      1      |    2   |  3  |    4   |    5   |    6   |
        Normal Hold | Normal Auto | Normal | Mid | High 1 | High 2 | High 3 |
        """
        # Active Trace and Mode
        trace = self.query(":TRACe:ACTive?").strip()
        mode = self.query(':TRACe:ATTRibute:{:}?'.format(trace)).strip()
        mode = {0:"WRITE", 1:"FIX", 2:"MAX HOLD", 3:"MIN HOLD", 4:"ROLL AVG", 5:"CALC"}[int(mode)]
        avg_cnt = int(self.query(":TRACe:ATTRibute:RAVG?").strip())
        if (mode in ["WRITE", "FIX", "MAX HOLD", "MIN HOLD", "CALC"]):
            avg_cnt = 1
        t_list_keys = ["active_trace", "trace_mode", "avg_count"]
        t_list_values = [trace, mode, avg_cnt]
        trace_dict = {key:value for (key, value) in zip(t_list_keys, t_list_values)}
        # Wavelength
        start_wvl = float(self.query(":SENSe:WAVelength:STARt?").strip())*1e9
        stop_wvl = float(self.query(":SENSe:WAVelength:STOP?").strip())*1e9
        wvl_res = float(self.query(":SENSe:BANDwidth:RESolution?").strip())*1e9
        samp_cnt = int(self.query(":SENSe:SWEep:POINts?").strip())
        t_list_keys = ["start", "stop", "resolution", "points"]
        t_list_values = [start_wvl, stop_wvl, wvl_res, samp_cnt]
        wvl_dict = {key:value for (key, value) in zip(t_list_keys, t_list_values)}
        # Level
        ref_lvl = self.query(":DISPlay:WINDow:TRACe:Y1:SCALe:RLEVel?").strip()
        level_unit = self.query(":DISPlay:WINDow:TRACe:Y1:SCALe:UNIT?").strip()
        level_unit = {0:'dBm',1:'W',2:'dBm',3:'W'}[int(level_unit)]
        sens = self.query(":SENSe:SENSe?").strip()
        sens = {0:'NORMAL HOLD',1:'NORMAL AUTO',2:'MID',3:'HIGH1',4:'HIGH2',5:'HIGH3',6:'NORMAL'}[int(sens)]
        chopper = self.query(":SENSe:CHOPper?").strip()
        chopper = {0:'OFF',2:'SWITCH'}[int(chopper)]
        t_list_keys = ["ref_level", "level_unit", "sensitivity", "chopper"]
        t_list_values = [ref_lvl, level_unit, sens, chopper]
        level_dict = {key:value for (key, value) in zip(t_list_keys, t_list_values)}
        # Return Values
        t_list_keys = ['trace','wavelength','level']
        t_list_values = [trace_dict, wvl_dict, level_dict]
        return {key:value for (key, value) in zip(t_list_keys, t_list_values)}

    @log.log_this()
    @vo._auto_connect
    def spectrum(self, active_trace=None):
        """Sweepss OSA's spectrum"""
        if (active_trace!=None):
            self.active_trace(set_trace=active_trace)
        y_trace = self.query_list(':TRAC:DATA:Y? {:}'.format(self.act_trace))
        x_trace = self.query_list(':TRAC:DATA:X? {:}'.format(self.act_trace))
        x_trace = (np.array(x_trace)*1e9).tolist()
        data = {'x':x_trace ,'y':y_trace}
        return data

    @vo._auto_connect
    def get_new_single(self, active_trace=None, get_parameters=True):
    # Active Trace
        if (active_trace!=None):
            self.active_trace(set_trace=active_trace)
    # Prepare OSA
        if (self.sweep_mode() != 'SING'):
            self.sweep_mode('SING')
        time.sleep(.05)
        self.write(':ABORt')
        time.sleep(.05)
        self.write('*WAI')
        time.sleep(.05)
        wait_for_setup = True
        while wait_for_setup:
            time.sleep(.05)
            try:
                wait_for_setup = not(int(self.query('*OPC?').strip()))
            except pyvisa.VisaIOError as visa_err:
                if (visa_err.error_code == -1073807339): #timeout error
                    pass
                else:
                    raise visa_err
    # Initiate Sweep
        self.write(':INITiate:IMMediate')
        time.sleep(.05)
    # Wait for sweep to finish
        wait_for_sweep = True
        while wait_for_sweep:
            time.sleep(.05)
            try:
                wait_for_sweep = not(int(self.query('*OPC?').strip()))
            except pyvisa.VisaIOError as visa_err:
                if (visa_err.error_code == -1073807339): #timeout error
                    pass
                else:
                    raise visa_err
    # Get Data
        data = self.spectrum()
    # Get Parameters
        if (get_parameters == True):
            params = self.sweep_parameters()
        else:
            params = {}
    # Return
        return {'data':data, 'params':params}
    
    def initiate_sweep(self):
        self.write(':INITiate:IMMediate')
    
#Set Methods
    @vo._auto_connect
    def wvl_range(self, set_range=None):
        if (set_range==None):
            start_wvl = float(self.query(":SENSe:WAVelength:STARt?").strip())*1e9
            stop_wvl = float(self.query(":SENSe:WAVelength:STOP?").strip())*1e9
            return {'start':start_wvl, 'stop':stop_wvl}
        else:
            cmd_str = "SENSe:WAVelength:STARt {:}NM; STOP {:}NM".format(set_range['start'],set_range['stop'])
            self.write(cmd_str)
    
    def resolution(self, set_res=None):
        ''' 2NM, 1NM, 0.5NM, 0.2NM, 0.1NM, 0.05NM, 0.02NM
        '''
        if (set_res == None):
            res = float(self.query(':SENSE:BANDWIDTH?').strip())*1e9
            return res
        else:
            self.write(':SENSE:BANDWIDTH:RESOLUTION {:.2f}NM'.format(set_res))
    
    @vo._auto_connect
    def sensitivity(self, set_sens=None):
        '''
        set_sens={'sense':<sensitivity>, 'chop':<chopper action>}
        
        NHLD = NORMAL HOLD
        NAUT = NORMAL AUTO
        NORM = NORMAL
        MID = MID
        HIGH1 = HIGH1 
        HIGH2 = HIGH2
        HIGH3 = HIGH3
        '''
        if (set_sens == None):
            sens = self.query(":SENSe:SENSe?").strip()
            sens = {0:'NHLD',1:'NAUT',2:'MID',3:'HIGH1',4:'HIGH2',5:'HIGH3',6:'NORM'}[int(sens)]
            chopper = self.query(":SENSe:CHOPper?").strip()
            chopper = {0:'OFF',2:'SWITCH'}[int(chopper)]
            return {'sense':sens, 'chop':chopper}
        else:
            if (set_sens['sense'] in ['NHLD', 'NAUT', 'NORM', 'MID', 'HIGH1', 'HIGH2', 'HIGH3']):
                self.write(":SENSe:SENSe {:}".format(set_sens['sense']))
            else:
                raise Exception('Unrecognized sensitivity setting {:}'.format(set_sens['sense']))
            if (set_sens['chop'] in ['OFF', 'SWITCH']):
                self.write(":SENSe:CHOPper {:}".format(set_sens['chop']))
            else:
                raise Exception('Unrecognized chopper setting {:}'.format(set_sens['chop']))

    def sweep_mode(self, set_mode=None):
        '''
        SINGle = SINGLE sweep mode
        REPeat = REPEAT sweep mode
        AUTO = AUTO sweep mode
        SEGMent = SEGMENT
        Response    1 = SINGle
                    2 = REPeat
                    3 = AUTO
                    4 = SEGMent
        '''
        if (set_mode == None):
            mode = self.query(":INITiate:SMODe?").strip()
            mode = {1:'SING',2:'REP',3:'AUTO',4:'SEGM'}[int(mode)]
            return mode
        else:
            if set_mode in ['SING','REP','AUTO','SEGM']:
                self.write(":INITiate:SMODe {:}".format(set_mode))
            else:
                raise Exception('Unrecognized sweep mode {:}'.format(set_mode))
    
    def active_trace(self, set_trace=None):
        if (set_trace == None):
            trace = self.query(':TRACe:ACTive?').strip()
            self.act_trace = trace
            return trace
        else:
            if set_trace in ['TRA', 'TRB', 'TRC', 'TRD', 'TRE', 'TRF', 'TRG']:
                self.write(':TRACE:ACTIVE {:}'.format(set_trace))
            else:
                raise Exception('Unrecognized trace {:}'.format(set_trace))
    
    @vo._auto_connect
    def trace_type(self, set_type=None, active_trace=None):
        '''
        WRITe = WRITE
        FIX = FIX
        MAX = MAX HOLD
        MIN = MIN HOLD
        RAVG = ROLL AVG
        CALC = CALC
        Response    0 = WRITe
                    1 = FIX
                    2 = MAX
                    3 = MIN
                    4 = RAVG
                    5 = CALC
        '''
        if (active_trace!=None):
            self.active_trace(set_trace=active_trace)
        if (set_type == None):
            trace = self.query(':TRACE:ATTRIBUTE?').strip()
            trace = {0:'WRIT',1:'FIX',2:'MAX',3:'MIN',4:'RAVG',5:'CALC'}[int(trace)]
            if (trace == 'RAVG'):
                avg_cnt = int(self.query(':TRACe:ATTRibute:RAVG?').strip())
            else:
                avg_cnt = 1
            return {'mode':trace, 'avg':avg_cnt}
        else:
            if set_type['mode'] in ['WRIT','FIX','MAX','MIN','RAVG','CALC']:
                self.write(':TRACE:ATTRIBUTE {:}'.format(set_type['mode']))
                if ((set_type['mode'] == 'RAVG') and ('avg' in set_type)):
                    self.write(':TRACe:ATTRibute:RAVG {:}'.format(int(set_type['avg'])))
            else:
                raise Exception('Unrecognized trace type {:}'.format(set_type))
    
    def level_scale(self, set_mode=None):
        '''
        LOG = LOG scale
        LIN = Linear scale
        Response 0 = LOGarithmic, 1 = LINear
        '''
        if (set_mode == None):
            mode = self.query(':DISPlay:WINDow:TRACe:Y1:SCALe:SPACing?').strip()
            mode = {0:'LOG', 1:'LIN'}[int(mode)]
            return mode
        else:
            if (set_mode in ['LOG', 'LIN']):
                self.write(':DISPLAY:TRACE:Y1:SPACING {:}'.format(set_mode))
            else:
                raise Exception('Unrecognized level scale {:}'.format(set_mode))
    
    @vo._auto_connect
    def fix_all(self, fix=None):
        if (fix == None):
            fixed = True
            for trace in ['TRA', 'TRB', 'TRC', 'TRD', 'TRE', 'TRF', 'TRG']:
                trace_type = self.trace_type(active_trace=trace)
                fixed *= (trace_type['mode'] == 'FIX')
            return bool(fixed)
        elif (fix == True):
            for trace in ['TRA', 'TRB', 'TRC', 'TRD', 'TRE', 'TRF', 'TRG']:
                self.trace_type(set_type={'mode':'FIX'}, active_trace=trace)
    
    @log.log_this()
    def __set_command_format(self):
        """Sets the OSA's formatting to AQ6370 style, should always be 1"""
        self.write('CFORM1')
