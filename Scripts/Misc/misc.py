# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 12:15:09 2019

@author: National Institute
"""
# %% Drivers
import datetime
import json

import numpy as np
import matplotlib.pyplot as plt
%matplotlib inline
%matplotlib qt5

from Drivers.VISA.ILXLightwave import LaserModule, TECModule, CombinationModule

from Drivers.VISA.Keysight import E36103A

from Drivers.Database.CouchbaseDB import PriorityQueue

from Drivers.Thorlabs import APT

from Drivers.Finisar import WaveShaper

from Drivers.VISA.Yokogawa import OSA


# %% Helper Functions

def tomorrow_at_noon():
    tomorrow = datetime.date.today()+datetime.timedelta(days=1)
    noon = datetime.time(hour=12)
    return datetime.datetime.combine(tomorrow,noon).timestamp()

#%%
comb_gen = PriorityQueue('comb_generator')

comb_gen.push(message={"state":{'comb_generator/state_12V_supply':{"state":'engineering'}}})

comb_gen.push(message={"state":{'comb_generator/state_12V_supply':{"state":'on'}}})


# %% ILX 1 ====================================================================
#==============================================================================
# %% RIO TEC
rio_tec = TECModule('GPIB0::23::INSTR', 1)

#--- Constants
rio_tec.tec_current_limit()
#Out[6]: 1.45

rio_tec.tec_temperature_limit()
#Out[9]: 50.0

rio_tec.tec_mode()
#Out[14]: 'R'

#--- Variable
rio_tec.tec_gain()
#Out[15]: 10

rio_tec.tec_resistance_setpoint()
#Out[16]: 9.51

rio_tec.tec_output()
#Out[17]: False

rio_tec.tec_output(output=True)

rio_tec.tec_output()
#Out[20]: True

rio_tec.tec_temperature()


# %% RIO Laser
rio_las = LaserModule('GPIB0::23::INSTR', 2)

#--- Contants
rio_las.laser_mode()
#Out[51]: 'Ihbw'

rio_las.laser_current_limit()
#Out[13]: 145

rio_las.laser_power_limit()
#Out[16]: 200

#--- Variable
rio_las.laser_current_setpoint()
#Out[22]: 96.13 - old
#Out[178]: 115.65

rio_las.laser_output()
#Out[25]: True

rio_las.laser_current()


# %% RIO pre-amp
rio_amp = CombinationModule('GPIB0::23::INSTR', 3)

#--- Constants
rio_amp.tec_mode()
#Out[22]: 'T'

rio_amp.tec_current_limit()
#Out[25]: 2.0

rio_amp.tec_temperature_limit()
#Out[28]: 60.0

rio_amp.tec_gain()
#Out[32]: 30

rio_amp.laser_mode()
#Out[39]: 'Ihbw'

rio_amp.laser_current_limit()
#Out[35]: 1050

rio_amp.laser_power_limit()
#Out[38]: 400

#--- Variable
rio_amp.tec_temperature_setpoint()
#Out[31]: 25.0

rio_amp.laser_current_setpoint()
#Out[27]: 900.0

rio_amp.output()
#Out[29]: (True, True)


# %% RIO combo
rio_cmb = CombinationModule('GPIB0::23::INSTR', 4)

#--- Constants
rio_cmb.tec_current_limit()
#Out[6]: 1.45

rio_cmb.tec_temperature_limit()
#Out[9]: 50.0

rio_cmb.tec_mode()
#Out[14]: 'R'

rio_cmb.laser_mode()
#Out[51]: 'Ihbw'

rio_cmb.laser_current_limit()
#Out[13]: 145

rio_cmb.laser_power_limit()
#Out[16]: 200

#--- Variable
rio_cmb.tec_gain()
#Out[15]: 10

rio_cmb.tec_resistance_setpoint()
#Out[16]: 9.51

rio_cmb.tec_output()
#Out[17]: True

rio_cmb.laser_current_setpoint()
#Out[22]: 122.

rio_cmb.output()
#Out[25]: True


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

#%% Filter Cavity =============
filt_cav = PriorityQueue('filter_cavity')


filt_cav.push(message={"state":{'filter_cavity/state':{"state":'safe'}}})
filt_cav.push(message={"state":{'filter_cavity/state':{"state":'lock'}}})


# %% WaveShaper ===============================================================
#==============================================================================
ws = WaveShaper.WS1000A('192.168.0.5')

domain = [280.18, 283.357]

#old_coefs = [
#    23.27920156,
#    -0.31415927,
#    -0.53407075,
#    -0.06283185,
#    1.57079633,
#    -0.12566371,
#    0.,
#    -0.12566371,
#    -0.56548668,
#    -0.18849556]
#%%
#new_coefs = [
#21.12229940806827,
#0.9938880964450989,
#-9.848254602962644,
#-2.788857337895246,
#-41.63125465629001,
#4.665367657691958]
new_coefs = [
20,
0.9938880964450989,
-10,
-2.788857337895246,
-61.63125465629001,
4.665367657691958]
#new_coefs = [
#    18]

new_poly_fit = np.polynomial.Polynomial([0,0]+new_coefs, domain=domain)
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

rt_stg.status()

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

nt_in.circle_parameters()
#Out[28]: 
#{'mode': 1,
# 'diameter': 0.001007095445181964,
# 'frequency': 60.3448275862069,
# 'min diameter': 0.0,
# 'max diameter': 0.0,
# 'adjust type': 1}

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

nt_out.circle_parameters()
#Out[11]: 
#{'mode': 1,
# 'diameter': 0.001007095445181964,
# 'frequency': 43.75,
# 'min diameter': 0.0,
# 'max diameter': 0.0,
# 'adjust type': 1}
#%%

# %% Spectral Optimization ====================================================
# =============================================================================
spec_opt = PriorityQueue('spectral_shaper')

spec_opt.push(message={'control_parameter':{'abort_optimizer':True}})

spec_opt.push(message={'control_parameter':{'setpoint_optimization':0}})
spec_opt.push(message={'control_parameter':{'setpoint_optimization':tomorrow_at_noon()}})

spec_opt.push(message={'control_parameter':{'DW_setpoint':-45}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_z_in_coupling",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_z_out_coupling",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{
'target':"optimize_IM_bias",
'exp_alpha':1,
'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{
'target':"optimize_optical_phase",
'exp_alpha':1,
'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_all_optical_phase",
                                                             'sig':3}}})
    
spec_opt.push(message={'control_parameter':{'run_optimizer':{
'target':"optimize_DW_setpoint",
'exp_alpha':1,
'sig':3}}})

# States
spec_opt.push(message={"state":{'spectral_shaper/state_optimizer':{"state":'optimal-nrs'}}})    
spec_opt.push(message={"state":{'spectral_shaper/state_optimizer':{"state":'optimal'}}})
spec_opt.push(message={"state":{'spectral_shaper/state_optimizer':{"state":'safe'}}})
    
    
#%% MLL
mll_state = PriorityQueue('mll_fR')
#
#mll_state.push(message={"state":{'mll_fR/state':{"state":"manual"}}})
#
mll_state.push(message={"state":{'mll_fR/state':{"state":"lock"}}})

#%% OSA

#osa = OSA("GPIB0::27::INSTR")
osa = OSA("TCPIP0::192.168.0.10::10001::SOCKET")
osa.level_unit()

#Out[288]: 'dBm/nm'

#%%
#data = osa.get_new_single(active_trace="TRA")

osa.trace_type(set_type={"mode":"WRIT"}, active_trace="TRA")
osa.wvl_range({"start":690, "stop":1320})
osa.sensitivity({"sense":"HIGH1", "chop":"OFF"})
osa.resolution(set_res=2)
#osa.sweep_mode("REP")
osa.initiate_sweep()

#%%
data = osa.get_new_single(get_parameters=True)
#data = osa.spectrum(get_parameters=True)

plt.figure("OSA")
#plt.clf()

plt.plot(data["data"]["x"], data["data"]["y"])


# %%
import os
base_dir = os.path.join("C:\\","Users","National Institute","Documents","Python Scripts","OSACtrl","2021-08-02")
date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
ident = "EOM-Comb"
file_name = "_".join((date, ident))+".txt"
file_path = os.path.join(base_dir, file_name)
with open(file_path, "x") as opened_file:
    json.dump(data, opened_file, indent="\t")