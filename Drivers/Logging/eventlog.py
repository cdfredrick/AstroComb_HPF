# -*- coding: utf-8 -*-
"""
Created on Thu Jun 15 12:56:31 2017

@author: Wesley Brand

Module: eventlog
    import eventlog as log

Requires:
    logging.conf
    #To decrease stuff in log file
    increase the level under astroComb to INFO or higher

Public functions:
    start_logging()
    log_this(level1=10, level2=10, log_string1='', log_string2='')
    log_error(mod_name, func_name, err, log_str='', level=40)

"""
#pylint: disable=W0703
### Intentionally catching a general exception


#Python imports
import logging
import sys
from functools import wraps
from Drivers.Database.MongoDB import MongoLogger

#Public functions
def start_logging(database=None, logger_level=logging.DEBUG, handler_level=logging.DEBUG, format_str=None, remove_old_handlers=True):
    """
    Must be called by external module to begin logging. Initializes a logger to
        the specified database or to the console stream. Use the keyword arguments
        to specify the target database, logger and handler levels, and format 
        string.
    If no database is specified then logs are sent to a default stream handler.
        All old handlers are removed by default.
    Default logging levels are set to debug.
    If no format str is specified then a default is provided, which includes the
        hierarchical name of the logger and the log message.
    """
    if database is not None:
    # If a database is specified, initialize the mongo logger
        if format_str is None:
            format_str = '%(name)s: %(message)s'
        logger = MongoLogger(database, name='astroComb', logger_level=logger_level, handler_level=handler_level, format_str=format_str, remove_old_handlers=remove_old_handlers)
    else:
    # If no database is specified, setup a simple stream handler
        if format_str is None:
            format_str='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        logger = logging.getLogger('astroComb')
        logger.setLevel(logger_level)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(handler_level)
        formatter = logging.Formatter(format_str)
        stream_handler.setFormatter(formatter)
        old_handlers = logger.handlers
        for handler in old_handlers:
            if remove_old_handlers:
                logger.removeHandler(handler)
        logger.addHandler(stream_handler)
    logger.info('Logging started!')
    return logger

def log_this(level1=logging.DEBUG, level2=logging.DEBUG, log_string1='', log_string2=''):
    """Takes optional integers for levels and optional descriptors.

    Levels |   10  |  20  |   30    |   40  |    50    |
           | debug | info | warning | error | critical |"""
    def function_decorator(func):
        """Actual function decorator"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """The new function wtih logging"""
            logger = logging.getLogger('astroComb.%s.%s' % (func.__module__,
                                                            func.__name__))
            message = log_string1 + ' Arguments: ' + str(args) + str(kwargs)
            logger.log(level1, message)
            result = func(*args, **kwargs)
            try:
                res_str = str(result)
            except Exception:  #There are many possible reasons a
                               #result is not string-able
                res_str = '{}'
            message = log_string2 + ' Returns: ' + res_str
            logger.log(level2, message)
            return result
        return wrapper
    return function_decorator

def log_error(mod_name, func_name, err, log_str='', level=logging.ERROR):
    """Takes originating function name and module and error to log.

    Optional descriptive string & log level
    Note that if function is in error handling function decorator
        you'll need to use functools.wraps on the function in the
        error handler that calls log_error (see log_this above)
    Levels |   10  |  20  |   30    |   40  |    50    |
           | debug | info | warning | error | critical |"""
    logger = logging.getLogger('astroComb.%s.%s' % (mod_name, func_name))
    logger.log(level, str(err) + log_str)

def log_warn(mod_name, func_name, log_str, level=logging.WARNING):
    """Takes originating function name and module and string to log.

    Optional level, not just for warnings
    The most general log-what-you-want call, use instead of print
        for final code
    Requires more hard-coding
    Levels |   10  |  20  |   30    |   40  |    50    |
           | debug | info | warning | error | critical |"""
    logger = logging.getLogger('astroComb.%s.%s' % (mod_name, func_name))
    logger.log(level, log_str)
