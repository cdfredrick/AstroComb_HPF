function status = WriteFinisarRelative3(WaveShaper,relamp,phase,port)
% Write the amp and phase, and port vectors to the Finisar Waveshaper
%  Example call:  status = WriteFinisarRelative3(WaveShaper,amp,phase,port)
%        where amp, phase, and port are vectors that specify the
%        attenuation, phase, and output port at each frequency.  WaveShaper
%        is the WaveShaper device name (from the CreateWaveShaper
%        function).  Returns the status = 0 if the function works.
%        Here relamp is in the range [0..1].

%D.E. Leaird, 29-Jul-10; update 4-Aug-10 to set Maximum attenuation to 60
% Updated 11-Mar-12 to utilize expanded amplitude sensitivty available with
% API 2.0.4; also using the check of the WS frequency range.
% Updated 13-Sep-12, Update to specifically check which WaveShaper device the vectors
%are being sent to; also include the port information.  Simulation mode
%included - Note that this is not general.  Simulation is invoked when no
%WaveShaper is connected; if a WaveShaper is connected normal communication
%occurs.

%Starting with API V2.0.4 it is possible to speed up the communication with
%the WaveShaper CONSIDERABLY by only writing values that change!  Here we
%are writing ALL values very time.  We should consider writing a different
%script to take into account this available functionality!

%Check to make sure the vectors amp, phase, and port are the correct dimensions,
%and have values within the correct range.
NumPixels = ceil((WaveShaper.StopF-WaveShaper.StartF).*1000);
if (~ismatrix(relamp))                   %This function only works on vectors.
    fprintf(1,'The Amplitude values must be a vector!\n');
    status = -104;
    return
end
if (min(size(relamp)) ~= 1)              %Make sure VALUE is not 2x2
    fprintf(1,'The Amplitude values must be a vector!\n');
    status = -104;
    return
end
if (length(relamp) ~= NumPixels)               %Must use the correct number of elements.
    fprintf(1,'The length of the Amplitude vector must be %i!\n', NumPixels);
    status = -105;
    return
end
if (max(relamp) > 1)                  %Maximum attenuation exceeded.
    fprintf(1,'The maximum of the Amplitude vector is 1!\n');
    status = -102;
    return
end
if (min(relamp) < 0)                     %Minimum attenuation limit
    fprintf(1,'The minimum of the Amplitude vector is 0!\n');
    status = -103;
    return
end

if (~ismatrix(phase))                   %This function only works on vectors.
    fprintf(1,'The Phase values must be a vector!\n');
    status = -104;
    return
end
if (min(size(phase)) ~= 1)              %Make sure VALUE is not 2x2
    fprintf(1,'The Phase values must be a vector!\n');
    status = -104;
    return
end
if (length(phase) ~= NumPixels)               %Must use the correct number of elements.
    fprintf(1,'The length of the Phase vector must be %i!\n', NumPixels);
    status = -105;
    return
end
if (max(phase) > (2*pi))                  %Maximum phase exceeded.
    fprintf(1,'The maximum of the Phase vector is 2pi!\n');
    status = -102;
    return
end
if (min(phase) < 0)                     %Minimum phase limit
    fprintf(1,'The minimum of the Phase vector is 0!\n');
    status = -103;
    return
end

if (~ismatrix(port))                   %This function only works on vectors.
    fprintf(1,'The Port values must be a vector!\n');
    status = -104;
    return
end
if (min(size(port)) ~= 1)              %Make sure VALUE is not 2x2
    fprintf(1,'The Port values must be a vector!\n');
    status = -104;
    return
end
if (length(port) ~= NumPixels)               %Must use the correct number of elements.
    fprintf(1,'The length of the Port vector must be %i!\n', NumPixels);
    status = -105;
    return
end
if (max(port) > WaveShaper.NumPorts)                  %Maximum Port exceeded.
    fprintf(1,'The maximum number of Ports is %i!\n', WaveShaper.NumPorts);
    status = -106;
    return
end
if (min(port) < 1)                     %Minimum Port limit
    fprintf(1,'The minimum of the Port vector is 1!\n');
    status = -107;
    return
end

amp = -10.*log10(relamp);
amp(isinf(amp)) = 60;       %Conversion to log may result in Inf values - set any Inf to 60.

%Create the buffer
% The format is freq (xxx.xxx) TAB amp (xx.xxx) TAB phase (x.xxxxxx) TAB port (x) NL
% (24 char per line)
buffer = [num2str(WaveShaper.StartF,'%7.3f') char(9) num2str(amp(1),'%6.3f') char(9) num2str(phase(1),'%8.6f') char(9) num2str(port(1),'%1i') char(10)];
for k = 2:NumPixels
    buffer = [buffer num2str((WaveShaper.StartF+0.001*k-0.001),'%7.3f') char(9) num2str(amp(k),'%6.3f') char(9) num2str(phase(k),'%8.6f') char(9) num2str(port(k),'%1i') char(10)];
end

[errcode, ~, temp2] = calllib('wslib','ws_load_profile',WaveShaper.Name, buffer);
if (errcode < 0)
    fprintf(1,'Error sending data to the Device...error %i\n.',errcode);
    status = errcode;
    return
end

if (WaveShaper.Simulation)                  %Execute the model
    [errcode, ~, ~, temp3] = calllib('wslib','ws_load_profile_for_modeling',WaveShaper.Name, buffer, 1, 0);
    if (errcode < 0)
        fprintf(1,'Error Executing the Model...error %i\n.',errcode);
        status = errcode;
        return
    end
end

status = 0;
return