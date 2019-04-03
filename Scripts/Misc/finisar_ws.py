# -*- coding: utf-8 -*-
"""
Created on Thu Oct 18 18:30:54 2018

@author: National Institute
"""
import numpy as np
from Drivers.Finisar import WaveShaper

SPEED_OF_LIGHT = 299792458 # m/s
SPEED_OF_LIGHT_NM_THZ = SPEED_OF_LIGHT*1e9*1e-12 # nm THz
# %%

ws = WaveShaper.WS1000A('192.168.0.5')

# %% Select Port

ws.port_profile(set_profile=(ws.freq*0 + 1).astype(np.int))


# %% Apply Attenuation

attn = ws.freq * 0
attn[0:5200] = 40
attn[8400:] = 40

ws.attn_profile(set_profile=attn)


# %% Apply Phase
#                       #  0   1,  2,  3,   4,   5,   6,   7,   8
#coef = 2*np.pi*np.array([0.5,  0,  78,  7,  -0.5,  -1,  -.1])
coef = 2*np.pi*np.array([0.5,       #0
                         0,         #1
                         3.705,      #2
                         -0.05,     #3
                         -.085,     #4
                         -.01,      #5
                         .25,       #6
                         -0.02,     #7
                         .00,      #8
                         -.02,       #9
                         -0.09,     #10
                         -.03,       #11
                         ])
phase = np.polynomial.Legendre(np.array(coef), domain=[SPEED_OF_LIGHT_NM_THZ/1070., SPEED_OF_LIGHT_NM_THZ/1058.])

ws.phase_profile(set_profile=phase(ws.freq))


# %% OLD Stuff
#
##NumPixels = ceil((Dev2.StopF-Dev2.StartF).*1000);
#dim=ws.freq.size;
#stepf=np.diff(ws.freq).mean();
#vectorf=ws.freq;
#z=0.039;#%0.142;%0.03793; %    0.03797;%km 65%04042 %170 267
#beta2= (21.45+.25-.0);# %23 %21.6
#Phi2=z*beta2;
#beta3= (0.1+.0);#%0.134;
#Phi3=beta3*z;
#beta4= -(0.165+.040+0.02); #%1.00;
#Phi4=beta4*z;
#beta6= -(0.17+.01+.01);#%15; %20.0;
#Phi6=beta6*z;
#beta8= (-0.01);#%15; %20.0;
#Phi8=beta8*z;
#
##%
##% Phi2 = z*19.8;
##% Phi3 = 0;
##% Phi4 = 0;
##% Phi6 = 0;
#Phi8 = 0;
#pixelKoheras=6710;#%4622;%6722 % Center line of the comb. 
#center=pixelKoheras*stepf;
#cs=center-dim*stepf/2;
#Hw=np.exp(1j*Phi2/2*(2*np.pi*(vectorf-cs))**2)*np.exp(1j*Phi3/6*(2*np.pi*(vectorf-cs))**3)*np.exp(1j*Phi4/24*(2*np.pi*(vectorf-cs))**4)*np.exp(1j*Phi6/720*(2*np.pi*(vectorf-cs))**6)*np.exp(1j*Phi8/40320*(2*np.pi*(vectorf-cs))**8);
#fase=np.angle(Hw)+np.pi;
## %amplitud=zeros(1,dim);
##%  amplitud(1,pixelKoheras+30*150:NumPixels)=1;
## %amplitud=amplitud.*0+1;
## % amplitud(1,12531:NumPixels)=0;
##%  gap=30*100;%2091;
## %amplitud(1,pixelKoheras-15:pixelKoheras+15)=0;
##   % amplitud(1,pixelKoheras+gap-15:pixelKoheras+gap+15)=0;
##     %amplitud(1,pixelKoheras-gap-15:pixelKoheras-gap+15)=0;
##  %amplitud(1,pixelKoheras-200:pixelKoheras+200)=0;
#
##  % amplitud = atten;
#amplitud=np.ones([1,dim]);
#amplitud[0,0:5200]=0;
#amplitud[0,8400:dim]=0;# %8300
#PORT=np.ones([1,dim]);
##%  fase=fase;
##%fase = fase.*0;
##WriteFinisarRelative3(Dev2,amplitud,fase,PORT)