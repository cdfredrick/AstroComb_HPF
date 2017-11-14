# -*- coding: utf-8 -*-
"""
Created on Sun Nov 12 12:00:00 2017

@author: Connor
"""

import pymongo
import datetime

class MongoClient:
    def __init__(self):
        '''
        Connects to a mongoDB client, which can then be used to access different
            databases and collections.
        The "keys" list the hardcoded names of the collections and of the keys
            needed to access records in the documents.
        '''
        # Connect to the mongoDB client
        self.client = pymongo.MongoClient()
        self.COLLECTION_KEYS = ['record', 'buffer', 'log']
        self.DOCUMENT_KEYS = ['entry', 'timestamp', 'log_level']
    
    def close(self):
        '''
        Closes the connection to the mongoDB. Any subsequent calls to the client
            will restart the connection.
        '''
        self.client.close()

class DatabaseMaster:
    def __init__(self, mongo_client, database, capped_collection_size=int(1e6)):
        '''
        The "master" handler for the database. This class enforces the database
            settings as given in the kwargs and ensures that the record and log
            have the correct indexes.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database
        
        **kwargs
        capped_collection_size: int, the size of the capped collection (buffer)
            in bytes.
        '''
    # Get the MongoDB client
        self.client = mongo_client
    # Get the requested database
        self.database = self.client[database]
    # Get the record
        self.record = self.database['record']
        # Create a descending index for documents with timestamps in the record
        self.record.create_index(('timestamp', pymongo.DESCENDING))
    # Get the buffer
        self.buffer = self.database['buffer']
        # Check that the buffer is as specified in the initialization options
        buffer_options = self.buffer.options()
        if not bool(buffer_options):
            # Create the collection if it does not already exist
            self.database.create_collection('buffer', capped=True, size=capped_collection_size)
        if (not buffer_options['capped']) or (buffer_options['size'] != capped_collection_size):
            # Convert the collection if it is not capped or if it is the wrong size
            self.database.command({'convertToCapped':'buffer', 'size':capped_collection_size})
    # Get the log
        self.log = self.database['log']
        # Create a descending index with timestamps for documents in the log
        self.log.create_index(('timestamp', pymongo.DESCENDING))
        # Create an ascending index with level for documents in the log
        self.log.create_index(('log_level', pymongo.ASCENDING))

    def read_buffer(self, number_of_documents=0, sort_ascending=True, tailable_cursor=True):
        '''
        Returns an iterable cursor object containing documents from the buffer.
        A tailable cursor remains open after the client exhausts the results in
            the initial cursor. Subsequent calls to the cursor only returns new 
            documents. A non-tailable cursor will automatically be closed after
            all results are exhausted. Regardless, all cursors time out in the 
            database (will be closed) after 10 minutes of inactivity.
        With the natural ordering of capped collections, ascending order gives 
            the oldest documents first, while descending gives the newest documents
            first.
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        tailable_cursor: bool, selects whether or not to return a tailable cursor
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('$natural', pymongo.ASCENDING)
        else:
            sort_order = ('$natural', pymongo.DESCENDING)
    # Tailable cursor
        if tailable_cursor:
            cursor = pymongo.cursor.CursorType.TAILABLE
        else:
            cursor = pymongo.cursor.CursorType.NON_TAILABLE
    # Cursor
        return self.buffer.find(limit=number_of_documents, cursor_type=cursor, sort=sort_order)

    def read_log(self, start, stop, log_level=10, sort_ascending=True, ):
        '''
        Returns an iterable cursor object containing documents from the log.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        log_level: int, selects the minimum log level returned.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('timestamp', pymongo.ASCENDING)
        else:
            sort_order = ('timestamp', pymongo.DESCENDING)
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}, 'log_level':{'$gte':log_level}}
        return self.log.find(ranged_filter, sort=sort_order)

    def read_record(self, start, stop, sort_ascending=True):
        '''
        Returns an iterable cursor object containing documents from the record.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('timestamp', pymongo.ASCENDING)
        else:
            sort_order = ('timestamp', pymongo.DESCENDING)
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}}
        return self.record.find(ranged_filter, sort=sort_order)

    def write_document_to_record(self, document):
        '''
        Writes a document into the record. This intended to be used to write documents
            from the buffer into the record
        
        *args
        document: a document in the format as given by any of the "read" functions.
        '''
        self.record.insert_one(document)

    def write_entry_to_buffer(self, entry):
        '''
        Writes an entry into the buffer. An entry into the buffer can be of any
            type, but all entries should be of the same type and should represent
            the same database object.
        
        *args
        entry: a thing to write to the buffer.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow()}
        self.buffer.insert_one(document)

    def write_entry_to_log(self, entry, log_level):
        '''
        Writes an entry into the log. An entry into the log can be of any type,
            but is ideally a text based description of the current state of, or
            an action taken within, the system as it relates to this database.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        entry: a thing to write to the log.
        log_level: int, the log level of the entry.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow(), 'log_level':log_level}
        self.log.insert_one(document)

    def write_entry_to_record(self, entry):
        '''
        Writes an entry into the record. This bypasses the buffer and directly 
            writes an entry into the record. The entry should have the same format
            as those written to the buffer.
        
        *args
        document: a thing to write to the record.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow()}
        self.record.insert_one(document)

class DatabaseReadWrite:
    def __init__(self, mongo_client, database):
        '''
        The "read and write" handler for the database. This class is used to form
            a read and write connection to a database, without needing to specify
            the database specific settings.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database

        '''
    # Get the MongoDB client
        self.client = mongo_client
    # Get the requested database
        self.database = self.client[database]
    # Get the record
        self.record = self.database['record']
    # Get the buffer
        self.buffer = self.database['buffer']
    # Get the log
        self.log = self.database['log']

    def read_buffer(self, number_of_documents=0, sort_ascending=True, tailable_cursor=True):
        '''
        Returns an iterable cursor object containing documents from the buffer.
        A tailable cursor remains open after the client exhausts the results in
            the initial cursor. Subsequent calls to the cursor only returns new 
            documents. A non-tailable cursor will automatically be closed after
            all results are exhausted. Regardless, all cursors time out in the 
            database (will be closed) after 10 minutes of inactivity.
        With the natural ordering of capped collections, ascending order gives 
            the oldest documents first, while descending gives the newest documents
            first.
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        tailable_cursor: bool, selects whether or not to return a tailable cursor
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('$natural', pymongo.ASCENDING)
        else:
            sort_order = ('$natural', pymongo.DESCENDING)
    # Tailable cursor
        if tailable_cursor:
            cursor = pymongo.cursor.CursorType.TAILABLE
        else:
            cursor = pymongo.cursor.CursorType.NON_TAILABLE
    # Cursor
        return self.buffer.find(limit=number_of_documents, cursor_type=cursor, sort=sort_order)

    def read_log(self, start, stop, log_level=10, sort_ascending=True, ):
        '''
        Returns an iterable cursor object containing documents from the log.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        log_level: int, selects the minimum log level returned.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('timestamp', pymongo.ASCENDING)
        else:
            sort_order = ('timestamp', pymongo.DESCENDING)
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}, 'log_level':{'$gte':log_level}}
        return self.log.find(ranged_filter, sort=sort_order)

    def read_record(self, start, stop, sort_ascending=True):
        '''
        Returns an iterable cursor object containing documents from the record.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('timestamp', pymongo.ASCENDING)
        else:
            sort_order = ('timestamp', pymongo.DESCENDING)
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}}
        return self.record.find(ranged_filter, sort=sort_order)

    def write_document_to_record(self, document):
        '''
        Writes a document into the record. This intended to be used to write documents
            from the buffer into the record
        
        *args
        document: a document in the format as given by any of the "read" functions.
        '''
        self.record.insert_one(document)

    def write_entry_to_buffer(self, entry):
        '''
        Writes an entry into the buffer. An entry into the buffer can be of any
            type, but all entries should be of the same type and should represent
            the same database object.
        
        *args
        entry: a thing to write to the buffer.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow()}
        self.buffer.insert_one(document)

    def write_entry_to_log(self, entry, log_level):
        '''
        Writes an entry into the log. An entry into the log can be of any type,
            but is ideally a text based description of the current state of, or
            an action taken within, the system as it relates to this database.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        entry: a thing to write to the log.
        log_level: int, the log level of the entry.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow(), 'log_level':log_level}
        self.log.insert_one(document)

    def write_entry_to_record(self, entry):
        '''
        Writes an entry into the record. This bypasses the buffer and directly 
            writes an entry into the record. The entry should have the same format
            as those written to the buffer.
        
        *args
        document: a thing to write to the record.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow()}
        self.record.insert_one(document)

class DatabaseRead:
    def __init__(self, mongo_client, database):
        '''
        The "read only" handler for the database. This class is used to form
            a read only connection to a database, without needing to specify
            the database specific settings. The methods in this class can not 
            change values in the database.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database

        '''
    # Get the MongoDB client
        self.client = mongo_client
    # Get the requested database
        self.database = self.client[database]
    # Get the record
        self.record = self.database['record']
    # Get the buffer
        self.buffer = self.database['buffer']
    # Get the log
        self.log = self.database['log']

    def read_buffer(self, number_of_documents=0, sort_ascending=True, tailable_cursor=True):
        '''
        Returns an iterable cursor object containing documents from the buffer.
        A tailable cursor remains open after the client exhausts the results in
            the initial cursor. Subsequent calls to the cursor only returns new 
            documents. A non-tailable cursor will automatically be closed after
            all results are exhausted. Regardless, all cursors time out in the 
            database (will be closed) after 10 minutes of inactivity.
        With the natural ordering of capped collections, ascending order gives 
            the oldest documents first, while descending gives the newest documents
            first.
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        tailable_cursor: bool, selects whether or not to return a tailable cursor
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('$natural', pymongo.ASCENDING)
        else:
            sort_order = ('$natural', pymongo.DESCENDING)
    # Tailable cursor
        if tailable_cursor:
            cursor = pymongo.cursor.CursorType.TAILABLE
        else:
            cursor = pymongo.cursor.CursorType.NON_TAILABLE
    # Cursor
        return self.buffer.find(limit=number_of_documents, cursor_type=cursor, sort=sort_order)

    def read_log(self, start, stop, log_level=10, sort_ascending=True, ):
        '''
        Returns an iterable cursor object containing documents from the log.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        log_level: int, selects the minimum log level returned.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('timestamp', pymongo.ASCENDING)
        else:
            sort_order = ('timestamp', pymongo.DESCENDING)
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}, 'log_level':{'$gte':log_level}}
        return self.log.find(ranged_filter, sort=sort_order)

    def read_record(self, start, stop, sort_ascending=True):
        '''
        Returns an iterable cursor object containing documents from the record.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = ('timestamp', pymongo.ASCENDING)
        else:
            sort_order = ('timestamp', pymongo.DESCENDING)
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}}
        return self.record.find(ranged_filter, sort=sort_order)
