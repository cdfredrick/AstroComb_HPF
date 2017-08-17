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
    comb_hard_shutdown()
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
            'thermocube', 'eo_comb_dc_bias']
S2_NAMES = ['yokogawa', 'cybel', 'tem_controller1']
S3_NAMES = ['yokogawa', 'finisar', 'nufern', 'tem_controller2']
S4_NAMES = ['yokogawa', 'pulse_shaper']


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
        try:
            self.device_dict = initiate_virtual_devices.open_all()
            #Keys list: 'yokogawa', 'ilx', 'rio_laser', 'preamp', 'ilx_2',
            #    'ilx_3', 'cybel', 'thermocube', 'rio_pd_monitor',
            #    'eo_comb_dc_bias'
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
            self.stage1.stage_one_warm_up()
            self.stage2.stage_two_warm_up()
            self.stage3.stage_three_warm_up()
            self.stage4.stage_four_warm_up()
        except ac_excepts.StartupError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)

    def comb_start_up(self):
        """Starts all of the devices in the comb, while checks if working."""
        try:
            self.stage1.stage_one_start_up()
            self.stage2.stage_two_start_up()
            self.stage3.stage_three_start_up()
            self.stage4.stage_four_start_up()
        except ac_excepts.StartupError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            #Don't try anything else

    def comb_soft_shutdown(self, stop):
        """Soft shutdown on stages 4 to 'stop'.

        i.e. stop=4 turns off stage 4 or if stop=2 turns off stages 4, 3,
            and 2."""
        if not stop in range(1, 4):
            raise ValueError('Invalid choice of stages to turn off.')
        try:
            self.stage4.stage_four_soft_shutdown()
            if stop <= 3:
                self.stage3.stage_three_soft_shutdown()
            if stop <= 2:
                self.stage2.stage_two_soft_shutdown()
            if stop == 1:
                self.stage1.stage_one_soft_shutdown()
        except ac_excepts.ShutdownError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Soft shutdown failed!',
                                           self.comb_soft_shutdown)

    def comb_hard_shutdown(self, stop):
        """Hard shutdown on stages 4 to 'stop'.

        i.e. stop=4 turns off stage 4 or if stop=2 turns off stages 4, 3,
            and 2."""
        if not stop in range(1, 4):
            raise ValueError('Invalid choice of stages to turn off.')
        try:
            self.stage4.stage_four_hard_shutdown()
            if stop <= 3:
                self.stage3.stage_three_hard_shutdown()
            if stop <= 2:
                self.stage2.stage_two_hard_shutdown()
            if stop == 1:
                self.stage1.stage_one_hard_shutdown()
        except ac_excepts.ShutdownError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.ShutdownError('Hard shutdown failed!',
                                           self.comb_hard_shutdown)
