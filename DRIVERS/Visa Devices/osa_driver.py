# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 07:26:32 2017

@authors: AJ Metcalf and Wesley Brand

Module: osa_driver

Requires:
    eventlog.py
    visa_objects.py

Public Function:
    plot_spectrum(array)

Public Class:
    OSA

with Public Methods:

    General:

    __init__(res_name, res_address)
    close()
    reset()

    Query:

    str = query_identity()
    save_n_graph_spectrum()
    dict = query_sweep_parameters() #nm

    Set:

    set_sweep_parameters(center_wl=1064,
                         span_wl=200, res_wl=2, sensitivity=1) #nm
    
    Manual:
    
    manual_spectrum_verify()

"""


#Python imports
import os

#3rd party imports
import numpy as np
import matplotlib.pyplot as plt

#Astrocomb imports
import visa_objects as vo
import eventlog as log
import ac_excepts


#Constants
OSA_ADDRESS = u'GPIB0::28::INSTR' #Make sure I'm right
EXT = '.txt'


#Public functions
def plot_spectrum(data):
    """Plots spectrum from yokogawa"""
    (lambdas, levels) = data.T
    spectrum = plt.plot(lambdas, levels)
    plt.xlabel('wavelength nm')
    plt.ylabel('dBm')
    plt.grid(True)
    return spectrum

#Private functions
def _find_directory():
    """Look for/create directory with OSA spectrum Files"""
    directory = 'YokogawaFiles'
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory + '/Yokogawa_'

def _check_file_path(file_string, count):
    """Returns 1+number of highest file in /YokogawaFiles/ sub directory"""
    while True:
        if os.path.exists(_form_file_name(file_string, count)):
            count += 1
        else: break
    return count

def _form_file_name(file_string, count):
    """Formats a file name string for saving"""
    return file_string + str(count).zfill(4) + EXT

def _write_data_file(data, file_name):
    """Saves OSA spectrum in tab delimited txt file"""
    data_file = open(file_name, 'w')
    np.savetxt(data_file, data, delimiter='\t')
    data_file.close()


class OSA(vo.Visa):
    """Holds Yokogawa OSA's attributes and method library."""

#General Methods

    @log.log_this(20)
    def __init__(self, res_address=OSA_ADDRESS):
        super(OSA, self).__init__(res_address)
        if self.resource is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create OSA instrument!', self.__init__)
        self.__set_command_format()
        self.file_string = _find_directory()
        self.file_count = _check_file_path(self.file_string, 0)
        self.file_name = _form_file_name(self.file_string, self.file_count)

    @log.log_this()
    def close(self):
        """Ends device session"""
        self.close_resource()

    
    @log.log_this(20)
    def reset(self):
        """Stops current machine operation and returns OSA to default values"""
        self.write('*RST')
        self.__set_command_format()

#Query Methods

    
    @log.log_this()
    def query_identity(self):
        """Queries OSA's identity"""
        ident = self.query('*IDN?')
        return ident

    
    @log.log_this()
    def query_sweep_parameters(self):
        """Returns sweep parameters as a dictionary

        dictionary keys: center_wl, span_wl, res_wl, sensitivity
        wavelengths are in nm

        Sensitivites:
              0     |      1      |    2   |  3  |    4   |    5   |    6   |
        Normal Hold | Normal Auto | Normal | Mid | High 1 | High 2 | High 3 |
        """
        pdict = {}
        nano = 10.**9
        pdict['center_wl'] = float(self.query(':SENS:WAV:CENT?'))*nano
        pdict['span_wl'] = float(self.query(':SENS:WAV:SPAN?'))*nano
        pdict['res_wl'] = float(self.query(':SENS:BAND:RES?'))*nano
        pdict['sensitivity'] = int(self.query(':SENS:SENS?'))
        return pdict

    @log.log_this()
    def get_spectrum(self, graph=False):
        """Saves OSA spectrum values to a file, returns a plot"""
        data = self._query_spectrum()
        _write_data_file(data, self.file_name)
        self.file_count += 1
        self.file_name = _form_file_name(self.file_string, self.file_count)
        if graph:
            spectrum = plot_spectrum(data)
            plt.show(spectrum)

    
    @log.log_this()
    def _query_spectrum(self):
        """Sweepss OSA's spectrum"""
        y_trace = self.query(':TRAC:DATA:Y? TRA')
        x_trace = self.query(':TRAC:DATA:X? TRA')
        wavelengths = np.fromstring(x_trace, sep=',')*10.**9
        powers = np.fromstring(y_trace, sep=',')
        data = np.array([wavelengths, powers]).T
        return data

#Set Methods

    
    @log.log_this()
    def __set_command_format(self):
        """Sets the OSA's formatting to AQ6370 style, should always be 1"""
        self.write('CFORM1')

    
    @log.log_this()
    def set_sweep_parameters(self, center_wl=1064, span_wl=600,
                             res_wl=2, sensitivity=1):
        """Sets OSA sweep region"""
        self.write(':SENS:WAV:CENT %snm' % center_wl)
        self.write(':SENS:WAV:SPAN %snm' %span_wl)
        self.write(':SENS:BAND:RES %snm' %res_wl)
        self.write(':SENS:SENS %s' %sensitivity)
        return

#Manual control method

    def manual_spectrum_verify(self):
        """Let's user decide if the comb has the correct spectrum."""
        self.get_spectrum(graph=True)
        while True:
            command = input('Is the spectrum correct? y=yes, s=set sweep \
                            parameters, r=restore default sweep parameters, \
                            a=abort')
            if command == 'y':
                return
            elif command == 's':
                while True:
                    center_wl = input('Set center wavelength in nm, default \
                                  is 1064')
                    span_wl = input('Set sweep span in nm, default is 600')
                    res_wl = input('Set sweep resolution in nm, default is 2')
                    sens = input('Set sweep sensitivity (0-6), default is 1')
                    if center_wl.is_integer() and span_wl.is_integer and\
                        res_wl.is_integer() and sens.is_integer():
                            #Might want more coding here to prevent entering 
                            # bad values
                        break
                    else:
                        print 'Values must be integers!'
                self.set_sweep_parameters(center_wl, span_wl,
                                                   res_wl, sens)
            elif command == 'r':
                self.set_sweep_parameters()
            elif command == 'a':
                raise ac_excepts.StartupError('Aborted spectrum verification!',
                                              self.manual_spectrum_verify)
            else:
                print "Input must be either be 'y', 's', 'r', or 'a'" 
