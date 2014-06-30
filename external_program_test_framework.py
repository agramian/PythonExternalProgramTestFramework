#!/usr/bin/python
# Filename: external_program_test_framework.py

import sys
import os
import shutil
import timeit
from sets import Set
import colorama
colorama.init()
from colorama import Fore, Back, Style
"""
Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
Style: DIM, NORMAL, BRIGHT, RESET_ALL
"""
from assert_variable_type import *
from run_subprocess import run_subprocess, TimeoutError

def description(description):
    def decorator(function):
        def wrapper(self):
            self.description = description
        return wrapper
    return decorator

class ExternalProgramTestSuite:
    """ A Class for creating Test Suites with
    test cases which call external programs 
    """
    # internal static variables
    _test_suites = {}
    _num_formatting_chars = 100
    _all_log_files = Set()
    _has_run = False
    _framework_output_file = None
    # public static variables
    color_output_text = True
    suite_header_color = Fore.MAGENTA
    case_header_color = Fore.CYAN
    suite_result_header_color = Fore.YELLOW
    
    def __init__(self, **kwargs):
        # reset the suite variables
        self._set_suite_defaults()          
        # test suite name is the name of the suite class
        # or the suite_name arg if passed
        if 'suite_name' in kwargs:
            if assert_variable_type(kwargs['suite_name'], str):
                self.suite_name = kwargs['suite_name']
        else:
            # suite name defaults to class name
            self.suite_name = self.__class__.__name__                          
        # add test suite to class static total list
        try:
            # make sure a suite with the same
            # name does not already exist
            if self.suite_name not in ExternalProgramTestSuite._test_suites:  
                ExternalProgramTestSuite._test_suites[self.suite_name] = {'self': self,
                                                                         'name': self.suite_name,
                                                                         'description': self.suite_description,
                                                                         'args': kwargs,
                                                                         'num_passed': 0,
                                                                         'num_tests': 0,
                                                                         'execution_time': 0,
                                                                         'has_run': False,
                                                                         'status_threshold': 100,
                                                                         'passed': False}
            else:
                raise ValueError('A suite with the name "%s" already exists. '
                                 'Please rename one of suite classes or pass a unique "suite_name" argument to one or both of the constructors.')
        except ValueError as e:
             raise Exception('[%s] %s' %(type(e).__name__, e))
    
    def log(self, print_string, error=False, color=Fore.RESET):
        """Wrapper over print function to allow writing
        test framework output to file if desired.
        """
        # write the print output to the log files
        if self.log_framework_output:
            if error and self.stderr_file is not None:
                with open(self.stderr_file, 'a') as f:
                    f.write(print_string + "\r\n")
            elif self.stdout_file is not None:
                 with open(self.stdout_file, 'a') as f:
                    f.write(print_string + "\r\n")
        # print the output and color appropriately
        if ExternalProgramTestSuite.color_output_text:
            print(color
                  + print_string
                  + Fore.RESET + Back.RESET + Style.RESET_ALL)
        # Aptana's interactive console doesn't accept ANSI escape
        # characters but at least it colors the stderr red so
        # separate normal output from error output appropriately
        else:
            if error:   
                sys.stderr.write(print_string + "\r\n")
                sys.stderr.flush()
            else:
                sys.stdout.write(print_string + "\r\n")
                sys.stdout.flush()
        
    def _set_suite_defaults(self):
        """Set the suite variables to their defaults
        """
        # set the default suite variables
        # default suite name and description
        self.suite_name = None        
        self.suite_description = None
        # number of passed test cases
        self.num_tests_passed = 0
        # threshold in percentage of tests
        # passed to decide status of suite
        self.suite_status_threshold = 100
        # whether to truncate the log file
        # before writing to it
        self.overwrite_log_file = True
        # whether to print process output
        # or just write it to the log file
        self.print_process_output = True
        self.log_framework_output = False
        # default log path
        self.default_log_file = "run.log"
        self.stdout_file = self.stderr_file= self.default_log_file
        # setup and teardown function
        self.suite_setup = None
        self.suite_teardown = None
        # timeout values
        self.suite_timeout = None
        self.suite_case_timeout = None                        

    def _set_case_defaults(self):
        """ 
        Set the case variables to their defaults
        """
        # default test case variables
        self.name = None
        self.executable_command = None
        self.command_arguments = []
        self.expected_return_value = 0
        # whether to print process output
        # or just write it to the log file
        self.print_case_output = self.print_process_output                      
        # default log path
        self.stdout_file = self.stderr_file= self.default_log_file        
        # default case description     
        self.description = None
        # subprocess execution time
        self.execution_time = 0       
        # subprocess timeout
        self.timeout = self.suite_case_timeout
        # skip setup and teardown
        self.skip_setup = False
        self.skip_teardown = False

    def _setup_suite(self, **kwargs):
        """ 
        Set the suite variables
        """        
        # if a test suite requires common variables across all test cases, 
        # they can be passed through kwargs and are set here
        for key, value in kwargs.items():
            if type(value) is str:
                exec('self.' + str(key) + '="' + value + '"') in globals(), locals()
            else:
                exec('self.' + str(key) + '=' + str(value)) in globals(), locals()
        # each function in a test suite class is a test case
        # so get the cases and add them to the testSuites list
        test_names = { key: value for key, value in self.__class__.__dict__.items() if isinstance(value, FunctionType) }
        self.test_cases = []
        for name in test_names:
            if name == "setup":
                self.suite_setup = getattr(self, name)
            elif name == "teardown":
                self.suite_teardown = getattr(self, name)
            else:              
                self.test_cases.append(name)             

    def _setup_case(self):
        # if not suites have been run and the overwriet log file
        # flag was set to True, truncate the log files    
        if self.overwrite_log_file and (not ExternalProgramTestSuite._has_run
                                        or len([(x) for x in [self.stdout_file, self.stderr_file]
                                                    if x not in ExternalProgramTestSuite._all_log_files]) > 0):
            for log_file in [self.stdout_file, self.stderr_file]:
                ExternalProgramTestSuite._all_log_files.add(log_file)
                with open(log_file, 'w') as f:
                    f.truncate(0)           
        # call setup function if set
        if not self.skip_setup and self.suite_setup is not None:
            self.suite_setup()            
    
    def _end_case(self):
        # call teardown function if set
        if not self.skip_teardown and self.suite_teardown is not None:
            self.suite_teardown()

    def _validate_test_arguments(self):
        """ 
        Validate test case argument types
        """
        #list
        assert_variable_type(self.command_arguments, list)
        #string
        string_vars = [self.executable_command,
                       self.description,
                       self.name,
                       self.stdout_file,
                       self.stderr_file]
        string_vars = string_vars + self.command_arguments
        [assert_variable_type(x, [str, NoneType]) for x in string_vars]
        # int
        integer_vars = [self.expected_return_value]
        # bool
        bool_vars = [self.print_process_output,
                     self.log_framework_output,
                     self.skip_setup,
                     self.skip_teardown]
        [assert_variable_type(x, bool) for x in bool_vars]
        # float
        float_vars = [self.timeout,
                      self.suite_timeout,
                      self.suite_case_timeout]
        [assert_variable_type(x, [int, float, NoneType]) for x in float_vars]
        # functions
        function_vars = [self.suite_setup,
                         self.suite_teardown]
        [assert_variable_type(x, [MethodType, NoneType]) for x in function_vars]     

    def run(self, suite_name=None):
        """
        Run the test suite
        """
        # setup suite
        if suite_name is None:
            suite_name = self.suite_name
        self._setup_suite(**ExternalProgramTestSuite._test_suites[suite_name]['args'])
        # run all the test cases
        for index, case in enumerate(sorted(self.test_cases)):
            test_setup = getattr(self, case)
            if not test_setup:
                raise Exception("Test Case %s does not exist" % str(test_setup))
            # reset the default suite/case variables
            self._set_case_defaults()
            # call test case function for setup 
            test_setup()
            # suite setup routine        
            self._setup_case()            
            # print test suite name and descripion if any
            # and if first loop through cases              
            if index == 0: 
                self.log("=" * ExternalProgramTestSuite._num_formatting_chars)
                self.log("TEST SUITE: %s" %suite_name,
                         False,
                         ExternalProgramTestSuite.suite_header_color)
                if self.suite_description:
                    self.log("Description: %s" %(str(ExternalProgramTestSuite._test_suites[suite_name]['description'])))            
            # print case name and description if any
            self.log("-" * ExternalProgramTestSuite._num_formatting_chars)
            self.log("CASE: %s" %case,
                     False,
                     ExternalProgramTestSuite.case_header_color)
            # validate args and run the test case
            try:
                self._validate_test_arguments()
                self._run_test_case()               
            except Exception as e:
                self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
            # set has_run flags
            ExternalProgramTestSuite._has_run = True
            # set suite attributes for static _test_suites list
            ExternalProgramTestSuite._test_suites[self.suite_name]['has_run'] = True
            ExternalProgramTestSuite._test_suites[self.suite_name]['status_threshold'] = self.suite_status_threshold
            # end case routine
            self._end_case()       
        # print test result
        self._print_suite_results()        

    def _run_test_case(self):
        """
        Run an individual test case
        """
        # print description if any
        if self.description:
            self.log("Description: %s" %(str(self.description)))
        self.log("-" * ExternalProgramTestSuite._num_formatting_chars)
        process = None
        execution_time = None
        try:
            process, execution_time = run_subprocess(self.executable_command,
                                                     self.command_arguments,
                                                     self.print_process_output,
                                                     self.stdout_file,
                                                     self.stderr_file,
                                                     self.timeout)
        except OSError as e:            
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        except ValueError as e:
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        except TimeoutError as e:
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        # print pass/fail, execution time
        if process is not None:                             
            if process.returncode == self.expected_return_value:
                self.log('PASS', False, Back.GREEN)
                self.num_tests_passed += 1
            else:
                self.log('FAIL', True, Back.RED)
            self.log("%.4f seconds" %(execution_time))
            ExternalProgramTestSuite._test_suites[self.suite_name]['execution_time'] = execution_time
            self.execution_time = execution_time  
        else:
             self.log('FAIL', True, Back.RED)

    def _print_suite_results(self):
        self.log( "*" * ExternalProgramTestSuite._num_formatting_chars)    
        self.log("SUITE RESULT",
                 False,
                 ExternalProgramTestSuite.suite_result_header_color)
        self.log( "*" * ExternalProgramTestSuite._num_formatting_chars)
        passed = self._print_info_and_status()
        self.log("=" * ExternalProgramTestSuite._num_formatting_chars)
        # add test result to class static suite list
        ExternalProgramTestSuite._test_suites[self.suite_name]['num_tests'] = len(self.test_cases)
        ExternalProgramTestSuite._test_suites[self.suite_name]['num_passed'] = self.num_tests_passed
        ExternalProgramTestSuite._test_suites[self.suite_name]['passed'] = passed               

    def _print_info_and_status(self, suite_name=""):
        num_tests = len(self.test_cases)
        passed = False
        try:
            if num_tests > 0:
                percentage_passed = (self.num_tests_passed * 1.0 / num_tests) * 100
            else:
                percentage_passed = 0 
            output_string = ("%s%d/%d (%.2f%%) in %.4f seconds"
                             %(suite_name,
                               self.num_tests_passed,
                               num_tests,
                               percentage_passed,
                               ExternalProgramTestSuite._test_suites[self.suite_name]['execution_time']))
            if percentage_passed >= self.suite_status_threshold:
                output_string += " OK"
                if self.suite_status_threshold != 100:
                    output_string += " with %.2f%% threshold" % self.suite_status_threshold
                self.log(output_string, False, Back.GREEN)
                passed = True
            else:
                output_string += " NOT OK"
                self.log(output_string, False, Back.RED)
        except Exception as e:
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        return passed           
            
    @staticmethod
    def run_all():
        """
        Run all registered test suites that have run
        """
        ExternalProgramTestSuite._has_run = False
        for suite, properties in ExternalProgramTestSuite._test_suites.items():
            ExternalProgramTestSuite.run(properties['self'], properties['name'])
        ExternalProgramTestSuite.print_total_results()
        
    @staticmethod
    def print_total_results():
        """
        Print the cumulative results from all suites registered and run
        """        
        # print results for each suite on one line
        # keep track of test results info for totals
        total_num_tests = 0
        total_num_passed = 0
        total_suites_passed = 0
        total_num_suites = 0
        total_execution_time = 0
        try:
            for index, (suite, results) in enumerate(ExternalProgramTestSuite._test_suites.items()):
                self = results['self']
                if index == 0:
                    self.log( "*" * ExternalProgramTestSuite._num_formatting_chars)    
                    self.log("ALL SUITE RESULTS",
                             False,
                             ExternalProgramTestSuite.suite_result_header_color)
                    self.log( "*" * ExternalProgramTestSuite._num_formatting_chars)
                if results['has_run']:                 
                    self._print_info_and_status(suite + ": ")
                    total_num_tests += results['num_tests']
                    total_num_passed += results['num_passed']
                    if total_num_tests > 0 and results['passed']: 
                        total_suites_passed += 1
                    total_execution_time += results['execution_time']
                    self.log("_" * ExternalProgramTestSuite._num_formatting_chars)
                    total_num_suites += 1
            # print cumulative total pass/fail            
            if total_num_tests > 0:
                self.log("TOTALS");
                self.log("." * ExternalProgramTestSuite._num_formatting_chars)                      
                percentage_passed = (total_suites_passed * 1.0 / total_num_suites) * 100
                self.log("%d/%d (%.2f%%) suites\n%d/%d (%.2f%%) tests\nin %.4f seconds"
                         %(total_suites_passed,
                           total_num_suites,
                           percentage_passed,
                           total_num_passed,
                           total_num_tests,
                           (total_num_passed * 1.0 / total_num_tests) * 100,
                           total_execution_time)) 
            if percentage_passed == 100:
                self.log("OK", False, Back.GREEN)
            else:
                self.log("NOT OK", False, Back.RED)
            self.log("." * ExternalProgramTestSuite._num_formatting_chars)
        except Exception as e:
            print(Fore.RED
                  + '[%s] %s' %(type(e).__name__, e)
                  + Fore.RESET + Back.RESET + Style.RESET_ALL)