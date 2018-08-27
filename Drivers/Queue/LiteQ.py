# -*- coding: utf-8 -*-
"""
Created on Mon Mar  5 11:33:07 2018

@author: Connor
"""

# %% Modules
import sqlite3
import datetime

# %% Q
class Q():
    def __init__(self, database_file):
        self.connection = sqlite3.connect(database_file, detect_types=sqlite3.PARSE_DECLTYPES)
        # Create queue table --------------------------------------------------
        self.execute('''
                     CREATE TABLE IF NOT EXISTS queue
                     (id INTEGER PRIMARY KEY ASC,
                     position TIMESTAMP,
                     timeout TIMESTAMP,
                     ttl_s REAL,
                     priority INTEGER,
                     active INTEGER)
                     ''')
        # Create timeout update trigger. --------------------------------------
        '''
        Increments the timeout timestamp upon a deletion in order to begin the 
        time to live interval for the new entry at the top of the queue.
        '''
        self.execute('''
                     CREATE TRIGGER IF NOT EXISTS update_timeout
                     AFTER DELETE ON queue
                     BEGIN
                     UPDATE queue
                     SET timeout = strftime("%Y-%m-%d %H:%M:%f","now", "+"||ttl_s||" seconds");
                     END;
                     ''')
        # Initialize Variables ------------------------------------------------
        self.activated = False
        self.queue = []
        self.row_ID = -1
        self.position = -1
        
    def execute(self, sql, keywords=None, return_id = False):
        try:
            with self.connection:
                c = self.connection.cursor()
                if keywords is None:
                    c.execute(sql)
                else:
                    c.execute(sql, keywords)
                if return_id:
                    return c.lastrowid
        except Exception:
            raise
    
    def get_queue(self):
        self.queue = list(self.connection.execute('''
                                                  SELECT * FROM queue
                                                  ORDER BY active DESC, priority ASC, position ASC
                                                  '''))
    
    def add_to_queue(self, ttl=5.0, priority=1):
        self.row_ID = self.execute('''
                     INSERT INTO queue
                     (position,
                     timeout,
                     ttl_s,
                     priority,
                     active)
                     VALUES
                     (strftime("%Y-%m-%d %H:%M:%f","now"),
                     strftime("%Y-%m-%d %H:%M:%f","now", :ttl_str),
                     :ttl,
                     :priority,
                     0)
                     ''',
                     keywords={'ttl_str':'{:.3f} seconds'.format(ttl), 'ttl':ttl,'priority':priority},
                     return_id=True)
        self.activated = False
    
    def remove_old_from_queue(self):
        '''
        Deletes the oldest timed out entry. This should only be needed as a 
        slow garbage collector for timed out entries. In normal operation, 
        entries should complete and then be deleted before timeout occurs.
        '''
        self.execute('''
                     DELETE FROM queue
                     WHERE id = (
                     SELECT id FROM queue
                     WHERE timeout < strftime("%Y-%m-%d %H:%M:%f","now")
                     ORDER BY active DESC, priority ASC, position ASC
                     LIMIT 1)
                     ''')
        
    
    def activate(self):
        # Get current queue
        self.get_queue()
        # Delete the expired entry from the queue
        if self.queue[0][2] < datetime.datetime.utcnow():
            self.remove_old_from_queue()
            self.get_queue()
        # Check position in the queue
        try:
            self.position = list(zip(*self.queue))[0].index(self.row_ID)
        except (ValueError, IndexError):
            # Entry has timed out, or has not been added to the queue
            self.add_to_queue()
            return False
        # Activate if at the top of the queue
        if self.position == 0:
            self.execute('''
                         UPDATE queue
                         SET active = 1
                         WHERE id = :id
                         ''',
                         keywords={'id':self.row_ID})
            self.activated = True
            return True
        else:
            return False
    
    def remove_from_queue(self):
        self.execute('''
                     DELETE FROM queue
                     WHERE id = :id
                     ''',
                     keywords={'id':self.row_ID})

# %%
class Q2():
    def __init__(self, database_file):
        self.connection = sqlite3.connect(database_file, detect_types=sqlite3.PARSE_DECLTYPES)
        # Create queue table --------------------------------------------------
        self.execute('''
                     CREATE TABLE IF NOT EXISTS queue
                     (id INTEGER PRIMARY KEY ASC,
                     position TIMESTAMP,
                     ttl_s REAL,
                     priority INTEGER)
                     ''')
        # Initialize Variables ------------------------------------------------
        self.activated = False
        self.queue = []
        self.row_ID = -1
        self.position = -1
        
    def execute(self, sql, keywords=None, return_id = False):
        try:
            with self.connection:
                c = self.connection.cursor()
                if keywords is None:
                    c.execute(sql)
                else:
                    c.execute(sql, keywords)
                if return_id:
                    return c.lastrowid
        except Exception:
            raise
    
    def get_queue(self):
        self.queue = list(self.connection.execute('''
                                                  SELECT * FROM queue
                                                  ORDER BY priority ASC, position ASC
                                                  '''))
    
    def add_to_queue(self, ttl=5.0, priority=1):
        self.row_ID = self.execute('''
                     INSERT INTO queue
                     (position,
                     ttl_s,
                     priority)
                     VALUES
                     (strftime("%Y-%m-%d %H:%M:%f","now"),
                     :ttl,
                     :priority)
                     ''',
                     keywords={'ttl':ttl,'priority':priority},
                     return_id=True)
        self.activated = False
    
    def remove_old_from_queue(self):
        '''
        Deletes the oldest timed out entry. This should only be needed as a 
        slow garbage collector for timed out entries. In normal operation, 
        entries should complete and then be deleted before timeout occurs.
        '''
        self.execute('''
                     DELETE FROM queue
                     WHERE id = (
                     SELECT id FROM queue
                     WHERE position < strftime("%Y-%m-%d %H:%M:%f","now","-"||ttl_s||" seconds")
                     ORDER BY priority ASC, position ASC
                     LIMIT 1)
                     ''')
        
    
    def activate(self):
        # Get current queue
        self.get_queue()
        # Delete the expired entry from the queue
        if self.queue[0][1]+datetime.timedelta(0,self.queue[0][2]) < datetime.datetime.utcnow():
            self.remove_old_from_queue()
            self.get_queue()
        # Check position in the queue
        try:
            self.position = list(zip(*self.queue))[0].index(self.row_ID)
        except (ValueError, IndexError):
            # Entry has timed out, or has not been added to the queue
            self.add_to_queue()
            return False
        # Activate if at the top of the queue
        if self.position == 0:
            self.activated = True
            return True
        else:
            return False
    
    def requeue(self):
        self.execute('''
                     UPDATE queue
                     SET position = strftime("%Y-%m-%d %H:%M:%f","now")
                     WHERE id = :id
                     ''',
                     keywords={'id':self.row_ID})
        self.activated = 0
    
    def remove_from_queue(self):
        self.execute('''
                     DELETE FROM queue
                     WHERE id = :id
                     ''',
                     keywords={'id':self.row_ID})






