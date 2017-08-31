# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 11:16:09 2017

@author: Wesley Brand

Public class:
    AstroComb

Public methods:
    comb_warm_up()
    comb_start_up()
    comb_soft_shutdown()
    comb_full_shutdown()
"""
#pylint: disable=W0102
##As long as the constants are maintained, making them defaults of __init__
##  should not be a problem


#Python imports
#import smtplib
#from email.MIMEMultipart import MIMEMultipart
#from email.MIMEText import MIMEText

#3rd party imports

#Astrocomb imports
import eventlog as log
import ac_excepts
import initiate_virtual_devices
import ac_stage_one
import ac_stage_two
import ac_stage_three
import ac_stage_four


#Constants
##Keys of devices in device dictionary
S1_NAMES = ['yokogawa', 'ilx', 'rio_laser', 'preamp', 'rio_pd_monitor',
            'thermocube', 'eo_comb_dc_bias'] #rf_oscillator
S2_NAMES = ['yokogawa', 'cybel', 'tem_fiberlock1']
S3_NAMES = ['yokogawa', 'finisar', 'tem_fiberlock2'] #nufern
S4_NAMES = ['yokogawa'] #pulse_shaper


#This function is currently not working, probably due to NIST firewall/proxy
#    A nice extra feature if can be fixed
#def send_email(subject, message):
#    """Sends an email to whoever is taking care of the comb when needed."""
#    comb_email = 'hpf.astrocomb@gmail.com'
#    comb_pswd = '1qazxsw2!QAZXSW@'
#    #password is the 1->z->x->2->1 loop twice with shift held the second time
#    server = smtplib.SMTP('smtp.gmail.com', 587, comb_email, timeout=60)
#    destination_emails = ['webr5214@colorado.edu'] #Test target
#    print 'set up'
#
#    msg = MIMEMultipart()
#    msg['From'] = comb_email
#    msg['To'] = destination_emails
#    msg['Subject'] = subject
#    msg.attach(MIMEText(message, 'plain'))
#    text = msg.as_string()
#    print 'message made'
#
#    server.ehlo()
#    print 'ehlo'
#    server.starttls()
#    print 'start'
#    server.login(comb_email, comb_pswd)
#    print 'logged in'
#    server.sendmail(comb_email, destination_emails, text)
#    print 'sent mail'
#    server.quit()

class AstroComb(object):
    """The master object that contains all devices and system commands."""

    def __init__(self, s1_names=S1_NAMES, s2_names=S2_NAMES, s3_names=S3_NAMES,
                 s4_names=S4_NAMES):

        log.start_logging()

        self.temp_control_on = False
        self.comb_light_on = False

        try:
            self.device_dict = initiate_virtual_devices.open_all()
            #Keys list: 'yokogawa', 'ilx', 'rio_laser', 'preamp', 'ilx_2',
            #    'ilx_3', 'cybel', 'thermocube', 'rio_pd_monitor',
            #    'eo_comb_dc_bias', 'tem_fiberlock1', 'tem_fiberlock2'
        except ac_excepts.VirtualDeviceError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Could not initiate devices!',
                                          self.__init__)

        s1_dict = {k:self.device_dict[k] for k in s1_names if k in
                   self.device_dict}
        self.stage1 = ac_stage_one.StageOne(s1_dict)

        s2_dict = {k:self.device_dict[k] for k in s2_names if k in
                   self.device_dict}
        self.stage2 = ac_stage_two.StageTwo(s2_dict)

        s3_dict = {k:self.device_dict[k] for k in s3_names if k in
                   self.device_dict}
        self.stage3 = ac_stage_three.StageThree(s3_dict)

        s4_dict = {k:self.device_dict[k] for k in s4_names if k in
                   self.device_dict}
        self.stage4 = ac_stage_four.StageFour(s4_dict)

        #Can build more objects that collect instruments, i.e. those that
        #   work together to maintain lock, those that need monitoring for
        #   malfunction, etc.


    def comb_warm_up(self):
        """Starts all of the TECs, may be run before startup, but not required."""
        try:
            if not self.temp_control_on:
                self.stage1.stage_one_warm_up()
                self.stage2.stage_two_warm_up()
                self.stage3.stage_three_warm_up()
                self.stage4.stage_four_warm_up()
                self.device_dict['thermocube'].query_alarms()
                self.temp_control_on = True
        except ac_excepts.StartupError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)

    def comb_start_up(self, start=1, stop=4):
        """Starts all of the devices in specified stages."""
        if not start in range(1, 4) or not stop in range(1, 4) or start > stop:
            raise ValueError('Invalid choice of stages to turn on.')

        if self.comb_light_on:
            log.log_warn(__name__, 'comb_start_up',
                         'Comb light already on', 20)
            return

        try:
            if start == 1:
                self.stage1.stage_one_start_up()
            if start <= 2 and stop >= 2:
                self.stage2.stage_two_start_up()
            if start <= 3 and stop >= 3:
                self.stage3.stage_three_start_up()
            if start <= 4 and stop == 4:
                self.stage4.stage_four_start_up()
                self.temp_control_on = True
                self.comb_light_on = True

        except ac_excepts.StartupError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Comb start up failed!',
                                          self.comb_start_up)

    def comb_soft_shutdown(self, start=4, stop=1):
        """Turns off lasers in stages start to stop, start=stop ok."""
        if not start in range(1, 4) or not stop in range(1, 4) or start < stop:
            raise ValueError('Invalid choice of stages to turn off.')

        try:
            if start == 4:
                self.stage4.stage_four_soft_shutdown()
            if start >= 3 and stop <= 3:
                self.stage3.stage_three_soft_shutdown()
            if start >= 2 and stop <= 2:
                self.stage2.stage_two_soft_shutdown()
            if start >= 1 and stop == 1:
                self.stage1.stage_one_soft_shutdown()
            self.comb_light_on = False
        except ac_excepts.ShutdownError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Soft shutdown failed!',
                                           self.comb_soft_shutdown)

    def comb_full_shutdown(self):
        """Shuts down everything, closes connections, ends program."""
        try:
            self.stage4.stage_four_full_shutdown()
            self.stage3.stage_three_full_shutdown()
            self.stage2.stage_two_full_shutdown()
            self.stage1.stage_one_full_shutdown()
            quit()

        except ac_excepts.ShutdownError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('full shutdown failed!',
                                           self.comb_full_shutdown)
