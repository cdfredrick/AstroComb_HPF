# -*- coding: utf-8 -*-
"""
Created on Thu Jun 15 12:56:31 2017

Public functions:

start_logging()
log_this(log_string, level)


@author: Wesley Brand
"""
import logging
import logging.config
from functools import wraps

def start_logging():
    """Must be called by external module to begin logging
    
    logs to astroComb.log
    see logging.conf for format details"""
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('astroComb')
    logger.info('Logging started!')
    return logger

def log_this(log_string, level):
    """Takes string that says what is being logged and an integer for the level
    
    Levels |   10  |  20  |   30    |   40  |    50    |
           | debug | info | warning | error | critical |"""
    def function_decorator(func):
        """Actual function decorator"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """The new function wtih logging"""
            logger = logging.getLogger('astroComb.%s.%s' % (func.__module__, func.__name__))
            message = log_string + ' with arguments: ' + str(args) + str(kwargs)
            logger.log(level, message)    
            func(*args, **kwargs)
        return wrapper
    return function_decorator
