from assert_variable_type import *

def name(name):
    """ Test case name decorator 
    """
    def decorator(function):
        def wrapper(self):
            self._name = name
            self._wait_sem += -1
            # if semaphor is 0 print
            # case header now
            if self._wait_sem == 0:
                self.case_header()
            function(self)
        return wrapper
    return decorator
          
def description(description):
    """ Test case description decorator 
    """    
    def decorator(function):
        def wrapper(self):
            self._description = description
            self._wait_sem += -1
            # if semaphor is 0 print
            # case header now
            if self._wait_sem == 0:
                self.case_header()
            function(self)
        return wrapper
    return decorator

def timelimit(timelimit):
    """ Test case timelimit decorator 
    """    
    def decorator(function):
        def wrapper(self):
            self._timelimit = timelimit
            self._wait_sem += -1
            # if semaphor is 0 print
            # case header now
            if self._wait_sem == 0:
                self.case_header()            
            function(self)
        return wrapper
    return decorator

def fixture(fixture, **kwargs):
    """ Test case timelimit decorator 
    """    
    def decorator(function):
        def wrapper(self):
            self._fixture = fixture
            # check for setup override
            # otherwise take from fixture
            if 'setup' in kwargs:
                self._case_setup = kwargs['setup']
            # check for teardown override
            # otherwise take from fixture
            if 'teardown' in kwargs:
                self._case_teardown = kwargs['teardown']
            self._wait_sem += -1
            # if semaphor is 0 print
            # case header now
            if self._wait_sem == 0:
                self.case_header()                         
            function(self)         
        return wrapper
    return decorator