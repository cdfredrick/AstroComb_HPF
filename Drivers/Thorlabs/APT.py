# -*- coding: utf-8 -*-
"""
Created on Tue Mar 19 10:06:34 2019

The communications protocol used in the Thorlabs controllers is based on the
message structure that always starts with a fixed length, 6-byte message header
which, in some cases, is followed by a variable length data packet. The header
part of the message always contains information that indicates whether or not a
data packet follows the header and if so, the number of bytes that the data
packet contains.

The 6 bytes in the message header are shown below:

                    Byte:   byte 0  byte 1  byte 2  byte 3  byte 4  byte 5
no data packet to follow    message ID      param1  param2  dest    source
data packet to follow       message ID      data length     dest    source

The meaning of some of the fields depends on whether or not the message is
followed by a data packet. This is indicated by the most significant bit in
byte 4, called the destination byte, therefore the receiving process must first
check if the MSB of byte 4 is set. If this bit is not set, then the message is
a header-only message and the interpretation of the bytes is as follows:
message ID: describes what the action the message requests
param1: first parameter (if the command requires a parameter, otherwise 0)
param2: second parameter (if the command requires a parameter, otherwise 0)
dest: the destination module
source: the source of the message

In all messages, where a parameter is longer than a single character, the bytes
are encoded in the Intel format, least significant byte first.

In non-card-slot type of systems the source and destination of messages is
always unambiguous, as each module appears as a separate USB node in the
system. In these systems, when the host sends a message to the module, it uses
the source identification byte of 0x01 (meaning host) and the destination byte
of 0x50 (meaning “generic USB unit”). In messages that the module sends back to
the host, the content of the source and destination bytes is swapped.

In card-slot (bay) type of systems, there is only one USB node for a number of
sub-modules, so this simple scheme cannot be used. Instead, the host sends a
message to the motherboard that the sub-modules are plugged into, with the
destination field of each message indicating which slot the message must be
routed to. Likewise, when the host receives a message from a particular
sub-module, it knows from the source byte which slot is the origin of the
message.

0x01    Host controller (i.e control PC)
0x11    Rack controller, motherboard in a card slot system or comms router board
0x21    Bay 0 in a card slot system
0x22    Bay 1 in a card slot system
0x23    etc.
0x24    etc.
0x25    etc.
0x26    etc.
...
0x2A    Bay 9 in a card slot system
0x50    Generic USB hardware unit

"""


# %% Modules

from functools import wraps
import struct
import serial


# %% Private Functions

def _auto_connect(func):
    '''A function decorator that handles automatic connections.

    If "auto connect" is enabled the communications port is enabled before the
    function execution and disabled afterwards. If the internal "connected"
    flag is true, the connection/disconnection procedure is ignored and the
    function executes as normal.
    '''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """Wrapped function"""
        if (self.auto_connect and not(self.connected)):
            try:
                self.open_port()
                result = func(self, *args, **kwargs)
                return result
            finally:
                self.close_port()
        else:
            result = func(self, *args, **kwargs)
            return result
    return wrapper


# %% APT Device

class APTDevice():
    def __init__(self, port, timeout=1.):
        assert isinstance(port, str)

        self.auto_connect = True
        self.connected = False

        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = 115200
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.timeout = timeout

    def open_port(self):
        if not self.ser.is_open:
            self.ser.open()
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.connected = True

    def close_port(self):
        if self.ser.is_open:
            self.ser.close()
            self.connected = False

    @_auto_connect
    def identify(self):
        # MGMSG_MOD_IDENTIFY
        buffer = struct.pack("<BBBBBB", 0x23, 0x02, 0x00, 0x00, 0x50, 0x01)
        self.ser.write(buffer)

    @_auto_connect
    def enable(self, enable=None, channel=1):
        if enable is None:
            # Check if the channel is enabled
            channel = {1:0x01, 2:0x02}[channel]
            # MGMSG_MOD_REQ_CHANENABLESTATE
            write_buffer = struct.pack("<BBBBBB", 0x11, 0x02, channel, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)
            # MGMSG_MOD_GET_CHANENABLESTATE
            read_buffer = self.ser.read(6)
            result = struct.unpack("<BBBBBB", read_buffer)
            enable_state = bool(result[3] & 0x01)
            return enable_state
        else:
            channel = {1:0x01, 2:0x02}[channel]
            enable_state = {True:0x01, False:0x02}[bool(enable)]
            # MGMSG_MOD_SET_CHANENABLESTATE
            write_buffer = struct.pack("<BBBBBB", 0x10, 0x02, channel, enable_state, 0x50, 0x01)
            self.ser.write(write_buffer)


# %% KDC101 Brushed Motor Controler and PRM1Z8 Rotation Stage

class KDC101_PRM1Z8(APTDevice):
    # Conversion Factors
    ENC_CNT_DEG = 1919.64 # encoder counts per degree
    VEL_SCL_FCT = 42941.66 # encoder counts per (degrees per second)
    ACC_SCL_FCT = 14.66 # encoder counts per (degrees per second**2)

    def __init__(self, port, timeout=1):
        super().__init__(port, timeout=timeout)

        # Suspend "End of Move Messages"
        self.suspend_EoM_msgs(True)

    @_auto_connect
    def suspend_EoM_msgs(self, suspend):
        '''Sent to disable or resume all unsolicited end of move messages and
        error messages returned by the controller:
            MGMSG_MOT_MOVE_STOPPED
            MGMSG_MOT_MOVE_COMPLETED
            MGMSG_MOT_MOVE_HOMED

        The command also disables the error messages that the controller sends
        when an error conditions is detected:
            MGMSG_HW_RESPONSE
            MGMSG_HW_RICHRESPONSE

        The messages are enabled by default when the controller is powered up.
        '''
        suspend = bool(suspend)
        if suspend:
            # MGMSG_MOT_SUSPEND_ENDOFMOVEMSGS
            write_buffer = struct.pack("<BBBBBB", 0x6B, 0x04, 0x00, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)
        else:
            # MGMSG_MOT_RESUME_ENDOFMOVEMSGS
            write_buffer = struct.pack("<BBBBBB", 0x6C, 0x04, 0x00, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)


    @_auto_connect
    def status(self):
        # MGMSG_MOT_REQ_DCSTATUSUPDATE
        write_buffer = struct.pack("<BBBBBB", 0x90, 0x04, 0x01, 0x00, 0x50, 0x01)
        self.ser.write(write_buffer)
        # MGMSG_MOT_GET_DCSTATUSUPDATE
        read_buffer = self.ser.read(size=20)
        # MGMSG_MOT_ACK_DCSTATUSUPDATE
        ack_buffer = struct.pack("<BBBBBB", 0x92, 0x04, 0x00, 0x00, 0x50, 0x01)
        self.ser.write(ack_buffer)
        # Unpack Read Buffer
        result = struct.unpack("<BBBBBBHlHHL", read_buffer)
        position = (result[7] / self.ENC_CNT_DEG) % 360 # degrees
        velocity = result[8] / self.VEL_SCL_FCT # degrees per second
        status_bits = {
                "forward hardware limit":   bool(result[10] & 0x00000001),
                "reverse hardware limit":   bool(result[10] & 0x00000002),
                "moving forward":           bool(result[10] & 0x00000010),
                "moving reverse":           bool(result[10] & 0x00000020),
                "jogging forward":          bool(result[10] & 0x00000040),
                "jogging reverse":          bool(result[10] & 0x00000080),
                "homing":                   bool(result[10] & 0x00000200),
                "homed":                    bool(result[10] & 0x00000400),
                "tracking":                 bool(result[10] & 0x00001000),
                "settled":                  bool(result[10] & 0x00002000),
                "motion error":             bool(result[10] & 0x00004000),
                "motor current limit":      bool(result[10] & 0x01000000),
                "channel enabled":          bool(result[10] & 0x80000000)}
        return (position, velocity, status_bits)

    @_auto_connect
    def home(self, home=None):
        if home is None:
            # Check if the device has been homed
            status_bits = self.status()[2]
            return {'homed':status_bits['homed'],
                    'homing':status_bits['homing']}
        elif home == True:
            # MGMSG_MOT_MOVE_HOME
            write_buffer = struct.pack("<BBBBBB", 0x43, 0x04, 0x01, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)

    @_auto_connect
    def position(self, position=None):
        if position is None:
            # Get the current position
            position = self.status()[0]
            return position
        else:
            # Calculate the encoder value
            enc_cnt = int(round((position % 360) * self.ENC_CNT_DEG))
            # MGMSG_MOT_MOVE_ABSOLUTE
            write_buffer = struct.pack('<BBBBBBHl', 0x53, 0x04, 0x06, 0x00, 0x50|0x80, 0x01,
                                       0x0001, enc_cnt)
            self.ser.write(write_buffer)

    @_auto_connect
    def move_relative(self, rel_position):
        enc_cnt = int(round(rel_position * self.ENC_CNT_DEG))
        # MGMSG_MOT_MOVE_RELATIVE
        write_buffer = struct.pack("<BBBBBBHl", 0x48, 0x04, 0x06, 0x00, 0x50|0x80, 0x01,
                                   0x0001, enc_cnt)
        self.ser.write(write_buffer)


# %% KPZ101 K-Cube Piezo Controller

class KPZ101(APTDevice):
    # Position Control Mode
    OPEN_LOOP = 0x01
    CLOSED_LOOP = 0x02
    OPEN_LOOP_SMOOTH = 0x03
    CLOSED_LOOP_SMOOTH = 0x04

    # IO Settings
    VOLTAGELIMIT_75V = 0x01
    VOLTAGELIMIT_100V = 0x02
    VOLTAGELIMIT_150V = 0x03
    HUB_ANALOGUEIN_A = 0x01
    HUB_ANALOGUEIN_B = 0x02
    EXTSIG_SMA = 0x03

    # Output Voltage
    CNT_VLT_FR = 2**(16-1) - 1 # integer counts per max voltage
    MAX_VLT = [0, 75, 100, 150]

    # Input Voltage Source
    SOFTWARE_ONLY = 0x00
    EXTERNAL_SIGNAL = 0x01
    POTENTIOMETER = 0x02

    def __init__(self, port, timeout=1):
        super().__init__(port, timeout=timeout)

        # Set Position Control Mode
        self.position_control_mode(mode=self.OPEN_LOOP)

        # Populate IO Settings
        self.io_settings()

    @_auto_connect
    def position_control_mode(self, mode=None, persist=True):
        '''When in closed-loop mode, position is maintained by a feedback
        signal from the piezo actuator. This is only possible when using
        actuators equipped with position sensing.

        mode : int
            0x01    Open Loop (no feedback)

            0x02    Closed Loop (feedback employed)

            0x03    Open Loop Smooth

            0x04    Closed Loop Smooth

        If set to Open Loop Smooth or Closed Loop Smooth is selected, the
        feedback status is the same as above however the transition from open
        to closed loop (or vise versa) is achieved over a longer period in
        order to minimize voltage transients (spikes).
        '''
        if mode is None:
            # Get the current position control mode
            # MGMSG_PZ_REQ_POSCONTROLMODE
            write_buffer = struct.pack("<BBBBBB", 0x41, 0x06, 0x01, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)
            # MGMSG_PZ_GET_POSCONTROLMODE
            read_buffer = self.ser.read(6)
            result = struct.unpack("<BBBBBB", read_buffer)
            mode = result[3]
            return mode
        else:
            assert mode in [self.OPEN_LOOP, self.CLOSED_LOOP, self.OPEN_LOOP_SMOOTH, self.CLOSED_LOOP_SMOOTH]
            # MGMSG_PZ_SET_POSCONTROLMODE
            write_buffer = struct.pack("<BBBBBB", 0x40, 0x06, 0x01, mode, 0x50, 0x01)
            self.ser.write(write_buffer)
            if persist:
                # MGMSG_PZ_SET_EEPROMPARAMS
                write_buffer = struct.pack("<BBBBBBHBB", 0xD0, 0x07, 0x04, 0x00, 0x50|0x80, 0x01,
                                           0x0001, 0x40, 0x06)
                self.ser.write(write_buffer)

    @_auto_connect
    def input_voltage_source(self, input_source=None, persist=True):
        '''Used to set the input source(s) which controls the output from the
        HV amplifier circuit (i.e. the drive to the piezo actuators).

        input_source : int
            0x00 = SOFTWARE_ONLY, Unit responds only to software inputs and the
            HV amp output is that set using the SetVoltOutput method or via the
            GUI panel.

            0x01 = EXTERNAL_SIGNAL, Unit sums the differential signal on the
            rear panel EXT IN (+) and EXT IN (-) connectors with the voltage
            set using the SetVoltOutput method

            0x02 = POTENTIOMETER, The HV amp output is controlled by a
            potentiometer input (either on the control panel, or connected to
            the rear panel User I/O D-type connector) summed with the voltage
            set using the SetVoltOutput method.
        '''
        if input_source is None:
            # MGMSG_PZ_REQ_INPUTVOLTSSRC
            write_buffer = struct.pack("<BBBBBB", 0x53, 0x06, 0x01, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)
            # MGMSG_PZ_GET_INPUTVOLTSSRC
            read_buffer = self.ser.read(10)
            result = struct.unpack("<BBBBBBHH", read_buffer)
            voltage_source = result[7]
            return voltage_source
        else:
            assert input_source in [self.SOFTWARE_ONLY, self.EXTERNAL_SIGNAL, self.POTENTIOMETER]
            # MGMSG_PZ_SET_INPUTVOLTSSRC
            write_buffer = struct.pack("<BBBBBBHH", 0x52, 0x06, 0x04, 0x00, 0x05|0x08, 0x01,
                                       0x0001, input_source)
            self.ser.write(write_buffer)
            if persist:
                # MGMSG_PZ_SET_EEPROMPARAMS
                write_buffer = struct.pack("<BBBBBBHBB", 0xD0, 0x07, 0x04, 0x00, 0x50|0x80, 0x01,
                                           0x0001, 0x52, 0x06)
                self.ser.write(write_buffer)

    @_auto_connect
    def io_settings(self, voltage_limit=None, analog_input=None, persist=True):
        '''This function is used to set various I/O settings.

        voltage_limit : int
            The piezo actuator connected to the T-Cube has a specific maximum
            operating voltage range. This parameter sets the maximum output to
            the value specified as follows...

            0x01 = VOLTAGELIMIT_75V,    75V limit

            0x02 = VOLTAGELIMIT_100V,   100V limit

            0x03 = VOLTAGELIMIT_150V,   150V limit

        analog_input : int
            When the K-Cube Piezo Driver unit is used a feedback signal can be
            passed from other cubes to the Piezo unit. This parameter is used
            to select the way in which the feedback signal is routed to the
            Piezo unit as follows...

            0x01 = HUB_ANALOGUEIN_A,    all cube bays

            0x02 = HUB_ANALOGUEIN_B,    adjacent pairs of cube bays (i.e. 1&2, 3&4, 5&6)

            0x03 = EXTSIG_SMA,          rear panel SMA connector
        '''
        if (voltage_limit is None) and (analog_input is None):
            # Get the current IO settings
            # MGMSG_PZ_REQ_TPZ_IOSETTINGS
            write_buffer = struct.pack("<BBBBBB", 0xD5, 0x07, 0x01, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)
            # MGMSG_PZ_GET_TPZ_IOSETTINGS
            read_buffer = self.ser.read(16)
            result = struct.unpack("<BBBBBBHHHHH", read_buffer)
            voltage_limit = result[7]
            analog_input = result[8]
            self.voltage_limit = voltage_limit
            self.analog_input = analog_input
            return {"voltage_limit":voltage_limit,
                    "analog_input":analog_input}
        else:
            if voltage_limit is None:
                voltage_limit = self.voltage_limit
            if analog_input is None:
                analog_input = self.analog_input
            # Check values
            assert voltage_limit in [self.VOLTAGELIMIT_75V, self.VOLTAGELIMIT_100V, self.VOLTAGELIMIT_150V]
            assert analog_input in [self.HUB_ANALOGUEIN_A, self.HUB_ANALOGUEIN_B, self.EXTSIG_SMA]
            # MGMSG_PZ_SET_TPZ_IOSETTINGS
            write_buffer = struct.pack("<BBBBBBHHHHH", 0xD4, 0x07, 0x0A, 0x00, 0x50|0x80, 0x01,
                                       0x0001, voltage_limit, analog_input, 0, 0)
            self.ser.write(write_buffer)
            self.voltage_limit = voltage_limit
            self.analog_input = analog_input
            if persist:
                # MGMSG_PZ_SET_EEPROMPARAMS
                write_buffer = struct.pack("<BBBBBBHBB", 0xD0, 0x07, 0x04, 0x00, 0x50|0x80, 0x01,
                                           0x0001, 0xD4, 0x07)
                self.ser.write(write_buffer)

    @_auto_connect
    def voltage(self, voltage=None):
        '''Used to set the output voltage applied to the piezo actuator.

        This command is applicable only in Open Loop mode. If called when in
        Closed Loop mode it is ignored.

        voltage : float
            The output voltage applied to the piezo when operating in open loop
            mode. The voltage is scaled into the range -32768 to 32767 (-0x7FFF
            to 0x7FFF) to which corresponds to -100% to 100% of the maximum
            output voltage as set using the TPZ_IOSETTINGS command.
        '''
        if voltage is None:
            # Get the current voltage output
            # MGMSG_PZ_REQ_OUTPUTVOLTS
            write_buffer = struct.pack("<BBBBBB", 0x44, 0x06, 0x01, 0x00, 0x50, 0x01)
            self.ser.write(write_buffer)
            # MGMSG_PZ_GET_OUTPUTVOLTS
            read_buffer = self.ser.read(10)
            result = struct.unpack("<BBBBBBHh", read_buffer)
            voltage = result[7]/self.CNT_VLT_FR * self.MAX_VLT[self.voltage_limit]
            return voltage
        else:
            assert (voltage >= 0) and (voltage <= self.MAX_VLT[self.voltage_limit])
            # MGMSG_PZ_SET_OUTPUTVOLTS
            voltage_cnt = int(round(voltage/self.MAX_VLT[self.voltage_limit] * self.CNT_VLT_FR))
            write_buffer = struct.pack("<BBBBBBHh", 0x43, 0x06, 0x04, 0x00, 0x50|0x80, 0x01,
                                       0x0001, voltage_cnt)

