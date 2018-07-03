'''
A port of Finisar's wsapi.py
'''

# %% Import Modules
import os

import ctypes
wsapi = None

# %% Import DLLs

finisar = os.path.dirname(__file__)

#ftd2xx = ctypes.CDLL(os.path.join(finisar,'ftd2xx.dll'))
#ws_cheetah = ctypes.CDLL(os.path.join(finisar,'ws_cheetah.dll'))
wsapi = ctypes.CDLL(os.path.join(finisar,'wsapi.dll'))


# %% WS1000

class WS1000():
    def __init__(self,config_file, name='ws1'):
        self.wsconfig = os.path.join(finisar,config_file)
        self.name = name
        ws_create_waveshaper(self.name, self.wsconfig)
        self.frequency_range = ws_get_frequencyrange(self.name)

    def parse_wsp(self):
        pass

    def format_wsp(self):
        pass
    
    def filter_profile(self):
        pass

# %% Constants
WS_SUCCESS =                0       # success
WS_ERROR =                  -1      # general Error
WS_INTERFACE_NOTSUPPORTED = -2      # interface not supported
WS_NULL_PARAM =             -3      # null input
WS_UNKNOWN_NAME =           -4      # name cannot be resolved
WS_NO_ITEM =                -5      # no such item
WS_INVALID_CID =            -6      # invalid class id
WS_INVALID_IID =            -7      # invalid interface id
WS_NULL_POINTER =           -8      # null pointer
WS_BUFFEROVERFLOW =         -9      # buffer overflow
WS_WRONGSTATE =             -10     # wrong state
WS_NO_THREADPOOL =          -11     #  thread pool
WS_NO_DIRECTORY =           -12     # no directory
WS_BUSY =                   -16     # busy
WS_NULL_BUFFER =            -17     # buffer is null
WS_NO_SUCH_FIELD =          -18     # no such field
WS_NO_SUCH_PROPERTY =       -19     # no such property
WS_IO_ERROR =               -20     # IO error
WS_TIMEOUT =                -21     # timeout
WS_ABORTED =                -22     # aborted
WS_LOADMODULE_ERROR =       -23     # load module failed
WS_GETPROCESS_ERROR =       -24     # get process error
WS_OPEN_PORT_FAILED =       -25     # failed to open port
WS_NOT_FOUND =              -26     # not found
WS_OPEN_FILE_FAILED =       -27     # failed to open file
WS_FILE_TOOLARGE =          -28     # file size too large
WS_INVALIDPORT =            -29     # invalid port number
WS_INVALIDFREQ =            -30     # invalid frequency
WS_INVALIDATTN =            -31     # invalid attenuation
WS_INVALIDPROFILE =         -32     # other profile error
WS_INVALIDSPACING =         -33     # invalid freq space
WS_NARROWBANDWIDTH =        -34     # bandwidth < 0.010 THz
WS_OPENFAILED =             -35     # open failed
WS_OPTION_ERROR =           -36     # option error
WS_COMPRESS_ERROR =         -37     # compress error
WS_WAVESHAPER_NOT_FOUND =   -38     # WaveShaper not found
WS_WAVESHAPER_CMD_ERROR =   -39     # command to ws error
WS_NOT_SUPPORTED =          -40     # function not supported
WS_DUPLICATE_NAME =         -41     # duplicate name
WS_INVALIDFIRMWARE =        -42     # invalid firmware format
WS_INCOMPATIBLEFIRMWARE =   -43     # firmware ver incompatible
WS_OLDERFIRMWARE =          -44     # firmware ver too old

LOADFLAG_DEFAULT    = 0
LOADFLAG_WAVESHAPER = 1
LOADFLAG_FLEXGRID   = 2

PROFILE_TYPE_BLOCKALL = 1
PROFILE_TYPE_TRANSMIT = 2
PROFILE_TYPE_BANDPASS = 3 
PROFILE_TYPE_BANDSTOP = 4
PROFILE_TYPE_GAUSSIAN = 5

# %% WaveShaper API

def ws_create_waveshaper(name, wsconfig):
    p = ctypes.create_string_buffer(name.encode('utf-8'))
    rc = wsapi.ws_create_waveshaper(p, wsconfig.encode('utf-8'))
    if (rc == WS_SUCCESS):
        pass# Connection to WaveShaper successfully established
    elif (rc == WS_DUPLICATE_NAME):
        pass
    else:
        raise Exception('Error creating a WaveShaper object instance with the user specified name. Code {:}'.format(rc))

def ws_delete_waveshaper(name):
    rc = wsapi.ws_delete_waveshaper(name.encode('utf-8'))
    if (rc == WS_SUCCESS):
        pass # Command successfully executed
    elif (rc == WS_WAVESHAPER_NOT_FOUND):
        pass # WaveShaper object does not exist
    else:
        raise Exception('Error deleting the WaveShaper object. Code {:}'.format(rc))

def ws_open_waveshaper(name):
    rc = wsapi.ws_open_waveshaper(name.encode('utf-8'))
    if (rc == WS_SUCCESS):
        pass #  Command successfully executed
    elif (rc == WS_WAVESHAPER_NOT_FOUND):
        raise Exception('Could not open the WaveShaper. Object does not exist. Code {:}'.format(rc)) # WaveShaper object does not exist
    elif (rc == WS_OPENFAILED):
        raise Exception('Could not open the Waveshaper. May be a connection problem. Code {:}'.format(rc)) # Could not open the WaveShaper. May be a connection problem.
    else:
        raise Exception('Error opening the WaveShaper object or establishing the connection to the defined WaveShaper object. Code {:}'.format(rc))

def ws_close_waveshaper(name):
    rc = wsapi.ws_close_waveshaper(name.encode('utf-8'))
    if (rc == WS_SUCCESS):
        pass # Command successfully executed)
    elif (rc == WS_WAVESHAPER_NOT_FOUND):
        pass # WaveShaper object does not exist)
    else:
        raise Exception('Error closing or disconnecting from the WaveShaper device. Code {:}'.format(rc))

def ws_get_frequencyrange(name):
    f1 = ctypes.c_float(0.0)
    f2 = ctypes.c_float(0.0)
    rc = wsapi.ws_get_frequencyrange(name.encode('utf-8'), ctypes.pointer(f1), ctypes.pointer(f2))
    if (rc == WS_SUCCESS):
        return (f1.value, f2.value) #  Command successfully executed
    elif (rc == WS_WAVESHAPER_NOT_FOUND):
        raise Exception('Error getting the start and stop frequency of the WaveShaper. WaveShaper object does not exist. Code {:}'.format(rc)) #  WaveShaper object does not exist
    else:
        raise Exception('Error getting the start and stop frequency of the WaveShaper. Code {:}'.format(rc))

def ws_load_profile(name, wsptext):
    rc =  wsapi.ws_load_profile(name.encode('utf-8'), wsptext.encode('utf-8'))
    if (rc == WS_SUCCESS):
        pass # Command successfully executed
    elif (rc == WS_WAVESHAPER_NOT_FOUND):
        raise Exception('Error applying WSP filter. WaveShaper object does not exist. Code {:}.'.format(rc)) # WaveShaper object does not exist
    elif (rc == WS_INVALIDPORT):
        raise Exception('Error applying WSP filter. Port number is not valid. Code {:}.'.format(rc)) # Port number is not valid
    elif (rc == WS_INVALIDFREQ):
        raise Exception('Error applying WSP filter. Frequency specified out of range. Code {:}.'.format(rc)) # Frequency specified out of range
    elif (rc == WS_INVALIDATTN):
        raise Exception('Error applying WSP filter. Attenuation is not valid (e.g. negative value). Code {:}.'.format(rc)) # Attenuation is not valid (e.g. negative value)
    elif (rc == WS_INVALIDSPACING):
        raise Exception('Error applying WSP filter. Frequencies not incremented in 0.001 THz step. Code {:}.'.format(rc)) # Frequencies not incremented in 0.001 THz step
    elif (rc == WS_NARROWBANDWIDTH):
        raise Exception('Error applying WSP filter. Bandwidth of frequencies to the same port is less than 0.010 THz. Code {:}.'.format(rc)) # bandwidth of frequencies to the same port is less than 0.010 THz
    elif (rc == WS_INVALIDPROFILE):
        raise Exception('Error applying WSP filter. Other parsing error. Code {:}.'.format(rc)) # Other parsing error
    elif (rc == WS_OPENFAILED):
        raise Exception('Error applying WSP filter. Could not open the WaveShaper. May be a connection problem. Code {:}.'.format(rc)) # Could not open the WaveShaper. May be a connection problem.
    elif (rc == WS_WAVESHAPER_CMD_ERROR):
        raise Exception('Error applying WSP filter. Error response from WaveShaper. May be communication corruption. Code {:}.'.format(rc)) # Error response from WaveShaper. May be communication corruption.
    else:
        raise Exception('Error applying WSP filter. Code {:}.'.format(rc))
    
def ws_load_predefinedprofile(name, filtertype, center=0.0, bandwidth=0.0, attn=0.0, port=0):
    '''
    Filter Type                 Parameters                              Description
    PROFILE_TYPE_BLOCKALL (1)   type                                    Block the entire optical spectrum of the WaveShaper.
    PROFILE_TYPE_TRANSMIT (2)   type, port                              Transmit the entire optical spectrum to the desired output port.
    PROFILE_TYPE_BANDPASS (3)   type, center, bandwidth, attn, port     Band pass filter.
    PROFILE_TYPE_BANDSTOP (4)   type, center, bandwidth, port           Band stop filter.
    PROFILE_TYPE_GAUSSIAN (5)   type, center, bandwidth, attn, port     Gaussian filter.
    '''
    rc = wsapi.ws_load_predefinedprofile(name.encode('utf-8'), filtertype, ctypes.c_float.from_param(center), ctypes.c_float.from_param(bandwidth), ctypes.c_float.from_param(attn), port)	
    if (rc == WS_SUCCESS):
        pass # Command successfully executed
    elif (rc == WS_WAVESHAPER_NOT_FOUND):
        raise Exception('Error applying WSP filter. WaveShaper object does not exist. Code {:}.'.format(rc)) # WaveShaper object does not exist
    elif (rc == WS_INVALIDPORT):
        raise Exception('Error applying WSP filter. Port number is not valid. Code {:}.'.format(rc)) # Port number is not valid
    elif (rc == WS_INVALIDFREQ):
        raise Exception('Error applying WSP filter. Frequency specified out of range. Code {:}.'.format(rc)) # Frequency specified out of range
    elif (rc == WS_INVALIDATTN):
        raise Exception('Error applying WSP filter. Attenuation is not valid (e.g. negative value). Code {:}.'.format(rc)) # Attenuation is not valid (e.g. negative value)
    elif (rc == WS_INVALIDSPACING):
        raise Exception('Error applying WSP filter. Frequencies not incremented in 0.001 THz step. Code {:}.'.format(rc)) # Frequencies not incremented in 0.001 THz step
    elif (rc == WS_NARROWBANDWIDTH):
        raise Exception('Error applying WSP filter. Bandwidth of frequencies to the same port is less than 0.010 THz. Code {:}.'.format(rc)) # bandwidth of frequencies to the same port is less than 0.010 THz
    elif (rc == WS_INVALIDPROFILE):
        raise Exception('Error applying WSP filter. Other parsing error. Code {:}.'.format(rc)) # Other parsing error
    elif (rc == WS_OPENFAILED):
        raise Exception('Error applying WSP filter. Could not open the WaveShaper. May be a connection problem. Code {:}.'.format(rc)) # Could not open the WaveShaper. May be a connection problem.
    elif (rc == WS_WAVESHAPER_CMD_ERROR):
        raise Exception('Error applying WSP filter. Error response from WaveShaper. May be communication corruption. Code {:}.'.format(rc)) # Error response from WaveShaper. May be communication corruption.
    else:
        raise Exception('Error applying WSP filter. Code {:}.'.format(rc))

def ws_get_profile(name):
    p = ctypes.create_string_buffer(512*1024)
    i = ctypes.c_int(512*1024)
    rc = wsapi.ws_get_profile(name.encode('utf-8'), p, ctypes.pointer(i))
    if (rc == WS_SUCCESS):
        return p.raw.strip("\x00") # Command successfully executed
    elif (rc == WS_WAVESHAPER_NOT_FOUND):
        raise Exception('Error getting the currently loaded filter profile. WaveShaper object does not exist. Code {:}'.format(rc))
    else:
        raise Exception('Error getting the currently loaded filter profile. Code {:}'.format(rc))


############################################################	
def ws_load_firmware(name, firmware):
	if(wsapi==None):
		return -1
	return wsapi.ws_load_firmware(name.encode('utf-8'), firmware.encode('utf-8'))

def ws_send_cmd(name, cmd):
	if(wsapi==None):
		return -1
	p = ctypes.create_string_buffer(1024)	
	i = ctypes.c_int(1024)
	rc = wsapi.ws_send_command(name.encode('utf-8'), cmd.encode('utf-8'), p, ctypes.pointer(i))
	if(rc==0):
		return p.raw.strip("\x00")
	else:
		return ""	

def ws_get_sno(name):
	if(wsapi==None):
		return -1
	p = ctypes.create_string_buffer(256)
	rc = wsapi.ws_get_sno(name.encode('utf-8'), p, 256)	
	if(rc==0):
		return p.raw.strip("\x00")
	else:
		return ""

def ws_get_portcount(name):
	if(wsapi==None):
		return -1
	i = ctypes.c_int(0)
	rc = wsapi.ws_get_portcount(name.encode('utf-8'), ctypes.pointer(i))	
	if(rc==0):
		return i.value
	else:
		return 0

def ws_get_version():
	if(wsapi==None):
		return -1
	wsapi.ws_get_version.restype = ctypes.c_char_p
	return wsapi.ws_get_version()

def ws_get_configversion(name):
	if(wsapi==None):
		return -1
	p = ctypes.create_string_buffer(1024)	
	rc = wsapi.ws_get_configversion(name.encode('utf-8'), p)
	if(rc==0):
		return p.raw.strip("\x00")
	else:
		return ""	

def ws_load_profile_for_modeling(name, wsptext, port):
	if(wsapi==None):
		return -1
	return wsapi.ws_load_profile_for_modeling(name.encode('utf-8'), wsptext, port, 0)

def ws_get_model_profile(name):
	if(wsapi==None):
		return -1
	p = ctypes.create_string_buffer(512*1024)
	i = ctypes.c_int(512*1024)
	rc = wsapi.ws_get_model_profile(name.encode('utf-8'), p, ctypes.pointer(i))
	if(rc==0):
		return p.raw.strip("\x00")
	else:
		return ""

