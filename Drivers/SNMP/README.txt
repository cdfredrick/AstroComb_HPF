# Loading MIB Example

Demonstrates loading the TRIPPLITE-PRODUCTS MIB. The process automatically imports any dependencies (i.e. TRIPPLITE for TRIPPLITE-PRODUCTS, and SNMPv2-SMI for TRIPPLITE.). The file names must match the given MIB name (no file extensions). Resolved (converted to python) MIB files are output to "<User path>\PySNMP Configuration\mibs". Something like this should be executed on initialization to ensure that the .py files are in place. Standard usage does not require specifying MibSource or calling the resolve function.

'''
from pysnmp.smi import rfc1902
from pysnmp.smi import builder
from pysnmp.smi import view

mibBuilder = builder.MibBuilder()
mibView = view.MibViewController(mibBuilder)

obj_id = rfc1902.ObjectIdentity('TRIPPLITE-PRODUCTS','tlpPduOutletCommand', 1)

obj_id.addAsn1MibSource('file://@mib@')
obj_id.addAsn1MibSource('http://mibs.snmplabs.com/asn1/@mib@')
obj_id.resolveWithMib(mibView)

print(obj_id.getMibSymbol())
print(obj_id.getOid())
print(obj_id.getLabel())
'''