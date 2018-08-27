# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 11:04:50 2017

@author: Wesley Brand

module: cybel_test
"""

import time
import numpy as np
import cybel_driver as cy
import eventlog as log

log.start_logging()

def wait(delay=2):
    """Sleeps for reading log output."""
    time.sleep(delay)

def test_run1():
    """Runs through basic queries."""
    cybel = cy.Cybel(cy.CYBEL_NAME, cy.CYBEL_ADDRESS)
    wait(6)
    print cybel.query_n_firmware()
    wait()
    print cybel.query_cpld_firmware()
    wait()
    print cybel.query_keep_on()
    wait()
    cybel.query_allowed_components()
    cybel.close()
    
def test_run2():
    cybel = cy.Cybel(cy.CYBEL_NAME, cy.CYBEL_ADDRESS)
    for i in np.arange(4):
        print cybel.query_tec_status(i)
        print cybel.query_pump_status(i)
        wait(3)
    print cybel.query_temp_error()
    wait(6)
    print cybel.query_trigger_n_laser_status()
    wait()
    print cybel.query_analog_input_values()
    wait(10)
    print cybel.query_analog_output_values()
    cybel.close()

def test_run3():
    cybel = cy.Cybel(cy.CYBEL_NAME, cy.CYBEL_ADDRESS)
    print cybel.query_trigger_timeout(), ' Hz'
    wait()
    print cybel.query_pulse_width(), ' ns'
    wait()
    print cybel.query_digital_temp_sensor, ' *C'
    wait()
    cybel.query_pulse_rep_rate(), ' kHz'
    cybel.close

def _get_temp_lists(cybel):
    input_dic = cybel.query_analog_input_values()
    output_dic = cybel.query_analog_output_values()
    in_list = [input_dic['seed_temp'], input_dic['pump1_temp'],
               input_dic['pump2_temp'], input_dic['pump3_temp']]
    out_list = [output_dic['seed_temp'], output_dic['pump1_temp'],
               output_dic['pump2_temp'], output_dic['pump3_temp']]
    print 'Input temps', in_list
    print 'Output temps', out_list
    return in_list, out_list

def test_run4():
    cybel = cy.Cybel(cy.CYBEL_NAME, cy.CYBEL_ADDRESS)
    for i in np.arange(4):
        if not cybel.query_tec_status(i):
            cybel.enable_tec(i)
            print 'TEC %d turned on!' % i

    wait(10)

    in_list, out_list = _get_temp_lists(cybel)
    for i in np.arange(4):
        cybel.set_tec_temp(i, out_list[i]+1)
        
    wait(10)
    in_list, out_list = _get_temp_lists(cybel)
    for i in np.arange(4):
        cybel.set_tec_temp(i, out_list[i]-1)

    wait(10)
    _get_temp_lists(cybel)

"""
    reboot()
    eeprom_save()

Enable Components:
    enable_pump(pump_num, pump_on)
    enable_tec(tec_num, tec_on)
    enable_keep_on(keep_on)

Queries:
    sn_str, fw_str = query_serial_and_firmware()
    str = query_cpld_firmware()
    TF = query_pump_status(pump_num)
    TF0, TF1, TF2, TF3 = query_temp_error()
    TF0, TF1  = query_trigger_n_laser_status()
    TF = query_tec_status(tec_num)
    query_pump_read_constants() #writes values to Cybel.pccr_list
    query_pump_write_constants() #writes values to Cybel.pccw_list
    query_pump_current_limits() #writes values to Cybel.pcl_list
    dict = query_analog_input_values()
    dict = query_analog_output_values()
    float = query_trigger_timeout() #Hz
    float = query_pulse_width() #ns
    float1, float2 = query_digital_temp_sensors(self) #Celsius
    float = query_pulse_rep_rate() #kHz
    TF = query_keep_on()
    query_allowed_components()

Set Values:
    set_tec_temp(tec_num, temp) #Celsius
    set_pump_current(pump_num, current) #amps
    set_seed_bias_voltage(voltage) #volts
    set_trigger_timeout(frequency) #Hz
    set_pulse_width(pw_val) #see table
    set_pump_read_constant(pump_num, val)
    set_pump_write_constant(pump_num, val)
"""