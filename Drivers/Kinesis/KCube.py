# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 13:55:39 2018

@author: National Institute
"""


# %% Modules
import ctypes as c

# %% Load DLLs

dc_servo = c.CDLL('Thorlabs.MotionControl.KCube.DCServo.dll')
piezo = c.CDLL('Thorlabs.MotionControl.KCube.Piezo.dll')


# %%
receiveBuffer = c.c_buffer(200)
sizeOfBuffer  = c.c_ulong(255)
def getDeviceList():
    dc_servo.TLI_BuildDeviceList()
    dc_servo.TLI_GetDeviceListExt(c.pointer(receiveBuffer), c.pointer(sizeOfBuffer))
    return [x for x in (receiveBuffer.value.decode()).split(',')[:-1]]

# %%
#print(dc_servo.TLI_BuildDeviceList())
#
SN = c.create_string_buffer(b"27251608")
# %%
#receiveBuffer = c.c_buffer(200)
#dc_servo.TLI_GetDeviceList(receiveBuffer)

# %% TEST
try:
    print('Connecting')
    dc_servo.CC_Open(c.byref(SN))
    print(dc_servo.CC_CheckConnection(c.byref(SN)))
    print('Device Position')
    pos = dc_servo.CC_GetPosition(c.byref(SN))
    print(pos)
    print('Real Value')
    print('{:.6g}'.format(pos/1919.64))

finally:
    dc_servo.CC_Close(SN)

# %% Rotation Stage and DC Motor
#    dc_servo.CC_GetPosition(c.byref(serialNo))
#    dc_servo.CC_NeedsHoming(c.byref(serialNo))
#    dc_servo.CC_MoveToPosition(c.byref(serialNo), int index)
#    dc_servo.CC_Home(c.byref(serialNo))


# %% OLD STUFF
"""
This program acquires spectra using a ANDO 6315E and rotates a Thorlabs K10CR1 rotation stage.
By Grace Kerber and Dan Hickstein
This program requires that the Thorlabs Kinesis drivers are in the same folder as this program.
pyVISA is used to communicate with the ANDO OSA using GPIB.
"""
from __future__ import print_function
import ctypes as c
import numpy as np
import os, time
import sys
import visa
import datetime
import matplotlib.pyplot as plt
import platform


print('Hello!')
#Set OSA Sensitivity (with time for each in parenthesis)
# 0 = Norm Range Hold (7   sec) # Don't use this one! It's terrible!!!
# 1 = Norm Range Auto (10  sec)
# 2 = High 1          (1.2 min)
# 3 = High 2          (2.4 min)
# 4 = High 3          (~17 min)
 
val_sens = int(1)

#Determines what angles to collect data at
ExtinguishAngle = 57.1  # Angle at which minimum power occurs
MaxPower        = 202.2 # Maximum Power through half wave plate
MinPower        = 0.9   # Minimum Power through half wave plate (power measured at ExtinguishAngle)
NumOfPoints     = 50    # number of data points (different power) to be collected 

powerarray = np.linspace(MaxPower, MinPower, NumOfPoints)


def angleFromPower(power, minPower=MinPower, maxPower=MaxPower, extinguishingAngle=ExtinguishAngle):
    return -(np.arcsin( ((power-minPower)/(maxPower-minPower))**0.5))*(180/np.pi)/2.  + extinguishingAngle

anglearray = angleFromPower(powerarray)


bits, version = platform.architecture()
print('Detected %s Python on %s. Loading %s DLLs'%(bits, version, bits))

dllname = os.path.join(os.path.dirname(__file__), 'dll%s'%bits[:2], 'Thorlabs.MotionControl.IntegratedStepperMotors.dll')
os.environ['PATH'] =   os.environ['PATH'] + ';' + os.path.join(os.path.dirname(__file__), 'dll%s'%bits[:2])

if not os.path.exists(dllname):
    raise ValueError('DLL Not found! dllname=%s'%dllname)

if bits == '32bit':
    p = c.CDLL(dllname) #Alternate between dll loading method
else:
    print('64 bit DLLs have not been tested. It should work though...')
    p = c.windll.LoadLibrary(dllname)  


print('The Estimated Time to finish is {:.0f} hours and {:.2f} minutes'.format(np.floor(scanTime*powerarray.size/60.), (scanTime*powerarray.size)%60, ))

def getHardwareInfo(SN):
    
    modelNo =         c.c_buffer(255)
    sizeOfModelNo =   c.c_ulong(255)
    hardwareType =    c.c_ushort()
    numChannels =     c.c_short()
    notes =           c.c_buffer(255)
    sizeOfNotes =     c.c_ulong(255)
    firmwareVersion = c.c_ulong()
    hardwareVersion = c.c_ushort()
    modState        = c.c_ushort()
    # p.PCC_GetHardwareInfo(SN)

    p.ISC_GetHardwareInfo(SN, 
                          c.pointer(modelNo), 
                          c.pointer(sizeOfModelNo), 
                          c.pointer(hardwareType),
                          c.pointer(numChannels),
                          c.pointer(notes),
                          c.pointer(sizeOfNotes),
                          c.pointer(firmwareVersion),
                          c.pointer(hardwareVersion),
                          c.pointer(modState) )
    

    return [x.value for x in (modelNo, sizeOfModelNo, hardwareType, numChannels, notes, sizeOfNotes, firmwareVersion, hardwareVersion, modState)]


def getMotorParamsExt(SN):
	# this doesn't work for some reason...
	stepsPerRev =  c.c_double()
	gearBoxRatio = c.c_double()
	pitch =        c.c_double()

	p.ISC_GetMotorParamsExt(SN, c.pointer(stepsPerRev), 
							       c.pointer(gearBoxRatio), 
							       c.pointer(pitch))

	return stepsPerRev.value, gearBoxRatio.value, pitch.value


def getDeviceList():
    p.TLI_BuildDeviceList()
    receiveBuffer = c.c_buffer(200)
    sizeOfBuffer  = c.c_ulong(255)
    p.TLI_GetDeviceListExt(c.pointer(receiveBuffer), c.pointer(sizeOfBuffer))
    return [x for x in (receiveBuffer.value).split(',')[:-1]]


def MoveToPosition(SN, deviceUnits, timeout=20, queryDelay=0.01, tolerance=1):
    """
    Moves the rotation stage to a certain position (given by device units).
    This call blocks future action until the move is complete.
    The timeout is in seconds
    
    SN is a c_buffer of the serial number string
    deviceUnits shold be a int.
    tolerance is when the blocking should end (device units)
    """
    
    GetStatus(SN)
    p.ISC_MoveToPosition(SN, c.c_int(int(deviceUnits)))

    t = time.time()

    while time.time()<(t+timeout):
        GetStatus(SN)
        p.ISC_RequestStatus(SN) # order the stage to find out its location
        currentPosition = p.ISC_GetPosition(SN)
        error = currentPosition - deviceUnits
        if np.abs(error)<tolerance: 
            return
        else:
            time.sleep(queryDelay)
    raise ValueError('Oh no!!! We never got there!! Maybe you should make the timeout longer than %.3f seconds dude.'%timeout)

    

try:
    serialNumber = getDeviceList()[0]
except:
    raise ValueError('Couldn\'t get the list of serial numbers! Is your stage plugged in? Or is Thorlabs Kinesis open?')

def GetStatus(SN):
    p.ISC_RequestStatus(SN)
    #bits = p.ISC_GetStatusBits(SN)
    #print bin(bits)
    
    
#---Create Base Directory for saving data
today = datetime.datetime.now().strftime("%Y-%m-%d")
cwd = os.getcwd()
base_dir = os.path.join(cwd, today)
if not(os.path.isdir(base_dir)):
    os.mkdir(base_dir)

run_counter = 1 
run_folder  = 'run %04i'%(run_counter)

# find the first available file name:
while os.path.isdir(os.path.join(base_dir, run_folder)):
    run_counter = run_counter+1
    run_folder = 'run %04i'%(run_counter)
new_base_dir = os.path.join(base_dir,run_folder)
os.mkdir(new_base_dir)    

print('Saving to:   %s\n' %(new_base_dir))

SN = c.c_buffer(serialNumber)

try:
    p.ISC_Close(SN)
    print('Previous stage connection closed.')
except:
    pass

p.ISC_Open(SN)

#hardwareinfoval = getHardwareInfo(SN)
p.ISC_StartPolling(SN,c.c_int(20))
p.ISC_LoadSettings(SN)

with open(os.path.join(new_base_dir, 'LOGFILE.txt'), 'w') as logfile:
    time_now  = datetime.datetime.now().strftime("%Y-%m-%d %X")
    logfile.write('Instrument: ANDO\n')
    logfile.write('Time\t'+time_now+'\n')
    logfile.write('Min_pow angle: %.4f\n'%ExtinguishAngle)
    logfile.write('Max Power: %.4f\n'%MaxPower)
    logfile.write('Min Power: %.4f\n'%MinPower)
    logfile.write('Num Points: %i\n'%NumOfPoints)
    logfile.write('FileNum\tPower\t Angle (deg)\n')
    
    for count, (power, angle) in enumerate(zip(powerarray, anglearray)):
        logfile.write('%04i\t%.6f\t%.6f\n'%(count+1, power,angle))


#Begin moving stage to Home- defines where zero is
print('Homing...'); sys.stdout.flush()
p.ISC_Home(SN)
time.sleep(0.5)

while (p.ISC_GetStatusBits(SN))!=(-2147482624):  #While Motor is moving.  Stopped is -2147482624
    #print p.ISC_GetStatusBits(SN)
    #print 'in the process of homing'
    time.sleep(1)
    
print('Rotation Stage Has Been Homed.\n')

# Calculate the conversion between "Device units" and degrees
stepsPerRev, gearBoxRatio, pitch = getMotorParamsExt(SN)
microstepsPerFullstep = 2048 # from https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=8750
conversion = stepsPerRev * microstepsPerFullstep * gearBoxRatio / pitch # convert to degrees
# conversion is in "Device units per degree"
# print('The step size of this device is assumed to be %.1e degrees'%(1/conversion))


### This is where the MAGIC happens. ###
degree = anglearray
for count, (degree) in enumerate(degree[::]):
    DegreePosition = degree #value in degrees

    # convert the desired position to integer "Device units" to be passed to the stage
    # NOTE: this involves rounding, and could introduce errors, especially if you are making
    # steps of just a few device units.
    deviceUnits = abs(int(DegreePosition*conversion))#-deviceUnitsZero) 
    print('% 3i of % 3i - %5.3f degrees - %6.2f mW - '%(count+1, powerarray.size,DegreePosition, powerarray[count]), end='')
    sys.stdout.flush()
    
    MoveToPosition(SN, deviceUnits)
    new_position = p.ISC_GetPosition(SN)
    new_degrees = new_position/conversion
    # print 'Reported %5.3f degrees (%i Device Units).'%(new_degrees, new_position); sys.stdout.flush()
    
    #Tells OSA to begin sweep
    osa.write("SGL")
    
    query = int(osa.query('SWEEP?')) # greater that zero means OSA is currently performing a sweep

    #Checking if OSA Done Sweeping
    while query > 0:
        time.sleep(.2) # in seconds  
        query = int(osa.query('SWEEP?'))
        
            
    ### Capturing Data Trace from OSA
                
    # Active Trace
    t_active = int(osa.query("ACTV?"))
    trace = "ABC"[t_active]
                
    # Instrument ID
    osa_ID = ''.join([i if ord(i) < 128 else ' ' for i in osa.read_raw().rstrip()]) # strips non-ASCII characters
    
    # Time Stamp
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %X")
                
    # Measurement Characteristics
    t_list_hds = "Center Wvl:,Span Range:,REF Level:,Level Scale:,Wvl Resolution:,Avg Count:,Sampl Count:,Sensitivity:,Monochro:,Waveform Type:".split(',')
    t_list = osa.query("ST"+trace+"?").rstrip().split(',')

    # Spectral Data
    osa.write("LDTDIG3") #sets retrieval the maximum of 3 decimal places
    level_unit = ["W","dBm"][bool(float(osa.query("LSCL?")))]
    abs_or_dens = ["","/nm"][int(osa.query("LSUNT?"))]
    t_wave = osa.query("WDAT"+trace).rstrip().split(',')[1:] #discards the sample count
    t_level = osa.query("LDAT"+trace).rstrip().split(',')[1:]
    # Format Data String:
    col_1 = ["Instrument:"] + ["Time Stamp:"] + t_list_hds + ["", "Wavelength(nm)"] + t_wave
    col_2 = [osa_ID] + [time_now] + t_list + ["", "Level("+level_unit+abs_or_dens+")"] + t_level
    col_comb = zip(col_1, col_2)
    data_list = []
    for data_row in col_comb:
        data_list.append('\t'.join(data_row))
    data_string = "\n".join(data_list)
    
    #Saving Data Trace   
    with open(os.path.join(new_base_dir,'ando-osa-data_'+today+'_%04i.txt'%(count+1)), 'w') as data_file:
        data_file.write(data_string)
        print('Saved')
        
    # plt.plot(t_wave,t_level)


print('Moving Back to Max Power')
MoveToPosition(SN, abs(int((ExtinguishAngle+45)*conversion)))
print('Power scan complete!')
p.ISC_Close(SN)