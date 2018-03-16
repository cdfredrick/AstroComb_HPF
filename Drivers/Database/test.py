# -*- coding: utf-8 -*-
"""
Created on Mon Mar 12 08:22:56 2018

@author: Connor
"""

# %%
from Drivers.Database import CouchbaseDB

# %%
import time
import numpy as np
import nidaqmx
import nidaqmx.stream_readers
DIF_TERM = nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL
CONT_SAMP = nidaqmx.constants.AcquisitionType.CONTINUOUS
FINITE_SAMP = nidaqmx.constants.AcquisitionType.FINITE
READ_ALL_AVAILABLE = nidaqmx.constants.READ_ALL_AVAILABLE
CHAN_PER_D_LINE = nidaqmx.constants.LineGrouping.CHAN_PER_LINE
# %%
t = nidaqmx.task.Task()
td = nidaqmx.task.Task()
# %%
#t.close()

# %%
samps = int(250e3/16*.2*3)
rate = 250e3/16
val_range = 10
t.ai_channels.add_ai_voltage_chan("Dev1/ai0",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai1",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai2",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai3",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai4",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai5",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai6",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai7",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai16",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai17",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai18",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai19",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai20",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai21",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai22",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.ai_channels.add_ai_voltage_chan("Dev1/ai23",terminal_config=DIF_TERM, min_val=-val_range, max_val=val_range)
t.timing.cfg_samp_clk_timing(rate, samps_per_chan=samps, sample_mode=CONT_SAMP)

td.di_channels.add_di_chan("Dev1/port0/line0:31", line_grouping=CHAN_PER_D_LINE)

td.timing.cfg_change_detection_timing(rising_edge_chan="Dev1/port0/line0:31", falling_edge_chan="Dev1/port0/line0:31", sample_mode=CONT_SAMP)

# %%
reader = nidaqmx.stream_readers.AnalogMultiChannelReader(t.in_stream)
result = np.empty((16,samps))
td.start()
t.start()

# %%
def read_DAQ(t):  
    then = time.time()
    time.sleep(0.2 - time.time() % 0.2)
    #t.start()
    #reader.read_many_sample(result)
    result = t.read(number_of_samples_per_channel=READ_ALL_AVAILABLE)
    result_d = td.read(number_of_samples_per_channel=READ_ALL_AVAILABLE)
    #t.stop()
    now = time.time()
    print('Digital: {:}'.format(np.sum(result_d, axis=1).astype(np.int)))
    print('Analog: {:}'.format(np.mean(result, axis=1)))
    print('DAQ Time = {:.5g}'.format(now-then))

# %%
p_Q = CouchbaseDB.PriorityQueue('test')

priority = False

then = time.time()
p_Q.push(priority=priority)
while True:
    position = p_Q.position()
    if position < 0:
        p_Q.push(priority=priority)
    elif position == 0:
        read_DAQ(t)
#        print(position)
        p_Q.pop()
#        p_Q.remove()
        print('Queue Time = {:.5g}'.format(time.time()-then))
        then = time.time()
        p_Q.push(priority=priority)
    elif position > 0:
#        print(position)
        pass