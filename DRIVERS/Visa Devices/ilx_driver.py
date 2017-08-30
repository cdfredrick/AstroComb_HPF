# -*- coding: utf-8 -*-
"""
Created on Mon Jun 26 10:31:06 2017

@author: Wesley Brand

Module: ilx_driver
#Laser diode control

Public Classes:
    ILX(vo.Visa)
    LDC(ILX)


ILX's Public Methods:

    las_chan_switch()
    tec_chan_switch()


LDC's Public Methods:

Enable:
    enable_las(las_on)
    enable_tec(tec_on)

Query laser:
    TF = query_las_on()
    str = query_las_mode()
    float = query_las_current()
    float = query_las_current_limit()
    float = query_las_current_set_point()

Set laser:
    set_las_current(current)
    set_las_current_limit(current)
    set_las_mode(mode_num)

Query TEC:
    TF = query_tec_on()
    str = query_tec_mode()
    float = query_tec_temp()

Set TEC:
    set_tec_mode(mode_num)
    set_tec_temp(temp)

"""
#pylint: disable=W0231
### Avoid ILX.__init__() in LDControl.__init__ because inherits
###  from ILX instance


#Astrocomb imports
import visa_objects as vo
import eventlog as log
import ac_excepts


#Constants
_MARKER = object()  #To check errors in LDControl class inheritance
ILX_ADDRESS = '' #ADD ME!!!


class ILX(vo.Visa):
    """Holds commands for ILX chassis and passes commands for components."""
    @log.log_this()
    def __init__(self, res_address=ILX_ADDRESS):
        self.res = super(ILX, self).__init__(res_address)
        if self.res is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create ILX instrument!', self.__init__)
        self.las_chan = 0
        self.tec_chan = 0
        self.las_chan_switch(1)
        self.tec_chan_switch(1)

    @vo.handle_timeout
    @log.log_this()
    def las_chan_switch(self, chan_num):
        """Sets the laser channel to read write from, must be 1-4."""
        if self.las_chan != chan_num:
            self.res.write('LAS:CHAN %d' % chan_num)
            self.las_chan = chan_num

    @vo.handle_timeout
    @log.log_this()
    def tec_chan_switch(self, chan_num):
        """Sets the laser channel to read write from, must be 1-4."""
        if self.tec_chan != chan_num:
            self.res.write('LAS:CHAN %d' % chan_num)
            self.tec_chan = chan_num

    @log.log_this()
    def close(self):
        """Ends device session."""
        self.res.close()

class LDControl(ILX):
    """Holds commands for laser control cards inside ILX.

    The ILX housing must be instantiated first and the object passed
    as an argument when instantiating the individual cards"""

    _inherited = ['res', 'las_chan', 'tec_chan']

    @log.log_this()
    def __init__(self, ilx_object, card_num):
        self._parent = ilx_object
        self.num = card_num

    def __getattr__(self, name, default=_MARKER):
        """Checks for attribute in parent ILX object."""
        if name in self._inherited:
            # Get from parent object
            try:
                return getattr(self._parent, name)
            except AttributeError:
                if default is _MARKER:
                    raise
                return default

        if name not in self.__dict__:
            raise AttributeError(name)

#Private command passing methods

    @vo.handle_timeout
    def _las_query(self, command):
        """Swtiches comm channel and queries LAS:"""
        self.las_chan_switch(self.num)
        result = self.res.query('LAS:' + command)
        return result

    @vo.handle_timeout
    def _las_set(self, command):
        """Swtiches comm channel and writes to LAS:"""
        self.las_chan_switch(self.num)
        self.res.write('LAS:' + command)

    @vo.handle_timeout
    def _tec_query(self, command):
        """Swtiches comm channel and queries TEC:"""
        self.tec_chan_switch(self.num)
        result = self.res.query('TEC:' + command)
        return result

    @vo.handle_timeout
    def _tec_set(self, command):
        """Swtiches comm channel and writes to TEC:"""
        self.tec_chan_switch(self.num)
        self.res.write('TEC:' + command)

#Enable methods

    @log.log_this(20)
    def enable_las(self, las_on):
        """Turns the laser on if las_on is True.

        TEC must be on to prevent frying"""
        if self.query_tec_on():
            self._las_set('ONLY:OUT %d' % vo.tf_toggle(las_on))
        else:
            raise ac_excepts.EnableError("Can't turn laser on if TEC is off!",
                                         self.enable_las)
    @log.log_this(20)
    def enable_tec(self, tec_on):
        """Turns the TEC on if tec_on is True."""
        self._tex_set('ONLY:OUT %d' % vo.tf_toggle(tec_on))

#laser query methods

    @log.log_this()
    def query_las_on(self):
        """Returns True if laser on, False if not."""
        return bool(int(self._las_query('OUT?')))

    @log.log_this()
    def query_las_mode(self):
        """Returns laser mode string.

        Modes:
        IHBW -> constant current, high bandwidth
        ILBW -> constant current, low bandwidth
        MDP -> constant optical power
        """
        return self._las_query('MODE?')

    @log.log_this()
    def query_las_current(self):
        """Returns the present laser current in mA."""
        return float(self._las_query('LDI?'))

    @log.log_this()
    def query_las_current_limit(self):
        """Returns the max laser current in mA."""
        return float(self._las_query('LIM:I?'))

    @log.log_this()
    def query_las_current_set_point(self):
        """Returns the laser current set point in mA."""
        return float(self._las_query('SET:LDI?'))

#Laser settings methods

    @log.log_this()
    def set_las_current(self, current):
        """Sets the laser current in mA."""
        self._las_set('LDI %s' % int(current))
    @log.log_this()
    def set_las_current_limit(self, current):
        """Sets the max laser current in mA."""
        self._las_set('LDI %s' % int(current))

    @log.log_this()
    def set_las_mode(self, mode_num):
        """Sets the laser stabilization mode.

        Modes:
        0 -> constant current, high bandwidth
        1 -> constant current, low bandwidth
        2 -> constant optical power
        """
        modes = ['IHBW', 'ILBW', 'MDP']
        self._las_set('MODE:%s' % modes[mode_num])

#TEC query methods

    @log.log_this()
    def query_tec_on(self):
        """Returns True if TEC on, False if not."""
        return bool(int(self._tec_query('OUT?')))

    @log.log_this()
    def query_tec_mode(self):
        """Returns TEC mode string.

        Modes:
        ITE -> constant current
        R -> constant resistance
        T -> constant temperature
        """
        return self._tec_query('MODE?')

    @log.log_this()
    def query_tec_temp(self):
        """Returns the TEC temp in C with 6 digits of precision."""
        return float(self._teq_query('T?'))

#TEC settings methods

    @log.log_this()
    def set_tec_mode(self, mode_num):
        """Sets the TEC stabilization mode.

        Modes:
        0 -> constant current
        1 -> constant resistance
        2 -> constant temperature
        """
        modes = ['ITE', 'R', 'T']
        self._tec_set('MODE:%s' % modes[mode_num])

    @log.log_this()
    def set_tec_temp(self, temp):
        """Sets TEC temp in C"""
        self._tec_set('T %s' % temp)
