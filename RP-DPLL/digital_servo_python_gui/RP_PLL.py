# -*- coding: utf-8 -*-

from __future__ import print_function
import socket
import struct
import traceback    # for print_stack, for debugging purposes: traceback.print_stack()
import time

import numpy as np
#import matplotlib.pyplot as plt

class socket_placeholder():
    def __init__(self):
        pass
    def sendall(*args):
        print("socket_placeholder::sendall(): No active socket")
        pass
    def recv(*args):
        print("socket_placeholder::recv(): No active socket")
        return []

class RP_PLL_device():

    
    
    
    MAGIC_BYTES_WRITE_REG       = 0xABCD1233
    MAGIC_BYTES_READ_REG        = 0xABCD1234
    MAGIC_BYTES_READ_BUFFER     = 0xABCD1235
    
    MAGIC_BYTES_WRITE_FILE      = 0xABCD1237
    MAGIC_BYTES_SHELL_COMMAND   = 0xABCD1238
    MAGIC_BYTES_REBOOT_MONITOR  = 0xABCD1239
    
    FPGA_BASE_ADDR          = 0x40000000

    MAX_SAMPLES_READ_BUFFER = 2**15 # should be equal to 2**ADDRESS_WIDTH from ram_data_logger.vhd


    def __init__(self):
        self.sock = socket_placeholder()
        return

    def OpenTCPConnection(self, HOST, PORT=5000):
        print("RP_PLL_device::OpenTCPConnection(): HOST = '%s', PORT = %d" % (HOST, PORT))
        self.HOST = HOST
        self.PORT = PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(1)
        self.sock.connect((self.HOST, self.PORT))

    # from http://stupidpythonideas.blogspot.ca/2013/05/sockets-are-byte-streams-not-message.html
    def recvall(self, count):
        buf = b''
        
        while count:
            newbuf = self.sock.recv(count)
            if not newbuf: return None
            buf += newbuf
            count -= len(newbuf)
            
        return buf


    # Function used to send a file write command:
    def write_file_on_remote(self, strFilenameLocal, strFilenameRemote):
        # open local file and load into memory:
        file_data = np.fromfile(strFilenameLocal, dtype=np.uint8)
        
        # send header
        packet_to_send = struct.pack('=III', self.MAGIC_BYTES_WRITE_FILE, len(strFilenameRemote), len(file_data))
        self.sock.sendall(packet_to_send)
        # send filename
        self.sock.sendall(strFilenameRemote.encode('ascii'))
        # send actual file
        self.sock.sendall(file_data.tobytes())
        
    # Function used to send a shell command to the Red Pitaya:
    def send_shell_command(self, strCommand):
        
        # send header
        packet_to_send = struct.pack('=III', self.MAGIC_BYTES_SHELL_COMMAND, len(strCommand), 0)
        self.sock.sendall(packet_to_send)
        # send filename
        self.sock.sendall(strCommand.encode('ascii'))
        
    # Function used to reboot the monitor-tcp program
    def send_reboot_command(self):
        
        # send header
        packet_to_send = struct.pack('=III', self.MAGIC_BYTES_REBOOT_MONITOR, 0, 0)
        self.sock.sendall(packet_to_send)

    #######################################################
    # Functions used to access the memory-mapped registers of the Zynq
    #######################################################

    def write_Zynq_register_uint32(self, address_uint32, data_uint32):
#        print "write_Zynq_register_uint32(): address_uint32 = %s, self.FPGA_BASE_ADDR+address_uint32 = %s, data = %d" % (hex(address_uint32), hex(self.FPGA_BASE_ADDR+address_uint32), data_uint32)
        if address_uint32 % 4:
            # Writing to non-32bits-aligned addresses is forbidden - it crashes the process running on the Zynq
            print("write_Zynq_register_uint32(0x%x, 0x%x) Error: Writing to non-32bits-aligned addresses is forbidden - it crashes the process running on the Zynq.")
            raise Exception("write_Zynq_register_uint32", "non-32-bits-aligned write")
            return
        packet_to_send = struct.pack('=III', self.MAGIC_BYTES_WRITE_REG, self.FPGA_BASE_ADDR+address_uint32, int(data_uint32) & 0xFFFFFFFF)
        self.sock.sendall(packet_to_send)

    def write_Zynq_register_int32(self, address_uint32, data_int32):
#        print "write_Zynq_register_int32(): address_uint32 = %s, self.FPGA_BASE_ADDR+address_uint32 = %s\n" % (hex(address_uint32), hex(self.FPGA_BASE_ADDR+address_uint32))
        if address_uint32 % 4:
            # Writing to non-32bits-aligned addresses is forbidden - it crashes the process running on the Zynq
            print("write_Zynq_register_uint32(0x%x, 0x%x) Error: Writing to non-32bits-aligned addresses is forbidden - it crashes the process running on the Zynq.")
            raise Exception("write_Zynq_register_uint32", "non-32-bits-aligned write")
            return
        packet_to_send = struct.pack('=IIi', self.MAGIC_BYTES_WRITE_REG, self.FPGA_BASE_ADDR+address_uint32, int(data_int32) & 0xFFFFFFFF)
        self.sock.sendall(packet_to_send)

    def read_Zynq_register_uint32(self, address_uint32):
        # print "read_Zynq_register_uint32(): address_uint32 = %s, self.FPGA_BASE_ADDR+address_uint32 = %s\n" % (hex(address_uint32), hex(self.FPGA_BASE_ADDR+address_uint32))
        packet_to_send = struct.pack('=III', self.MAGIC_BYTES_READ_REG, self.FPGA_BASE_ADDR+address_uint32, 0)  # last value is reserved
        self.sock.sendall(packet_to_send)
        data_buffer = self.recvall(4)   # read 4 bytes (32 bits)
        if data_buffer is None:
            return 0
        if len(data_buffer) != 4:
            print("read_Zynq_register_uint32() Error: len(data_buffer) != 4: repr(data_buffer) = %s" % (repr(data_buffer)))
        register_value_as_tuple = struct.unpack('I', data_buffer)
        return register_value_as_tuple[0]

    def read_Zynq_register_int32(self, address_uint32):
        # print "read_Zynq_register_int32(): address_uint32 = %s, self.FPGA_BASE_ADDR+address_uint32 = %s\n" % (hex(address_uint32), hex(self.FPGA_BASE_ADDR+address_uint32))
        packet_to_send = struct.pack('=III', self.MAGIC_BYTES_READ_REG, self.FPGA_BASE_ADDR+address_uint32, 0)  # last value is reserved
        self.sock.sendall(packet_to_send)
        data_buffer = self.recvall(4)   # read 4 bytes (32 bits)
        if data_buffer is None:
            return 0
        if len(data_buffer) != 4:
            print("read_Zynq_register_uint32() Error: len(data_buffer) != 4: repr(data_buffer) = %s" % (repr(data_buffer)))
        register_value_as_tuple = struct.unpack('i', data_buffer)
        return register_value_as_tuple[0]

    def read_Zynq_register_uint64(self, address_uint32_lsb, address_uint32_msb):
        # print "read_Zynq_register_uint64()"
        results_lsb = self.read_Zynq_register_uint32(address_uint32_lsb)
        results_msb = self.read_Zynq_register_uint32(address_uint32_msb)

        # print 'results_lsb = %d' % results_lsb
        # print 'results_msb = %d' % results_msb

        # convert to 64 bits using numpy's casts
        results = np.array((results_lsb, results_msb), np.dtype(np.uint32))
        results = np.frombuffer(results, np.dtype(np.uint64) )

        return results

    def read_Zynq_register_int64(self, address_uint32_lsb, address_uint32_msb):
        # print "read_Zynq_register_uint64()"
        results_lsb = self.read_Zynq_register_uint32(address_uint32_lsb)
        results_msb = self.read_Zynq_register_uint32(address_uint32_msb)

        # print 'results_lsb = %d' % results_lsb
        # print 'results_msb = %d' % results_msb

        # convert to 64 bits using numpy's casts
        results = np.array((results_lsb, results_msb), np.dtype(np.uint32))
        results = np.frombuffer(results, np.dtype(np.int64) )

        return results
  
    def read_Zynq_buffer_int16(self, address_uint32, number_of_points):
        #return '\x00\x00'
        address_uint32 = 0    # currently unused
        if number_of_points > self.MAX_SAMPLES_READ_BUFFER:
            number_of_points = self.MAX_SAMPLES_READ_BUFFER
            print("number of points clamped to %d." % number_of_points)
            #traceback.print_stack()
        packet_to_send = struct.pack('=III', self.MAGIC_BYTES_READ_BUFFER, self.FPGA_BASE_ADDR+address_uint32, number_of_points)    # last value is reserved
#        print "read_Zynq_buffer_int16: before sendall()"
        self.sock.sendall(packet_to_send)
#        print "read_Zynq_buffer_int16: after sendall()"
        data_buffer = self.recvall(int(2*number_of_points)) # read number_of_points samples (16 bits each)
#        print "read_Zynq_buffer_int16: len(data_buffer) = %d, data_buffer:" % (len(data_buffer))
#        print repr(data_buffer[0:10])
        if data_buffer is None:
            return b''
        
        return data_buffer    # returns a raw string buffer, to be read for example with np.fromstring(data_buffer, dtype=np.int16)

    #######################################################
    # Functions to emulate the Opal Kelly API:
    #######################################################
    # this function is now disabled because we simply implemented "triggers" differently: they are simply the update_flag of an empty, but otherwise standard parallel bus register
    # def ActivateTriggerIn(self, endpoint, value):
    #   # this should send a trigger, most likely by toggling a value, and having the fpga diff that value
    #   # or it could be simply a write to a dummy address and we just use the sys_we as the trigger
    #   # although I am not sure if it is guaranteed to be 1-clock-cycle long
    #   #print('ActivateTriggerIn(): TODO')
    #   self.write_Zynq_register_uint32((endpoint+value)*4+value*4, 0)

    def SetWireInValue(self, endpoint, value_16bits):
        # this only needs to update the internal state
        # for this, there would need to be two versions of the internal state, so that we can diff them and commit only the addresses that have changed
        # but its much simpler for now to just commit the change directly

        #print('SetWireInValue(): TODO')

        # the multiply by 4 is because right now the zynq code doesn't work unless reading on a 32-bits boundary, so we map the addresses to different values
        if value_16bits < 0:
            # write as a signed value
            self.write_Zynq_register_int32(endpoint*4, value_16bits)
        else:
            # write as an unsigned value
            self.write_Zynq_register_uint32(endpoint*4, value_16bits)


    def UpdateWireIns(self):
        # commit changes to the fpga
        # Wire ins are from the PC to the FPGA
        # for now we don't do anything since every SetWireInValue() call actually commits the changes to the fpga...
        #print('UpdateWireIns(): TODO')
        return

    def GetWireOutValue(self, endpoint):
        # print('GetWireOutValue(): TODO')
        # this reads a single 32-bits value from the fpga registers
        # the Opal Kelly code expected a 16-bits value, so we mask them out for compatibility
        rep = self.read_Zynq_register_uint32(4*endpoint)
        return rep & 0xFFFF # the multiply by 4 is because right now the zynq code doesn't work unless reading on a 32-bits boundary, so we map the addresses to different values

    def UpdateWireOuts(self):
        # wire outs are from the FPGA to the PC
        # in the Opal Kelly API, this function was necessary to perform a read (ie to update the values returned by GetWireOutValue)
        # but with the Red Pitaya Zynq, we actually perform the read at every GetWireOutValue() call, 
        # and this function is completely unecessary
        return 0

        # we basically need to read all the state...
        # in fact, this feature is currently used only for:
        # readLEDs(), just 6 bits
        # readStatusFlags() (which indicate a bunch of 1-bit values)
        # readResidualsStreamingStatus(), again, just 2 bits
        # get_AD9783_SPI_register(), which makes no sense on the new hardware platform
        # ditherRead(), which reads 3x 16 bits values
        # so we could easily overhaul this to something more manageable...

        # print('UpdateWireOuts(): TODO')
        return 0

    def ReadFromPipeOut(self, pipe_address, buffer):
        # read bytes into the buffer, which is a pre-allocated string of the right length
        #buffer = "\x00"*len(buffer)    # for now, return all zeros only
#        print "ReadFromPipeOut: address = %d" % pipe_address
        buffer = self.read_Zynq_buffer_int16(pipe_address, int(round(len(buffer)/2)))

        
        bytes_read = len(buffer)
        return bytes_read



def main():
    rp = RP_PLL_device()
    rp.OpenTCPConnection("192.168.1.100")
    #rp.sock.sendall(struct.pack('=IHhIiIhd', 0xABCD1236, 0, -8*1024, 3, 16*1024, 5, -1, 1.0000000000000004))
    magic_bytes_flank_servo = 0xABCD1236
    iStopAfterZC = 1    # 1 or 0 (true or false)
    ramp_minimum = -8*1024  # -8*1024 is the minimum of the DAC output (-1V into 50 ohms)
    number_of_ramps = 3
    number_of_steps = 16*1024   # 16*1024 is the full span of the dac output (2 Vpp into 50 ohms)
    max_iterations = 500000
    threshold_int16 = 2300
    ki = 1e-3
    
    print("calling sendall")
    for k in range(1):
        rp.sock.sendall(struct.pack('=IHhIiIhd', magic_bytes_flank_servo, iStopAfterZC,
                                    ramp_minimum, number_of_ramps, number_of_steps, 
                                    max_iterations, threshold_int16, ki))
        print("after sendall, calling recvall")
        if max_iterations != 0:
            data_buffer = rp.recvall((number_of_ramps*number_of_steps+max_iterations)*2*2)
            print("after recvall")
            data_np = np.fromstring(data_buffer, dtype=np.int16)
    print('before sleep')
    if max_iterations == 0:
        time.sleep(5)
    print('after sleep')
    rp.sock.close()
    
    
    
    if max_iterations != 0:
        # show data
        plt.close('all')
        plt.figure()
        plot(data_np[1::2], data_np[0::2])
        plt.figure()
        plot(data_np[0::2])
        plt.figure()
        plot(data_np[1::2])
        
        return data_np
    else:
        return 0

def main2():
#if 1:
    rp = RP_PLL_device()
    rp.OpenTCPConnection("192.168.2.12")
    print("hi")
    
#    rp.write_file_on_remote(strFilenameLocal='d:\\test_file.bin', strFilenameRemote='/opt/test_file.bin')
    

    
    time.sleep(3)
    print("quitting")
    return
    
    
    addr_housekeeping = 3
    addr_leds = 0x00030
    
    address_uint32 = (addr_housekeeping << 20) + addr_leds
    data_uint32 = 8+1*16
    rp.write_Zynq_register_uint32(address_uint32, data_uint32)
#   
#   addr_vco = 2Z
#   addr_vco_amplitude = 0x0000
#   addr_vco_freq_msb  = 0x0004
#   addr_vco_freq_lsb  = 0x0008
#   
#   vco_amplitude = round(0.01*(2**15-1))
#   vco_freq_word = np.array([round((15e6/100e6+1./600.)*2.**48)]).astype(np.int64)
#   # break vco word into msbs and lsbs:
#   vco_freq_word_msbs = vco_freq_word >> 32
#   vco_freq_word_lsbs = np.bitwise_and(vco_freq_word, (1<<32)-1)
#   
#   # write amplitude
#   address_uint32 = (addr_vco << 20) + addr_vco_amplitude
#   data_uint32 = vco_amplitude
#   rp.write_Zynq_register_uint32(address_uint32, data_uint32)
#   # write msbs
#   address_uint32 = (addr_vco << 20) + addr_vco_freq_msb
#   data_uint32 = vco_freq_word_msbs
#   rp.write_Zynq_register_uint32(address_uint32, vco_freq_word_msbs)
#   # write lsbs
#   address_uint32 = (addr_vco << 20) + addr_vco_freq_lsb
#   data_uint32 = vco_freq_word_lsbs
#   rp.write_Zynq_register_uint32(address_uint32, vco_freq_word_lsbs)
    
    # write some frequency
    addr_dpll = 0
    addr_ref_freq_msb = 0x8001
    address_uint32 = (addr_dpll << 20) + addr_ref_freq_msb*4    # times 4 due to address space translation
    rp.write_Zynq_register_uint32(address_uint32, 0x1000)

    # first trigger a write
    addr_logger = 1
    addr_trig_write = 0x1004
    address_uint32 = (addr_logger << 20) + addr_trig_write
    rp.write_Zynq_register_uint32(address_uint32, 0)
 
    address_uint32 = 0  # apparently this is currently unused
    number_of_points = rp.MAX_SAMPLES_READ_BUFFER   
    data_buffer = rp.read_Zynq_buffer_int16(address_uint32, number_of_points)
#   print("after recvall")
    data_np = np.fromstring(data_buffer, dtype=np.int16)
    print(data_np)
    for k in range(10):
        print('%d:\t%s' % (k, hex((data_np[k])&0xFFFF)))
#    print hex(data_np[7])
#    print hex(data_np[7])
#    print hex(data_np[7])
    
    plt.figure()
    plt.plot(data_np, '.-')
    
#   spc = np.fft.fft(data_np * np.blackman(len(data_np)))
#   plt.figure()
#   plt.plot(10*np.log10(np.abs(spc)**2.))
    
#   return data_np
        
if __name__ == '__main__':
##    data_np = main()
    data_np = main2()
    


                

# # Stuff for the initialization, which has to be completely re-done anyway:
# self.dev = ok.FrontPanel()
# n_devices = self.dev.GetDeviceCount()

# self.dev_list[k] = self.dev.GetDeviceListSerial(k)


# self.dev = ok.FrontPanel()

# self.dev.OpenBySerial(self.dev.GetDeviceListSerial(0))

# self.dev.OpenBySerial(str(strSerial))

# #if self.dev.IsOpen():

# error_code = self.dev.ConfigureFPGA(strFirmware)