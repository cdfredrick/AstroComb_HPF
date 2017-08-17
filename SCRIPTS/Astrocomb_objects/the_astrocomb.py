# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 11:16:09 2017

@author: Wesley Brand

Public class:
    AstroComb

Public methods:
    main_startup_sequence()
"""

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
#import ac_stage_three
#import ac_stage_four

#def send_email(subject, message):
#    """Sends an email to whoever is taking care of the comb when needed."""
#    comb_email = 'hpf.astrocomb@gmail.com'
#    comb_pswd = '1qazxsw2!QAZXSW@'
#    #password is the 1->z->x->2->1 loop twice with shift held the second time
#    server = smtplib.SMTP('smtp.gmail.com', 587, comb_email, timeout=60)
#    destination_emails = ['webr5214@colorado.edu']
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

    def __init__(self):
        log.start_logging()
        try:
            device_dict = initiate_virtual_devices.open_all()
            #Keys list: 'yokogawa', 'ilx', 'rio_laser', 'preamp', 'ilx_2',
            #    'ilx_3', 'cybel', 'thermocube', 'rio_pd_monitor',
            #    'eo_comb_dc_bias'
        except ac_excepts.VirtualDeviceError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            raise ac_excepts.StartupError('Could not initiate devices!',
                                          self.__init__)

        s1_names = ['yokogawa', 'ilx', 'rio_laser', 'preamp',
                    'rio_pd_monitor', 'thermocube', 'eo_comb_dc_bias']
        s1_dict = {k:device_dict[k] for k in s1_names if k in device_dict}
        self.stage1 = ac_stage_one.StageOne(s1_dict)

        s2_names = ['yokogawa', 'cybel', 'tem_controller']
        s2_dict = {k:device_dict[k] for k in s2_names if k in device_dict}
        self.stage2 = ac_stage_two.StageTwo(s2_dict)

#        s3_names = []
#        s3_dict = {k:device_dict[k] for k in s3_names if k in device_dict}
#        self.stage3 = ac_stage_three.StageThree(s3_dict)
#
#        s4_names = []
#        s4_dict = {k:device_dict[k] for k in s4_names if k in device_dict}
#        self.stage4 = ac_stage_four.StageFour(s4_dict)

    def main_startup_sequence(self):
        """Starts all of the devices in the comb, while checks if working."""
        try:
            self.stage1.stage_one_startup_sequence()
            self.stage2.stage_two_startup_sequence()
#            self.stage3.stage_three_startup_sequence()
#            self.stage4.stage_four_startup_sequence()
        except ac_excepts.StartupError as err:
            log.log_error(err.method.__module__, err.method.__name__, err)
            #Don't try anything else
