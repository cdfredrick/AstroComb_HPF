# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 12:15:09 2019

@author: National Institute
"""
# %% Drivers
from Drivers.VISA.ILXLightwave import LaserModule, TECModule, CombinationModule

from Drivers.VISA.Keysight import E36103A

from Drivers.Database.CouchbaseDB import PriorityQueue

from Drivers.Thorlabs import APT

# %% ILX 1 ====================================================================
#==============================================================================
# %% RIO TEC
rio_tec = TECModule('GPIB0::23::INSTR', 1)

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
#Out[22]: 101.33

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

mll_TEC.tec_output()
#Out[4]: False

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


# %% 2nd Stage Coupling =======================================================
#==============================================================================
# x, y -> nanotrack; z -> focus

# %% Rotation Stage ===========================================================

rt_stg = APT.KDC101_PRM1Z8(port, serial_number='')

# %% 2nd Stage Input ==========================================================

# X in ()
x_in = APT.KPZ101(port, serial_number='')

# Y in ()
y_in = APT.KPZ101(port, serial_number='')

# Z in ()
z_in = APT.KPZ101(port, serial_number='')

# Nanotrack in
nt_in = APT.TNA001(port, serial_number='')

# %% 2nd Stage Out ============================================================

# X out ()
x_out = APT.KPZ101(port, serial_number)

# Y out ()
y_out = APT.KPZ101(port, serial_number)

# Z out ()
z_out = APT.KPZ101(port, serial_number)

# Nanotrack out
nt_out = APT.TNA001(port, serial_number='')


# %% Spectral Optimization ====================================================
# =============================================================================
spec_opt = PriorityQueue('spectral_shaper')

spec_opt.push(message={'control_parameter':{'abort_optimizer':True}})

spec_opt.push(message={'control_parameter':{'setpoint_optimization':0}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_DW_setpoint",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_z_in_coupling",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_z_out_coupling",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_IM_bias",
                                                             'sig':3}}})

spec_opt.push(message={'control_parameter':{'run_optimizer':{'target':"optimize_optical_phase",
                                                             'sig':3}}})
