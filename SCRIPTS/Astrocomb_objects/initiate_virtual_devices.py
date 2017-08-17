# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 11:51:18 2017

@author: Wesley Brand

Module: initiate_virtual_devices

Public function:
    dict = open_all()

Current list of keys in returned dict, maintain in the_astrocomb.py too:
    'yokogawa', 'ilx', 'rio_laser', 'preamp', 'ilx_2', 'ilx_3', 'cybel',
    'thermocube', 'rio_pd_monitor', 'eo_comb_dc_bias'

Devices that are missing (no drivers):
    Stage one:
        rf_oscillator

    Stage two:
        tem_controller


"""

#Astrocomb imports
import ilx_driver
import thermocube_driver
import simple_daq_driver
import osa_driver
import cybel_driver


#Constants

##ILX card numbers
RIO_CARD_NUM = 0 #NEED correct ILX card number of rio laser!!!
PREAMP_CARD_NUM = 1 #NEED correct ILX card number of preamp!!!
ILX_2_CARD_NUM = 2 #!!!
ILX_3_CARD_NUM = 3 #!!!

##DAQ power monitor for Rio laser
RIO_PD_CHAN = 3 #NEED Correct analog in channel of monitor photodiode!!!
RIO_PD_THRESHOLD = 0.5 #NEED correct threshold value in volts!!!

##DAQ DC voltage monitor for EO Comb
DC_BIAS_CHAN = 4 #NEED Correct analog in channel of EO Comb DC BIAS!!!
DC_BIAS_THRESHOLD = 0.5 #NEED correct threshold value in volts!!!

def open_all():
    """Creates virtual objects for all of the devices."""
    device_dict = {}

    #Visa Devices
    device_dict['yokogawa'] = osa_driver.OSA()
    ilx_devices, ilx_names = _open_ilx_devices()
    for i, name in enumerate(ilx_names):
        device_dict[name] = ilx_devices[i]
    device_dict['cybel'] = cybel_driver.Cybel()

    #DAQ devices
    device_dict['thermocube'] = thermocube_driver.ThermoCube()
    daq_devices, daq_names = _open_simple_daq_devices()
    for i, name in enumerate(daq_names):
        device_dict[name] = daq_devices[i]
    return device_dict

def _open_ilx_devices(rio_card=RIO_CARD_NUM, preamp_card=PREAMP_CARD_NUM,
                      card_2=ILX_2_CARD_NUM, card_3=ILX_3_CARD_NUM):
    """Returns a list of device objects and names."""
    ilx = ilx_driver.ILX()
    rio_laser = ilx_driver.LDControl(ilx, rio_card)
    preamp = ilx_driver.LDControl(ilx, preamp_card)
    ilx_2 = ilx_driver.LDControl(ilx, card_2)
    ilx_3 = ilx_driver.LDControl(ilx, card_3)
    ilx_devices = [ilx, rio_laser, preamp, ilx_2, ilx_3]
    ilx_names = ['ilx', 'rio_laser', 'preamp', 'ilx_2', 'ilx_3']
    return ilx_devices, ilx_names

def _open_simple_daq_devices(pd_chan=RIO_PD_CHAN,
                             pd_threshold=RIO_PD_THRESHOLD,
                             dc_chan=DC_BIAS_CHAN,
                             dc_threshold=DC_BIAS_THRESHOLD):
    """Returns a list of device objects and names."""
    rio_pd_monitor = simple_daq_driver.SimpleDAQ(pd_chan, 'Rio laser power',
                                                 pd_threshold)
    eo_comb_dc_bias = simple_daq_driver.SimpleDAQ(dc_chan, 'EO Comb voltage',
                                                  dc_threshold)
    daq_devices = [rio_pd_monitor, eo_comb_dc_bias]
    daq_names = ['rio_pd_monitor', 'eo_comb_dc_bias']
    return daq_devices, daq_names
