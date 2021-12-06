"""
XEM6010 Phase-lock box GUI, frequency counter display, interfaces to the dual-mode (triangular or rectangular averaging) counter
by JD Deschenes, October 2013

"""
from __future__ import print_function

import sys
import time
import datetime
from PyQt5 import QtGui, Qt, QtCore
#import PyQt5.Qwt5 as Qwt
import numpy as np
import tables as tb
import MongoDB
import threading

import math


import os
import errno
import sys

from user_friendly_QLineEdit import user_friendly_QLineEdit

#from SuperLaserLand_JD2 import SuperLaserLand_JD2

# To communicate with the temperature controller process
import AsyncSocketComms

import weakref

# stuff for Python 3 port
import pyqtgraph as pg


def get_lap(time_interval):
    '''Use this function to get an incrementing integer linked to the system
    clock.
    '''
    return int(time.time() // time_interval)

def update_buffer(buffer, new_data, length):
    '''Use this function to update a 1D rolling buffer, as typically found in
    the monitor variables.
    '''
    length = int(abs(length))
    buffer = np.append(buffer, new_data)
    if buffer.size > length:
        buffer = buffer[-length:]
    return buffer

class FreqErrorWindowWithTempControlV2(QtGui.QWidget):

        
    def __init__(self, sl, strTitle, output_number=0, strNameTemplate='', custom_style_sheet='', port_number=0, xem_gui_mainwindow=0):
        super(FreqErrorWindowWithTempControlV2, self).__init__()

        self.strTitle = strTitle
        self.strNameTemplate = strNameTemplate
        self.sl = weakref.proxy(sl)
        self.output_number = output_number
        self.setObjectName('MainWindow')
        self.setStyleSheet(custom_style_sheet)
        if xem_gui_mainwindow:
            self.xem_gui_mainwindow = weakref.proxy(xem_gui_mainwindow)
        else:
            self.xem_gui_mainwindow = None
        
        self.port_number = port_number
        #print('before openTCPConnection')
        self.openTCPConnection()
        #print('after openTCPConnection')
        if self.client is None:
            print('Warning: no connection to temp control')
            
        self.last_update_freq = time.clock()
        self.initUI()
        self.qchk_triangular.blockSignals(True)
        self.qchk_triangular.setChecked(self.sl.bTriangularAveraging)
        self.qchk_triangular.blockSignals(False)
        self.chkTriangular_checked()
        
        self.openOutputFiles()
        self.initSL()
        
        self.recovery_history = np.array([])
        self.recovery_session = 0
        self.bReturn_full_DAC_output = False


#    def __del__(self):
#        # Close data files:
#        if hasattr(self, 'file_output1'):
#            self.file_output1.close()
#        if hasattr(self, 'file_output2'):
#            self.file_output2.close()

    def openTCPConnection(self):
        start_time = time.clock()
        if self.port_number != 0:
            try:
                time_before = time.clock()
                self.client = AsyncSocketComms.AsyncSocketClient(self.port_number)
                self.last_update = float("-inf")
                self.setpoint_change = 0.
                print('Connection to temp control established.')
            except:
                time_after = time.clock()
                print('openTCPConnection(): Time taken by AsyncSocketComms.AsyncSocketClient(): %f sec' % (time_after-time_before))
                self.client = None
                self.last_update = time.clock()
                self.setpoint_change = 0.
        else:
            self.client = None
        end_time = time.clock()
        print('openTCPConnection(): Time taken: %f sec' % (end_time-start_time))

    def initBuffer(self):
    # Initialize data buffers for plotting
#        print('initBuffer')
        #self.gate_time_counter = self.sl.N_CYCLES_GATE_TIME/self.sl.fs
        self.DAC_history = np.array([])
        self.DAC_mean_history = np.array([])
        self.DAC_thrsh_history = np.array([])
        self.DAC_low_history = np.array([])
        self.DAC_high_history = np.array([])
        self.time_history_dacs = np.array([])

        self.freq_history = np.array([])
        self.time_history_counters = np.array([])
            
    def openOutputFiles(self):
        self.mongo_client = MongoDB.MongoClient()
        self.db = {}
        self.STATE_DBs = ['mll_f0/state', 'cw_laser/state_frequency']
        self.MONITOR_DBs = ['mll_f0/freq_err', 'mll_f0/dac_output', 'mll_f0/dac_limits',
                           'cw_laser/freq_err', 'cw_laser/dac_output', 'cw_laser/dac_limits'] 
        self.MASTER_DBs = self.STATE_DBs + self.MONITOR_DBs

        self.lock = {}
        for database in self.MASTER_DBs:
            self.lock[database] = threading.Lock()
            self.db[database] = MongoDB.DatabaseMaster(self.mongo_client, database, capped_collection_size=int(0.5/0.2*1e6))
        
        # Default State Settings
        self.STATE_SETTINGS = {
                'mll_f0/state':{
                        'state':'lock',
                        'prerequisites':{
                                'critical':True,
                                'necessary':True,
                                'optional':True},
                        'compliance':False,
                        'desired_state':'lock',
                        'initialized':True,
                        'heartbeat':datetime.datetime.utcnow()},
                'cw_laser/state_frequency':{
                        'state':'lock',
                        'prerequisites':{
                                'critical':True,
                                'necessary':True,
                                'optional':True},
                        'compliance':False,
                        'desired_state':'lock',
                        'initialized':True,
                        'heartbeat':datetime.datetime.utcnow()}}
        self.SETTINGS = self.STATE_SETTINGS
        
        # Local Settings
        self.local_settings = {}
        for database in self.SETTINGS:
            with self.lock[database]:
                self.local_settings[database] = self.db[database].read_buffer()
            # Check all SETTINGS
                db_initialized = True
                for setting in self.SETTINGS[database]:
                # Check that there is anything at all
                    if (self.local_settings[database]==None):
                        self.local_settings[database]={}
                # Check that the key exists in the database
                    if not(setting in self.local_settings[database]):
                        db_initialized = False
                        self.local_settings[database][setting] = self.SETTINGS[database][setting]
                if not(db_initialized):
                # Update the database values if necessary
                    self.db[database].write_record_and_buffer(self.local_settings[database])
            
        # Initialize Record Timers and Data Arrays
        self.record_timer = {}
        self.record_interval = 10 #seconds
        self.array = {}
        for monitor_db in self.MONITOR_DBs:
            self.record_timer[monitor_db] = get_lap(self.record_interval)
            self.array[monitor_db] = np.array([])
        
        monitor_db = 'mll_f0/dac_limits'
        with self.lock[monitor_db]:
            # Append to the record array
            self.array[monitor_db+'min'] = np.array([])
            self.array[monitor_db+'max'] = np.array([])
        
        monitor_db = 'cw_laser/dac_limits'
        with self.lock[monitor_db]:
            # Append to the record array
            self.array[monitor_db+'min'] = np.array([])
            self.array[monitor_db+'max'] = np.array([])
        
        
    def initSL(self):
        
#        print('initSL')
        self.initBuffer()
        # Start timer which grabs data
        self.timerID = self.startTimer(200)
        
    def chkTriangular_checked(self):
        if self.qchk_triangular.isChecked():
            self.sl.setCounterMode(True)
        else:
            self.sl.setCounterMode(False)
        print('Updating counter mode')

    def freq_plot_limits_edited(self):
        self.freq_ymax = float(self.qedit_ymax.text())
        self.freq_ymin = float(self.qedit_ymin.text())

    def rec_thresh_edited(self):
        self.recovery_thrsh_std = float(self.qedit_rec_thresh.text())

    def hist_buff_edited(self):
        self.hist_buff_length = float(self.qedit_history.text())

    def chkLimit_DAC_checked(self):
        self.bReturn_full_DAC_output = not(self.qchk_limit_DAC.isChecked())

    def initUI(self):
        
        # Put everything in a groupbox so we can change the border of the window without it looking too obnoxious:
        self.qgroupbox_freq = Qt.QGroupBox('')
        self.qgroupbox_freq.setAutoFillBackground(True)

        # Add a QwtPlot to the UI:
        #self.qplt_freq = Qwt.QwtPlot()
        self.qplt_freq = pg.PlotWidget()
        self.qplt_freq.setTitle('Lock #%d Frequency error' % (self.output_number))
        #self.qplt_freq.setCanvasBackground(Qt.Qt.white)
        
        # plotgrid = Qwt.QwtPlotGrid()
        # plotgrid.setMajPen(Qt.QPen(Qt.Qt.black, 0, Qt.Qt.DotLine));
        # plotgrid.setMinPen(Qt.QPen(Qt.Qt.black, 0, Qt.Qt.DotLine));
        # plotgrid.attach(self.qplt_freq);
        self.qplt_freq.showGrid(x=True, y=True)
        
        # Add another QwtPlot to the UI:
        self.qplt_dac = pg.PlotWidget()
        self.qplt_dac.setTitle('Lock #%d DAC outputs' % (self.output_number))
        #self.qplt_dac.setCanvasBackground(Qt.Qt.white)
        self.qplt_dac.setYRange(0, 1)
        
        # plotgrid = Qwt.QwtPlotGrid()
        # plotgrid.setMajPen(Qt.QPen(Qt.Qt.black, 0, Qt.Qt.DotLine));
        # plotgrid.setMinPen(Qt.QPen(Qt.Qt.black, 0, Qt.Qt.DotLine));
        # plotgrid.attach(self.qplt_dac);
        self.qplt_dac.showGrid(x=True, y=True)
        
        # Create the curve in the plot
        self.curve_freq_error = self.qplt_freq.getPlotItem().plot(pen='b')
        #self.curve_freq_error.attach(self.qplt_freq)
        #self.curve_freq_error.setPen(Qt.QPen(Qt.Qt.blue))
        
        # Create the curve in the plot
        self.curve_dac = self.qplt_dac.getPlotItem().plot(pen='b')
        self.curve_dac_uthrsh = self.qplt_dac.getPlotItem().plot(connect='finite', pen=pg.mkPen(0.1, style=QtCore.Qt.DotLine))
        self.curve_dac_lthrsh = self.qplt_dac.getPlotItem().plot(connect='finite', pen=pg.mkPen(0.1, style=QtCore.Qt.DotLine))
        self.curve_dac_ulim = self.qplt_dac.getPlotItem().plot(connect='finite', pen=pg.mkPen(0.25, style=QtCore.Qt.DashLine))
        self.curve_dac_llim = self.qplt_dac.getPlotItem().plot(connect='finite', pen=pg.mkPen(0.25, style=QtCore.Qt.DashLine))
                    
        
        # Create widgets to specify buffer length and clear buffer:
        self.qbtn_reset = Qt.QPushButton('Clear display')
        self.qbtn_reset.clicked.connect(self.initBuffer)
        self.qlabel_history = Qt.QLabel('Display [s]')
        self.qedit_history = user_friendly_QLineEdit('600')
        self.hist_buff_length = 600
        self.qedit_history.setMaximumWidth(40)
        self.qedit_history.editingFinished.connect(self.hist_buff_edited)

        self.qchk_fullscale_freq = Qt.QCheckBox('Fullscale Freq Graph')
        self.qchk_fullscale_freq.setChecked(True)
        
        self.qchk_fullscale_dac = Qt.QCheckBox('Fullscale DAC Graph')
        self.qchk_fullscale_dac.setChecked(True)
        
        self.qchk_triangular = Qt.QCheckBox('Triangular averaging')
        self.qchk_triangular.setChecked(True)
        self.qchk_triangular.clicked.connect(self.chkTriangular_checked)
        
        # Controls for the vertical scale of the frequency graph:
        print(type(self.sl.fs))
        print(self.sl.fs)
        self.qedit_ymin = user_friendly_QLineEdit(self.SI_scale(-self.sl.fs/4., sig_figs=4))
        self.qedit_ymax = user_friendly_QLineEdit(self.SI_scale(self.sl.fs/4., sig_figs=4))
        self.freq_ymin = -self.sl.fs/4.
        self.freq_ymax = self.sl.fs/4.
        self.qedit_ymin.setMaximumWidth(80)
        self.qedit_ymax.setMaximumWidth(80)
        self.qlabel_ymin = Qt.QLabel('y min [Hz]')
        self.qlabel_ymax = Qt.QLabel('y max [Hz]')
        self.qedit_ymin.editingFinished.connect(self.freq_plot_limits_edited)
        self.qedit_ymax.editingFinished.connect(self.freq_plot_limits_edited)

        # Controls for Auto Recovery
        self.qchk_autorecover = Qt.QCheckBox('Auto Recover')
        self.qchk_autorecover.setChecked(False)
        self.qlabel_rec_thresh = Qt.QLabel('Recovery Threshold')
        self.qedit_rec_thresh = user_friendly_QLineEdit('5')
        self.recovery_thrsh_std = 5.
        self.qedit_rec_thresh.editingFinished.connect(self.rec_thresh_edited)
        self.qedit_rec_thresh.setMaximumWidth(40)
        self.qchk_limit_DAC = Qt.QCheckBox('Limit DAC Output')
        self.qchk_limit_DAC.setChecked(False)
        self.qchk_limit_DAC.clicked.connect(self.chkLimit_DAC_checked)

        # Put the two graphs into a vertical box layout, so that they share all the vertical space equally:
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.qplt_freq)
        vbox.addWidget(self.qplt_dac)
        
        # Put all the widgets into a grid layout
        grid = QtGui.QGridLayout()
        grid.addLayout(vbox,                                0, 3, 16, 1)
        
        grid.addWidget(self.qbtn_reset,                     0, 0, 1, 3)
        grid.addWidget(self.qlabel_history,                 1, 0, 1, 2)
        grid.addWidget(self.qedit_history,                  1, 2)
        grid.addWidget(self.qchk_triangular,                2, 0, 1, 3)
        grid.addWidget(self.qchk_fullscale_freq,            3, 0, 1, 3)
        grid.addWidget(self.qlabel_ymin,                    4, 0, 1, 2)
        grid.addWidget(self.qedit_ymin,                     4, 1, 1, 2, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.qlabel_ymax,                    5, 0, 1, 2)
        grid.addWidget(self.qedit_ymax,                     5, 1, 1, 2, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.qchk_fullscale_dac,             6, 0, 1, 3)
        

        #FEATURE
        grid.addWidget(self.qchk_autorecover,           	  7, 0, 1, 3)
        grid.addWidget(self.qlabel_rec_thresh,              8, 0, 1, 2)
        grid.addWidget(self.qedit_rec_thresh,               8, 2)
        grid.addWidget(self.qchk_limit_DAC,                 9, 1, 1, 2)

        
        if self.client or True:
            # we need to add the controls which implement the temperature control loop:
            self.qlabel_threshold_step = Qt.QLabel('Threshold for step:')
            self.qedit_threshold_step = Qt.QLineEdit('0.2')
            self.qedit_threshold_step.setMaximumWidth(40)
            
            
            self.qlabel_threshold_disable = Qt.QLabel('Threshold for disable:')
            self.qedit_threshold_disable = Qt.QLineEdit('0.05')
            self.qedit_threshold_disable.setMaximumWidth(40)
            
            self.qlabel_step_size = Qt.QLabel('Step size [deg C]:')
            self.qedit_step_size = Qt.QLineEdit('0.05')
            self.qedit_step_size.setMaximumWidth(40)
            
            self.qlabel_step_delay = Qt.QLabel('Step delay [s]:')
            self.qedit_step_delay = Qt.QLineEdit('120')
            self.qedit_step_delay.setMaximumWidth(40)
            
            self.qchk_temp_control = Qt.QCheckBox('Temperature control')
            self.qchk_temp_control.setChecked(False)
            
            self.qchk_clear_temp_control = Qt.QCheckBox('Clear Temperature control')
            self.qchk_clear_temp_control.setChecked(False)
            
            #FEATURE
            #grid.addWidget(self.qlabel_threshold_step,          8, 0)
            #grid.addWidget(self.qedit_threshold_step,           8, 1)
            #grid.addWidget(self.qlabel_threshold_disable,       9, 0)
            #grid.addWidget(self.qedit_threshold_disable,        9, 1)
            #grid.addWidget(self.qlabel_step_size,               10, 0)
            #grid.addWidget(self.qedit_step_size,                11, 1)
            #
            #grid.addWidget(self.qlabel_step_delay,              12, 0)
            #grid.addWidget(self.qedit_step_delay,               13, 1)
            #
            #grid.addWidget(self.qchk_temp_control,              14, 0, 1, 2)
            #grid.addWidget(self.qchk_clear_temp_control,        15, 0, 1, 2)
            
            
            grid.addWidget(Qt.QLabel(''),                       16, 0, 1, 2)
            grid.setRowStretch(15, 1)
            grid.setColumnStretch(2, 1)
        else:
            # no controls for the temp control loop
        
        
            grid.addWidget(Qt.QLabel(''),                       8, 0, 1, 2)
            grid.setRowStretch(8, 1)
            grid.setColumnStretch(2, 1)
        
        
        self.qgroupbox_freq.setLayout(grid)

        vbox2 = Qt.QVBoxLayout()
        vbox2.addWidget(self.qgroupbox_freq)
        self.setLayout(vbox2)
#        self.setLayout(vbox)

        # Adjust the size and position of the window
        # self.resize(800, 480)
        self.center()
        self.setWindowTitle(self.strTitle)    
        #self.show()
        
    def center(self):
        
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
#        print()
#        5435sdfsf
#        qr.moveCenter(cp)
#        self.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(800+100, 50))
        if self.output_number == 0:
            self.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(985, 10))
        else:
            self.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(985, 10+450+80))
            
    def timerEvent(self, e):
        
#        print('timerEvent, timerID = %d' % self.timerID)
        self.qchk_triangular.blockSignals(True)
        self.qchk_triangular.setChecked(self.sl.bTriangularAveraging)
        self.qchk_triangular.blockSignals(False)
        
        self.displayFreqCounter()
        
        return
        
    def runTempControlLoop(self, current_time, current_output):
        # Simple algorithm:
        # If the dac2 output crosses a threshold, we send a step to the temperature setpoint to nudge it in the right direction.
        # We then wait for a certain delay before we re-do a step
#        print('runTempControlLoop(): current_time = %f, current_output = %f' % (current_time, current_output))
    
        # Read off the values from the UI:
        try:
            step_delay = float(self.qedit_step_delay.text())
        except:
            step_delay = 0
            
        try:
            threshold_step = float(self.qedit_threshold_step.text())
        except:
            threshold_step = 0.2
            
        try:
            threshold_disable = float(self.qedit_threshold_disable.text())
        except:
            threshold_disable = 0.05
            
        try:
            step_size = float(self.qedit_step_size.text())
        except:
            step_size = 0.01
    
        if self.qchk_temp_control.isChecked() == True:
            if self.client:
#                print('Temp control established, client connected.')
                
    #            print('last_update = %f, step_delay = %f, current_time = %f' % (self.last_update, step_delay, current_time))
                if self.last_update + step_delay <= current_time:
                    # Compare the output to two thresholds:
                    # first threshold means to disable the temperature control loop completely, because the low PZT has railed.
                    if current_output < threshold_disable or current_output > 1-threshold_disable:
                        # disable temp control loop:
                        self.qchk_temp_control.setChecked(False)
                        strOfTime = time.strftime("%m_%d_%Y_%H_%M_%S_")
                        print('Disabled temp control because the PZT is too close to the rail and thus has most likely railed already. time = %s' % strOfTime)
                        return
                    
                    # Second threshold means to send a step (in the right direction)
                    if current_output < threshold_step or current_output > 1-threshold_step:
                        if current_output < threshold_step:
                            step_sign = -1
                        else:
                            step_sign = 1
                            
                       
                        self.setpoint_change = self.setpoint_change + step_sign*step_size
                        # Implement limits:
                        if self.setpoint_change > 10.:
                            self.setpoint_change = 10.
                        elif self.setpoint_change < -10.:
                            self.setpoint_change = -10.
                        
                        self.last_update = time.clock()

                        try:                        
                            print('Sending a new setpoint: %f degrees' % self.setpoint_change)
                            self.client.send_text('%f\n' % self.setpoint_change)
                        except:
                            e = sys.exc_info()[0]
                            # If we get here, this probably means that the TCP connection to the temperature controller was lost.
                            print('Exception occurred sending the new temperature setpoint.')
                            print(str(e))
                            self.client = None
                            
#                            raise
                        return
                    
                else:
                    # the steps are inhibited because we made one too recently
#                    print('Steps inhibited')
                    return
            
                #clear temperature control integrator if temp control is turned off        
                if self.qchk_clear_temp_control.isChecked() == True:
                    self.setpoint_change = 0.
                    try:
                        print('Clearing Temperature Control')
                        self.client.send_text('%f\n' % self.setpoint_change)
                        self.qchk_clear_temp_control.setChecked(False)
                    except:
                        e = sys.exc_info()[0]
                        # If we get here, this probably means that the TCP connection to the temperature controller was lost.
                        print('Exception occurred sending the new temperature setpoint.')
                        print(str(e))
                        self.client = None
                else:
                    return
            else:   # self.client == None
                # Try to open TCP connection to the temperature controller code
                print('Trying to establish connection to the temperature controller')
                self.openTCPConnection()
#        else:
#            print('Temp control disactivated.')
                    

    def runAutoRecover(self, current_dac, current_time, timestamp):
        if (self.output_number == 0):
        # 'mll_f0/freq_err' ---------------------
            state_db = 'mll_f0/state'
        elif (self.output_number == 1):
        # 'cw_laser/freq_err' ---------------------
            state_db = 'cw_laser/state_frequency'
        # Try to read the lock state
        try:
            bLock = self.xem_gui_mainwindow.qchk_lock.isChecked()
        except:
            print('failed to read lock state')
            bLock = False

        if bLock and self.qchk_autorecover.isChecked():
        # If the lock and auto recovery are enabled
            if self.recovery_history.size == 0:
            # Initialize timestamps
                self.recovery_last_timestamp = current_time
                self.recovery_lost_timestamp = current_time
                self.recovery_gained_timestamp = current_time
                self.bRecord_unlock = False
            # Update state variable
                with self.lock[state_db]:
                    if not(self.local_settings[state_db]['compliance']):
                        self.local_settings[state_db]['compliance'] = True
                        self.db[state_db].write_record_and_buffer(self.local_settings[state_db])
            # Append to the DAC history if the sample size is too small
                self.recovery_history = np.append(self.recovery_history, current_dac)
                # Return NANs for plotting (mean, recovery threshold, DAC threshold)
                return (np.nan, np.nan, np.nan, np.nan)
            elif self.recovery_history.size < 50:
            # Append to the DAC history if the sample size is too small
                self.recovery_history = np.append(self.recovery_history, current_dac)
            # Update timestamps
                self.recovery_last_timestamp = current_time
                # Return NANs for plotting (mean, recovery threshold, DAC threshold)
                return (np.nan, np.nan, np.nan, np.nan)
            else:
            # Calculate the historical mean and standard deviation
                dac_std_threshold = self.recovery_thrsh_std
                dac_range_threshold = 0.1
                output_data = self.recovery_history
                dac_avg = np.mean(output_data)
                dac_avg_slope = np.mean(np.diff(output_data))/(len(output_data)-1)
                dac_expected = dac_avg + dac_avg_slope*len(output_data)/2
                dac_std = np.std(output_data - dac_avg_slope*np.arange(len(output_data)))
                new_upper_limit = int(round(dac_expected + (dac_std_threshold*dac_std)/(1-2*dac_range_threshold)))
                new_lower_limit = int(round(dac_expected - (dac_std_threshold*dac_std)/(1-2*dac_range_threshold)))
                
            # Check for sudden changes
                if np.abs(current_dac - dac_expected) > dac_std_threshold*dac_std:
                # If the current DAC value is out of bounds, relock to the average
                    self.sl.set_dac_offset(self.output_number, int(round(dac_expected)))
                    self.xem_gui_mainwindow.qloop_filters[self.output_number].qchk_lock.setChecked(False)
                    self.xem_gui_mainwindow.qloop_filters[self.output_number].updateFilterSettings()
                    self.xem_gui_mainwindow.qloop_filters[self.output_number].qchk_lock.setChecked(True)
                    self.xem_gui_mainwindow.qloop_filters[self.output_number].updateFilterSettings()
                    print("{}: channel {} lost lock".format(time.strftime('%c'),self.output_number))
                # Update the timestamps
                    self.recovery_lost_timestamp = self.recovery_last_timestamp
                    self.recovery_gained_timestamp = time.time()
                    self.recovery_gained_datetime = datetime.datetime.utcnow()
                    self.bRecord_unlock = True
                # Update State Variable
                    with self.lock[state_db]:
                        if (self.local_settings[state_db]['compliance']):
                            self.local_settings[state_db]['compliance'] = False
                            self.db[state_db].write_record_and_buffer(self.local_settings[state_db], timestamp=timestamp)
                # Update the UI
                    dac_in_slider_units = self.xem_gui_mainwindow.dac_offset_in_slider_units(int(round(dac_expected)), self.output_number)
                    self.xem_gui_mainwindow.q_dac_offset[self.output_number].blockSignals(True)
                    self.xem_gui_mainwindow.q_dac_offset[self.output_number].setValue(dac_in_slider_units)
                    self.xem_gui_mainwindow.q_dac_offset[self.output_number].blockSignals(False)
                elif current_time - self.recovery_gained_timestamp > 10.:
                # If the current DAC value is locked and in bounds
                    if self.recovery_history.size < 500:
                    # Add it to the DAC history, appending up to a certain size
                        self.recovery_history = np.append(self.recovery_history, current_dac)
                    else:
                    # Roll the values otherwise
                        self.recovery_history = np.append(self.recovery_history[1:],current_dac)
                    if self.bRecord_unlock:
                    # If available, record an unlock event
                        self.bRecord_unlock = False
                    # Update state variable
                        with self.lock[state_db]:
                            self.local_settings[state_db]['compliance'] = True
                            self.db[state_db].write_record_and_buffer(self.local_settings[state_db], timestamp=self.recovery_gained_datetime)
                # Update the timestamps
                    self.recovery_last_timestamp = current_time
            # Update DAC output limits
                if self.qchk_limit_DAC.isChecked():
                # If DAC output limits are enabled
                    self.sl.set_dac_limits(self.output_number, new_lower_limit, new_upper_limit)
                    dac_limit_low = self.sl.restricted_DACs_limit_low[self.output_number]
                    dac_limit_high = self.sl.restricted_DACs_limit_high[self.output_number]
                else:
                    if self.bReturn_full_DAC_output:
                    # Return the full output range if output limits are disabled
                        self.sl.set_dac_limits(self.output_number, self.sl.DACs_limit_low[self.output_number], self.sl.DACs_limit_high[self.output_number])
                        self.bReturn_full_DAC_output = False
                    dac_limit_low = np.nan
                    dac_limit_high = np.nan
            # Return the mean and thresholds for plotting
                return (int(round(dac_expected)), int(round(dac_std_threshold*dac_std)), dac_limit_low, dac_limit_high)
        else:
        # If lock or auto recovery are disabled
            if (self.recovery_history.size > 0) and self.qchk_limit_DAC:
            # If DAC output limits are enabled, return the full DAC output range if a auto recovery session ends
                self.sl.set_dac_limits(self.output_number, self.sl.DACs_limit_low[self.output_number], self.sl.DACs_limit_high[self.output_number])
        # Clear the accumulated DAC history
            self.recovery_history = np.array([])
        # Update State Variable
            with self.lock[state_db]:
                if (self.local_settings[state_db]['compliance']):
                    self.local_settings[state_db]['compliance'] = False
                    self.db[state_db].write_record_and_buffer(self.local_settings[state_db])
        # Return NANs for plotting (mean, recovery threshold, DAC thresholds)
            return (np.nan, np.nan, np.nan, np.nan)

    
    def displayFreqCounter(self):
#        (freq_counter_samples, time_axis, DAC0_output, DAC1_output, DAC2_output) = self.sl.read_zero_deadtime_freq_counter(self.output_number)
        try:
            (freq_counter_samples, time_axis, DAC0_output, DAC1_output, DAC2_output) = self.sl.read_dual_mode_counter(self.output_number)   
            # print (freq_counter_samples, time_axis, DAC0_output, DAC1_output, DAC2_output)
            channelName = ''
            if self.output_number == 0:
                channelName = 'CEO'
            if self.output_number == 1:
                channelName = 'Optical'
            timestamp = datetime.datetime.utcnow()
            new_record_lap = get_lap(self.record_interval)
        except:
            print('Exception occured reading counter data. disabling further updates.')
            self.killTimer(self.timerID)
            freq_counter_samples = 0
            time_axis = 0
            DAC0_output = 0
            DAC1_output = 0
            DAC2_output = 0
            
            raise
            
        try:
            if time_axis is not None:
                time_axis = np.mean(time_axis)
                if DAC0_output is not None and self.output_number is 0:
                    # Run auto recovery for DAC0
                    dac_mean, dac_thrsh, dac_low, dac_high = self.runAutoRecover(np.mean(DAC0_output), time_axis, timestamp)
                    dac_output = DAC0_output
                    # Scale to actual voltage:
                    dac_scale = float(self.sl.DACs_limit_high[0] - self.sl.DACs_limit_low[0])/2.
                    DAC0_output = DAC0_output/dac_scale
                    DAC0_low = dac_low/dac_scale
                    DAC0_high = dac_high/dac_scale
                    
                # 'mll_f0/dac_output' ---------------------
                    monitor_db = 'mll_f0/dac_output'
                    data = np.mean(DAC0_output)
                    with self.lock[monitor_db]:
                        # Append to the record array
                        self.array[monitor_db] = np.append(self.array[monitor_db], data)
                    self.db[monitor_db].write_buffer({'V':data}, timestamp=timestamp)
                    # Update record
                    if (new_record_lap > self.record_timer[monitor_db]):
                        # Record statistics ---------------------
                        self.db[monitor_db].write_record({
                                'V':self.array[monitor_db].mean(),
                                'std':self.array[monitor_db].std(),
                                'n':self.array[monitor_db].size},
                                timestamp=timestamp)
                        # Empty the array
                        with self.lock[monitor_db]:
                            self.array[monitor_db] = np.array([])
                        # Propogate lap numbers -----------------------------------------
                            self.record_timer[monitor_db] = new_record_lap
                # 'mll_f0/dac_limits' ---------------------
                    monitor_db = 'mll_f0/dac_limits'
                    data_min = np.mean(DAC0_low)
                    data_max = np.mean(DAC0_high)
                    with self.lock[monitor_db]:
                        # Append to the record array
                        self.array[monitor_db+'min'] = np.append(self.array[monitor_db+'min'], data_min)
                        self.array[monitor_db+'max'] = np.append(self.array[monitor_db+'max'], data_max)
                    self.db[monitor_db].write_buffer({'min_V':data_min,'max_V':data_max}, timestamp=timestamp)
                    # Update record
                    if (new_record_lap > self.record_timer[monitor_db]):
                        # Record statistics ---------------------
                        self.db[monitor_db].write_record({
                                'min_V':self.array[monitor_db+'min'].mean(),
                                'min_std':self.array[monitor_db+'min'].std(),
                                'min_n':self.array[monitor_db+'min'].size,
                                'max_V':self.array[monitor_db+'max'].mean(),
                                'max_std':self.array[monitor_db+'max'].std(),
                                'max_n':self.array[monitor_db+'max'].size},
                                timestamp=timestamp)
                        # Empty the array
                        with self.lock[monitor_db]:
                            self.array[monitor_db+'min'] = np.array([])
                            self.array[monitor_db+'max'] = np.array([])
                        # Propogate lap numbers -----------------------------------------
                            self.record_timer[monitor_db] = new_record_lap
                # Heartbeat -----------------------------------------
                    state_db = 'mll_f0/state'
                    with self.lock[state_db]:
                        self.local_settings[state_db]['heartbeat'] = datetime.datetime.utcnow()
                        self.db[state_db].write_buffer(self.local_settings[state_db])
                
                if DAC1_output is not None and self.output_number is 1:
                    # Run auto recovery for DAC1
                    dac_mean, dac_thrsh, dac_low, dac_high = self.runAutoRecover(np.mean(DAC1_output), time_axis, timestamp)
                    dac_output = DAC1_output
                    # Scale to actual voltage:
                    dac_scale = float(self.sl.DACs_limit_high[1] - self.sl.DACs_limit_low[1])/2.
                    DAC1_output = DAC1_output/dac_scale
                    DAC1_low = dac_low/dac_scale
                    DAC1_high = dac_high/dac_scale
                    # 'cw_laser/dac_output' ---------------------
                    monitor_db = 'cw_laser/dac_output'
                    data = np.mean(DAC1_output)
                    with self.lock[monitor_db]:
                        # Append to the record array
                        self.array[monitor_db] = np.append(self.array[monitor_db], data)
                    self.db[monitor_db].write_buffer({'V':data}, timestamp=timestamp)
                    # Update record
                    if (new_record_lap > self.record_timer[monitor_db]):
                        # Record statistics ---------------------
                        self.db[monitor_db].write_record({
                                'V':self.array[monitor_db].mean(),
                                'std':self.array[monitor_db].std(),
                                'n':self.array[monitor_db].size},
                                timestamp=timestamp)
                        # Empty the array
                        with self.lock[monitor_db]:
                            self.array[monitor_db] = np.array([])
                        # Propogate lap numbers -----------------------------------------
                            self.record_timer[monitor_db] = new_record_lap
                # 'cw_laser/dac_limits' ---------------------
                    monitor_db = 'cw_laser/dac_limits'
                    data_min = np.mean(DAC1_low)
                    data_max = np.mean(DAC1_high)
                    with self.lock[monitor_db]:
                        # Append to the record array
                        self.array[monitor_db+'min'] = np.append(self.array[monitor_db+'min'], data_min)
                        self.array[monitor_db+'max'] = np.append(self.array[monitor_db+'max'], data_max)
                    self.db[monitor_db].write_buffer({'min_V':data_min,'max_V':data_max}, timestamp=timestamp)
                    # Update record
                    if (new_record_lap > self.record_timer[monitor_db]):
                        # Record statistics ---------------------
                        self.db[monitor_db].write_record({
                                'min_V':self.array[monitor_db+'min'].mean(),
                                'min_std':self.array[monitor_db+'min'].std(),
                                'min_n':self.array[monitor_db+'min'].size,
                                'max_V':self.array[monitor_db+'max'].mean(),
                                'max_std':self.array[monitor_db+'max'].std(),
                                'max_n':self.array[monitor_db+'max'].size},
                                timestamp=timestamp)
                        # Empty the array
                        with self.lock[monitor_db]:
                            self.array[monitor_db+'min'] = np.array([])
                            self.array[monitor_db+'max'] = np.array([])
                        # Propogate lap numbers -----------------------------------------
                            self.record_timer[monitor_db] = new_record_lap
                # Heartbeat -----------------------------------------
                    state_db = 'cw_laser/state_frequency'
                    with self.lock[state_db]:
                        self.local_settings[state_db]['heartbeat'] = datetime.datetime.utcnow()
                        self.db[state_db].write_buffer(self.local_settings[state_db])
                
                if DAC2_output is not None and self.output_number is 2:
                    # Scale to minimum and maximum limits: 0 means minimum, 1 means maximum
                    DAC2_output = (DAC2_output - self.sl.DACs_limit_low[2]).astype(np.float)/float(self.sl.DACs_limit_high[2] - self.sl.DACs_limit_low[2])
                    # Write data to disk:
                
                if (DAC0_output is not None) or (DAC1_output is not None):
                    # Scale to volts
                    dac_scale = float(self.sl.DACs_limit_high[self.output_number] - self.sl.DACs_limit_low[self.output_number])/2.
                    dac_output = dac_output/dac_scale
                    dac_mean = dac_mean/dac_scale
                    dac_thrsh = dac_thrsh/dac_scale
                    dac_low = dac_low/dac_scale
                    dac_high = dac_high/dac_scale
                    # Write to plot buffers
                    self.DAC_history = np.append(self.DAC_history, dac_output)
                    self.DAC_mean_history = np.append(self.DAC_mean_history, dac_mean)
                    self.DAC_thrsh_history = np.append(self.DAC_thrsh_history, dac_thrsh)
                    self.DAC_low_history = np.append(self.DAC_low_history, dac_low)
                    self.DAC_high_history = np.append(self.DAC_high_history, dac_high)
                    self.time_history_dacs = np.append(self.time_history_dacs, time_axis)
                    # Filter plot points by age
                    hist_filt = (time_axis - self.time_history_dacs) < self.hist_buff_length
                    self.DAC_history = self.DAC_history[hist_filt]
                    self.DAC_mean_history = self.DAC_mean_history[hist_filt]
                    self.DAC_thrsh_history = self.DAC_thrsh_history[hist_filt]
                    self.DAC_low_history = self.DAC_low_history[hist_filt]
                    self.DAC_high_history = self.DAC_high_history[hist_filt]
                    self.time_history_dacs = self.time_history_dacs[hist_filt]
                    # Update graph:
                    self.curve_dac.setData(self.time_history_dacs - time_axis, self.DAC_history)
                    self.curve_dac_uthrsh.setData(self.time_history_dacs - time_axis, self.DAC_mean_history+self.DAC_thrsh_history)
                    self.curve_dac_lthrsh.setData(self.time_history_dacs - time_axis, self.DAC_mean_history-self.DAC_thrsh_history)
                    self.curve_dac_ulim.setData(self.time_history_dacs - time_axis, self.DAC_high_history)
                    self.curve_dac_llim.setData(self.time_history_dacs - time_axis, self.DAC_low_history)
                    self.qplt_dac.setTitle('%s Lock DAC output = %f' % (channelName, self.DAC_history[-1]))
                    if self.qchk_fullscale_dac.isChecked():
                        #self.qplt_dac.setAxisScaleEngine(Qwt.QwtPlot.yLeft, Qwt.QwtLinearScaleEngine())
                        self.qplt_dac.setYRange(-1, 1)
                        #self.qplt_dac.setAxisScale(Qwt.QwtPlot.yLeft, 0, 1)
                    else:
                        self.qplt_dac.enableAutoRange(y=True)
                        #self.qplt_dac.setAxisAutoScale(Qwt.QwtPlot.yLeft)
            
                
                if freq_counter_samples is not None:
                    # Write data to disk:
                    if (self.output_number == 0):
                    # 'mll_f0/freq_err' ---------------------
                        monitor_db = 'mll_f0/freq_err'
                    elif (self.output_number == 1):
                    # 'cw_laser/freq_err' ---------------------
                        monitor_db = 'cw_laser/freq_err'
                    data = np.mean(freq_counter_samples)
                    with self.lock[monitor_db]:
                        # Append to the record array
                        self.array[monitor_db] = np.append(self.array[monitor_db], data)
                    self.db[monitor_db].write_buffer({'Hz':data}, timestamp=timestamp)
                    # Update record
                    if (new_record_lap > self.record_timer[monitor_db]):
                        # Record statistics ---------------------
                        self.db[monitor_db].write_record({
                                'Hz':self.array[monitor_db].mean(),
                                'std':self.array[monitor_db].std(),
                                'n':self.array[monitor_db].size},
                                timestamp=timestamp)
                        # Empty the array
                        with self.lock[monitor_db]:
                            self.array[monitor_db] = np.array([])
                        # Propogate lap numbers -----------------------------------------
                            self.record_timer[monitor_db] = new_record_lap

                    # Write to plot buffers
                    self.freq_history = np.append(self.freq_history, freq_counter_samples)
                    self.time_history_counters = np.append(self.time_history_counters, time_axis)
                    # Filter plot points by age
                    hist_filt = (time_axis - self.time_history_counters) < self.hist_buff_length
                    self.freq_history = self.freq_history[hist_filt]
                    self.time_history_counters = self.time_history_counters[hist_filt]
                    # Update graph:
                    self.curve_freq_error.setData(self.time_history_counters - time_axis, self.freq_history)
                    counts_mean = self.SI_scale(np.mean(self.freq_history), sig_figs=4)
                    counts_std = self.SI_scale(np.std(self.freq_history), sig_figs=3)
                    self.qplt_freq.setTitle('{0:} Lock Freq error, mean = {1:} Hz, std = {2:} Hz'.format(channelName, counts_mean, counts_std))
                    if self.qchk_fullscale_freq.isChecked():
                        #self.qplt_freq.setAxisScaleEngine(Qwt.QwtPlot.yLeft, Qwt.QwtLinearScaleEngine())
                        try:
                            ymin = self.freq_ymin
                            ymax = self.freq_ymax
                        except:
                            ymin = -25e6
                            ymax = 25e6
                        
                        #self.qplt_freq.setAxisScale(Qwt.QwtPlot.yLeft, ymin, ymax)
                        self.qplt_freq.setYRange(ymin, ymax)
                    else:
                        #self.qplt_freq.setAxisAutoScale(Qwt.QwtPlot.yLeft)
                        self.qplt_freq.enableAutoRange(y=True)
                    
                    #self.qplt_freq.replot()

            
        except:
            print('Exception occured parsing counter data. disabling further updates.')
            self.killTimer(self.timerID)
            freq_counter_samples = 0
            time_axis = 0
            DAC0_output = 0
            DAC1_output = 0
            DAC2_output = 0
            
            raise

    def SI_scale(self, x, sig_figs = 6):
        if sig_figs < 3:
            sig_figs = 3
        if x != 0:
            raw_scale = np.log10(np.abs(x))
            mod = int(raw_scale) % 3
            scale = int(raw_scale - mod)
            frac_digits =  int(sig_figs - mod -0.5*(1+np.sign(raw_scale)))
            str_x = "{0:.{2:}f}e{1:}".format(x*10.**(-scale), scale, frac_digits)
            return str_x
        else:
            str_x = "{0:.{2:}f}e{1:}".format(0., 0, int(sig_figs-1))
            return str_x

    # From: http://stackoverflow.com/questions/273192/create-directory-if-it-doesnt-exist-for-file-write
    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
                
                