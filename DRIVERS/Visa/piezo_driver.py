# -*- coding: utf-8 -*-
"""
Created on Mon Dec 18 2017

@author: Connor

"""

#Astrocomb imports
import visa_objects as vo
import eventlog as log
import ac_excepts


# %% Thorlabs MDT693B
class MDT639B(vo.Visa):
    """Holds commands for ILX chassis and passes commands for components."""
    @log.log_this()
    def __init__(self, visa_address, res_manager=None):
        super(MDT639B, self).__init__(visa_address, res_manager=res_manager)
        if self.resource is None:
            raise ac_excepts.VirtualDeviceError(
                'Could not create piezo instrument!', self.__init__)
        self.resource.read_termination = '\r>'
        self.echo(set_echo=False)
        self.x_min()
        self.x_max()
        self.y_min()
        self.y_max()
        self.z_min()
        self.z_max()
    
    @log.log_this()
    def identification(self):
        '''
        Gets the product header and firmware version.
        '''
    # Send query
        result = self.query('id?')
        return result
    
    @log.log_this()
    def echo(self, set_echo=None):
        '''
        (0=Off, 1=On) When on all commands are echoed back.
        '''
        if set_echo is None:
        # Send query
            result = self.query('echo?')
            if result=='[Echo Off]':
                return False
            else:
                return True
        else:
        # Limit range
            set_echo = vo.tf_toggle(set_echo)
        # Send command
            self.query('echo={:}'.format(set_echo))
    
    @log.log_this()
    def vlimit(self):
        '''
        Gets output voltage limit switch setting (0=75V, 1=100V, 2=150V).
        '''
    # Send query
        result = self.query()
        return float(result.strip('[]'))
    
    @log.log_this()
    def display(self, set_intensity=None):
        '''
        The display intensity (0-15).
        '''
        if set_intensity is None:
        # Send query
            result = self.query('intensity?')
            return int(result)
        else:
        # Limit range
            if set_intensity < 0:
                set_inensity = 0
            elif set_inensity > 15:
                set_intensity = 15
        # Send command
            self.query('intensity={:}'.format(int(set_intensity)))
    
    @log.log_this()
    def master_scan_action(self, set_action=None):
        '''
        The Master Scan enable state (0=Off, 1=On)
        '''
        if set_action is None:
        # Send query
            result = self.query('msenable?')
            return bool(result)
        else:
        #Limit range
            set_action = vo.tf_toggle(set_action)
        # Send command
            self.query('msenable={:}'.format(set_action))
    
    @log.log_this()
    def x_min(self, set_min=None):
        '''
        The minimum output voltage limit for the x axis
        '''
        if set_min is None:
        # Send query
            result = self.query('xmin?')
            self.x_min = float(result)
            return float(result)
        else:
        # Limit range
            if set_min < 0:
                set_min = 0
            elif set_min > self.x_max:
                set_min = self.x_max
        # Send command
            self.query('xmin={:f}'.format(set_min))
    
    @log.log_this()
    def x_max(self, set_max=None):
        '''
        The maximum output voltage limit for the x axis
        '''
        if set_max is None:
        # Send query
            result = self.query('xmax?')
            self.x_max = float(result)
            return float(result)
        else:
        # Limit range
            if set_max < self.x_min:
                set_max = self.x_min
            elif set_max > 150.50:
                set_max = 150.50
        # Send command
            self.query('xmax={:f}'.format(set_max))
        
    @log.log_this()
    def x_voltage(self, set_voltage=None):
        '''
        The output voltage for the x axis.
        '''
        if set_voltage is None:
        # Send query
            result = self.query('xvoltage?')
            return float(result.strip('[]'))
        else:
        # Limit range
            if set_voltage < self.x_min:
                set_voltage = self.x_min
            elif set_voltage > self.x_max:
                set_voltage = self.x_max
        # Send command
            self.query('xvoltage={:f}'.format(set_voltage))
    
    @log.log_this()
    def y_min(self, set_min=None):
        '''
        The minimum output voltage limit for the y axis
        '''
        if set_min is None:
        # Send query
            result = self.query('ymin?')
            self.y_min = float(result)
            return float(result)
        else:
        # Limit range
            if set_min < 0:
                set_min = 0
            elif set_min > self.y_max:
                set_min = self.y_max
        # Send command
            self.query('ymin={:f}'.format(set_min))
    
    @log.log_this()
    def y_max(self, set_max=None):
        '''
        The maximum output voltage limit for the y axis
        '''
        if set_max is None:
        # Send query
            result = self.query('ymax?')
            self.y_max = float(result)
            return float(result)
        else:
        # Limit range
            if set_max < self.y_min:
                set_max = self.y_min
            elif set_max > 150.50:
                set_max = 150.50
        # Send command
            self.query('ymax={:f}'.format(set_max))
        
    @log.log_this()
    def y_voltage(self, set_voltage=None):
        '''
        The output voltage for the y axis.
        '''
        if set_voltage is None:
        # Send query
            result = self.query('yvoltage?')
            return float(result.strip('[]'))
        else:
        # Limit range
            if set_voltage < self.y_min:
                set_voltage = self.y_min
            elif set_voltage > self.y_max:
                set_voltage = self.y_max
        # Send command
            self.query('yvoltage={:f}'.format(set_voltage))
    
    @log.log_this()
    def z_min(self, set_min=None):
        '''
        The minimum output voltage limit for the z axis
        '''
        if set_min is None:
        # Send query
            result = self.query('zmin?')
            self.z_min = float(result)
            return float(result)
        else:
        # Limit range
            if set_min < 0:
                set_min = 0
            elif set_min > self.z_max:
                set_min = self.z_max
        # Send command
            self.query('zmin={:f}'.format(set_min))
    
    @log.log_this()
    def z_max(self, set_max=None):
        '''
        The maximum output voltage limit for the z axis
        '''
        if set_max is None:
        # Send query
            result = self.query('zmax?')
            self.z_max = float(result)
            return float(result)
        else:
        # Limit range
            if set_max < self.z_min:
                set_max = self.z_min
            elif set_max > 150.50:
                set_max = 150.50
        # Send command
            self.query('zmax={:f}'.format(set_max))
        
    @log.log_this()
    def z_voltage(self, set_voltage=None):
        '''
        The output voltage for the z axis.
        '''
        if set_voltage is None:
        # Send query
            result = self.query('zvoltage?')
            return float(result.strip('[]'))
        else:
        # Limit range
            if set_voltage < self.z_min:
                set_voltage = self.z_min
            elif set_voltage > self.z_max:
                set_voltage = self.z_max
        # Send command
            self.query('zvoltage={:f}'.format(set_voltage))

