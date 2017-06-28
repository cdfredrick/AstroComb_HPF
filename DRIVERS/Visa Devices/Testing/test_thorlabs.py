# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 13:18:27 2017

@author: wjb4
"""
import time
import eventlog as log
import thorlabs_cld1015_driver as thor


log.start_logging()
THOR = thor.LaserDiodeControl(thor.LD_NAME, thor.LD_ADDRESS)
if THOR.res is None:
    raise SystemExit
THOR.read()
i = 0
while True:
    test_val = THOR.test()
    print 'Test: %s' % test_val
    print '\r \n'
    i += 1
    if i > 10:
        break
    time.sleep(1)
THOR.close()