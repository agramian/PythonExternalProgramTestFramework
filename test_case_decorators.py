def name(name):
    """ Test case name decorator 
    """
    def decorator(function):
        def wrapper(self):
            self._name = name
            function(self)
        return wrapper
    return decorator
          
def description(description):
    """ Test case description decorator 
    """    
    def decorator(function):
        def wrapper(self):
            self._description = description
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