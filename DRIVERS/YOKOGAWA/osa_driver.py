# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 07:26:32 2017

@authors: AJ Metcalf and Wesley Brand

Module: osa_driver
    import osa_driver as yok

Requires:
    eventlog.py
    visa_objects.py

Public class:
    OSA

with Public Methods:
    __init__(res_name, res_address)
    close()
    query_identity()
    query_spectrum()


"""

import os
import numpy as np
import matplotlib.pyplot as plt
import visa_objects as vo
import eventlog as log

OSA_NAME = 'OSA'
OSA_ADDRESS = u'GPIB0::28::INSTR'
EXT = '.txt'

def plot_spectrum(data):
    """Plots spectrum from yokogawa"""
    (lambdas, levels) = data.T
    plt.plot(lambdas, levels)
    plt.xlabel('wavelength nm')
    plt.ylabel('dBm')
    plt.grid(True)
    plt.show()

def _find_directory():
    """Look for directory with Yokogawa which contains OSA spectrum Files,
    create directory if it does not exist"""
    directory = 'YokogawaFiles'
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory + '/Yokogawa_'

def _check_file_path(file_string, count):
    """Look for highest numberd file in /YokogawaFiles/ sub directory and return
    file name of latest file number + 1 then create file"""
    while True:
        if os.path.exists(_form_file_name(file_string, count)):
            count += 1
        else: break
    return count

def _form_file_name(file_string, count):
    """Formats a file name string for saving"""
    return file_string + str(count).zfill(4) + EXT

@log.log_this()
def _write_data_file(data, file_name):
    """Saves OSA spectrum in tab delimited txt file"""
    data_file = open(file_name, 'w')
    np.savetxt(data_file, data, delimiter='\t')
    data_file.close()

class OSA(vo.Visa):
    """Holds Yokogawa OSA's attributes and method library."""
    @log.log_this(20)
    def __init__(self, res_name, res_address):
        super(OSA, self).__init__(res_name, res_address)
        self.res = super(OSA, self).open_resource()
        if self.res is None:
            print 'Could not create OSA instrument!'
            return
        self.__set_command_format()
        self.file_string = _find_directory()
        self.file_count = _check_file_path(self.file_string, 0)
        self.file_name = _form_file_name(self.file_string, self.file_count)

    @log.log_this()
    def close(self):
        """Ends device session"""
        self.res.close()

    @vo.handle_timeout
    @log.log_this()
    def __set_command_format(self):
        """Sets the OSA's formatting to AQ6370 style, should always be 1"""
        self.res.write('CFORM1')

    @vo.handle_timeout
    @log.log_this()
    def query_identity(self):
        """Queries OSA's identity"""
        ident = self.res.query('*IDN?')
        print 'OSA Identity = %s' % ident

    @log.log_this()
    def save_n_graph_spectrum(self):
        """Prints a graph of osa spectrum to console and saves values to a file"""
        data = self._query_spectrum()
        _write_data_file(data, self.file_name)
        self.file_count += 1
        self.file_name = _form_file_name(self.file_string, self.file_count)
        plot_spectrum(data)

    @vo.handle_timeout
    @log.log_this()
    def _query_spectrum(self):
        """Queries OSA's spectrum"""
        y_trace = self.res.query(':TRACE:DATA:Y? TRA')
        x_trace = self.res.query(':TRACE:DATA:X? TRA')
        lambdas = np.fromstring(x_trace, sep=',')*1000000000
        levels = np.fromstring(y_trace, sep=',')
        lambdas = lambdas[1:]
        levels = levels[1:]
        data = np.array([lambdas, levels]).T
        return data
        #startWL = float(osa.query("STAWL?")[0:-2])
        #stopWL  = float(osa.query("STPWL?")[0:-2])
        #self.lambdas = np.linspace(startWL,stopWL,nPoints)
