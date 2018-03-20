# -*- coding: utf-8 -*-
"""
Created on Tue Mar 13 15:33:09 2018

@author: Connor
"""
# %% Modules
import nidaqmx
import time
from functools import wraps

from Drivers.Logging import EventLog as log


# %% Constants
TERMINAL_DIFFERENTIAL = nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL
TERMINAL_NRSE = nidaqmx.constants.TerminalConfiguration.NRSE
TERM_CONFIG = {'DIFF':TERMINAL_DIFFERENTIAL, 'NRSE':TERMINAL_NRSE}

SAMP_CONTINUOUS = nidaqmx.constants.AcquisitionType.CONTINUOUS
SAMP_FINITE = nidaqmx.constants.AcquisitionType.FINITE

READ_ALL_AVAILABLE = nidaqmx.constants.READ_ALL_AVAILABLE

CHAN_PER_DIGITAL_LINE = nidaqmx.constants.LineGrouping.CHAN_PER_LINE


# %% Private Functions
def _handle_daq_error(func):
    """A function decorator that closes the task upon untamed errors."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """Wrapped function"""
        try:
            result = func(self, *args, **kwargs)
            return result
        except Exception as first_error:
            try:
                self._close_tasks()
            except:
                pass
            raise first_error
    return wrapper


# %% General Input Task
class InTask():
    @_handle_daq_error
    @log.log_this()
    def __init__(self, timeout=5.0):
        '''
        timeout:
            -The time in seconds before trying to start the task times out.
        '''
        self.timeout = timeout
        # Create tasks
        self.task_cont = nidaqmx.task.Task()
        self.task_point = nidaqmx.task.Task()
    
    @_handle_daq_error
    @log.log_this()
    def reserve_cont(self, status=None):
        if status is None:
        # Query the status of the task
            result = self.task_cont.is_task_done()
            return not(result)
        else:
        # Start or stop the task
            status = bool(status)
            if status:
                self.start_cont()
            else:
                self.stop_cont()
    
    @_handle_daq_error
    @log.log_this()
    def reserve_point(self, status=None):
        if status is None:
        # Query the status of the task
            result = self.task_point.is_task_done()
            return not(result)
        else:
        # Start or stop the task
            status = bool(status)
            if status:
                self.start_point()
            else:
                self.stop_point()
    
    @_handle_daq_error
    @log.log_this()
    def start_cont(self):
        '''
        Calling this function starts the continuous data acquisition
        '''
        self.stop_point()
        if self.task_cont.is_task_done():
            loop_for_reservation = True
            start_time = time.time()
            while loop_for_reservation:
                try:
                    self.task_cont.start()
                except nidaqmx.DaqError as daq_error:
                    # Check for 'resource is reserved' error
                    if (daq_error.error_code == -50103) and (time.time()-start_time < self.timeout):
                        # Keep trying if the resource is buys
                        pass
                    else:
                        raise daq_error
                else:
                    loop_for_reservation = False
                    
    @_handle_daq_error
    @log.log_this()
    def start_point(self):
        '''
        Calling this function starts the point data acquisition
        '''
        self.stop_cont()
        if self.task_point.is_task_done():
            loop_for_reservation = True
            start_time = time.time()
            while loop_for_reservation:
                try:
                    self.task_point.start()
                except nidaqmx.DaqError as daq_error:
                    # Check for 'resource is reserved' error
                    if (daq_error.error_code == -50103) and (time.time()-start_time < self.timeout):
                        # Keep trying if the resource is buys
                        pass
                    else:
                        raise daq_error
                else:
                    loop_for_reservation = False
    
    @_handle_daq_error
    @log.log_this()
    def stop_cont(self):
        '''
        Calling this function stops the continuous data acquisition
        '''
        if not self.task_cont.is_task_done():
            self.task_cont.stop()
    
    @_handle_daq_error
    @log.log_this()
    def stop_point(self):
        '''
        Calling this function stops the point data acquisition
        '''
        if not self.task_point.is_task_done():
            self.task_cont.stop()
    
    @log.log_this()
    def _close_tasks(self):
        '''
        This method closes and clears the tasks. A new task object must then be
        created in order to read values again. So as to not deadlock the DAQ, 
        this should only be called when catching untamed DAQ errors.
        '''
        self.task_cont.close()
        self.task_point.close()


# %% General Output Task
class OutTask():
    @_handle_daq_error
    @log.log_this()
    def __init__(self, timeout=5.0):
        '''
        timeout:
            -The time in seconds before trying to start the task times out.
        '''
        self.timeout = timeout
        # Create task
        self.task_cont = nidaqmx.task.Task()
    
    @_handle_daq_error
    @log.log_this()
    def reserve_cont(self, status=None):
        if status is None:
        # Query the status of the task
            result = self.task_cont.is_task_done()
            return not(result)
        else:
        # Start or stop the task
            status = bool(status)
            if status:
                self.start_cont()
            else:
                self.stop_cont()
    
    @_handle_daq_error
    @log.log_this()
    def start_cont(self):
        '''
        Calling this function starts the continuous write
        '''
        if self.task_cont.is_task_done():
            loop_for_reservation = True
            start_time = time.time()
            while loop_for_reservation:
                try:
                    self.task_cont.start()
                except nidaqmx.DaqError as daq_error:
                    # Check for 'resource is reserved' error
                    if (daq_error.error_code == -50103) and (time.time()-start_time < self.timeout):
                        # Keep trying if the resource is buys
                        pass
                    else:
                        raise daq_error
                else:
                    loop_for_reservation = False
    
    @_handle_daq_error
    @log.log_this()
    def stop_cont(self):
        '''
        Calling this function stops the continuous write
        '''
        if not self.task_cont.is_task_done():
            self.task_cont.stop()
        
    @log.log_this()
    def _close_tasks(self):
        '''
        This method closes and clears the tasks. A new task object must then be
        created in order to read values again. So as to not deadlock the DAQ, 
        this should only be called when catching untamed errors.
        '''
        self.task_cont.close()


# %% Analog Input Task
class AiTask(InTask):
    @_handle_daq_error
    @log.log_this()
    def __init__(self, config_list, max_rate, cont_buffer_size, timeout=5.0):
        '''
        Initializes the analog input task. 
        config_list:
            -The config_list contains a list of dictionaries that give the
            physical channel address, the terminal configuration, and the min
            and max voltage cutoffs. Setting the cutoffs appropriately gives the 
            highest resolution for the task. Check the specifications of the 
            DAQ to find its fixed input ranges. Each row of the list
            corresponds to a single physical channel. A single channel must
            still be enclosed in a list.
            [{'physical_channel':'Dev1/ai0',
              'terminal_config':'NRSE' or 'DIFF',
              'min_val':-0.1,
              'max_val':0.1}, ...]
        max_rate:
            -The max_rate is the fixed rate of samples per second. This rate is
            evenly split between the channels in the task.
        cont_buffer_size:
            -The size of the sample buffer per channel. This value must be 
            larger than the number of samples obtained by the DAQ between calls
            to the "read" function during continuous acquisition or an
            error will be thrown.
        timeout:
            -The time in seconds before trying to start the task times out.
        '''
        super(AiTask, self).__init__(timeout=timeout)
        # Add channels
        for config in config_list:
            self.task_cont.ai_channels.add_ai_voltage_chan(
                    config['physical_channel'],
                    terminal_config=TERM_CONFIG[config['terminal_config']],
                    min_val=config['min_val'],
                    max_val=config['max_val'])
            self.task_point.ai_channels.add_ai_voltage_chan(
                    config['physical_channel'],
                    terminal_config=TERM_CONFIG[config['terminal_config']],
                    min_val=config['min_val'],
                    max_val=config['max_val'])
        # Configure timing
        self.rate = float(max_rate)/len(config_list)
        self.buffer_size = int(cont_buffer_size)
        self.task_cont.timing.cfg_samp_clk_timing(
                self.rate,
                sample_mode=SAMP_CONTINUOUS,
                samps_per_chan=self.buffer_size)
        self.task_point.timing.cfg_samp_clk_timing(
                self.rate,
                sample_mode=SAMP_FINITE,
                samps_per_chan=self.buffer_size)
    
    @_handle_daq_error
    @log.log_this()
    def read_cont(self):
        '''
        This method reads all new data from the buffer. Reading from a running
        task gives greatest throughput efficiency. The result contains a list
        of lists with the measured values of each channel. The order of the 
        channels is the same as that given during initialization. If necessary,
        this method will stop the point acquisition.
        '''
        self.stop_point()
        result = self.task_cont.read(number_of_samples_per_channel=READ_ALL_AVAILABLE)
        return result
    
    @_handle_daq_error
    @log.log_this()
    def read_point(self, samples_per_channel=None):
        '''
        This method retrieves the most recent point measurement(s) from the
        DAQ. The result contains a list of point measurements of each
        channel. The order of the channels is the same as that giben during
        initialization. If necessary, this method will stop the continuous
        acquisition.
        samples_per_channel:
            -The number of samples per channel to retrieve. This value may be
            as high as the buffer given during initialization.
            -The default count is the buffer size
        '''
        self.stop_cont()
        if samples_per_channel is None:
            samples_per_channel = self.buffer_size
        else:
            samples_per_channel = int(samples_per_channel)
        if samples_per_channel <= 1:
            result = self.task_point.read()
        else:
            result = self.task_point.read(number_of_samples_per_channel=samples_per_channel)
        return result


# %% Digital Input Task
class DiTask(InTask):
    @_handle_daq_error
    @log.log_this()
    def __init__(self, config_list, timeout=5.0):
        '''
        Initializes the digital input task. 
        config_list:
            -The config_list contains a list of dictionaries that give the
            physical channel address. Each row of the list corresponds to a
            single physical channel. A single channel must still be enclosed 
            in a list.
            [{'physical_channel':'Dev1/port0/line0'}, ...]
        timeout:
            -The time in seconds before trying to start the task times out.
        '''
        super(DiTask, self).__init__(timeout=timeout)
        # Create task
        self.task_cont = nidaqmx.task.Task()
        self.task_point = nidaqmx.task.Task()
        # Add channels
        for config in config_list:
            self.task_cont.di_channels.add_di_chan(
                    config['physical_channel'],
                    line_grouping=CHAN_PER_DIGITAL_LINE)
            self.task_point.di_channels.add_di_chan(
                    config['physical_channel'],
                    line_grouping=CHAN_PER_DIGITAL_LINE)
        # Configure timing
        all_channels = ', '.join([config['physical_channel'] for config in config_list])
        self.task_cont.timing.cfg_change_detection_timing(
                rising_dege_chan=all_channels,
                falling_edge_chan=all_channels,
                sample_mode=SAMP_CONTINUOUS)
        self.task_point.timing.cfg_implicit_timing(samps_per_chan=1)
    
    @_handle_daq_error
    @log.log_this()
    def read_cont(self):
        '''
        This method reads all new data from the buffer. Reading from a running
        task gives greatest throughput efficiency. The result contains a list
        of lists with the measured values of each channel. The order of the 
        channels is the same as that given during initialization. If necessary,
        this method will stop the point acquisition.
        '''
        self.stop_point()
        result = self.task_cont.read(number_of_samples_per_channel=READ_ALL_AVAILABLE)
        return result
    
    @_handle_daq_error
    @log.log_this()
    def read_point(self):
        '''
        This method retrieves the most recent single point measurement from the
        DAQ. The result contains a list of one point measurements of each
        channel. The order of the channels is the same as that giben during
        initialization. If necessary, this method will stop the continuous
        acquisition.
        '''
        self.stop_cont()
        result = self.task_point.read()
        return result


# %% Analog Output Task
class AoTask(OutTask):
    @_handle_daq_error
    @log.log_this()
    def __init__(self, config_list, timeout=5.0):
        '''
        Initializes the analog output task. 
        config_list:
            -The config_list contains a list of dictionaries that give the
            physical channel address and the min and max voltage cutoffs. 
            Setting the cutoffs appropriately gives the highest resolution for
            the task. Check the specifications of the DAQ to find its fixed 
            output ranges. Each row of the list corresponds to a single
            physical channel. A single channel must still be enclosed in a list.
            [{'physical_channel':'Dev1/ao0',
              'min_val':-0.1,
              'max_val':0.1}, ...]
        timeout:
            -The time in seconds before trying to start the task times out.
        '''
        super(AoTask, self).__init__(timeout=timeout)
        # Create task
        self.task_cont = nidaqmx.task.Task()
        # Add channels
        for config in config_list:
            self.task_cont.ao_channels.add_ao_voltage_chan(
                    config['physical_channel'],
                    min_val=config['min_val'],
                    max_val=config['max_val'])
        # Configure timing
        self.task_cont.timing.cfg_implicit_timing(samps_per_chan=1)
    
    @_handle_daq_error
    @log.log_this()
    def write_cont(self, data):
        '''
        This method writes "data" to the output task. The task must be started
        in order for output to begin. If there are multiple channels in the 
        task, "data" should consist of a 1D list with the desired values for
        each channel. The order of the channels is the same as that given
        during initialization. If there is only 1 channel then "data" must be
        input as a scalar value.
        data:
            -The voltage value(s) to write to the DAQ channel. This must be a
            scalar if there is only 1 channel in the task, and it must be a 1D
            list if there are multiple channels.
            1.0 or [1.0, 2.0, ...]
        '''
        self.task_cont.write(data, auto_start=False)


# %% Digital Output Task
class DoTask(OutTask):
    @_handle_daq_error
    @log.log_this()
    def __init__(self, config_list, timeout=5.0):
        '''
        Initializes the digital output task. 
        config_list:
            -The config_list contains a list of dictionaries that give the
            physical channel address. Each row of the list corresponds to a
            single physical channel. A single channel must still be enclosed
            in a list.
            [{'physical_channel':'Dev1/port0/line0'}, ...]
        '''
        super(DoTask, self).__init__(timeout=timeout)
        # Create task
        self.task_cont = nidaqmx.task.Task()
        # Add channels
        for config in config_list:
            self.task_cont.do_channels.add_do_chan(
                    config['physical_channel'],
                    line_grouping=CHAN_PER_DIGITAL_LINE)
        # Configure timing
        self.task_cont.timing.cfg_implicit_timing(samps_per_chan=1)    
    
    @_handle_daq_error
    @log.log_this()
    def stop_cont(self):
        '''
        Calling this function stops the continuous write
        '''
        if not self.task_cont.is_task_done():
            self.task_cont.stop()
    
    @_handle_daq_error
    @log.log_this()
    def write_cont(self, data):
        '''
        This method writes "data" to the output task. The task must be started
        in order for output to begin. If there are multiple channels in the
        task, "data" should consist of 1D list with the desired boolean values
        of each channel. The order of the channels is the same as that given
        during initialization. If there is only 1 channel then "data" must be
        input as a scalar boolean value.
        data:
            -The boolean value(s) to write to the DAQ channel. This must be a
            scalar if there is only 1 channel in the task, and it must be a 1D
            list if there are multiple channels.
            True or [True, False, ...]
        '''
        self.task_cont.write(data, auto_start=False)


