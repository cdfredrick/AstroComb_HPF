# -*- coding: utf-8 -*-
"""
Created on Sun Nov 12 12:00:00 2017

@author: Connor
"""
# %% Packages
import pymongo
import datetime
import logging

# %% MongoClient
class MongoClient:
    def __init__(self):
        '''
        Connects to a mongoDB client, which can then be used to access different
            databases and collections.
        The "keys" list the hardcoded names of the collections and of the keys
            needed to access records in the documents (documents are returned 
            as dictionaries).
        '''
        # Connect to the mongoDB client
        self.client = pymongo.MongoClient()
        self.COLLECTION_KEYS = ['record', 'buffer', 'log', 'log_buffer']
        self.DOCUMENT_KEYS = ['entry', 'timestamp', 'log_level']
    
    def close(self):
        '''
        Closes the connection to the mongoDB. Any subsequent calls to the client
            will restart the connection.
        '''
        self.client.close()

# %% DatabaseMaster
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
        self.get_databases(mongo_client, database)
        self.ensure_compliance(capped_collection_size)

    def ensure_compliance(self, capped_collection_size):
    # The record
        # Create a descending index for documents with timestamps in the record
        self.record.create_index([('timestamp', pymongo.DESCENDING)])
    # The buffer
        # Check that the buffer is as specified in the initialization options
        buffer_options = self.buffer.options()
        if not bool(buffer_options):
            # Create the collection if it does not already exist
            self.database.create_collection('buffer', capped=True, size=capped_collection_size)
        elif (not buffer_options['capped']) or (buffer_options['size'] != capped_collection_size):
            # Convert the collection if it is not capped or if it is the wrong size
            self.database.command({'convertToCapped':'buffer', 'size':capped_collection_size})
    # The log
        # Create a descending index with timestamps for documents in the log
        self.log.create_index([('timestamp', pymongo.DESCENDING)])
        # Create an ascending index with level for documents in the log
        self.log.create_index([('log_level', pymongo.ASCENDING)])
    # The log buffer
        # Check that the log buffer is as specified in the initialization options
        buffer_options = self.log_buffer.options()
        if not bool(buffer_options):
            # Create the collection if it does not already exist
            self.database.create_collection('log_buffer', capped=True, size=capped_collection_size)
        elif (not buffer_options['capped']) or (buffer_options['size'] != capped_collection_size):
            # Convert the collection if it is not capped or if it is the wrong size
            self.database.command({'convertToCapped':'log_buffer', 'size':capped_collection_size})

    def get_databases(self, mongo_client, database):
    # Get the MongoDB client
        self.client = mongo_client.client
    # Get the requested database
        self.database_name = database
        self.database = self.client[self.database_name]
    # Get the record
        self.record = self.database['record']
    # Get the buffer
        self.buffer = self.database['buffer']
    # Get the log
        self.log = self.database['log']
    # Get the log buffer
        self.log_buffer = self.database['log_buffer']

    def read_buffer(self, number_of_documents=0, sort_ascending=True, tailable_cursor=False):
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
            sort_order = [('$natural', pymongo.ASCENDING)]
        else:
            sort_order = [('$natural', pymongo.DESCENDING)]
    # Tailable cursor
        if tailable_cursor:
            cursor = pymongo.cursor.CursorType.TAILABLE
        else:
            cursor = pymongo.cursor.CursorType.NON_TAILABLE
    # Cursor
        return self.buffer.find(limit=number_of_documents, cursor_type=cursor, sort=sort_order)

    def read_log(self, start, stop, number_of_documents=0, log_level=logging.INFO, sort_ascending=True, ):
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
            sort_order = [('timestamp', pymongo.ASCENDING)]
        else:
            sort_order = [('timestamp', pymongo.DESCENDING)]
    # Ranged filter
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}, 'log_level':{'$gte':log_level}}
    # Cursor
        return self.log.find(ranged_filter, limit=number_of_documents, sort=sort_order)

    def read_log_buffer(self, number_of_documents=0, sort_ascending=True, log_level=logging.INFO, tailable_cursor=False):
        '''
        Returns an iterable cursor object containing documents from the log buffer.
        A tailable cursor remains open after the client exhausts the results in
            the initial cursor. Subsequent calls to the cursor only returns new 
            documents. A non-tailable cursor will automatically be closed after
            all results are exhausted. Regardless, all cursors time out in the 
            database (will be closed) after 10 minutes of inactivity.
        With the natural ordering of capped collections, ascending order gives 
            the oldest documents first, while descending gives the newest documents
            first.
        The recommended log levels are as those in the logging package.
        Levels  |   10  |  20  |   30    |   40  |    50    |
                | debug | info | warning | error | critical |
        
        **kwargs
        number_of_documents: int, maximum number of documents collected into the
            cursor. A maximum number of "0" is equivalent to an unlimited amount.
        tailable_cursor: bool, selects whether or not to return a tailable cursor
        log_level: int, selects the minimum log level returned.
        sort_ascending: bool, selects to sort the cursor either by ascending or
            descending order. 
        '''
    # Sort order
        if sort_ascending:
            sort_order = [('$natural', pymongo.ASCENDING)]
        else:
            sort_order = [('$natural', pymongo.DESCENDING)]
    # Tailable cursor
        if tailable_cursor:
            cursor = pymongo.cursor.CursorType.TAILABLE
        else:
            cursor = pymongo.cursor.CursorType.NON_TAILABLE
    # log filter
        log_filter = {'log_level':{'$gte':log_level}}
    # Cursor
        return self.log_buffer.find(log_filter, limit=number_of_documents, cursor_type=cursor, sort=sort_order)

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
            sort_order = [('timestamp', pymongo.ASCENDING)]
        else:
            sort_order = [('timestamp', pymongo.DESCENDING)]
    # Ranged filter
        ranged_filter = {'timestamp':{'$gte':start, '$lte':stop}}
    # Cursor
        return self.record.find(ranged_filter, limit=number_of_documents, sort=sort_order)

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

    def write_buffer(self, entry):
        '''
        Writes an entry into the buffer. An entry into the buffer can be of any
            type, but all entries should be of the same type and should represent
            the same database object.
        
        *args
        entry: a thing to write to the buffer.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow()}
        self.buffer.insert_one(document)

    def write_log(self, entry, log_level):
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
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow(), 'log_level':log_level}
        self.log.insert_one(document)
    
    def write_log_buffer(self, entry, log_level):
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
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow(), 'log_level':log_level}
        self.log_buffer.insert_one(document)

    def write_record(self, entry):
        '''
        Writes an entry into the record. This bypasses the buffer and directly 
            writes an entry into the record. The entry should have the same format
            as those written to the buffer.
        
        *args
        document: a thing to write to the record.
        '''
        document = {'entry':entry, 'timestamp':datetime.datetime.utcnow()}
        self.record.insert_one(document)

# %% DatabaseReadWrite
class DatabaseReadWrite(DatabaseMaster):
    def __init__(self, mongo_client, database):
        '''
        The "read and write" handler for the database. This subclass is used to
            form a read and write connection to a database, without needing to
            specify the database specific settings.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database
        '''
    # Initialize
        self.get_databases(mongo_client, database)
    # Disable methods from the master class
        self.ensure_compliance = None

# %% DatabaseRead
class DatabaseRead(DatabaseMaster):
    def __init__(self, mongo_client, database):
        '''
        The "read only" handler for the database. This subclass is used to form
            a read only connection to a database, without needing to specify
            the database specific settings. The methods in this subclass can not 
            change values in the database.
        
        *args
        mongo_client: a MongoClient object
        database: str, the name of the requested database
        '''
    # Initialize
        self.get_databases(mongo_client, database)
    # Disable methods from the master class
        self.ensure_compliance = None
        self.write_document_to_log = None
        self.write_document_to_record = None
        self.write_buffer = None
        self.write_log = None
        self.write_log_buffer = None
        self.write_record = None
    
 
# %% Logging Handler

class LoggingHandler(logging.Handler):
    """
    A handler class which writes logging records, appropriately formatted,
        to the a specified database's log buffer. This is used to simplify the 
        log generation process with the use of the python "logging" package.
    """
    def __init__(self, database):
        """
        A DatabaseMaster or DatabaseReadWrite object must be specified.
        The resulting handler object will have a 'database_name' attribute that
            can be used to identify the handler's destination.
        """
        logging.Handler.__init__(self)
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

def mongo_logger(database, name=None, logger_level=logging.DEBUG, handler_level=logging.DEBUG, format_str=None):
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
    name: str, the name of the logger instance
    logger_level: int, minimum logging level that the logger will pass to the
        handler
    handler_level: int, minimum logging level that the handler will log
    format_str: str, used to specify custom message formating
    '''
# Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logger_level)
# Create the mongoDB handler and set level
    mongo_handler = LoggingHandler(database)
    mongo_handler.setLevel(handler_level)
# Create formatter
    if format_str is not None:
        formatter = logging.Formatter(format_str)
    # Add formatter to ch
        mongo_handler.setFormatter(formatter)
# Remove redundant handlers
    old_handlers = logger.handlers
    for handler in old_handlers:
        try:
            if handler.database_name == database.database_name:
                logger.removeHandler(handler)
        except:
            pass
# Add handler to logger
    logger.addHandler(mongo_handler)
# Return logger object
    return logger

# %% Testing and Examples
if __name__ == '__main__':
    mongo_client = MongoClient()
# Testing
    print('\n Testing the connection ========================================')
    test_database = DatabaseMaster(mongo_client, 'test_database')
    #test_database = DatabaseReadWrite(mongo_client, 'test_database')
    #test_database = DatabaseRead(mongo_client, 'test_database')
    # Read and write to buffer
    print('\n Read and write to the buffer ----------------------------------')
    for x in range(int(2e4)):
        test_database.write_buffer(x**2.)
        # Read buffer (default)
    print('\n Read buffer: sort ascending')
    for doc in test_database.read_buffer():
        pass
    print(doc)
        # Read buffer (sort descending)
    print('\n Read buffer: sort descending')
    for doc in test_database.read_buffer(sort_ascending=False):
        pass
    print(doc)
        # Read buffer (document limit)
    print('\n Read buffer: document limit, sort ascending')
    for doc in test_database.read_buffer(number_of_documents=3):
        print(doc)
        # Read buffer (document limit, sort descening)
    print('\n Read buffer: document limit, sort descending')
    for doc in test_database.read_buffer(number_of_documents=3, sort_ascending=False):
        print(doc)
        # Read buffer (tailable cursor)
    print('\n Read buffer: tailable cursor, sort ascending')
    cursor = test_database.read_buffer(tailable_cursor=True)
    for doc in cursor:
        pass
    print(doc)
    print('\t new documents')
    for x in range(10):
        test_database.write_buffer(x**2.)
    for doc in cursor:
        print(doc)
        # Read buffer (tailable cursor, sort descending)
    print('\n Read buffer: tailable cursor, sort descending')
    cursor = test_database.read_buffer(tailable_cursor=True, sort_ascending=False)
    for doc in cursor:
        pass
    print(doc)
    print('\t new documents')
    for x in range(10):
        test_database.write_buffer(x**2.)
    for doc in cursor:
        print(doc)
    print('\t tailable cursor only works with ascending sort')
        # Read buffer (tailable cursor, document limit)
    print('\n Read buffer: tailable cursor, sort descending')
    cursor = test_database.read_buffer(number_of_documents=3, tailable_cursor=True)
    for doc in cursor:
        pass
    print(doc)
    print('\t new documents')
    for x in range(10):
        test_database.write_buffer(x**2.)
    for doc in cursor:
        print(doc)
    print('\t tailable cursor only works with no document limits')
    
    # Read and write to the record
    print('\n Read and write to the record ----------------------------------')
    for x in range(int(2e1)):
        test_database.write_record(x**2.)
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
        test_database.write_buffer(x**2.)
    for doc in test_database.read_buffer(number_of_documents=5, sort_ascending=False):
        test_database.write_document_to_record(doc)
    for doc in test_database.read_record(start, datetime.datetime.utcnow(), number_of_documents=5, sort_ascending=False):
        print(doc)
    
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
    logger = mongo_logger(test_database)
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
