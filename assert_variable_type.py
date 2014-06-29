#!/usr/bin/python
# Filename: assert_variable_type.py

from types import *

def assert_variable_type(variable, expected_type):
    """Return True if a variable is of a certain type or types.
    Otherwise raise a ValueError exception.
    
    Positional arguments:
    variable -- the variable to be checked
    expected_type -- the expected type or types of the variable              
    """
    # if expected type is not a list make it one
    if not isinstance(expected_type, list):
        expected_type = [expected_type]
    # make sure all entries in the expected_type list are types
    for t in expected_type:
        if not isinstance(t, type):
            raise ValueError('expected_type argument  "%s" is not a type' %str(t))
    # check the type of the variable against the list
    # then raise an exception or return True
    if not len([(t) for t in expected_type if isinstance(variable, t)]):
        raise ValueError('%s is not an instance of type %s' %(str(variable),' or '.join([str(t) for t in expected_type])))
    return True