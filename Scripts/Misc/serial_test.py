# -*- coding: utf-8 -*-
"""
Created on Thu Oct 18 14:18:58 2018

@author: National Institute
"""

import serial

# %% Water Chiller
port = serial.Serial()
port.port = 'COM3'
port.baudrate = 9600
port.bytesize = serial.EIGHTBITS
port.stopbits = serial.STOPBITS_ONE
port.parity = serial.PARITY_NONE
port.timeout = 2
print(port)

#%% Remote Start
with port as s:
     s.write(bytes.fromhex('E0'))
     print(s.read(1).hex())

#%% Temperature
with port as s:
     s.write(bytes.fromhex('C9'))
     print(int.from_bytes(s.read(2), 'little'))

#%% Temperature Setpoint
with port as s:
     s.write(bytes.fromhex('C1'))
     print(int.from_bytes(s.read(2), 'little'))

#%% Faults Table
with port as s:
     s.write(bytes.fromhex('C8'))
     print(s.read(1).hex())
