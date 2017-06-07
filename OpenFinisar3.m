function WSdevice = OpenFinisar3(WS)
% Load the Finisar Waveshaper library, create the device object, and open
% The directory WaveManger installation path and it's sub-directories must
% be in the Matlab path (after the driver is installed).
% D.E. Leaird 29-Jul-10
% 17-Oct-11 Updated for changes in the way the WaveManger API installs
% 11-Mar-12 Updated to include simulation (no connected WaveShaper) option -
%  requires WaveManager API 2.0.4, and set the WaveShaper to Transmit All
%  at startup
% 3-Sep-12 Updated to generalize the installation path / AWG config file,
% allow for multiple AWG's, and return an AWGdevice object that will be
% REQUIRED on Write functions...so we can tell if the write is 'real' or
% 'simulation', as well as determine the port count of the device, and frequency
% range, as well as the device name.
% 17-Oct-12 Updated to include WS3 device;
% 14-Nov-12 Updated to check the Registry path for 64 bit vs. 32-bit
% 23-Jan-13 Updated the wsconfig filename of WS2
% 24-Jan-13 Changed path of the .wsconfig file to the 'standard' used by
%  Finisar, it is no longer necessary to copy these files to the install
%  WaveManager path as was done previously
%
%       Example call:  device = OpenFinisar3('WS1');     % 'WS1'
%       corresponds to the 1000s, 1x1 WaveShaper.

WS0 = 'SN93_4000S.wsconfig';       %Test config file from Finisar
WS1 = 'SN058038.wsconfig';         %1000s - 1x1 WaveShaper
WS2 = 'SN079908.wsconfig';         %4000s - 1x4 C+L
WS3 = 'WS200339.wsconfig';         %1000s/sp - 1x1 Single Polarization
WS4 = 'WS200484.wsconfig';          %1000s/sp @ 1um DEMO
% Find the WaveManager install path from the registry
try
    WaveManagerInstallPath = winqueryreg('HKEY_LOCAL_MACHINE','Microsoft\Windows\CurrentVersion\WaveManager','Path');      
catch ME
    if (strcmp(ME.message,'Specified key is invalid.'))
        try
            WaveManagerInstallPath = winqueryreg('HKEY_LOCAL_MACHINE','SOFTWARE\Wow6432Node\WaveManager','Path');
        catch ME1
            if (strcmp(ME1.message,'Specified key is invalid.'))
                try
                    WaveManagerInstallPath = winqueryreg('HKEY_LOCAL_MACHINE','SOFTWARE\Wavemanager','Path');
                catch ME2
                    if (strcmp(ME2.message,'Specified key is invalid.'))
                        fprintf(1,'Error in determining the registry key; terminating.\n');
                        return
                    else
                        fprintf(1','Error in determining the Wavemanager path from the registry (#3); terminating.\n');
                        return
                    end
                end
            else
                fprintf(1,'Error in determing the Wavemanager path from the Registry (#2); terminating.\n');
                return
            end
        end
    else
        fprintf(1,'Error in determing the Wavemanager Path from the Registry; terminating.\n');
        return
    end
end
%  Determine the Current version of WaveManager
try
    WaveManagerVersion = winqueryreg('HKEY_LOCAL_MACHINE','SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\WaveManager','DisplayVersion');
catch ME
    if (strcmp(ME.message,'Specified key is invalid.'))
        WaveManagerVersion = winqueryreg('HKEY_LOCAL_MACHINE','SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\WaveManager','DisplayVersion');
    else
        fprintf(1,'Error in determing the Wavemanager Version from the Registry; terminating.\n');
        return
    end
end
%  Find %appdata% from the Registry
try
    AppDataDirectory = winqueryreg('HKEY_CURRENT_USER','Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders','AppData');
catch ME
    if (strcmp(ME.message,'Specified key is invalid.'))
        fprintf(1,'Error determining the AppData directory from the Registry; terminating.\n');
        return
    end
end

PeriodLocation = strfind(WaveManagerVersion,'.');
MajorVersion = eval(WaveManagerVersion(1:PeriodLocation(1)-1));
MinorVersion = eval(WaveManagerVersion(PeriodLocation(1)+1:PeriodLocation(2)-1));
SubVersion   = eval(WaveManagerVersion(PeriodLocation(2)+1:length(WaveManagerVersion)));
if ~((MajorVersion > 2) || ...
     ((MajorVersion >= 2) && (MinorVersion > 0)) || ...
     ((MajorVersion >= 2) && (MinorVersion >= 0) && (SubVersion >= 4)))
    fprintf(1,'The WaveManager version must be 2.0.4 or higher...exiting.\n');
    return
end

if (strcmp(WS,'WS0'))          %Check user configuration selection, and point to the Config FILE
    WS = WS0;
elseif (strcmp(WS,'WS1'))
    WS = WS1;
elseif (strcmp(WS,'WS2'))
    WS = WS2;
elseif (strcmp(WS,'WS3'))
    WS = WS3;
elseif (strcmp(WS,'WS4'))
    WS = WS4;
else
    fprintf(1,'\nIncorrect WaveShaper configuration selected; exiting.\n');
    return;
end

%Load the external library required for communication with the WaveShaper
% only if the library is NOT already loaded
if ~(libisloaded('wslib'))
    loadlibrary('wsapi','include/ws_api.h','alias','wslib');
end

%Create the WaveShaper device
%  First make the unique name from the config file name (which has the
%  serial number)
PeriodLocation = strfind(WS,'.');
WSname = strcat('ws',WS(1:PeriodLocation-1));
WSdevice.Name = WSname;                        %WSdevice structure - name field

%Create the WaveShaper
[errcode, ~, ~] = calllib('wslib','ws_create_waveshaper',WSname,strcat(AppDataDirectory,'\WaveManager\wsconfig\',WS));
if (errcode < 0)
    fprintf(1,'Error Creating the Device...error %i\n.',errcode);
    return
end

%Attempt to Open the WaveShaper device
[errcode,~] = calllib('wslib','ws_open_waveshaper',WSname);
WSdevice.Simulation = false;               %Simulation = False is the default
if (errcode == -38)         %WS not Found...Delete the ws object, and re-create / open for simulation
    [errcode,~] = calllib('wslib','ws_delete_waveshaper',WSname);
    if ((errcode < 0) && (errcode ~= -38))
        fprintf(1,'Error Deleteing the waveshaper...error %i\n.',errcode);
        return
    end
    [errcode, ~, ~] = calllib('wslib','ws_create_waveshaper_forsimulation',WSname,strcat(AppDataDirectory,'\WaveManager\wsconfig\',WS));
    if (errcode < 0)
        fprintf(1,'Error Creating the Device for Simulation...error %i\n.',errcode);
        return
    end
    [errcode,~] = calllib('wslib','ws_open_waveshaper',WSname);
    if (errcode < 0)
        fprintf(1,'Error Opening the waveshaper for simulation...error %i\n.',errcode);
        return
    end    
    WSdevice.Simulation = true;
elseif (errcode < 0)
    fprintf(1,'Error Opening the waveshaper...error %i\n.',errcode);
    return
end

%Get the port count
[errcode, ~, NumPorts] = calllib('wslib','ws_get_portcount',WSname, 0);
if (errcode < 0)
    fprintf(1,'Error getting the number of ports...error %i\n.',errcode);
    return
end
WSdevice.NumPorts = NumPorts;

%Get the frequency range
[errcode, ~, startf, stopf] = calllib('wslib','ws_get_frequencyrange',WSname, 0, 0);
if (errcode < 0)
    fprintf(1,'Error getting the frequency range...error %i\n.',errcode);
    return
end
WSdevice.StartF = startf;
WSdevice.StopF = stopf;

%Load a predefined profile - transmit all, on Port 1
[errcode,~] = calllib('wslib','ws_load_predefinedprofile',WSname,2,0,0,0,1);      %Transmit, Ignore Center, BW, Amp, Set Port =1
if (errcode < 0)
   fprintf(1,'Error Loading Transmit All Predefined Profile...error %i\n.',errcode);
   return
end  
    
return
