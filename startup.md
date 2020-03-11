The following lists the procedure for turning on the astrocomb system. The one-off commands needed to enact these instructions remotely are contained within "Scripts/Misc/misc.py".

1. Check that the liquid chiller is on
2. Set the IM bias to the last known level
3. Enable ILX 1's outputs
    1. CH1: RIO temperature controller
    2. CH2: RIO laser current controller
    3. CH3: RIO amplifier pump laser 1
    4. CH4: NA
4. Enable ILX 2's outputs
    1. CH1: Aux. Comb temperature controller
    2. CH2: Aux. Comb pump laser
    3. CH3: Aux. Comb amplifier pump laser 1
    4. CH4: Aux. Comb amplifier pump laser 2
5. Start "monitor_daq.py"
6. Start "comb_generation.py"
    - Note: this script enables the high power RF components
7. Start "rf_oscillators.py"
8. Start "mll_fR.py"
    - Note: the temperature of the oscillator may take some time to stabilize within range of the phase lock servo
9. Start "XEM_GUI.py"
    - Note: this file is currently found within a separate repository in the *Frequency-comb-DPLL* folder.
    1. Lock the "CEO" signal near 0 V
    2. Lock the "Optical" (RIO CW) signal nearest to its historical average after accounting for drift
10. Enable the Finisar WaveShaper and apply the last know mask
11. Start "filter_cavity.py"
    - Note: depending on the state of the hysteresis, the offset of the HV amplifier may need to be adjusted in order to find the lock point. This is found in the state settings as "y_voltage"
12. Enable the Cybel amplifier
    - Note: this step is performed in the *Cybel* app
	1. Enable 1 through 3 in that order
	2. Enable operation without the GUI
	3. Close the GUI
13. Reset the Nufern amplifier to a known state
    - Note: steps 1-5 **cannot** be done remotely
    1. Turn the key to the off ("0") position
    2. Disconnect power (4-pin) and USB for ~30s
    3. Reconnect power and USB
    4. Turn the key to the "enable" position (the next position after "1")
    5. Confirm that the interlock button is pulled out
    6. Open the nuAmp GUI and ensure that the output is at 0% and disabled
14. Turn on the OSA
    - Note: this step **cannot** be done remotely
15. Reset the K-Cubes and T-Cubes to a known state
    - Note: this step is performed in the *Kinesis* app
    1. Home the rotation stage
    2. Set the rotation stage to 30 deg
    3. Latch the NanoTracks to the center of their ranges
    4. Set "in-z" and "out-z" to their last known level
16. Reset the FiberLock to a known state
    - Note: this step is performed in the *Kangoo* app
    1. Stop at the center of its range
    2. Disable automatic relocking (found in the "hidden parameters")
17. Setup the broadening stage
    1. Enable output of the Nufern amplifier at 0%
    2. Enable the FiberLock by selecting the "search" button in the Kangoo GUI
    3. Enable the NanoTracks by selecting the "track" button in the Kinesis GUI
    4. Turn up the Nufern amplifier to 50% in increments of 10% while confirming that the FiberLock and NanoTracks are locked and tracking
    5. Close the FiberLock's Kangoo GUI
    6. Adjust the rotation stage until the dispersive wave is visible on the OSA
    7. Close the Kinesis GUI
18. Start "broadening_stage.py"
19. Start "spectral_shaper.py"
    - Schedule optimizations as needed

If the RIO frequency (optical lock) needs to be adjusted,
1. Stop the "broadening_stage.py" and "spectral_shaper.py" scripts
2. Latch the FiberLock and NanoTracks
3. Move the Nufern to 0% and disable
4. Unlock the "Optical" signal
5. Move the frequency by adjusting the "Offset DAC" with the scroll wheel
6. Lock the "Optical" signal
7. Confirm that the filter cavity is still locked
8. Follow the startup instructions starting at "17"

