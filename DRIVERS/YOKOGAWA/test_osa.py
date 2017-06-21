# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 14:19:40 2017
@author: Wesley Brand
"""


import osa_driver as yok
import eventlog as log

log.start_logging()



def test():
    """Tests some basic methods and connectability of OSA"""
    osa = yok.OSA(yok.OSA_NAME, yok.OSA_ADDRESS)
    print osa.file_name
    if osa.res is None:
        raise SystemExit
    osa.query_identity()
    osa.save_n_graph_spectrum()
    osa.close()

test()
