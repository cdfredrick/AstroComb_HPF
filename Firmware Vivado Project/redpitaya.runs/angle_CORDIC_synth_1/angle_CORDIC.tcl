# 
# Synthesis run script generated by Vivado
# 

set_msg_config -id {HDL 9-1061} -limit 100000
set_msg_config -id {HDL 9-1654} -limit 100000
create_project -in_memory -part xc7z010clg400-1

set_param project.compositeFile.enableAutoGeneration 0
set_param synth.vivado.isSynthRun true
set_msg_config -source 4 -id {IP_Flow 19-2162} -severity warning -new_severity info
set_property webtalk.parent_dir {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.cache/wt} [current_project]
set_property parent.project_path {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.xpr} [current_project]
set_property default_lib work [current_project]
set_property target_language Verilog [current_project]
set_property vhdl_version vhdl_2k [current_fileset]
read_ip {{D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC.xci}}
set_property used_in_implementation false [get_files -all {{d:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC.dcp}}]
set_property is_locked true [get_files {{D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC.xci}}]

read_xdc dont_touch.xdc
set_property used_in_implementation false [get_files dont_touch.xdc]
synth_design -top angle_CORDIC -part xc7z010clg400-1 -mode out_of_context
rename_ref -prefix_all angle_CORDIC_
write_checkpoint -noxdef angle_CORDIC.dcp
catch { report_utilization -file angle_CORDIC_utilization_synth.rpt -pb angle_CORDIC_utilization_synth.pb }
if { [catch {
  file copy -force {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.runs/angle_CORDIC_synth_1/angle_CORDIC.dcp} {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC.dcp}
} _RESULT ] } { 
  send_msg_id runtcl-3 error "ERROR: Unable to successfully create or copy the sub-design checkpoint file."
  error "ERROR: Unable to successfully create or copy the sub-design checkpoint file."
}
if { [catch {
  write_verilog -force -mode synth_stub {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC_stub.v}
} _RESULT ] } { 
  puts "CRITICAL WARNING: Unable to successfully create a Verilog synthesis stub for the sub-design. This may lead to errors in top level synthesis of the design. Error reported: $_RESULT"
}
if { [catch {
  write_vhdl -force -mode synth_stub {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC_stub.vhdl}
} _RESULT ] } { 
  puts "CRITICAL WARNING: Unable to successfully create a VHDL synthesis stub for the sub-design. This may lead to errors in top level synthesis of the design. Error reported: $_RESULT"
}
if { [catch {
  write_verilog -force -mode funcsim {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC_sim_netlist.v}
} _RESULT ] } { 
  puts "CRITICAL WARNING: Unable to successfully create the Verilog functional simulation sub-design file. Post-Synthesis Functional Simulation with this file may not be possible or may give incorrect results. Error reported: $_RESULT"
}
if { [catch {
  write_vhdl -force -mode funcsim {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC_sim_netlist.vhdl}
} _RESULT ] } { 
  puts "CRITICAL WARNING: Unable to successfully create the VHDL functional simulation sub-design file. Post-Synthesis Functional Simulation with this file may not be possible or may give incorrect results. Error reported: $_RESULT"
}

if {[file isdir {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.ip_user_files/ip/angle_CORDIC}]} {
  catch { 
    file copy -force {{D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC_stub.v}} {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.ip_user_files/ip/angle_CORDIC}
  }
}

if {[file isdir {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.ip_user_files/ip/angle_CORDIC}]} {
  catch { 
    file copy -force {{D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.srcs/sources_1/ip/angle_CORDIC/angle_CORDIC_stub.vhdl}} {D:/Users/Alex/Documents/GitHub/Frequency-comb-DPLL/Firmware Vivado Project/redpitaya.ip_user_files/ip/angle_CORDIC}
  }
}
