# -*- coding: utf-8 -*-
"""
Created on Fri Jun 02 14:45:19 2017

@author: rm3531
"""


import numpy as np
import matplotlib.pyplot as plt
import wsapi as ws

CONFIG = 'WS200484.wsconfig'
PROFILE = 'WSP Examples/Gaussian_profile_BW200GHz.wsp'

def ws_create(config_name):
    rc = ws.ws_create_waveshaper('ws1', config_name)
    print 'ws_create_waveshaper rc = ' + str(ws.ws_get_result_description(rc))
    return rc
def ws_load_profile(rc, profile_name):
    WSPfile = open(profile_name, 'r')
    profile_text = WSPfile.read()
    rc = ws.ws_load_profile('ws1', profile_text)
    print 'ws_load_profile rc = ' + str(ws.ws_get_result_description(rc))
    return rc
def ws_delete(rc):
    rc = ws.ws_delete_waveshaper('ws1')
    print 'ws.ws_delete_waveshaper rc = ' + str(ws.ws_get_result_description(rc))
    return rc


RC = ws_create(CONFIG)
RC = ws_load_profile(RC, PROFILE)
RC = ws_delete(RC)