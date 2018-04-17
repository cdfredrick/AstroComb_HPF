# -*- coding: utf-8 -*-
"""
Created on Sun Nov 12 12:00:00 2017

@author: Connor
"""
# %% Modules ==================================================================

import pymongo
import datetime
import logging


# %% MongoClient ==============================================================

class MongoClient:
    def __init__(self, host='localhost', port=27017):
        '''
        Connects to a mongoDB client, which can then be used to access different
            databases and collections.
        The "keys" list the hardcoded names of the collections and of the keys
            needed to access records in the documents (documents are returned 
            as dictionaries). Items in the record and buffer only contain the
            '_id' and '_timestamp' key by default. The user specifies the other
            keys with the input dictionary. Logs contain all 4 hardcoded
            document keys.
        '''
        # Connect to the mongoDB client
        self.client = pymongo.MongoClient(host=host, port=port, maxPoolSize=None)
        self.COLLECTION_KEYS = ['record', 'buffer', 'log', 'log_buffer']
        self.DOCUMENT_KEYS = ['_id', 'entry', '_timestamp', 'log_level']
    
    def close(self):
        '''
        Closes the connection to the mongoDB. Any subsequent calls to the client
            will restart the connection.
        '''
        self.client.close()

# %% DatabaseRead =============================================================

class DatabaseRead():
    def __init__(self, mongo_client, database):
        '''
        The "read only" handler for the database. This subclass is used to form
            a read only connection to a database, without needing to specify
            the database specific settings. The methods in this subclass can not 
            change values in the database.
        In order to allow for a more hierarchical structure, names may be 
            separated by a single forward slash '/'. The preceding name will be
            the name of the database and the following name will be that of a 
            collection. The sub collection names ('record', 'buffer', 
            'log', 'log_buffer') will be appended to the collection name. Only 
            one level is supported, mongoDB does not support nested collections.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database. Use the '/' separator
            to include multiple collections in a single database file.
        '''
    # Initialize
        self.get_collections(mongo_client, database)

    def get_collections(self, mongo_client, database):
    # Get the MongoDB client
        self.client = mongo_client.client
        self.COLLECTION_KEYS = mongo_client.COLLECTION_KEYS
        self.DOCUMENT_KEYS = mongo_client.DOCUMENT_KEYS
    # Parse database name
        database = database.split('/')
        if len(database) is 2:
            collection = database[1]+'_'
            database = database[0]
        else:
            collection = ''
            database = database[0]
    # Get the requested database
        self.database_name = database
        self.collection_name = collection
        self.database = self.client[self.database_name]
    # Get the record
        self.record = self.database[self.collection_name+'record']
    # Get the buffer
        self.buffer = self.database[self.collection_name+'buffer']
    # Set constants
        self.COLLECTION_KEYS = [self.collection_name+key for key in self.COLLECTION_KEYS]
    
    def read_buffer(self, number_of_documents=1, sort_ascending=False, tailable_cursor=False, no_cursor_timeout=False):
        '''
        Returns an iterable cursor object containing documents from the buffer.
        A tailable cursor remains open after the client exhausts the results in
            the initial cursor. Subsequent calls to the cursor only returns new 
            documents. A non-tailable cursor will automatically be closed after
            all results are exhausted. Regardless, all cursors time out in the 
            database (will be closed) after 10 minutes of inactivity.
            -If tailable cursor is specified the documents will be returned in
            ascending sort order and there will be no document limit.
            -Set no_cursor_timeout to "True" to prevent the natural ~1s cursor
            timeout if no new objects are added to the DB.
        With the natural ordering of capped collections, ascending order gives 
            the oldest documents first, while descending gives the newest documents
            first.
        When only one document is requested this method autmatically returns 
            the dictionary as given by the "entry_dict" of the write methods.
            Otherwise an interable Cursor object is returned.
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order.
        tailable_cursor: bool, selects whether or not to return a tailable cursor
        no_cursor_timeout: bool, sets action of the cursor timeout
        '''
    # Tailable cursor
        if tailable_cursor:
            # A tailable cursor only works with ascending sort and unlimited document count
            cursor_type = pymongo.cursor.CursorType.TAILABLE
            sort_ascending=True
            number_of_documents=0
        else:
            cursor_type = pymongo.cursor.CursorType.NON_TAILABLE
    # Sort order
        if sort_ascending:
            sort_order = [('$natural', pymongo.ASCENDING)]
        else:
            sort_order = [('$natural', pymongo.DESCENDING)]
    # Cursor
        cursor = self.buffer.find(limit=number_of_documents, cursor_type=cursor_type, sort=sort_order, no_cursor_timeout=no_cursor_timeout)
        if number_of_documents == 1:
        # Return the object if one exists
            cursor = list(cursor)
            if len(cursor) == 1:
                cursor = cursor[0]
                cursor.pop('_id')
                cursor.pop('_timestamp')
                return cursor
            else:
                return
        else:
        # Return the cursor in full
            return cursor

    def read_record(self, start, stop, number_of_documents=0, sort_ascending=True):
        '''
        Returns an iterable cursor object containing documents from the record.
        The start and stop times are given as datetime.datetime objects. These
            can be formed directly with datetime.datetime.utcnow() or with
            datetime.datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0),
            and with differences between datetime.datetime objects and 
            datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)
            objects. All times should be given in UTC.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        When only one document is requested this method autmatically returns 
            the dictionary as given by the "entry_dict" of the write methods.
            Otherwise an interable Cursor object is returned.
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = [('_timestamp', pymongo.ASCENDING)]
        else:
            sort_order = [('_timestamp', pymongo.DESCENDING)]
    # Ranged filter
        ranged_filter = {'_timestamp':{'$gte':start, '$lte':stop}}
    # Cursor
        cursor = self.record.find(ranged_filter, limit=number_of_documents, sort=sort_order)
        if number_of_documents == 1:
        # Return the object if one exists
            cursor = list(cursor)
            if len(cursor) == 1:
                cursor = cursor[0]
                cursor.pop('_id')
                cursor.pop('_timestamp')
                return cursor
            else:
                return
        else:
        # Return the cursor in full
            return cursor


# %% LogRead =============================================================
class LogRead():
    def __init__(self, mongo_client, database):
        '''
        The "read only" handler for the database. This subclass is used to form
            a read only connection to a database, without needing to specify
            the database specific settings. The methods in this subclass can not 
            change values in the database.
        In order to allow for a more hierarchical structure, names may be 
            separated by a single forward slash '/'. The preceding name will be
            the name of the database and the following name will be that of a 
            collection. The sub collection names ('record', 'buffer', 
            'log', 'log_buffer') will be appended to the collection name. Only 
            one level is supported, mongoDB does not support nested collections.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database. Use the '/' separator
            to include multiple collections in a single database file.
        '''
    # Initialize
        self.get_collections(mongo_client, database)

    def get_collections(self, mongo_client, database):
    # Get the MongoDB client
        self.client = mongo_client.client
        self.COLLECTION_KEYS = mongo_client.COLLECTION_KEYS
        self.DOCUMENT_KEYS = mongo_client.DOCUMENT_KEYS
    # Parse database name
        database = database.split('/')
        if len(database) is 2:
            collection = database[1]+'_'
            database = database[0]
        else:
            collection = ''
            database = database[0]
    # Get the requested database
        self.database_name = database
        self.collection_name = collection
        self.database = self.client[self.database_name]
    # Get the log
        self.log = self.database[self.collection_name+'log']
    # Get the log buffer
        self.log_buffer = self.database[self.collection_name+'log_buffer']
    # Set constants
        self.COLLECTION_KEYS = [self.collection_name+key for key in self.COLLECTION_KEYS]

    def read_log(self, start, stop, number_of_documents=0, log_level=logging.INFO, sort_ascending=True):
        '''
        Returns an iterable cursor object containing documents from the log.
        The start and stop times are given as datetime.datetime objects. These
            can be formed directly with datetime.datetime.utcnow() or with
            datetime.datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0),
            and with differences between datetime.datetime objects and 
            datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)
            objects. All times should be given in UTC.
        With the timestamp ordering, ascending order gives the oldest documents
            first, while descending gives the newest documents first.
        The recommended log levels are as those in the logging package.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        When only one document is requested this method autmatically returns 
            the dictionary containing the entry, timestamp, and level.
            Otherwise an interable Cursor object is returned.
        
        *args
        start: a datetime.datetime instance marking the start of the query period.
        stop: a datetime.datetime instance marking the end of the query period.
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        log_level: int, selects the minimum log level returned.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = [('_timestamp', pymongo.ASCENDING)]
        else:
            sort_order = [('_timestamp', pymongo.DESCENDING)]
    # Ranged filter
        ranged_filter = {'_timestamp':{'$gte':start, '$lte':stop}, 'log_level':{'$gte':log_level}}
    # Cursor
        cursor = self.log.find(ranged_filter, limit=number_of_documents, sort=sort_order)
        if number_of_documents == 1:
        # Return the object if one exists
            cursor = list(cursor)
            if len(cursor) == 1:
                cursor = cursor[0]
                cursor.pop('_id')
                return cursor
            else:
                return
        else:
        # Return the cursor in full
            return cursor

    def read_log_buffer(self, number_of_documents=0, sort_ascending=True, log_level=logging.INFO, tailable_cursor=False, no_cursor_timeout=False):
        '''
        Returns an iterable cursor object containing documents from the log buffer.
        A tailable cursor remains open after the client exhausts the results in
            the initial cursor. Subsequent calls to the cursor only returns new 
            documents. A non-tailable cursor will automatically be closed after
            all results are exhausted. Regardless, all cursors time out in the 
            database (will be closed) after 10 minutes of inactivity.
            -If tailable cursor is specified the documents will be returned in
            ascending sort order and there will be no document limit.
        With the natural ordering of capped collections, ascending order gives 
            the oldest documents first, while descending gives the newest documents
            first.
        The recommended log levels are as those in the logging package.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        When only one document is requested this method autmatically returns 
            the dictionary containing the entry, timestamp, and level.
            Otherwise an interable Cursor object is returned.
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        log_level: int, selects the minimum log level returned.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        tailable_cursor: bool, selects whether or not to return a tailable cursor
        no_cursor_timeout: bool, sets action of the cursor timeout
        '''
    # Tailable cursor
        if tailable_cursor:
            # A tailable cursor only works with ascending sort and unlimited document count
            cursor_type = pymongo.cursor.CursorType.TAILABLE
            sort_ascending=True
            number_of_documents=0
        else:
            cursor_type = pymongo.cursor.CursorType.NON_TAILABLE
    # Sort order
        if sort_ascending:
            sort_order = [('$natural', pymongo.ASCENDING)]
        else:
            sort_order = [('$natural', pymongo.DESCENDING)]
    # log filter
        log_filter = {'log_level':{'$gte':log_level}}
    # Cursor
        cursor = self.log_buffer.find(log_filter, limit=number_of_documents, cursor_type=cursor_type, sort=sort_order, no_cursor_timeout=no_cursor_timeout)
        if number_of_documents == 1:
        # Return the object if one exists
            cursor = list(cursor)
            if len(cursor) == 1:
                cursor = cursor[0]
                cursor.pop('_id')
                return cursor
            else:
                return
        else:
        # Return the cursor in full
            return cursor


# %% DatabaseReadWrite ========================================================

class DatabaseReadWrite(DatabaseRead):
    def __init__(self, mongo_client, database):
        '''
        The "read and write" handler for the database. This subclass is used to
            form a read and write connection to a database, without needing to
            specify the database specific settings.
        In order to allow for a more hierarchical structure, names may be 
            separated by a single forward slash '/'. The preceding name will be
            the name of the database and the following name will be that of a 
            collection. The sub collection names ('record', 'buffer', 
            'log', 'log_buffer') will be appended to the collection name. Only 
            one level is supported, mongoDB does not support nested collections.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database. Use the '/' separator
            to include multiple collections in a single database file.
        '''
    # Initialize
        super(DatabaseReadWrite, self).__init__(mongo_client, database)

    def write_document_to_record(self, document):
        '''
        Writes a document into the record. This is intended to be used to write 
            documents from the buffer into the record. Since the database 
            requires object IDs to be unique, the old object ID is dropped and
            a new one is automatically created upon insertion.
        
        *args
        document: a document in the format as given by the read_buffer function.
        '''
        document.pop('_id')
        self.record.insert_one(document)

    def write_buffer(self, entry_dict, timestamp=None):
        '''
        Writes an entry into the buffer. An entry into the buffer can contain any
            type, but all entries should contain the same type and should represent
            the same database object. Entries must be dictionaries.
        
        *args
        entry_dict: a dictionary containing things to write to the buffer.
        '''
        if (timestamp == None) or (type(timestamp) != datetime.datetime):
            document = {'_timestamp':datetime.datetime.utcnow()}
        else:
            document = {'_timestamp':timestamp}
        document = dict(list(document.items()) + list(entry_dict.items()))
        self.buffer.insert_one(document)

    def write_record(self, entry_dict, timestamp=None):
        '''
        Writes an entry into the record. This bypasses the buffer and directly 
            writes an entry into the record. For compatibility considerations, 
            the entry should have the same format as those written to the buffer.
        
        *args
        entry_dict: a dictionary containing thing to write to the record.
        '''
        if (timestamp == None) or (type(timestamp) != datetime.datetime):
            document = {'_timestamp':datetime.datetime.utcnow()}
        else:
            document = {'_timestamp':timestamp}
        document = dict(list(document.items()) + list(entry_dict.items()))
        self.record.insert_one(document)
    
    def write_record_and_buffer(self, entry_dict, timestamp=None):
        '''
        Writes an entry into the record and into the buffer. For compatibility
        considerations, the entry should have the same format as those written
        to the buffer.
        
        *args
        entry_dict: a dictionary containing thing to write to the record.
        '''
        if (timestamp == None) or (type(timestamp) != datetime.datetime):
            document = {'_timestamp':datetime.datetime.utcnow()}
        else:
            document = {'_timestamp':timestamp}
        document = dict(list(document.items()) + list(entry_dict.items()))
        self.buffer.insert_one(document)
        self.record.insert_one(document)


# %% LogReadWrite ========================================================

class LogReadWrite(LogRead):
    def __init__(self, mongo_client, database):
        '''
        The "read and write" handler for the database. This subclass is used to
            form a read and write connection to a database, without needing to
            specify the database specific settings.
        In order to allow for a more hierarchical structure, names may be 
            separated by a single forward slash '/'. The preceding name will be
            the name of the database and the following name will be that of a 
            collection. The sub collection names ('record', 'buffer', 
            'log', 'log_buffer') will be appended to the collection name. Only 
            one level is supported, mongoDB does not support nested collections.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database. Use the '/' separator
            to include multiple collections in a single database file.
        '''
    # Initialize
        super(LogReadWrite, self).__init__(mongo_client, database)
   
    def write_document_to_log(self, document):
        '''
        Writes a document into the log. This is intended to be used to write
            documents from the log buffer into the record. Since the database 
            requires object IDs to be unique, the old object ID is dropped and
            a new one is automatically created upon insertion.
        
        *args
        document: a document in the format as given by the read_log function.
        '''
        document.pop('_id')
        self.log.insert_one(document)

    def write_log(self, entry, log_level, timestamp=None):
        '''
        Writes an entry into the log. An entry into the log can be of any type,
            but is ideally a text based description of the current state of, or
            an action taken within, the system as it relates to this database.
        The recommended log levels are as those in the logging package.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        entry: a thing to write to the log.
        log_level: int, the log level of the entry.
        '''
        if (timestamp == None) or (type(timestamp) != datetime.datetime):
            timestamp = datetime.datetime.utcnow()
        document = {'entry':entry, '_timestamp':timestamp, 'log_level':log_level}
        self.log.insert_one(document)
    
    def write_log_buffer(self, entry, log_level, timestamp=None):
        '''
        Writes an entry into the log buffer. An entry into the log can be of
            any type, but is ideally a text based description of the current 
            state of, or an action taken within, the system as it relates to
            this database.
        The recommended log levels are as those in the logging package.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        entry: a thing to write to the log.
        log_level: int, the log level of the entry.
        '''
        if (timestamp == None) or (type(timestamp) != datetime.datetime):
            timestamp = datetime.datetime.utcnow()
        document = {'entry':entry, '_timestamp':timestamp, 'log_level':log_level}
        self.log_buffer.insert_one(document)
    
    def write_log_and_log_buffer(self, entry, log_level, timestamp=None):
        '''
        Writes an entry into the log and log buffer. An entry into the log can
            be of any type, but is ideally a text based description of the 
            current state of, or an action taken within, the system as it 
            relates to this database.
        The recommended log levels are as those in the logging package.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        *args
        entry: a thing to write to the log.
        log_level: int, the log level of the entry.
        '''
        if (timestamp == None) or (type(timestamp) != datetime.datetime):
            timestamp = datetime.datetime.utcnow()
        document = {'entry':entry, '_timestamp':timestamp, 'log_level':log_level}
        self.log.insert_one(document)
        self.log_buffer.insert_one(document)


# %% DatabaseMaster ===========================================================

class DatabaseMaster(DatabaseReadWrite):
    def __init__(self, mongo_client, database, capped_collection_size=int(1e6)):
        '''
        The "master" handler for the database. This class enforces the database
            settings as given in the kwargs and ensures that the record and log
            have the correct indexes.
        In order to allow for a more hierarchical structure, names may be 
            separated by a single forward slash '/'. The preceding name will be
            the name of the database and the following name will be that of a 
            collection. The sub collection names ('record', 'buffer', 
            'log', 'log_buffer') will be appended to the collection name. Only 
            one level is supported, mongoDB does not support nested collections.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database. Use the '/' separator
            to include multiple collections in a single database file.
        
        **kwargs
        capped_collection_size: int, the size of the capped collection (buffer)
            in bytes.
        '''
        super(DatabaseMaster, self).__init__(mongo_client, database)
        self.ensure_compliance(capped_collection_size)

    def ensure_compliance(self, capped_collection_size):
    # The record
        # Create a descending index for documents with timestamps in the record
        self.record.create_index([('_timestamp', pymongo.DESCENDING)])
    # The record buffer
        # Check that the buffer is as specified in the initialization options
        buffer_options = self.buffer.options()
        if not bool(buffer_options):
            # Create the collection if it does not already exist
            self.database.create_collection(self.COLLECTION_KEYS[1], capped=True, size=capped_collection_size)
        elif (not buffer_options['capped']) or (buffer_options['size'] != capped_collection_size):
            # Convert the collection if it is not capped or if it is the wrong size
            self.database.command({'convertToCapped':self.COLLECTION_KEYS[1], 'size':capped_collection_size})


# %% LogMaster ===========================================================

class LogMaster(LogReadWrite):
    def __init__(self, mongo_client, database, capped_collection_size=int(1e6)):
        '''
        The "master" handler for the database. This class enforces the database
            settings as given in the kwargs and ensures that the record and log
            have the correct indexes.
        In order to allow for a more hierarchical structure, names may be 
            separated by a single forward slash '/'. The preceding name will be
            the name of the database and the following name will be that of a 
            collection. The sub collection names ('record', 'buffer', 
            'log', 'log_buffer') will be appended to the collection name. Only 
            one level is supported, mongoDB does not support nested collections.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database. Use the '/' separator
            to include multiple collections in a single database file.
        
        **kwargs
        capped_collection_size: int, the size of the capped collection (buffer)
            in bytes.
        '''
        super(LogMaster, self).__init__(mongo_client, database)
        self.ensure_compliance(capped_collection_size)

    def ensure_compliance(self, capped_collection_size):
    # The log
        # Create a descending index with timestamps for documents in the log
        self.log.create_index([('_timestamp', pymongo.DESCENDING)])
        # Create an ascending index with level for documents in the log
        self.log.create_index([('log_level', pymongo.ASCENDING)])
    # The log buffer
        # Check that the log buffer is as specified in the initialization options
        buffer_options = self.log_buffer.options()
        if not bool(buffer_options):
            # Create the collection if it does not already exist
            self.database.create_collection(self.COLLECTION_KEYS[3], capped=True, size=capped_collection_size)
        elif (not buffer_options['capped']) or (buffer_options['size'] != capped_collection_size):
            # Convert the collection if it is not capped or if it is the wrong size
            self.database.command({'convertToCapped':self.COLLECTION_KEYS[3], 'size':capped_collection_size})


# %% Logging Handler ==========================================================

class MongoLogBufferHandler(logging.Handler):
    """
    A handler class which writes logging records, appropriately formatted,
        to the a specified database's log buffer. This is used to simplify the 
        log generation process with the use of the python "logging" package.
    """
    def __init__(self, database):
        """
        A LogMaster or LogReadWrite object must be specified.
        The resulting handler object will have a 'database_name' attribute that
            can be used to identify the handler's destination.
        """
        logging.Handler.__init__(self)
        if (not(isinstance(database,LogMaster)) and not(isinstance(database,LogReadWrite))):
            raise TypeError('A LogMaster or LogReadWrite object must be specified. A {:} was specified instead'.format(type(database)))
        self.database_name = database.database_name
        self.write_log_buffer = database.write_log_buffer
        
    def emit(self, record):
        """
        If a formatter is specified, it is used to format the record. The record
            is then written to the log.
        """
        try:
            msg = self.format(record)
            log_level = record.levelno
            self.write_log_buffer(msg, log_level)
        except Exception:
            self.handleError(record)

class MongoLogHandler(logging.Handler):
    """
    A handler class which writes logging records, appropriately formatted,
        to the a specified database's permanent log. This is used to simplify
        the log generation process with the use of the python "logging" package.
    """
    def __init__(self, database):
        """
        A LogMaster or LogReadWrite object must be specified.
        The resulting handler object will have a 'database_name' attribute that
            can be used to identify the handler's destination.
        """
        logging.Handler.__init__(self)
        if (not(isinstance(database,LogMaster)) and not(isinstance(database,LogReadWrite))):
            raise TypeError('A LogMaster or LogReadWrite object must be specified. A {:} was specified instead'.format(type(database)))
        self.database_name = database.database_name
        self.write_log = database.write_log
        
    def emit(self, record):
        """
        If a formatter is specified, it is used to format the record. The record
            is then written to the log.
        """
        try:
            msg = self.format(record)
            log_level = record.levelno
            self.write_log(msg, log_level)
        except Exception:
            self.handleError(record)

def MongoLogger(database, name=None, logger_level=logging.DEBUG, log_buffer_handler_level=logging.DEBUG, log_handler_level=logging.WARNING, format_str=None, remove_all_handlers=True):
    '''
    Returns a logger instance whose handler writes to the given database's log
        buffer. This is a helper function used to simplify logger setup.
    The name specifies the logger's place in the logging hierarchy. Every
        logger called by the same name is the same logger instance, so only one
        call to this function is needed per database and Python interpreter 
        process. Other pointers to this logger instance can be created by calling 
        logging.getLogger(name). Child loggers, which inherit the properties and
        handlers from their parents can be automatically created by calling the
        getLogger method with the name specified in the dot separated format, 
        i.e. "name.child.grandchild".
    The logger_level and handler_level respectively specify the minimum log 
        level sent to the handler from the logger and from the handler to the 
        database.
    See the logging documentation for details on the format string.
    
    *args
    database: a DatabaseMaster or DatabaseReadWrite object
    
    *kwargs
    name: str, the name of the logger instance. 
    logger_level: int, minimum logging level that the logger will pass to the
        handler
    handler_level: int, minimum logging level that the handler will log
    format_str: str, used to specify custom message formating
    remove_all_handlers: bool, remove all handlers before adding the new ones
    '''
# Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logger_level)
# Create the mongoDB log buffer handler and set level
    mongo_log_buffer_handler = MongoLogBufferHandler(database)
    mongo_log_buffer_handler.setLevel(log_buffer_handler_level)
# Create the mongoDB log handler and set level
    mongo_log_handler = MongoLogHandler(database)
    mongo_log_handler.setLevel(log_handler_level)
# Create formatter
    if format_str is not None:
        formatter = logging.Formatter(format_str)
    # Add formatter to chs
        mongo_log_buffer_handler.setFormatter(formatter)
        mongo_log_handler.setFormatter(formatter)
# Remove redundant or old handlers
    old_handlers = logger.handlers
    for handler in old_handlers:
        if remove_all_handlers:
            logger.removeHandler(handler)
        else:
            try:
                if handler.database_name == database.database_name:
                    logger.removeHandler(handler)
            except:
                pass
# Add handlers to logger
    logger.addHandler(mongo_log_buffer_handler)
    logger.addHandler(mongo_log_handler)
# Return logger object
    return logger

# %% Testing and Examples =====================================================

if __name__ == '__main__':
    mongo_client = MongoClient()
# Testing
    print('\n Testing Database connection ===================================')
    test_database = DatabaseMaster(mongo_client, 'test_database')
    #test_database = DatabaseReadWrite(mongo_client, 'test_database')
    #test_database = DatabaseRead(mongo_client, 'test_database')
    # Read and write to buffer
    print('\n Read and write to the buffer ----------------------------------')
    for x in range(int(2e4)):
        test_database.write_buffer({'entry':x**2.})
        # Read buffer (default)
    print('\n Read buffer: sort ascending')
    for doc in test_database.read_buffer(number_of_documents=0, sort_ascending=True):
        pass
    print(doc)
        # Read buffer (sort descending)
    print('\n Read buffer: sort descending')
    for doc in test_database.read_buffer(number_of_documents=0):
        pass
    print(doc)
        # Read buffer (document limit)
    print('\n Read buffer: document limit, sort ascending')
    for doc in test_database.read_buffer(number_of_documents=3, sort_ascending=True):
        print(doc)
        # Read buffer (document limit, sort descening)
    print('\n Read buffer: document limit, sort descending')
    for doc in test_database.read_buffer(number_of_documents=3):
        print(doc)
        # Read buffer (tailable cursor)
    print('\n Read buffer: tailable cursor, sort ascending')
    cursor = test_database.read_buffer(tailable_cursor=True, sort_ascending=True)
    for doc in cursor:
        pass
    print(doc)
    print('\t new documents')
    for x in range(10):
        test_database.write_buffer({'entry':x**2.})
    for doc in cursor:
        print(doc)
        # Read buffer (tailable cursor, sort descending)
    print('\n Read buffer: tailable cursor, sort descending')
    cursor = test_database.read_buffer(number_of_documents=0, tailable_cursor=True)
    for doc in cursor:
        pass
    print(doc)
    print('\t new documents')
    for x in range(10):
        test_database.write_buffer({'entry':x**2.})
    for doc in cursor:
        print(doc)
    print('\t tailable cursor only works with ascending sort')
        # Read buffer (tailable cursor, document limit)
    print('\n Read buffer: tailable cursor, sort descending')
    cursor = test_database.read_buffer(number_of_documents=3, sort_ascending=False, tailable_cursor=True)
    for doc in cursor:
        pass
    print(doc)
    print('\t new documents')
    for x in range(10):
        test_database.write_buffer({'entry':x**2.})
    for doc in cursor:
        print(doc)
    print('\t tailable cursor only works with no document limits')
    
    # Read and write to the record
    print('\n Read and write to the record ----------------------------------')
    for x in range(int(2e1)):
        test_database.write_record({'entry':x**2.})
        # Read record (default)
    print('\n Read record: sort ascending')
    stop = datetime.datetime.utcnow()
    start = stop - datetime.timedelta(days=1)
    for doc in test_database.read_record(start, stop):
        pass
    print(doc)
        # Read record (document limit)
    print('\n Read record: sort ascending, document limit')
    stop = datetime.datetime.utcnow()
    start = stop - datetime.timedelta(days=1)
    for doc in test_database.read_record(start, stop, number_of_documents=3):
        print(doc)
        # Read record (sort descending)
    print('\n Read buffer: sort descending')
    for doc in test_database.read_record(start, stop, sort_ascending=False):
        pass
    print(doc)
        # Read record (sort descending, document limit)
    print('\n Read buffer: sort descending, document limit')
    for doc in test_database.read_record(start, stop, sort_ascending=False, number_of_documents=3):
        print(doc)
        # Write documents from the buffer
    print('\n Write documents from buffer')
    for x in range(5):
        test_database.write_buffer({'entry':x**2.})
    for doc in test_database.read_buffer(number_of_documents=5, sort_ascending=False):
        test_database.write_document_to_record(doc)
    for doc in test_database.read_record(start, datetime.datetime.utcnow(), number_of_documents=5, sort_ascending=False):
        print(doc)
#  Log Testing and Examples ---------------------------------------------------
    print('\n Testing Log connection ========================================')
    test_database = LogMaster(mongo_client, 'test_database')
    #test_database = DatabaseReadWrite(mongo_client, 'test_database')
    #test_database = DatabaseRead(mongo_client, 'test_database')
    # Read and write to buffer
    # Read and write to the log buffer
    print('\n Read and write to the log buffer ------------------------------')
    for x in range(int(2e1)):
        test_database.write_log_buffer(str(x**2.), x)
        # Read log (default)
    print('\n Read log buffer: sort ascending')
    for doc in test_database.read_log_buffer():
        pass
    print(doc)
        # Read log (sort descending)
    print('\n Read log buffer: sort descending')
    for doc in test_database.read_log_buffer(sort_ascending=False):
        pass
    print(doc)
        # Read log (log_level)
    print('\n Read log buffer: sort ascending, log_level')
    for doc in test_database.read_log_buffer(log_level=15):
        pass
    print(doc)
        # Read log (log_level, document limit)
    print('\n Read log buffer: sort ascending, log_level, document limit')
    for doc in test_database.read_log_buffer(log_level=15, number_of_documents=3):
        print(doc)
        # Write with logger
    print('\n \t Write with logger')
            # create logger
    logger = MongoLogger(test_database)
    #from Drivers.Logging.EventLog import start_logging
    #logger = start_logging(test_database)
    #logger = start_logging()
            # 'application' code
    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warn message')
    logger.error('error message')
    logger.critical('critical message')
    for doc in test_database.read_log_buffer(number_of_documents=5, sort_ascending=False, log_level=logging.DEBUG):
        print(doc)
    logging.shutdown()
    
    # Read and write to the log
    print('\n Read and write to the log ------------------------------')
    for x in range(int(2e1)):
        test_database.write_log(str(x**2.), x)
        # Read log (default)
    print('\n Read log: sort ascending')
    stop = datetime.datetime.utcnow()
    start = stop - datetime.timedelta(days=1)
    for doc in test_database.read_log(start, stop):
        pass
    print(doc)
        # Read log (sort descending)
    print('\n Read log: sort descending')
    for doc in test_database.read_log(start, stop, sort_ascending=False):
        pass
    print(doc)
        # Read log (log_level)
    print('\n Read log: sort ascending, log_level')
    for doc in test_database.read_log(start, stop, log_level=15):
        pass
    print(doc)
        # Read log (log_level, document limit)
    print('\n Read log: sort ascending, log_level, document limit')
    for doc in test_database.read_log(start, stop, log_level=15, number_of_documents=3):
        print(doc)
# Close the connection to the database
    mongo_client.close()
