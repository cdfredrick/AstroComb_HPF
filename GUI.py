# -*- coding: utf-8 -*-
"""
Created on Wed Feb 01 12:55:59 2017

@author: ajm6
"""

import sys
from PyQt4 import QtGui, QtCore
from ThorLabs import CLD1015
from radio_button_widget_class import RadioButtonWidget
#MMain Window of GUI
class Window(QtGui.QMainWindow):
    def __init__(self, parent = None):
        super(Window, self).__init__(parent)
        #self.setGeometry(50, 50, 1000, 600)
        #self.setStyleSheet("background-color:rgb(70,100,60)")
        self.setWindowTitle("AstroComb Control")
        self.setWindowIcon(QtGui.QIcon('nist-logo.png'))
   
        #create the menu
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')

        #add menu actions
        exit_act = fileMenu.addAction('Exit')
        open_act = fileMenu.addAction('Open File')
        save_act = fileMenu.addAction('Save File')
        
        #create the tool buttons
        exit_btn = QtGui.QToolButton(self)
        open_btn = QtGui.QToolButton(self)
        save_btn = QtGui.QToolButton(self)
        conn_btn = QtGui.QPushButton("Connect",self)
        
        #Add main program label
        title_label = QtGui.QLabel("AstroComb Control V1.1",self)
        title_label.setStyleSheet("font: 20pt; color:black")
        #create radio buttons for hardware
        self.Hardware_list = list()
        self.Hardware_list.append('RIO')
        self.Hardware_list.append('AMP1')
        self.Hardware_list.append('AMP2')
        self.Hardware_list.append('CYBEL')
        self.Hardware_list.append('FIBERLOCK I')
        self.Hardware_list.append('FINISAR')
        self.Hardware_list.append('NEWFERN')
        self.Hardware_list.append('FIBERLOCK II')
        self.Hardware_list.append('DAQ')
        self.Hardware_list.append('OSA')
        self.RadioWidget = RadioButtonWidget('HARDWARE',self,self.Hardware_list)
        
        #create radio buttons for DAQ channels
        self.DAQ_list = list()
        self.DAQ_list.append('CTT DC Bias')
        self.DAQ_list.append('Menlo Lock')
        self.DAQ_list.append('Cavity Lock')
        self.DAQ_list.append('RIO Lock')
        self.DAQ_list.append('Chiller Temp Alarm')
        self.DAQ_list.append('Chiller Sys Alarm')
        self.DAQWidget = RadioButtonWidget('SYSTEM MONITOR',self,self.DAQ_list)
            
        #add labels
        self.Schematic_label = QtGui.QLabel("Schematic Goes Here",self)
        self.Info_label = QtGui.QLabel("HARDWARE INFO",self)
        self.Info_label.setStyleSheet("font: 13pt")
        
        #add information list widget
        self.HardwareInfo_list = QtGui.QListWidget()
        self.HardwareInfo_list.setStyleSheet("background-color:rgb(200,200,200); color:white; border:2px solid white")
        #add schematic image
       # myPixmap = QtGui.QPixmap('Schematic.JPG')
       # self.Schematic_label.setPixmap(myPixmap)
        
        
        #format main window layout by adding sublayouts
        Exit_layout = QtGui.QVBoxLayout()
        Exit_layout.addStretch()
        Exit_sublayout = QtGui.QHBoxLayout()
        Exit_sublayout.addWidget(exit_btn)
        Exit_sublayout.addWidget(open_btn)
        Exit_sublayout.addWidget(save_btn)
        Exit_layout.addLayout(Exit_sublayout)
        
        Connect_layout = QtGui.QHBoxLayout()
        Connect_sublayout = QtGui.QVBoxLayout()
        Connect_sublayout.addWidget(conn_btn)

        Connect_sublayout.addWidget(self.RadioWidget)
        Connect_sublayout.addWidget(self.DAQWidget)
        Connect_sublayout.addStretch()
        Connect_layout.addLayout(Connect_sublayout)
        Connect_layout.addStretch()
        
        Schematic_sublayout = QtGui.QVBoxLayout()
        Schematic_sublayout.addWidget(self.Schematic_label)
        self.Schematic_label.setStyleSheet("margin:20px; border:4px solid green")
      
        info_sublayout = QtGui.QVBoxLayout()
        info_sublayout.addWidget(self.Info_label)
        info_sublayout.addWidget(self.HardwareInfo_list)
        info_sublayout.addStretch()
        
        col1_sublayout = QtGui.QHBoxLayout()
        col1_sublayout.addLayout(Connect_layout)
        col1_sublayout.addLayout(Schematic_sublayout)
        col1_sublayout.addStretch()
        
        col2_sublayout = QtGui.QHBoxLayout()
        col2_sublayout.addLayout(info_sublayout)
        col2_sublayout.addStretch()
        col2_sublayout.addLayout(Exit_layout)
        col2_sublayout.addStretch()
       
        main_layout = QtGui.QVBoxLayout()
        main_layout.addWidget(title_label)
        main_layout.addLayout(col1_sublayout)
        main_layout.addLayout(col2_sublayout)
        
        #create a central container widget
        widget = QtGui.QWidget(self)
        widget.setLayout(main_layout)
        widget.setStyleSheet("background-color:rgb(150,150,150);color:black")
        self.setCentralWidget(widget)
        
        #assign the actions
        exit_btn.setDefaultAction(exit_act)
        open_btn.setDefaultAction(open_act)
        save_btn.setDefaultAction(save_act)
        conn_btn.clicked.connect(self.connect_)
        #create the connections
        exit_act.triggered.connect( self.exit_)
        open_act.triggered.connect( self.open_)
        save_act.triggered.connect( self.save_)
        
        self.show()
        
    def exit_(self):
        choice = QtGui.QMessageBox.question(self, 'Close!',
                                         "Do you want to Close?",
                                           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if choice == QtGui.QMessageBox.Yes:
            print("Closing Program")
            sys.exit()
        else:
           pass
     
    def open_(self):
        print('Open File')
        
    def save_(self):
        print('Save File')
        
    def connect_(self):

       self.IO_RIO = CLD1015('USB0::0x1313::0x804F::M00328014::INSTR','RIO')
       print("Connection to RIO Laser")
       ans = CLD1015.SetAllParameters(self.IO_RIO)
       print(ans)
       RIO_radio = self.RadioWidget.radio_button_list[0]
       RIO_radio.setStyleSheet("background-color: green")
       self.HardwareInfo_list.addItems(ans)
       self.HardwareInfo_list.show()
       RIO_radio.setChecked(True)

def run():       
    app = QtGui.QApplication(sys.argv)
    GUI = Window()
    sys.exit(app.exec_())


run()