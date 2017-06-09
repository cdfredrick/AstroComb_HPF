# -*- coding: utf-8 -*-
"""
Created on Thu Jun 08 10:30:47 2017

@author: ajm6
"""

import Finisar as PS
import math
import numpy as np
import matplotlib.pyplot as plt
"""Create Finisar Resource"""
WS = PS.Finisar("SN200520")

"""Open Communication with Finisar"""
status = PS.Finisar.open_communication(WS)

"""Setup frequency vector"""
dim = math.ceil((WS.StopF - WS.StartF)*1000)
frequency_step = (WS.StopF-WS.StartF)/dim; #THz
frequency_vector = np.arange(-dim/2,dim/2,1)*frequency_step


"""Initialize mask vectors"""   
amp = np.ones((dim,1))
fase = np.zeros((dim,1))
port = np.ones((dim,1))
                                                                          
"""Create phase mask"""
z = 0.03793 #length of fiber in km
beta_2 = 21
beta_3 = 0.1
beta_4 = 0.0
beta_6 = 0.0
center_pixel = 6722 #center pixel of spectrum
cs = center_pixel*frequency_step
center_frequency = cs-dim*frequency_step/2

phi2 = z*beta_2
phi3 = z*beta_3
phi4 = z*beta_4
phi6 = z*beta_6
hw = fase;

hw1= 1j*phi2/2*pow((2*math.pi*(frequency_vector-center_frequency)),2)
hw2= 1j*phi3/6*pow((2*math.pi*(frequency_vector-center_frequency)),3)
hw3 = 1j*phi4/24*pow((2*math.pi*(frequency_vector-center_frequency)),4)
hw4 = 1j*phi6/720*pow((2*math.pi*(frequency_vector-center_frequency)),6)
fase = np.angle(np.exp(hw1+hw2+hw3+hw4))+math.pi

status = PS.Finisar.write_mask(WS,amp,fase,port,dim)

status = PS.Finisar.close_communication(WS)
plt.plot(fase)
                    
plt.show()
