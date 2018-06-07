# -*- coding: utf-8 -*-
"""
Created on Sun Mar 11 16:01:52 2018

@author: Connor
"""

# %% Modules ==================================================================

from couchbase.cluster import Cluster
from couchbase.cluster import PasswordAuthenticator
from couchbase.exceptions import NotFoundError, KeyExistsError, QueueEmpty, TemporaryFailError
from couchbase.bucket import LOCKMODE_WAIT

import threading
import time

from Drivers.Logging import EventLog as log


# %% Priority Queue ===========================================================

class PriorityQueue():
    @log.log_this()
    def __init__(self, queue_ID, bucket='queue', host='localhost', username='default', password='default', timeout=50):
        '''The priority queue implements a FIFO queue with optional priority
        insertion. The "bucket", "host", "username", and "password" keywords
        must match those specified in the database configuration. The "timeout"
        keyword sets the amount of time before the queue becomes stale, upon 
        which the queue is emptied of all items. The queue object should be
        threadsafe, each thread of execution enters in as a unique item.
        '''
        self.cluster = Cluster('couchbase://{:}'.format(host))
        authenticator = PasswordAuthenticator(username, password)
        self.cluster.authenticate(authenticator)
        self.cb = self.cluster.open_bucket(bucket, lockmode=LOCKMODE_WAIT)
        # Create id counter (if it does not exist)
        self.c_ID = 'id_counter'
        self.cb.counter(self.c_ID, initial=0)
        # Create the queue (if it does not exist)
        self.q_ID = queue_ID
        try:
            self.cb.insert(self.q_ID, [])
        except (KeyExistsError, TemporaryFailError):
            pass
        self.last_id = {}
        # Initialize queue timeout (s)
        self.timeout = int(timeout)
        try:
            self.cb.touch(self.q_ID, ttl=self.timeout)
        except TemporaryFailError:
            pass
    
    @log.log_this()
    def push(self,priority=False, message='', remove_old_id=False):
        '''Set the "clean_old_ids" keyword to True if other interpreter
        sessions are liable to remove queue items entered by the current
        session. Old thread identifiers will be removed from the "local"
        last_id.
        '''
        id_int = self.cb.counter(self.c_ID).value
        priority = bool(priority)
        new_item = {'id':id_int, 'priority':priority, 'message':message}
        loop_for_cas = True
        while loop_for_cas:
            try:
                try:
                    if priority:
                        # Lock and Get current queue
                        result = self.cb.lock(self.q_ID, ttl=1)
                        cas = result.cas
                        result = self.cb.get(self.q_ID)
                        queue = result.value
                        # Get current priority index
                        if len(queue) < 2:
                            self.cb.queue_push(self.q_ID, new_item, cas=cas, ttl=self.timeout)
                        else:
                            try:
                                # Insert before the first priority item
                                priority_index = [item['priority'] for item in queue].index(True)
                            except ValueError:
                                # If no priority item, insert into second place
                                priority_index = -2
                            # Insert into queue
                            queue.insert(priority_index, new_item)
                            self.cb.upsert(self.q_ID, queue, cas=cas, ttl=self.timeout)
                    else:
                        # Insert into 
                        self.cb.queue_push(self.q_ID, new_item, ttl=self.timeout)
                except NotFoundError:
                    # Recreate the queue if it does not exist
                    self.cb.queue_push(self.q_ID, new_item, create=True, ttl=self.timeout)
            except KeyExistsError:
                pass
            except TemporaryFailError:
                pass
            else:
                loop_for_cas = False
        # Clean up old thread identifiers
        if remove_old_id:
            queue = self.get_queue()
            current_id_ints = [item['id'] for item in queue]
            id_keys = [key for (key, value) in self.last_id.items() if not(value in current_id_ints)]
            for key in id_keys:
                self.last_id.pop(key)
        # Return the new item's id
        self.last_id[threading.get_ident()] = id_int
        return id_int
    
    @log.log_this()
    def position(self, id_int=None):
        if id_int is None:
            if threading.get_ident() in self.last_id:
                id_int = self.last_id[threading.get_ident()]
            else:
                id_int = -1
        try:
            result = self.cb.get(self.q_ID)
            queue = result.value
            if len(queue) > 0:
                try:
                    # The last item in the list is the top of the queue
                    index = [item['id'] for item in queue[::-1]].index(id_int)
                except ValueError:
                    index = -1
            else:
                index = -1
        except NotFoundError:
            index = -1
        # Return index
        return index
    
    @log.log_this()
    def remove(self, id_int=None):
        if id_int is None:
            if threading.get_ident() in self.last_id:
                id_int = self.last_id[threading.get_ident()]
            else:
                id_int = -1
        try:
            loop_for_cas = True
            while loop_for_cas:
                try:
                    # Get current queue
                    result = self.cb.get(self.q_ID)
                    cas = result.cas
                    queue = result.value
                    # Get current index
                    try:
                        index = [item['id'] for item in queue].index(id_int)
                    except ValueError:
                        index = -1
                    # Remove from queue
                    if index >= 0:
                        queue.pop(index)
                        self.cb.upsert(self.q_ID, queue, cas=cas,ttl=self.timeout)
                except KeyExistsError:
                    pass
                else:
                    loop_for_cas = False
        except NotFoundError:
            pass
        # Clear last_ids
        id_keys = [key for (key,value) in self.last_id.items() if (value==id_int)]
        for key in id_keys:
            self.last_id.pop(key)
    
    @log.log_this()
    def pop(self):
        try:
            loop_for_cas = True
            while loop_for_cas:
                try:
                    item = self.cb.queue_pop(self.q_ID, ttl=self.timeout).value
                except TemporaryFailError:
                    pass
                else:
                    loop_for_cas = False
        except QueueEmpty:
            item = {}
        except NotFoundError:
            item = {}
        # Clear last_ids
        if 'id' in item:
            id_keys = [key for (key,value) in self.last_id.items() if (value==item['id'])]
            for key in id_keys:
                self.last_id.pop(key)
        # Return the item
        return item
    
    @log.log_this()
    def get_queue(self):
        try:
            result = self.cb.get(self.q_ID)
            queue = result.value
        except NotFoundError:
            queue = []
        return queue[::-1]
    
    @log.log_this()
    def touch(self):
        try:
            loop_for_cas = True
            while loop_for_cas:
                try:
                    self.cb.touch(self.q_ID, ttl=self.timeout)
                except TemporaryFailError:
                    pass
                else:
                    loop_for_cas = False
        except NotFoundError:
            pass
    
    @log.log_this()
    def queue_and_wait(self, priority=False, message=''):
        queued = True
        wait_for_queue = True
        while wait_for_queue:
            queue_position = self.position()
            if (queue_position == 0):
            # Item is at the top of the queue
                wait_for_queue = False
            elif (queue_position < 0):
            # Enter item into queue
                queued = False
                self.push(priority=priority, message=message)
            else:
            # Wait for queue
                time.sleep(0.01)
        return queued


# %% FIFO Queue ===============================================================

class FIFOQueue():
    @log.log_this()
    def __init__(self, queue_ID, bucket='queue', host='localhost', username='default', password='default', timeout=50):
        '''The FIO queue implements a simple FIFO queue. The "bucket", "host", 
        "username", and "password" keywords must match those specified in the
        database configuration. The "timeout" keyword sets the amount of time
        before the queue becomes stale, upon which the queue is emptied of all
        items. The queue object should be threadsafe, each thread of execution
        enters in as a unique item.
        '''
        self.cluster = Cluster('couchbase://{:}'.format(host))
        authenticator = PasswordAuthenticator(username, password)
        self.cluster.authenticate(authenticator)
        self.cb = self.cluster.open_bucket(bucket)
        # Create id counter (if it does not exist)
        self.c_ID = 'id_counter'
        self.cb.counter(self.c_ID, initial=0)
        # Create the queue (if it does not exist)
        self.q_ID = queue_ID
        try:
            self.cb.insert(self.q_ID, [])
        except KeyExistsError:
            pass
        self.last_id = {}
        # Initialize queue timeout (s)
        self.timeout = int(timeout)
        self.cb.touch(self.q_ID, ttl=self.timeout)

    @log.log_this()
    def push(self, message='', remove_old_id=False):
        '''Set the "clean_old_ids" keyword to True if other interpreter
        sessions are liable to remove queue items entered by the current
        session. Old thread identifiers will be removed from the "local"
        last_id.
        '''
        id_int = self.cb.counter(self.c_ID).value
        new_item = {'id':id_int, 'message':message}
        try:
            self.cb.queue_push(self.q_ID, new_item, ttl=self.timeout)
        except NotFoundError:
            # Recreate the queue if it does not exist
            self.cb.queue_push(self.q_ID, new_item, create=True, ttl=self.timeout)
        # Clean up old thread identifiers
        if remove_old_id:
            queue = self.get_queue()
            current_id_ints = [item['id'] for item in queue]
            id_keys = [key for (key, value) in self.last_id.items() if not(value in current_id_ints)]
            for key in id_keys:
                self.last_id.pop(key)
        # Return the new item's id
        self.last_id[threading.get_ident()] = id_int
        return id_int
    
    @log.log_this()
    def position(self, id_int=None):
        if id_int is None:
            if threading.get_ident() in self.last_id:
                id_int = self.last_id[threading.get_ident()]
            else:
                id_int = -1
        try:
            result = self.cb.get(self.q_ID)
            queue = result.value
            if len(queue) > 0:
                try:
                    # The last item in the list is the top of the queue
                    index = [item['id'] for item in queue[::-1]].index(id_int)
                except ValueError:
                    index = -1
            else:
                index = -1
        except NotFoundError:
            index = -1
        # Return index
        return index
    
    @log.log_this()
    def remove(self, id_int=None):
        if id_int is None:
            if threading.get_ident() in self.last_id:
                id_int = self.last_id[threading.get_ident()]
            else:
                id_int = -1
        try:
            loop_for_cas = True
            while loop_for_cas:
                try:
                    # Get current queue
                    result = self.cb.get(self.q_ID)
                    cas = result.cas
                    queue = result.value
                    # Get current index
                    try:
                        index = [item['id'] for item in queue].index(id_int)
                    except ValueError:
                        index = -1
                    # Remove from queue
                    if index >= 0:
                        queue.pop(index)
                        self.cb.upsert(self.q_ID, queue, cas=cas, ttl=self.timeout)
                except KeyExistsError:
                    pass
                else:
                    loop_for_cas = False
        except NotFoundError:
            pass
        # Clear last_ids
        id_keys = [key for (key,value) in self.last_id.items() if (value==id_int)]
        for key in id_keys:
            self.last_id.pop(key)
    
    @log.log_this()
    def pop(self):
        try:
            item = self.cb.queue_pop(self.q_ID, ttl=self.timeout).value
        except QueueEmpty:
            item = {}
        except NotFoundError:
            item = {}
        # Clear last_ids
        if 'id' in item:
            id_keys = [key for (key,value) in self.last_id.items() if (value==item['id'])]
            for key in id_keys:
                self.last_id.pop(key)
        # Return the item
        return item
    
    @log.log_this()
    def get_queue(self):
        try:
            result = self.cb.get(self.q_ID)
            queue = result.value
        except NotFoundError:
            queue = []
        return queue[::-1]
    
    @log.log_this()
    def touch(self):
        try:
            self.cb.touch(self.q_ID, ttl=self.timeout)
        except NotFoundError:
            pass
    
    @log.log_this()
    def queue_and_wait(self, message=''):
        queued = True
        wait_for_queue = True
        while wait_for_queue:
            queue_position = self.position()
            if (queue_position == 0):
            # Item is at the top of the queue
                wait_for_queue = False
            elif (queue_position < 0):
            # Enter item into queue
                queued = False
                self.push(message=message)
            else:
            # Wait for queue
                pass
        return queued


