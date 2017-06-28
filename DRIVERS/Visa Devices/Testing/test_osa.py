# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 14:19:40 2017
@author: Wesley Brand
"""


import osa_driver as yok
import eventlog as log

log.start_logging()

print __name__

def test():
    """Tests some basic methods and connectability of OSA"""
    osa = yok.OSA(yok.OSA_NAME, yok.OSA_ADDRESS)
    if osa.res is None:
        raise SystemExit
    osa.query_identity()
    osa.set_sweep_parameters()
    pdict = osa.query_sweep_parameters()
    print pdict
    osa.get_spectrum(True)
    osa.close()

test()
