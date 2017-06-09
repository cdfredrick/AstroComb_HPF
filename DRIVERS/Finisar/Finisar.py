# -*- coding: utf-8 -*-
"""
Created on Thu Jun 08 10:30:47 2017

@author: ajm6

List of public methods in class Finisar:
    
Initiate: 
    __init__(serial_number)
    
        Example Call: 
            resource = Finisar(serial number)  
General:
    open_communication(resource)
    close_communication(resource)
Write:
    write_mask(resource,mask)
    
        Examle Call:
            dim = resource.dim
            amp = np.ones((dim,1))
            phase = np.zeros((dim,1))
            port = np.ones((dim,1))

for i in range(1,int(dim)):
    buffer = buffer + "%7.3f" % (WS.StartF+0.001*i-0.001) + "\t" + 
    "%6.3f" % amp[i] + "\t" + "%8.6f" % phase[i] + "\t" + "%1i" % phase[i] + "\n"
"""
import wsapi as ws
import math
import numpy as np

class Finisar:
    def __init__(self,SN):
        """Clears values for start and stop frequency, and creates a waveshaper instance.  
        Note: You still cannot write to device without first opening communicaiton using 
        the open_communication function"""
        self.StartF = 0     #Start Frequency in THz
        self.StopF = 0      #Stop Frequency in THz
        self.SN = SN
        #Create WaveShaper instance SN200520 and name it "ws1"
        self.rc = ws.ws_create_waveshaper("ws1",SN + ".wsconfig")
        print "ws_create_waveshaper rc="+str(ws.ws_get_result_description(self.rc))

    def open_communication(self):
        """Opens Communication with waveshaper, allowing you to write and read from it"""
        self.rc = ws.ws_open_waveshaper("ws1")
        print "ws_open_waveshaper rc=" + str(ws.ws_get_result_description(self.rc))
        #rc = ws.ws_open_waveshaper("ws1")
        self.StartF = ws.ws_get_startfreq("ws1")
        print "Start Frequency = " + str(self.StartF) +" THz"
        self.StopF = ws.ws_get_stopfreq("ws1")
        print "Stop Frequency = " + str(self.StopF) + " THz"
        
    def write_mask(self,amp,phase,port,dim):  
        """Writes amplitude, phase, and port vectors to waveshaper
        vectors should all be V(1,dim) in dimension.
        format, freq(xxx.xxx) TAB amp(xx.xxx) TAB phase(x.xxxxxx) TAB port(x) NewLine"""
        buffer = "%7.3f" % self.StartF + "\t" + "%6.3f" % amp[0] + "\t" + "%8.6f" % phase[0] + "\t" + "%1i" % port[0] + "\n"                                                 
        for i in range(1,int(dim)):
            buffer = buffer + "%7.3f" % (self.StartF+0.001*i-0.001) + "\t" + "%6.3f" % amp[i] + "\t" + "%8.6f" % phase[i] + "\t" + "%1i" % port[i] + "\n"
        self.rc = ws.ws_load_profile("ws1",buffer)                                                
        print "ws_write_waveshaper rc=" + str(ws.ws_get_result_description(self.rc))
        
    def close_communication(self):
        """Closes communication with waveshaper and deletes the waveshaper instance"""
        self.rc = ws.ws_close_waveshaper("ws1")
        print "ws_close_waveshaper rc=" + str(ws.ws_get_result_description(self.rc))
        self.rc = ws.ws_delete_waveshaper("ws1")
        print "ws_delete_waveshaper rc=" + str(ws.ws_get_result_description(self.rc))
        
   
