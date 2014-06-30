#!/usr/bin/python
# Filename: run_subprocess.py

import time
import timeit
import subprocess
from assert_variable_type import *
from nbstream_readerwriter import NonBlockingStreamReaderWriter as NBSRW

def run_subprocess(executable_command,
                   command_arguments = [],
                   print_process_output=True,
                   stdout_file=None,
                   stderr_file=None,
                   timeout=None,
                   poll_seconds=.100):
    """Create and run a subprocess and return the process and
    execution time after it has completed.  The execution time
    does not include the time taken for file i/o when logging
    the output if stdout_file and stderr_file arguments are given. 

    Positional arguments:
    executable_command (str) -- executable command to run
    command_arguments (list) -- arguments or  
    print_process_output (bool) -- whether to print the process' live output 
    stdout_file (str) -- file to log stdout to
    stderr_file (str) -- file to log stderr to              
    """
    # validate arguments
    # list
    assert_variable_type(command_arguments, list)     
    # strings
    _string_vars = [executable_command,
                    stdout_file,
                    stderr_file]
    [assert_variable_type(x, str) for x in _string_vars + command_arguments]
    # bools 
    assert_variable_type(print_process_output, bool) 
    # floats
    _float_vars = [timeout,
                   poll_seconds]     
    [assert_variable_type(x, [int, float, NoneType]) for x in _float_vars]
    global process, _nbsr_stdout, _nbsr_stderr
    process = None
    _nbsr_stdout = None
    _nbsr_stderr = None
    def _exec_subprocess():
        # create the subprocess to run the external program
        global process, _nbsr_stdout, _nbsr_stderr
        process = subprocess.Popen([executable_command] + command_arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # wrap p.stdout with a NonBlockingStreamReader object:
        _nbsr_stdout = NBSRW(process.stdout, stdout_file)
        _nbsr_stderr = NBSRW(process.stderr, stderr_file)
        # set deadline if timeout was set
        _deadline = None
        if timeout is not None:           
            _deadline = time.time() + timeout
        # poll process while it runs
        while process.poll() is None:
            # throw TimeoutError if timeout was specified and deadline has passed           
            if _deadline is not None and time.time() > _deadline and process.poll() is None:
                process.terminate()
                raise TimeoutError("Sub-process did not complete before %.4f seconds elapsed" %(timeout))
            # sleep to yield for other processes           
            time.sleep(poll_seconds)
    execution_time = timeit.timeit(_exec_subprocess, number=1)                             
    # return process to allow application to communicate with it
    # and extract whatever info like stdout, stderr, returncode
    # also return execution_time to allow 
    return process, execution_time

class TimeoutError(Exception): pass