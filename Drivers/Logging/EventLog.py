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
LOGGER_NAME = 'Astrocomb'

#Python imports
import logging
import sys
from functools import wraps
from Drivers.Database.MongoDB import MongoLogger

#Public functions
def start_logging(database=None, logger_level=logging.DEBUG, log_buffer_handler_level=logging.DEBUG, log_handler_level=logging.WARNING, format_str=None, remove_all_handlers=True):
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
            format_str = '%(name)s:\n %(message)s'
        logger = MongoLogger(database, name=LOGGER_NAME, logger_level=logger_level, log_buffer_handler_level=log_buffer_handler_level, log_handler_level=log_handler_level, format_str=format_str, remove_all_handlers=remove_all_handlers)
    else:
    # If no database is specified, setup a simple stream handler
        if format_str is None:
            format_str='%(asctime)s [%(levelname)s] %(name)s:\n %(message)s \n'
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logger_level)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_buffer_handler_level)
        formatter = logging.Formatter(format_str)
        stream_handler.setFormatter(formatter)
        old_handlers = logger.handlers
        for handler in old_handlers:
            if remove_all_handlers:
                logger.removeHandler(handler)
        logger.addHandler(stream_handler)
    logger.info('Logging started!')
    return logger

def log_this(prologue_str='', epilogue_str='', prologue_level=logging.DEBUG, epilogue_level=logging.DEBUG):
    """Takes optional integers for levels and optional descriptors.
    Automatically catches, logs, and raises untamed errors.

    Levels |   10  |  20  |   30    |   40  |    50    |
           | DEBUG | INFO | WARNING | ERROR | CRITICAL |"""
    def function_decorator(func):
        """Actual function decorator"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """The new function wtih logging"""
            logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,func.__module__,func.__name__))
            message = 'Prologue:\t'+ prologue_str + '\nInput:\t' + str(args) +','+ str(kwargs)
            logger.log(prologue_level, message)
            result = func(*args, **kwargs)
            # Log returned result
            try:
                res_str = str(result)
            except:
                res_str = ''
            message = 'Epilogue:\t' + epilogue_str + '\nReturns:\t' + res_str
            logger.log(epilogue_level, message)
            # Return the result
            return result
        return wrapper
    return function_decorator

def log(mod_name, func_name, log_str, level):
    """Writes function name, module, and log string to the specified log level.
    
    Programmatically retreive the module name with "__name__",
    and the function name with "<func>.__name__", to return the same values
    as those in the "log_this" function wrapper.

    Optional descriptive string & log level
    Note that if function is in error handling function decorator
        you'll need to use functools.wraps on the function in the
        error handler that calls log_error (see log_this above)
    Levels |   10  |  20  |   30    |   40  |    50    |
           | DEBUG | INFO | WARNING | ERROR | CRITICAL |"""
    logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,mod_name, func_name))
    logger.log(level, log_str)

def log_critical(mod_name, func_name, log_str):
    """Writes function name, module, and log string to the critical log level.
    
    Programmatically retreive the module name with "__name__",
    and the function name with "<func>.__name__", to return the same values
    as those in the "log_this" function wrapper.
    """
    logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,mod_name, func_name))
    logger.critical(log_str)

def log_error(mod_name, func_name, log_str):
    """Writes function name, module, and log string to the ERROR log level.
    
    Programmatically retreive the module name with "__name__",
    and the function name with "<func>.__name__", to return the same values
    as those in the "log_this" function wrapper.
    
    Note that if function is in error handling function decorator
        you'll need to use functools.wraps on the function in the
        error handler that calls log_error (see log_this above)"""
    logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,mod_name, func_name))
    logger.error(log_str)

def log_exception(mod_name, func_name, log_str=''):
    """Writes function name, module, and exception to the ERROR log level.
    Exception info is automatically added to the logging message.
    This method should only be called from an exception handler.
    
    Programmatically retreive the module name with "__name__",
    and the function name with "<func>.__name__", to return the same values
    as those in the "log_this" function wrapper.
    
    Optional descriptive string
    
    Note that if function is in error handling function decorator
        you'll need to use functools.wraps on the function in the
        error handler that calls log_error (see log_this above)"""
    logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,mod_name, func_name))
    logger.exception(log_str)

def log_warning(mod_name, func_name, log_str):
    """Writes function name, module, and log string to the WARNING log level.
    
    Programmatically retreive the module name with "__name__",
    and the function name with "<func>.__name__", to return the same values
    as those in the "log_this" function wrapper.
    """
    logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,mod_name, func_name))
    logger.warning(log_str)

def log_info(mod_name, func_name, log_str):
    """Writes function name, module, and log string to the INFO log level.
    
    Programmatically retreive the module name with "__name__",
    and the function name with "<func>.__name__", to return the same values
    as those in the "log_this" function wrapper.
    """
    logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,mod_name, func_name))
    logger.info(log_str)

def log_debug(mod_name, func_name, log_str):
    """Writes function name, module, and log string to the DEBUG log level.
    
    Programmatically retreive the module name with "__name__",
    and the function name with "<func>.__name__", to return the same values
    as those in the "log_this" function wrapper.
    """
    logger = logging.getLogger('{:}.{:}.{:}'.format(LOGGER_NAME,mod_name, func_name))
    logger.debug(log_str)


