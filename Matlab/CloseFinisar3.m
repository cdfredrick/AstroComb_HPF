function CloseFinisar3(Device,Unload)
% Close the Finisar Waveshaper, unload the library if requested
% D.E. Leaird, 29-Jul-10; Updated 7-Sep-12 to include a specific device
%     Example call: CloseFinisar3(device,1)       %device came from OpenFinisar3, 1=unload library
%                        0 = do not unload the library (may be using
%                        another WaveShaper).

[errcode, temp1] = calllib('wslib','ws_close_waveshaper',Device.Name);
if (errcode < 0)
    fprintf(1,'Error Closing the Device...error %i\n.',errcode);
    return
end
[errcode,temp1] = calllib('wslib','ws_delete_waveshaper',Device.Name);
if (errcode < 0)
    fprintf(1,'Error Deleteing the waveshaper...error %i\n.',errcode);
    return
end

if (Unload)
    unloadlibrary('wslib');
end

return
