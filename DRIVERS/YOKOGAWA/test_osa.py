# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 14:19:40 2017
@author: ajm6
"""

import matplotlib.pyplot as plt
import osa_driver as yok
import eventlog as log

log.start_logging()

def plot_spectrum(lambdas, levels):
    """Plots spectrum from yokogawa"""
    plt.plot(lambdas, levels)
    plt.xlabel('wavelength nm')
    plt.ylabel('dBm')
    plt.grid(True)
    plt.show()

def test():
    """Tests some basic methods and connectability of OSA"""
    osa = yok.OSA(yok.OSA_NAME, yok.OSA_ADDRESS)
    if osa.res is None:
        raise SystemExit
    osa.query_identity()
    (lambdas, levels) = osa.query_spectrum()
    plot_spectrum(lambdas, levels)
    osa.close()

test()


#"""Look for directory with Yokogawa which contains OSA spectrum Files,
#create directory if it does not exist"""
#directory = "YokogawaFiles"
#if not os.path.exists(directory):
#    os.makedirs(directory)
#testString = directory + "/Yokogawa_"
#extension = ".txt"
#currentCount = 0

#"""Look for highest numberd file in /YokogawaFiles/ sub directory and return
#file name of latest file number + 1 then create file"""
#def checkFilePath(testString, extension, currentCount):
#    if os.path.exists(testString + str(currentCount) +extension):
#        return checkFilePath(testString, extension, currentCount+1)
#    else:
#        return testString + str(currentCount) +extension


#Ans = checkFilePath(testString,extension,currentCount)
#F=open(Ans,"w+")
#print Ans

#F.close()
