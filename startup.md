The following lists the procedure for turning on/off the astrocomb system. The one-off commands needed to enact these instructions remotely are contained within "Scripts/Misc/misc.py".

-----------------------------------------------------------------------

Startup
-------

1. Check that the liquid chiller is on
2. Check that the database software (mongoDB, couchbase) is running on the computer
3. Set the IM bias to the last known level
4. Enable ILX 1's outputs
    1. CH1: RIO temperature controller
    2. CH2: RIO laser current controller
    3. CH3: RIO amplifier pump laser 1
5. Enable ILX 2's outputs
    1. CH1: Aux. Comb temperature controller
    2. CH2: Aux. Comb pump laser
    3. CH3: Aux. Comb amplifier pump laser 1
    4. CH4: Aux. Comb amplifier pump laser 2
6. Start "monitor_daq.py"
7. Start "comb_generator.py"
    - Note: this script enables the high power RF components
8. Start "rf_oscillators.py"
9. Start "mll_fR.py"
    - Note: the temperature of the oscillator may take some time to stabilize within range of the phase lock servo
10. Start "XEM_GUI.py"
    - Note: this file is currently found within a separate repository in the *Frequency-comb-DPLL* folder.
    1. Lock the "CEO" signal near 0 V
    2. Lock the "Optical" (RIO CW) signal nearest to its historical average after accounting for drift
    3. Enable "Auto Recover" and "Limit DAC Output"
    4. Set "Recovery Threshold" of "Optical" to 7.
11. Enable the Finisar WaveShaper and apply the last know mask
12. Enable the Cybel amplifier (COM8)
    - Note: this step is performed in the *Cybel* app
    1. Enable 1 through 3 in that order
    2. Enable operation without the GUI
    3. Close the GUI
13. Start "filter_cavity.py"
    - Note: depending on the state of the hysteresis, the offset of the HV amplifier may need to be adjusted in order to find the lock point. This is found in the state settings as "y_voltage"
14. Reset the Nufern amplifier to a known state
    - Note: steps 2-9 **cannot** be done remotely. The Nufern control panel is located inside the comb enclosure.
    1. Open the nuAmp GUI, ensure that the output is at 0%
    2. Engage the interlock button (push in)
    3. Turn the key to the off ("0") position
    4. Disconnect power (4-pin)
	5. Turn the key and cycle the interlock button to release trapped charges. Ensure key and interlock are in the off position before proceeding
    6. Reconnect power
    7. Turn the key to the "1" position (the next position after "1")
    8. Disengage the interlock button (pull out)
    9. Turn the key to "enable" position (the next position after "1")
	10. Enable output of the Nufern amplifier at 0% in the nuAmp GUI
	Note: On initialization, the temperature reading will be inaccurate until after the Nufern has been fully enabled in the GUI. It should read room temperature soon after the output has turned on.
15. Turn on the OSA
    - Note: this step **cannot** be done remotely
    1. Press the front panel power button and skip the on-screen instructions.
16. Reset the K-Cubes and T-Cubes to a known state
    - Note: this step is performed in the *Kinesis* app
    1. Home the rotation stage
    2. Set the rotation stage to 55 deg
    3. Latch the NanoTracks to the center of their ranges
    4. Set "in-z" and "out-z" to their last known level
17. Reset the FiberLock to a known state
    - Note: this step is performed in the *Kangoo* app
    1. Stop at the center of its range
    2. Disable automatic re-locking (found in the "hidden parameters")
18. Setup the broadening stage
    1. Enable the FiberLock by selecting the "search" button in the Kangoo GUI
    2. Enable the NanoTracks by selecting the "track" button in the Kinesis GUI
    3. Turn up the Nufern amplifier to 30% in increments of 10% while confirming that the FiberLock and NanoTracks are locked and tracking
    4. Adjust the Nufern power in 1% increments until the dispersive wave is visible on the OSA
	5. Close the FiberLock's Kangoo GUI
    6. Close the Kinesis GUI
19. Start "broadening_stage.py"
20. Start "spectral_shaper.py"
    - Schedule optimizations as needed
21. Start TIMS
    1. Open "Anaconda Prompt"
    2. Enter: cd C:\HPFics
    3. Enter: python -m TIMS.clients.tims_nistlfc


-------------------------------------------------------------------------------

Changing the Offset Frequency
-----------------------------

If the RIO frequency (optical lock) needs to be adjusted,
1. Stop the "broadening_stage.py" and "spectral_shaper.py" scripts
2. Latch the FiberLock and NanoTracks
3. Set the Nufern to 0% and disable
4. Open the AC RP window to the "Optical Lock" tab
4. Enable "Auto-refrech"  and dsiable the "lock"
5. Adjust the frequency using the "Offset DAC" slider.
	1. Use the scroll wheel on the mouse to slowly move the frequency
	2. Continue adjusting until the peak in the spectrum has returned to 40 MHz and the "Detected VCO Gain" is green.
6. Enable the lock
7. Confirm that the filter cavity is locked
8. Enable the Nufern at 0%
8. Follow the startup instructions beginning at step "18"


-------------------------------------------------------------------------------

Shutdown
--------

This is mostly just the startup in reverse.
1. Stop "spectral_shaper.py"
2. Stop "broadening_stage.py"
3. Shutdown the broadening stage
    1. Open the Kinesis GUI
    2. Open the FiberLock's Kangoo GUI
    3. Turn down the Nufern amplifier to 0% in the nuAmp GUI
    4. Disable the NanoTracks by selecting the "latch" button in the Kinesis GUI
    5. Disable the FiberLock by unselecting the "lock" button in the Kangoo GUI
    6. Disable output of the Nufern amplifier
4. Turn off the OSA
    - Note: this step **cannot** be done remotely
    1. Press the front panel power button and follow the on-screen instructions.
5. Disable the Nufern amplifier
    - Note: steps 1-3 **cannot** be done remotely. The nufern control panel is located inside the comb enclosure.
    1. Ensure that the output is at 0% and disabled in the nuAmp GUI
    2. Depress the interlock button
    3. Turn the key to the off ("0") position
6. Stop "filter_cavity.py"
7. Disable the Cybel amplifier (COM8)
    - Note: this step is performed in the *Cybel* app
    1. Disable 3 through 1 in that order. Do not change the pump current settings.
8. Stop "XEM_GUI.py"
    1. Disable the "CEO" lock in the GUI
    2. Disable the "Optical" (RIO CW) lock in the GUI
    3. Close the window
9. Stop "mll_fR.py"
10. Stop "rf_oscillators.py"
11. Stop "comb_generation.py"
12. Disable the high power RF components
    1. Navigate to "192.168.0.2", login with the default credentials
    2. Disable load 1 (Acopian 2, 12V)
13. Stop "monitor_daq.py"
14. Disable ILX 2's outputs
    1. CH4: Aux. Comb amplifier pump laser 2
    2. CH3: Aux. Comb amplifier pump laser 1
    3. CH2: Aux. Comb pump laser
    4. CH1: Aux. Comb temperature controller
15. Disable ILX 1's outputs
    1. CH3: RIO amplifier pump laser 1
    2. CH2: RIO laser current controller
    3. CH1: RIO temperature controller
