# -*- coding: utf-8 -*-
"""
Created on Wed Aug 09 13:15:05 2017

@author: Wesley Brand

Public classes:
    AstroCombExceptions

    Subclasses:
        ConnectionError
        CurrentError
        DAQError
        EnableError
        LaserLockError
        ShutdownError
        StartupError
        TempError
        ThresholdError
        VirtualDeviceError

"""


class AstroCombExceptions(Exception):
    """The base class for all astrocomb exceptions.

    Let's you catch all custom exceptions
    try:
        ...
    except AstroCombExceptions:
        ...                                           """
    def __init__(self, message, method):
        super(AstroCombExceptions, self).__init__(message) #Regular exception
        self.method = method #Error origin, rarely a function but ok too

#Keep the following classes alphabetized


class ConnectionError(AstroCombExceptions):
    """Raise when a device cannot be connected to/loses connection."""


class CurrentError(AstroCombExceptions):
    """Raise when a device is not within correct current range."""


class DAQError(AstroCombExceptions):
    """Raise after a PyDAQmx error is caught to stop current process."""


class EnableError(AstroCombExceptions):
    """Raise when a device does not or cannot turn on."""


class LaserLockError(AstroCombExceptions):
    """Raise if Rio laser not locked."""


class ShutdownError(AstroCombExceptions):
    """Raise when a startup sequence cannot be completed."""


class StartupError(AstroCombExceptions):
    """Raise when a startup sequence cannot be completed."""


class TempError(AstroCombExceptions):
    """Raise for a temperature control problem (ThermoCube or TEC)."""


class ThresholdError(AstroCombExceptions):
    """Raise for a measurement that does not meet required value (DAQ)."""


class VirtualDeviceError(AstroCombExceptions):
    """Raise when a virtual device cannot be created (probably wrong address)."""
