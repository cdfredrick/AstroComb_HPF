function deviceobject = OpenYokogawaOSA(gpibboardindex, deviceaddress)
% Prepare and open a GPIB object for the Ando OSA.
% Use board GPIBBOARDINDEX, and electronics at address DEVICEADDRESS
% Returns DEVICEOBJECT that is used in subsequent calls.
% Remember to close the instrument when finished with fclose(DEVICEOBJECT)
% D.E. Leaird, 3-Jun-04
deviceobject = gpib('ni',gpibboardindex, deviceaddress, 'InputBufferSize', 500000, 'EOIMode', 'on', 'EOSCharCode', 'LF', 'EOSMode', 'none', 'Timeout', 60.0);
fopen(deviceobject)