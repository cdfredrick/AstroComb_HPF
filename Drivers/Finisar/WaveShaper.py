'''
A port of Finisar's wsapi.py
'''

# %% Import Modules
import os
import numpy as np
import ctypes
import requests
import json


# %% Constants
SPEED_OF_LIGHT = 299792458 # m/s
SPEED_OF_LIGHT_NM_THZ = SPEED_OF_LIGHT*1e9*1e-12 # nm THz

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
WS_NO_THREADPOOL =          -11     # thread pool
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


# %% Helper Functions
def format_wsp(freq, attn, phase, port, wrap=True):
    '''The WaveShaper Preset (WSP) file format allows the user to specify
    the spectral amplitude and phase of the WaveShaper optical response,
    and, in the case of the WaveShaper 4000S, direct the output light to a
    particular port.

    The format of a WSP filter is a tab delimited text string with four
    columns:
        Absolute Frequency (THz), Attenuation (dB), Phase (rad) and Port Number.

    The following rules must be followed to create a valid WSP
    filter/switch specification:
        1. The frequencies are defined in absolute values, in units of THz,
        and with a resolution of 0.001 THz (1 GHz). The frequency range
        which can be specified must be less than, or equal to, the
        operating range of the WaveShaper. (For example, for C-band
        WaveShapers, the frequency range in the file should be within the
        range of 191.250 to 196.275 THz.) Frequency values must increment
        in 0.001 THz (1 GHz) steps. A partial definition that covers a
        continuous range within the valid frequency range is also allowed.
        2. The port needs to be defined in the fourth column. Selecting
        Port 0 sets that frequency to “Block”. Please ensure that the ports
        specified in this column are ports that are available on the
        WaveShaper (“0” and “1” are valid in the case of a WaveShaper 1000,
        values 0-4 are valid for a WaveShaper 4000).
        3. The minimum bandwidth of each band of frequencies that is to be
        sent to a particular output port needs to be at least 0.010 THz
        (10 GHz).
        4. The WSP input file will be checked during ws_load_profile
        function call. An error code will be returned if the WSP input
        fails during the validation process. This is discussed in detail in Section 4.5

    freq:
        Absolute Frequency (THz)
        Range:
            [WaveShaper Minimum Frequency, WaveShaper Maximum Frequency]
        These can be interrogated from the unit using the
        ws_get_frequencyrange
    attn:
        Attenuation (dB)
        Range:
            [0, 40]
        1. The requested Attenuation must be a positive number in the range
        0 to 40 dB.
        2. Requested Attenuation values of greater than 40 dB will be set
        to the ’Block’ state (nominally 50 dB).
        3. Requested Attenuations between 35 and 40dB will be attempted to
        be set but if the requested attenuation is greater than the
        capability of the WaveShaper chassis, the attenuation will be set
        to the ‘Block’ state for that frequency.
        4. Attempts to program gain (requested attenuation less than 0 dB)
        will be truncated to 0 dB.
    phase:
        Phase (rad)
        Range:
            [0, 2pi]
        The WSP may specify a phase outside of this range, however, this
        will be re-calculated by the WaveShaper software on interpolation
        as (phase modulo 2π).
    port:
        Port Number
        Range:
            [0, 1 (WS1000) or 4 (WS4000)]
        Port 0 = block
    '''
    # Format data
    freq = ['{:.3f}'.format(item) for item in freq]
    attn = ['{:.1f}'.format(item) for item in attn]
    if (wrap==True):
        phase = wrap_phase(phase)
    phase = ['{:.4f}'.format(item) for item in phase]
    port = ['{:d}'.format(int(item)) for item in port]
    # Create WSP Array
    wsp_array = np.array([freq, attn, phase, port])
    wsp_text = '\n'.join(['\t'.join([item for item in row]) for row in wsp_array.T])
    return wsp_text

def parse_wsp(wsp_text, unwrap=True):
    '''Converts the wsp text string into arrays of numbers

    Returns separate arrays for (freq, attn, phase, and port)
    '''
    wsp_array = np.array([np.array([float(item) for item in row.split('\t')]) for row in wsp_text.strip().split('\n')]).T
    if (unwrap==True):
        return (wsp_array[0], wsp_array[1], unwrap_phase(wsp_array[2]), wsp_array[3].astype(np.int))
    else:
        return (wsp_array[0], wsp_array[1], wsp_array[2], wsp_array[3].astype(np.int))

def wrap_phase(phase):
    '''Phase modulo 2 pi. Reverse of unwrap_phase'''
    return np.mod(phase, 2*np.pi)

def unwrap_phase(phase):
    '''Unwrap by changing deltas between values to 2*pi complement. Reverse of
    wrap_phase. Retrieves correct absolute phase up to an arbitrary offset.'''
    phase = np.unwrap(phase, discont=np.pi)
    return phase - phase.mean()


# %% WaveShaper USB API
class WaveShaperUSB():
    def __init__(self):
        self.finisar_path = os.path.dirname(__file__)
        self.wsapi = ctypes.CDLL(os.path.join(self.finisar_path,'wsapi.dll'))

    def ws_create_waveshaper(self, name, wsconfig):
        '''Creates a WaveShaper object instance with a user specified name.

        The user can choose any name containing one or more letters or digits or
        underscore, provided that distinct names are used for each WaveShaper
        device. Note that WS_CREATE_WAVESHAPER object will not open the
        communication port or make connections to the WaveShaper device. Opening a
        connection to the device is done by invoking WS_OPEN_WAVESHAPER function.

        name:
            User specified WaveShaper name. A valid name contains one or more
            letters or digits or underscore. Each WaveShaper object must have a
            unique name.
        wsconfig:
            Path string to configuration file.
        '''
        p = ctypes.create_string_buffer(name.encode('utf-8'))
        rc = self.wsapi.ws_create_waveshaper(p, wsconfig.encode('utf-8'))
        if (rc == WS_SUCCESS):
            pass # Connection to WaveShaper successfully established
        elif (rc == WS_DUPLICATE_NAME):
            print('Error creating a WaveShaper object instance with the user specified name. WaveShaper name already in use. Code {:}'.format(rc)) # WaveShaper name already in use
        else:
            raise Exception('Error creating a WaveShaper object instance with the user specified name. Code {:}'.format(rc))

    def ws_delete_waveshaper(self, name):
        '''This command deletes the WaveShaper object. The WaveShaper object will
        be automatically closed, if it is in open state.

        name:
            Previously created WaveShaper name
        '''
        rc = self.wsapi.ws_delete_waveshaper(name.encode('utf-8'))
        if (rc == WS_SUCCESS):
            pass # Command successfully executed
        elif (rc == WS_WAVESHAPER_NOT_FOUND):
            print('Error deleting the WaveShaper object. WaveShaper object does not exist. Code {:}'.format(rc)) # WaveShaper object does not exist
        else:
            raise Exception('Error deleting the WaveShaper object. Code {:}'.format(rc))

    def ws_open_waveshaper(self, name):
        '''This command opens an existing WaveShaper object and establishes the
        connection to the defined WaveShaper.

        Note that it is optional to call this function before invoking profile
        downloading functions. WaveShaper API will automatically open the
        connection before downloading profile if it is not opened yet. However, it
        is recommended to invoke “ws_open_waveshaper” explicitly for better
        performance, when downloading multiple filter profiles. Downloading speed
        will be increased, as no reconnection is needed between downloading each
        new profile.

        name:
            Previously created WaveShaper name
        '''
        rc = self.wsapi.ws_open_waveshaper(name.encode('utf-8'))
        if (rc == WS_SUCCESS):
            pass #  Command successfully executed
        elif (rc == WS_WAVESHAPER_NOT_FOUND):
            raise Exception('Could not open the WaveShaper. Object does not exist. Code {:}'.format(rc)) # WaveShaper object does not exist
        elif (rc == WS_OPENFAILED):
            raise Exception('Could not open the Waveshaper. May be a connection problem. Code {:}'.format(rc)) # Could not open the WaveShaper. May be a connection problem.
        else:
            raise Exception('Error opening the WaveShaper object or establishing the connection to the defined WaveShaper object. Code {:}'.format(rc))

    def ws_close_waveshaper(self, name):
        '''Close WaveShaper. Disconnect from the WaveShaper device.

        Note that it is optional to call this function. The connection will be
        automatically closed during deletion of WaveShaper object (see
        WS_DELETE_WAVESHAPER).

        name:
            Previously created WaveShaper name
        '''
        rc = self.wsapi.ws_close_waveshaper(name.encode('utf-8'))
        if (rc == WS_SUCCESS):
            pass # Command successfully executed)
        elif (rc == WS_WAVESHAPER_NOT_FOUND):
            print('Error closing or disconnecting from the WaveShaper device. WaveShaper object does not exist. Code {:}'.format(rc)) # WaveShaper object does not exist
        else:
            raise Exception('Error closing or disconnecting from the WaveShaper device. Code {:}'.format(rc))

    def ws_get_frequencyrange(self, name):
        '''Get start and stop frequency of the WaveShaper in THz.

        This allows the user to determine, for instance, if the attached WaveShaper
        is for C- or L-band operation. This is also a useful check to ensure that
        a WSP does not extend beyond the operating range of the unit being
        controlled.

        name:
            Previously created WaveShaper name
        '''
        f1 = ctypes.c_float(0.0)
        f2 = ctypes.c_float(0.0)
        rc = self.wsapi.ws_get_frequencyrange(name.encode('utf-8'), ctypes.pointer(f1), ctypes.pointer(f2))
        if (rc == WS_SUCCESS):
            return (round(f1.value,3), round(f2.value,3)) #  Command successfully executed
        elif (rc == WS_WAVESHAPER_NOT_FOUND):
            raise Exception('Error getting the start and stop frequency of the WaveShaper. WaveShaper object does not exist. Code {:}'.format(rc)) #  WaveShaper object does not exist
        else:
            raise Exception('Error getting the start and stop frequency of the WaveShaper. Code {:}'.format(rc))

    def ws_load_profile(self, name, wsptext):
        '''Apply WSP filter and wait for completion.

        Calculates the filter profile based on WSP-text, then loads filter profile
        to WaveShaper device.

        name:
            Previously created WaveShaper name
        wsptext:
            WSP text string
        '''
        rc =  self.wsapi.ws_load_profile(name.encode('utf-8'), wsptext.encode('utf-8'))
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

    def ws_load_predefinedprofile(self, name, filtertype=PROFILE_TYPE_TRANSMIT, center=0.0, bandwidth=0.0, attn=0.0, port=0):
        '''This function allows the user to apply one of several pre-defined
        filters.

        The spectral profile is calculated based on the input parameters, and then
        is uploaded to the target WaveShaper, waiting for the operation to
        complete.

        name:
            Previously created WaveShaper name
        filtertype:
            Predefine filter type (see filter type table below)
        center:
            Center Frequency (THz). Set to 0.0f, if not used.
        bandwidth:
            Bandwidth (GHz) . Set to 0.0f, if not used.
        attn:
            Attenuation (dB) . Set to 0.0f, if not used. Attenuation must be a
            positive number in the range 0 to 40 dB.
        port:
            Port number. Set to 0, if not used

        Filter Type                 Parameters                              Description
        PROFILE_TYPE_BLOCKALL (1)   type                                    Block the entire optical spectrum of the WaveShaper.
        PROFILE_TYPE_TRANSMIT (2)   type, port                              Transmit the entire optical spectrum to the desired output port.
        PROFILE_TYPE_BANDPASS (3)   type, center, bandwidth, attn, port     Band pass filter.
        PROFILE_TYPE_BANDSTOP (4)   type, center, bandwidth, port           Band stop filter.
        PROFILE_TYPE_GAUSSIAN (5)   type, center, bandwidth, attn, port     Gaussian filter.
        '''
        rc = self.wsapi.ws_load_predefinedprofile(name.encode('utf-8'), filtertype, ctypes.c_float.from_param(center), ctypes.c_float.from_param(bandwidth), ctypes.c_float.from_param(attn), port)
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

    def ws_get_profile(self, name, psize=512*1024, return_psize=False):
        '''Get WSP representation of currently loaded filter profile.

        This function can be used to determine WSP version of a currently-loaded
        filter. This can be useful when a series of partial WSP files have been
        loaded and the user wishes to analyze or save the current status of the
        WaveShaper.

        psize points to the size of the buffer variable as input. Upon completion,
        the size variable will be updated with actual WSP text length. If the
        output size is larger than input size, user should reallocate a larger
        buffer and invoke the function again to get full WSP text.

        name:
            Previously created WaveShaper name
        psize:
            Buffer size
        '''
        p = ctypes.create_string_buffer(psize)
        i = ctypes.c_int(psize)
        rc = self.wsapi.ws_get_profile(name.encode('utf-8'), p, ctypes.pointer(i))
        if (rc == WS_SUCCESS):
            if (return_psize==True):
                return (p.raw.decode('utf-8').rstrip('\x00').strip(), i.value) # Command successfully executed
            else:
                return p.raw.decode('utf-8').rstrip('\x00').strip() # Command successfully executed
        elif (rc == WS_WAVESHAPER_NOT_FOUND):
            raise Exception('Error getting the currently loaded filter profile. WaveShaper object does not exist. Code {:}'.format(rc))
        else:
            raise Exception('Error getting the currently loaded filter profile. Code {:}'.format(rc))


# %% WS1000S (USB)
class WS1000S(WaveShaperUSB):
    def __init__(self, config_file, name='ws1'):
        '''Initialize a WaveShaper object. The act of connecting to a
        WaveShaper will reset the instrument.

        config_file:
            path to .wsconfig file specific to the desired WaveShaper
        '''
    # Initialize USB driver
        super().__init__()
    # Create WaveShaper object
        self.wsconfig = os.path.join(self.finisar_path,config_file)
        self.name = name
        self.ws_create_waveshaper(self.name, self.wsconfig)
    # Get WaveShaper parameters
        self.filter_profile() # populate freq, attn, phase, and port arrays
        self.frequency_range = np.array(self.ws_get_frequencyrange(self.name)) # THz
        self.wavelength_range = np.sort(SPEED_OF_LIGHT_NM_THZ/self.frequency_range) # nm

    def filter_profile(self, set_profile=None, return_profile=True):
        '''Read and write filter profiles to the WaveShaper.

        set_profile:
            a tuple of lists representing frequency, attenuation, phase, and
            port number, or a dictionary containing the information necessary
            to activate a predefined filter.
        '''
        if (set_profile == None):
        # Read profile from WaveShaper
            self.buffer_size = self.ws_get_profile(self.name, psize=1, return_psize=True)[1] # get buffer size
            wsp_profile = self.ws_get_profile(self.name, psize=self.buffer_size) # get ws profile
            (self.freq, self.attn, self.phase, self.port) = parse_wsp(wsp_profile) # parse wsp text
            if (return_profile==True):
                return (self.freq, self.attn, self.phase, self.port) # return data arrays
        elif isinstance(set_profile,dict):
        # Write predefined profile to WaveShaper
            self.ws_load_predefinedprofile(self.name, **set_profile) # write predefined profile
            self.filter_profile(return_profile=False) # update local data arrays
        else:
        # Write custom WSP profile
            self.ws_load_profile(self.name, format_wsp(*set_profile)) # write ws profile
            self.filter_profile(return_profile=False) # update local data arrays

    def phase_profile(self, set_profile=None):
        '''Specifically reads and writes only the phase profile'''
        if (set_profile == None):
        # Read phase profile from WaveShaper
            self.filter_profile(return_profile=False)
            return self.phase
        else:
        # Write custom phase profile
            self.filter_profile(return_profile=False) # update local data arrays
            self.filter_profile(set_profile=(self.freq, self.attn, set_profile, self.port), return_profile=False) # write new phase profile

    def attn_profile(self, set_profile=None):
        '''Specifically reads and writes only the attenuation profile'''
        if (set_profile == None):
        # Read attenuation profile from WaveShaper
            self.filter_profile(return_profile=False)
            return self.attn
        else:
        # Write custom attenuation profile
            self.filter_profile(return_profile=False) # update local data arrays
            self.filter_profile(set_profile=(self.freq, set_profile, self.phase, self.port), return_profile=False) # write new phase profile

    def port_profile(self, set_profile=None):
        '''Specifically reads and writes only the port profile'''
        if (set_profile == None):
        # Read port profile from WaveShaper
            self.filter_profile(return_profile=False)
            return self.port
        else:
        # Write custom port profile
            self.filter_profile(return_profile=False)
            self.filter_profile(set_profile=(self.freq, self.attn, self.phase, set_profile), return_profile=False)


# %% WaveShaper HTTP API (Ethernet)
class WaveShaperHTTP():
    def __init__(self):
        self.timeout = 1 # seconds

    def load_profile(self, ip_address, filter_profile):
        '''Upload filter profile to the WaveShaper.

        HTTP method: POST
        URL: http://<_ip_>/waveshaper/loadprofile
        POST Data: JSON formatted request includes the following fields.
        JSON FIELD      DESCRIPTION
        type            Filter type with one of the following options:
                            wsp, blockall, transmit, bandpass, bandstop, gaussian
        wsp             wsp filter definition string
                        only used when type is wsp
        port            Port value (number)
                        only used when the type is bandpass, bandstop or gaussian
        center          Center frequency in THz (number),
                        only used when the type is bandpass, bandstop or gaussian
        bandwidth       Filter bandwidth in THz (number)
                        only used when the type is bandpass, bandstop or gaussian
        attn            Attenuation in dB (number)
                        only used when the type is bandpass, bandstop or gaussian

        Response: JSON formatted response includes the following fields.
        JSON FIELD      DESCRIPTION
        rc              Result code (number)
        rctext          Result in text format
        sno             WaveShaper serial number
        '''
        count = 0
        while count < 3:
            try:
                result = requests.post('http://'+ip_address+'/waveshaper/loadprofile', json.dumps(filter_profile), timeout=self.timeout)
            except requests.exceptions.Timeout:
                count += 1
            else:
                count = 3
        return result

    def get_profile(self, ip_address):
        '''Retrieve currently loaded WaveShaper filter profile.

        HTTP method: GET
        URL: http://<_ip_>/waveshaper/getprofile
        Response: Currently loaded WaveShaper filter profile encoded in WSP formatted string.
        '''
        count = 0
        while count < 3:
            try:
                result = requests.get('http://'+ip_address+'/waveshaper/getprofile', timeout=self.timeout).text #.json() or .text?
            except requests.exceptions.Timeout:
                count += 1
            else:
                count = 3
        return result

    def dev_info(self, ip_address):
        '''Retrieve information about the WaveShaper.

        HTTP method: GET
        URL: http://<_ip_>/waveshaper/devinfo
        Response: JSON formatted response includes the following fields.

        JSON FIELD      DESCRIPTION
        model           WaveShaper model
        sno             WaveShaper serial number
        ver             Firmware version
        startfreq       Start frequency (number)
        stopfreq        Stop frequency (number)
        ip              Current IP address
        portcount       Number of output port(s) (number)
        rctext          Result in text format
        '''
        count = 0
        while count < 3:
            try:
                result = requests.get('http://'+ip_address+'/waveshaper/devinfo', timeout=self.timeout).json()
            except requests.exceptions.Timeout:
                count += 1
            else:
                count = 3
        return result


# %% WS1000A (Ethernet)
class WS1000A(WaveShaperHTTP):
    def __init__(self, ip_address):
        '''Initialize a WaveShaper object. The HTTP connnection does not
        disturb previously applied filter profiles.

        ip_address:
            IP address to the desired WaveShaper
        '''
    # Initialize HTTP driver
        super().__init__()
        self.ip_address = ip_address
    # Get WaveShaper parameters
        result = self.dev_info(self.ip_address)
        self.frequency_range = np.array([result['startfreq'], result['stopfreq']]) # THz
        self.wavelength_range = np.sort(SPEED_OF_LIGHT_NM_THZ/self.frequency_range) # nm
        (self.freq, self.attn, self.phase, self.port) = parse_wsp(self.get_profile(self.ip_address)) # populate freq, attn, phase, and port arrays
        self.wvl = SPEED_OF_LIGHT_NM_THZ/self.freq

    def filter_profile(self, set_profile=None, return_profile=True):
        '''Read and write filter profiles to the WaveShaper.

        set_profile:
            a tuple of lists representing frequency, attenuation, phase, and
            port number, or a dictionary containing the information necessary
            to activate a predefined filter.
        '''
        if (set_profile is None):
        # Read profile from WaveShaper
            (self.freq, self.attn, self.phase, self.port) = parse_wsp(self.get_profile(self.ip_address)) # populate freq, attn, phase, and port arrays
            if (return_profile==True):
                return (self.freq, self.attn, self.phase, self.port) # return data arrays
        elif isinstance(set_profile,dict):
        # Write predefined profile to WaveShaper
            self.load_profile(self.ip_address, set_profile) # write predefined profile
            self.filter_profile(return_profile=False) # update local data arrays
        else:
        # Write custom WSP profile
            set_profile = {'type':'wsp', 'wsp':format_wsp(*set_profile)}
            self.load_profile(self.ip_address, set_profile) # write ws profile
            self.filter_profile(return_profile=False) # update local data arrays

    def phase_profile(self, set_profile=None):
        '''Specifically reads and writes only the phase profile'''
        if (set_profile is None):
        # Read phase profile from WaveShaper
            self.filter_profile(return_profile=False)
            return self.phase
        else:
        # Write custom phase profile
            self.filter_profile(return_profile=False) # update local data arrays
            self.filter_profile(set_profile=(self.freq, self.attn, set_profile, self.port), return_profile=False) # write new phase profile

    def attn_profile(self, set_profile=None):
        '''Specifically reads and writes only the attenuation profile'''
        if (set_profile is None):
        # Read attenuation profile from WaveShaper
            self.filter_profile(return_profile=False)
            return self.attn
        else:
        # Write custom attenuation profile
            self.filter_profile(return_profile=False) # update local data arrays
            self.filter_profile(set_profile=(self.freq, set_profile, self.phase, self.port), return_profile=False) # write new phase profile

    def port_profile(self, set_profile=None):
        '''Specifically reads and writes only the port profile'''
        if (set_profile is None):
        # Read port profile from WaveShaper
            self.filter_profile(return_profile=False)
            return self.port
        else:
        # Write custom port profile
            self.filter_profile(return_profile=False)
            self.filter_profile(set_profile=(self.freq, self.attn, self.phase, set_profile), return_profile=False)


