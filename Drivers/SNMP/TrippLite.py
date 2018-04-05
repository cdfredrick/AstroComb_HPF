# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 14:55:34 2018

@author: Connor
"""

# %% Modules ==================================================================
from pysnmp.smi import rfc1902
from pysnmp.smi import builder
from pysnmp.smi import view

from pysnmp.hlapi import SnmpEngine
from pysnmp.hlapi import CommunityData
from pysnmp.hlapi import UdpTransportTarget
from pysnmp.hlapi import ContextData
from pysnmp.hlapi import getCmd, nextCmd, setCmd


# %% PDU

class PDUOutlet():
    def __init__(self, ip_address, outlet_id, timeout=1, retries=5):
        self.mib = 'TRIPPLITE-PRODUCTS'
        self.transport_addr = (str(ip_address), 161)
        self.transport_target = UdpTransportTarget(self.transport_addr, timeout=timeout, retries=retries)
        self.outlet_id = int(outlet_id)
        self.device_id = 1
        self.community = CommunityData('tripplite')
    # Initialize the MIB
        mibBuilder = builder.MibBuilder()
        mibView = view.MibViewController(mibBuilder)
        obj_id = rfc1902.ObjectIdentity(self.mib)
        obj_id.addAsn1MibSource('file://@mib@')
        obj_id.addAsn1MibSource('http://mibs.snmplabs.com/asn1/@mib@')
        obj_id.resolveWithMib(mibView)
    
    def query(self, oid,  base=False):
    # Get current outlet state
        if base:
            obj_id = rfc1902.ObjectIdentity(self.mib, oid)
        else:
            obj_id = rfc1902.ObjectIdentity(oid)
        g = getCmd(SnmpEngine(),
                   self.community,
                   self.transport_target,
                   ContextData(),
                   rfc1902.ObjectType(obj_id))
        errorIndication, errorStatus, errorIndex, varBinds = next(g)
        print(errorIndication, '\n')
        print(errorStatus, '\n')
        print(errorIndex, '\n')
        print(varBinds, '\n')
        oid, value = varBinds[0]
        print(varBinds[0].prettyPrint(), '\n')
        print(oid, '\n')
        print(value, '\n')
    
    def outlet_state(self, set_state=None):
        '''The current state of the outlet. Setting this value to turnOff(1)
        will turn off the outlet. Setting this value to turnOn(2) will turn on
        the outlet. Setting this value to cycle(3) will turn the outlet off, 
        then turn it back on:
            0 = idle or unknown
            1 = off
            2 = on
            3 = cycle (turn off, then turn on
        '''
        if set_state is None:
        # Get current outlet state
            obj_id = rfc1902.ObjectIdentity(self.mib, 'tlpPduOutletState', self.device_id, self.outlet_id)
            g = getCmd(SnmpEngine(),
                       self.community,
                       self.transport_target,
                       ContextData(),
                       rfc1902.ObjectType(obj_id))
            errorIndication, errorStatus, errorIndex, varBinds = next(g)
            oid, value = varBinds[0]
            print(oid)
            return int(value)
        else:
        # Send outlet state
            obj_id = rfc1902.ObjectIdentity(self.mib, 'tlpPduOutletCommand', self.device_id, self.outlet_id)
            g = setCmd(SnmpEngine(),
                       self.community,
                       self.transport_target,
                       ContextData(),
                       rfc1902.ObjectType(obj_id, int(set_state)))
            errorIndication, errorStatus, errorIndex, varBinds = next(g)
    
    def outlet_ramp_action(self, set_action=None):
        '''The ramp action to take on a given outlet when powering on the 
        device:
            0 = remain off
            1 = turn on after delay
        '''
        if set_action is None:
        # Get current outlet state
            obj_id = rfc1902.ObjectIdentity(self.mib, 'tlpPduOutletRampAction', self.device_id, self.outlet_id)
            g = getCmd(SnmpEngine(),
                       self.community,
                       self.transport_target,
                       ContextData(),
                       rfc1902.ObjectType(obj_id))
            errorIndication, errorStatus, errorIndex, varBinds = next(g)
            oid, value = varBinds[0]
            return int(value)
        else:
        # Send outlet state
            obj_id = rfc1902.ObjectIdentity(self.mib, 'tlpPduOutletRampAction', self.device_id, self.outlet_id)
            g = setCmd(SnmpEngine(),
                       self.community,
                       self.transport_target,
                       ContextData(),
                       rfc1902.ObjectType(obj_id, int(set_action)))
            errorIndication, errorStatus, errorIndex, varBinds = next(g)
    
    def outlet_ramp_delay(self, set_delay=None):
        '''The number of seconds to delay before powering on the given outlet:
            integer values only
        '''
        if set_delay is None:
        # Get current outlet state
            obj_id = rfc1902.ObjectIdentity(self.mib, 'tlpPduOutletRampDelay', self.device_id, self.outlet_id)
            g = getCmd(SnmpEngine(),
                       self.community,
                       self.transport_target,
                       ContextData(),
                       rfc1902.ObjectType(obj_id))
            errorIndication, errorStatus, errorIndex, varBinds = next(g)
            oid, value = varBinds[0]
            return int(value)
        else:
        # Send outlet state
            obj_id = rfc1902.ObjectIdentity(self.mib, 'tlpPduOutletRampDelay', self.device_id, self.outlet_id)
            g = setCmd(SnmpEngine(),
                       self.community,
                       self.transport_target,
                       ContextData(),
                       rfc1902.ObjectType(obj_id), int(set_delay))
            errorIndication, errorStatus, errorIndex, varBinds = next(g)
    