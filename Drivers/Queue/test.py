# -*- coding: utf-8 -*-
"""
Created on Thu Mar  8 17:32:57 2018

@author: Connor
"""
# %%
import LiteQ
import datetime
import time

# %%
q = LiteQ.Q2('testing2')

# %%
then = datetime.datetime.now()
q.add_to_queue(ttl=5.0, priority=1)
while True:
    if q.activate():
        now = datetime.datetime.now()
        print(now-then)
        print(q.queue)
        #q.remove_from_queue()
        #q.add_to_queue(ttl=5.0, priority=1)
        q.requeue()
        then = now
    time.sleep(0.01)