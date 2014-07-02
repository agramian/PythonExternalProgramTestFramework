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
            function(self)
        return wrapper
    return decorator

def fixture(fixture, **kwargs):
    """ Test case timelimit decorator 
    """    
    def decorator(function):
        def wrapper(self):
            try:
                setup, teardown = fixture()
            except Exception:
                raise ValueError('a proper fixture returning a setup and teardown function was not provided')
            # check for setup override
            # otherwise take from fixture
            if 'setup' in kwargs:
                setup = kwargs['setup']
            # check for teardown override
            # otherwise take from fixture
            if 'teardown' in kwargs:
                teardown = kwargs['teardown']
            # verify types of fixture functions
            try:
                assert_variable_type(setup, [FunctionType, MethodType, NoneType])
            except:
                raise ValueError('the fixture setup argument was not a function or None type')
            try:
                assert_variable_type(teardown, [FunctionType, MethodType, NoneType])
            except:
                raise ValueError('the fixture setup argument was not a function or None type')            
            # call fixture setup if set
            if setup is not None:
                if isinstance(setup, MethodType):
                    setup(self)
                else:
                    setup()
            function(self)
            # call fixture teardown if set
            if teardown is not None:
                if isinstance(teardown, MethodType):
                    teardown(self)
                else:
                    teardown()          
        return wrapper
    return decorator