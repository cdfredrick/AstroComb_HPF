function DataSet = YokogawaOSA(OSA_Addr)
%Matlab script to read, and save optical spectrum data with auto filenaming
%similar to the scheme used with the LabWindows OSA and FastScope programs.
%  The current directory is used to save data, and a file is created with
%  the last file number used.
% Example call:  data = YokogawaOSA(1);  where 1 is the GPIB address.
%
%D.E. Leaird, 6-Aug-08, modified 10-Feb-10
%A.J. Metcalf, 5-Feb-16, modified for Yokogawa OSA
% Modified 13-Apr-10 to include the possibility to write multiple dates
% files in the same directory starting back at file 1.
% Modified 29-Apr-10 to make sure the file-count file is only looked for in
% the local directory; include the gpib address as a parameter as all other
% functions of this type.

GPIB_Board = 0;
FileNumberFile = '.\YokogawaSpecFiles5.txt';

%See if any files have been saved in this directory (determined by the
%filenumber file being present) / get the last filenumber saved:
FileID=fopen(FileNumberFile,'r');
if (FileID == -1)   %The filenumber file does not exist - create it.
    LastFileNumber = 0;
    FileID = fopen(FileNumberFile,'w');
    fprintf(FileID,'LastFile=%i',LastFileNumber);
else
    %See what the date of file creation was
%     temp=GetFileTime(FileNumberFile,'Local');
temp=1;
    temp=temp.Write;
    if (datenum(temp(1:3)) == today)  %This means the file was created today, and the index should be incremented
        LastFileNumber = fscanf(FileID,'LastFile=%i');  %Read the index
    else                %Start over with a new index.
        LastFileNumber = 0;
        FileID = fopen(FileNumberFile,'w');
        fprintf(FileID,'LastFile=%i',LastFileNumber);
    end
end
fclose(FileID);

%Format the filename to be used (ADmmddyy.xxx):
LastFileNumber = LastFileNumber +1;
Today=date;
FileName=['AD' datestr(Today,'mm') datestr(Today,'dd') datestr(Today,'yy') '.' sprintf('%03i',LastFileNumber)];

%Get the data
OSAID = OpenYokogawaOSA(GPIB_Board,OSA_Addr);
DataSet = ReadYokogawaOSA(OSAID);
fclose(OSAID);
delete(OSAID);
clear OSAID

plot(DataSet(:,1),DataSet(:,2))

save(FileName,'DataSet','-ascii','-tabs','-double');
fprintf(1,'File saved as: %s\n',FileName);

%Save the file number
FileID = fopen(FileNumberFile,'w');
fprintf(FileID,'LastFile=%i',LastFileNumber);
fclose(FileID);
return




%%%%%%%%%%%%%%%%
%Sub-functions

function deviceobject = OpenYokogawaOSA(gpibboardindex, deviceaddress)
% Prepare and open a GPIB object for the Ando OSA.
% Use board GPIBBOARDINDEX, and electronics at address DEVICEADDRESS
% Returns DEVICEOBJECT that is used in subsequent calls.
% Remember to close the instrument when finished with fclose(DEVICEOBJECT)
% D.E. Leaird, 3-Jun-04
deviceobject = gpib('ni',gpibboardindex, deviceaddress, 'InputBufferSize', 1200000, 'EOIMode', 'on', 'EOSCharCode', 'LF', 'EOSMode', 'none', 'Timeout', 30.0);
fopen(deviceobject)
return


function CombinedMatrix = ReadYokogawaOSA(DevObj)
% Read the Ando OSA, trace A, and return power as a function of wavelength.
% Remember to close the instrument when finished with fclose(DEVICEOBJECT)
% D.E. Leaird, 03-Jun-04; Modified 6-Aug-08

%Get vertical data
CmdToOSA = ['CFORM1' char(13)];
fprintf(DevObj,CmdToOSA);
CmdToOSA = [':TRAC[:DATA]:Y? TRA' char(13)];
fprintf(DevObj,CmdToOSA);
temp = fscanf('');
array = sscanf(temp,'%e,');
numpoints1 = array(1);
power = array(2:length(array));

%Get horizontal data
CmdToOSA = [':TRAC[:DATA]:X? TRA' char(13)];
fprintf(DevObj,CmdToOSA);
temp = fscanf(DevObj);
array = sscanf(temp,'%e,');
numpoints2 = array(1);
wavelength = array(2:length(array));
CombinedMatrix = [wavelength power];

%Make sure both lengths agree)
if (numpoints1 == numpoints2)
   return
else
   wavelength = 0;
   power = 0;
   CombinedMatrix = [wavelength power];
   return
end

return
