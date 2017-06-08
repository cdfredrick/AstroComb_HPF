# -*- coding: utf-8 -*-
"""
Created on Thu Jun 08 10:30:47 2017

@author: ajm6
"""

import Finisar as PS
import math
import numpy as np

WS = PS.Finisar("SN200520")

status = PS.Finisar.open_communication(WS)
dim = math.ceil((WS.StopF - WS.StartF)*1000)
amp = np.ones((dim,1))
phase = np.zeros((dim,1))
port = np.ones((dim,1))
                                                                          
                                                   
#print buffer
amp = np.ones((dim,1))
phase = np.zeros((dim,1))
port = np.ones((dim,1))
#buffer = "%7.3f" % WS.StartF + "\t" + "%6.3f" % amp[0] + "\t" + "%8.6f" % phase[0] + "\t" + "%1i" % phase[0] + "\n"

#for i in range(1,int(dim)):
#    buffer = buffer + "%7.3f" % (WS.StartF+0.001*i-0.001) + "\t" + "%6.3f" % amp[i] + "\t" + "%8.6f" % phase[i] + "\t" + "%1i" % phase[i] + "\n"
    
status = PS.Finisar.write_mask(WS,amp,phase,port,dim)

status = PS.Finisar.close_communication(WS)