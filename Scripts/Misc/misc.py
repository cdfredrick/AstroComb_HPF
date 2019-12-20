# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 12:15:09 2019

@author: National Institute
"""
# %% Drivers
import datetime
import numpy as np
import matplotlib.pyplot as plt

from Drivers.VISA.ILXLightwave import LaserModule, TECModule, CombinationModule

from Drivers.VISA.Keysight import E36103A

from Drivers.Database.CouchbaseDB import PriorityQueue

from Drivers.Thorlabs import APT

from Drivers.Finisar import WaveShaper

# %% Helper Functions

def tomorrow_at_noon():
    tomorrow = datetime.date.today()+datetime.timedelta(days=1)
    noon = datetime.time(hour=12)
    return datetime.datetime.combine(tomorrow,noon).timestamp()


# %% ILX 1 ====================================================================
#==============================================================================
# %% RIO TEC
rio_tec = TECModule('GPIB0::23::INSTR', 1)

rio_tec.tec_gain()
#Out[15]: 10

rio_tec.tec_resistance_setpoint()
#Out[16]: 9.51

rio_tec.tec_output()
#Out[17]: False

rio_tec.tec_output(output=True)

rio_tec.tec_output()
#Out[20]: True


# %% RIO Laser
rio_las = LaserModule('GPIB0::23::INSTR', 2)

rio_las.laser_current_setpoint()
#Out[22]: 99.03

rio_las.laser_output()
#Out[23]: False

rio_las.laser_output(output=True)

rio_las.laser_output()
#Out[25]: True

# %% RIO pre-amp
rio_amp = CombinationModule('GPIB0::23::INSTR', 3)

rio_amp.laser_current_setpoint()
#Out[27]: 900.0

rio_amp.tec_temperature_setpoint()
#Out[28]: 25.0

rio_amp.output()
#Out[29]: (False, False)

rio_amp.output(output=True)

rio_amp.output()
#Out[31]: (True, True)


# %% ILX 2 ====================================================================
#==============================================================================
# %% MLL TEC
mll_TEC = TECModule('GPIB0::20::INSTR', 1)
mll_TEC.tec_resistance_setpoint()
#Out[3]: 7.862

mll_TEC.tec_gain()
#Out[4]: 30 (or 10?)

mll_TEC.tec_output()
#Out[5]: False

mll_TEC.tec_output(output=True)

mll_TEC.tec_output()
#Out[6]: True


# %% MLL Osc Pump
mll_osc = CombinationModule('GPIB0::20::INSTR', 2)

mll_osc.laser_current_setpoint()
#Out[3]: 700.0

mll_osc.tec_temperature_setpoint()
#Out[4]: 25.0

mll_osc.output()
#Out[5]: (False, False)

mll_osc.output(output=True)

mll_osc.output()
#Out[7]: (True, True)


# %% MLL Amp 1
mll_amp1 = CombinationModule('GPIB0::20::INSTR', 3)

mll_amp1.laser_current_setpoint()
#Out[3]: 450.0

mll_amp1.tec_temperature_setpoint()
#Out[4]: 25.0

mll_amp1.output()
#Out[5]: (False, False)

mll_amp1.output(output=True)

mll_amp1.output()
#Out[7]: (True, True)


# %% MLL Amp 2
mll_amp2 = CombinationModule('GPIB0::20::INSTR', 4)

mll_amp2.laser_current_setpoint()
#Out[9]: 1000.0

mll_amp2.tec_temperature_setpoint()
#Out[10]: 25.0

mll_amp2.output()
#Out[11]: (False, False)

mll_amp2.output(output=True)

mll_amp2.output()
#Out[13]: (True, True)


# %% IM Bias ==================================================================
#==============================================================================
imbias = E36103A('USB0::0x2A8D::0x0702::MY57427460::INSTR')

imbias.voltage_setpoint()
#Out[2]: 3.5245

imbias.output()
#Out[3]: True

# %% WaveShaper ===============================================================
#==============================================================================
ws = WaveShaper.WS1000A('192.168.0.5')

domain = [280.18, 283.357]

old_coefs = [
    23.27920156,
    -0.31415927,
    -0.53407075,
    -0.06283185,
    1.57079633,
    -0.12566371,
    0.,
    -0.12566371,
    -0.56548668,
    -0.18849556]
#%%
new_coefs = [
    -6.0394090775996965 + 0.3*0 - 1.0*0,
    -5.800888350528486 + 2.*0 -2.*0,
    -10.846185606096743 + 0.5*0 - 0.2*0,
    -1.3103647581879212 + 0.7*0 - .7*0,
    -0.7194257485576765 + 0.1*0 - 0.4*0,
    0.3945781226450866 + 0.7*0 - 0.7*0]

#new_coefs = [
#    12.873779823260552,
#    -0.00010805471567221225,
#    -8.382069235254972,
#    0.24959336119687642,
#    -1.5047378684494916,
#    0.19003929512744833]

#new_coefs = [
#    12.957652700500315,
#    -0.49569232204816693,
#    -8.414189277585605,
#    0.380450128189349,
#    -1.3942859402315253,
#    0.3111486710709459,
#    0.18849527583609194]


#new_coefs = [13.1542830681408,
#    -1.3832367395245435,
#    -8.436227608887236,
#    -0.06927063677322859,
#    -1.5790805588000139,
#    0.4499070303956333]

#new_coefs = [
#    10.591856341521305,
#    -3.594328183434416,
#    -8.64367174144833,
#    -1.3639937867675582,
#    -1.1992416114120243,
#    -0.1520067562032628]
new_poly_fit = np.polynomial.Legendre([0,0]+new_coefs, domain=domain)
# Send new phase profile
ws.phase_profile(new_poly_fit(ws.freq))

#plt.figure(0)
#plt.clf()
#x = np.linspace(domain[0], domain[1], 1000)
##plt.plot(WaveShaper.SPEED_OF_LIGHT_NM_THZ/x, old_poly_fit(x))
#plt.plot(WaveShaper.SPEED_OF_LIGHT_NM_THZ/x, new_poly_fit(x))
#plt.ylabel('Phase (rad)')
#plt.xlabel('Wavelength (nm)')

# %% APT Testing
test = APT.APTDevice("COM19", serial_number=82873587)

# %% 2nd Stage Coupling =======================================================
#==============================================================================
# x, y -> nanotrack; z -> focus

# %% Rotation Stage ===========================================================

rt_stg = APT.KDC101_PRM1Z8("COM10", serial_number=27251608)

rt_stg.home()
#Out[2]: {'homed': True, 'homing': False}

# %% 2nd Stage Input ==========================================================

# X in ()
x_in = APT.KPZ101("COM12", serial_number=29500912)

# Y in ()
y_in = APT.KPZ101("COM11", serial_number=29500931)

# Z in ()
z_in = APT.KPZ101("COM18", serial_number=29501649)

z_in.voltage()
#Out[5]: 42.989898373363445

# Nanotrack in
nt_in = APT.TNA001("COM19", serial_number=82873587)

nt_in.position()
#Out[7]: {'x': 0.47512016479743646, 'y': 0.5457541771572442}

nt_in.TRACK_MODE
#Out[8]: 3

nt_in.LATCH_MODE
#Out[9]: 2

nt_in.track_mode()
#Out[10]: 2

# %% 2nd Stage Out ============================================================

# X out ()
x_out = APT.KPZ101("COM15", serial_number=29500921)

# Y out ()
y_out = APT.KPZ101("COM14", serial_number=29500575)

# Z out ()
z_out = APT.KPZ101("COM17", serial_number=29501638)

z_out.voltage()
#Out[5]: 69.98275704214606

# Nanotrack out
nt_out = APT.TNA001("COM16", serial_number=82875187)

nt_out.position()
#Out[7]: {'x': 0.5883268482490273, 'y': 0.5646753643091478}

nt_out.TRACK_MODE
#Out[8]: 3

nt_out.LATCH_MODE
#Out[9]: 2

nt_out.track_mode()
#Out[10]: 2

# %% Spectral Optimization ====================================================
# =============================================================================
spec_opt = PriorityQueue('spectral_shaper')

spec_opt.push(message={'control_parameter':{'abort_optimizer':True}})

spec_opt.push(message={'control_parameter':{'setpoint_optimization':0}})
spec_opt.push(message={'control_parameter':{'setpoint_optimization':tomorrow_at_noon()}})

spec_opt.push(message={'control_parameter':{'DW_setpoint':-43.5}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_z_in_coupling",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_z_out_coupling",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_IM_bias",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_optical_phase",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_all_optical_phase",
                                                             'sig':3}}})
    
spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_DW_setpoint",
                                                             'sig':3}}})
    
#%%
mll_state = PriorityQueue('mll_fR')

mll_state.push(message={"state":{'mll_fR/state':{"state":"manual"}}})

mll_state.push(message={"state":{'mll_fR/state':{"state":"lock"}}})