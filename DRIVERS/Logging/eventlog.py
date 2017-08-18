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
import logging.config
from functools import wraps


#Constants
CONFIG_FILE_NAME = 'log_config.conf'

#Public functions
def start_logging(config_file_name=CONFIG_FILE_NAME):
    """Must be called by external module to begin logging.

    logs to astroComb.log
    see log_config.conf for format details"""
    logging.config.fileConfig(config_file_name)
    # If you get a "cannot find formatters section" error include
    #   the full file path for log_config.conf, python is actually
    #   not finding the file itself
    logger = logging.getLogger('astroComb')
    logger.info('Logging started!')
    return logger

def log_this(level1=10, level2=10, log_string1='', log_string2=''):
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

def log_error(mod_name, func_name, err, log_str='', level=40):
    """Takes originating function name and module and error to log.

    Optional descriptive string & log level
    Note that if function is in error handling function decorator
        you'll need to use functools.wraps on the function in the
        error handler that calls log_error (see log_this above)
    Levels |   10  |  20  |   30    |   40  |    50    |
           | debug | info | warning | error | critical |"""
    logger = logging.getLogger('astroComb.%s.%s' % (mod_name, func_name))
    logger.log(level, str(err) + log_str)

def log_warn(mod_name, func_name, log_str, level=30):
    """Takes originating function name and module and string to log.

    Optional level, not just for warnings
    The most general log-what-you-want call, use instead of print
        for final code
    Requires more hard-coding
    Levels |   10  |  20  |   30    |   40  |    50    |
           | debug | info | warning | error | critical |"""
    logger = logging.getLogger('astroComb.%s.%s' % (mod_name, func_name))
    logger.log(level, log_str)
