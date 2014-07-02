#!/usr/bin/python
# Filename: external_program_test_framework.py

import sys
import os
import shutil
import time
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
from test_case_decorators import *
from assert_variable_type import *
from run_subprocess import run_subprocess, TimeoutError

def case_header(function):
    """ Test case header output decorator 
    """  
    def wrapper(self):
        # print case name
        self.log("-" * ExternalProgramTestSuite._num_formatting_chars)
        self.log("CASE: %s" %self._name,
                 False,
                 ExternalProgramTestSuite.case_header_color)
        # print description if any
        if self._description is not None:
            self.log("Description: %s" %(str(self._description)))
        self.log("-" * ExternalProgramTestSuite._num_formatting_chars)        
        function(self)
    return wrapper

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
                                                                          'num_checks': 0,
                                                                          'num_checks_passed': 0,
                                                                          'execution_time': 0,
                                                                          'has_run': False,
                                                                          'pass_threshold': 100,
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
        self._num_tests_passed = 0
        # num checks and failures
        self._total_checks_passed = 0
        self._total_checks = 0        
        # threshold in percentage of tests
        # passed to decide status of suite
        self.suite_pass_threshold = 100
        # whether to truncate the log file
        # before writing to it
        self.overwrite_log_file = True
        # whether to print process output
        # or just write it to the log file
        self.print_process_output = True
        self.log_framework_output = False
        # default log path
        self._default_log_file = "run.log"
        self.stdout_file = self.stderr_file= self._default_log_file
        # setup and teardown function
        self._suite_setup = None
        self._suite_teardown = None
        # timelimit values
        self._suite_timelimit_met = True
        self.suite_timelimit = None
        self.suite_case_timelimit = None                        

    def _set_case_defaults(self):
        """ 
        Set the case variables to their defaults
        """
        # default test case variables
        self._name = None
        # whether to print process output
        # or just write it to the log file
        self.print_case_output = self.print_process_output                      
        # default log path
        self.stdout_file = self.stderr_file= self._default_log_file        
        # default case description     
        self._description = None
        # num checks and failures
        self._num_checks_passed = 0
        self._num_checks = 0
        # threshold in percentage of checks
        # passed to decide status of case
        self.case_pass_threshold = 100
        # test case time limit
        self._timelimit = self.suite_case_timelimit
        # skip setup and teardown
        self._skip_setup = False
        self._skip_teardown = False

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
                self._suite_setup = getattr(self, name)
            elif name == "teardown":
                self._suite_teardown = getattr(self, name)
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
    
    def _end_case(self):
        pass

    def _validate_test_arguments(self):
        """ 
        Validate test case argument types
        """
        #string
        string_vars = [self._description,
                       self._name,
                       self.stdout_file,
                       self.stderr_file]
        string_vars = string_vars
        [assert_variable_type(x, [str, NoneType]) for x in string_vars]
        # bool
        bool_vars = [self.print_process_output,
                     self.log_framework_output,
                     self._skip_setup,
                     self._skip_teardown]
        [assert_variable_type(x, bool) for x in bool_vars]
        # float
        float_vars = [self._timelimit,
                      self.suite_timelimit,
                      self.suite_case_timelimit]
        [assert_variable_type(x, [int, float, NoneType]) for x in float_vars]
        # functions
        function_vars = [self._suite_setup,
                         self._suite_teardown]
        [assert_variable_type(x, [MethodType, NoneType]) for x in function_vars]     

    def run(self, suite_name=None):
        """
        Run the test suite
        """
        # capture start time
        suite_start_time = time.clock() 
        # setup suite
        if suite_name is None:
            suite_name = self.suite_name
        self._setup_suite(**ExternalProgramTestSuite._test_suites[suite_name]['args'])
        # call suite setup function if set
        if self._suite_setup is not None:
            self._suite_setup()         
        # run all the test cases
        for index, case in enumerate(sorted(self.test_cases)):
            self.test_case = getattr(self, case)
            if not self.test_case:
                raise Exception("Test Case %s does not exist" % str(self.test_case))
            # reset the default suite/case variables
            self._set_case_defaults()
            # set test case name to case
            self._name = case            
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
                    self.log("Description: %s" %(self.suite_description))
                    ExternalProgramTestSuite._test_suites[suite_name]['description'] = self.suite_description          
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
            ExternalProgramTestSuite._test_suites[self.suite_name]['pass_threshold'] = self.suite_pass_threshold
            # end case routine
            self._end_case()
        # call suite teardown function if set
        if self._suite_teardown is not None:
            self._suite_teardown()
        # capture suite end time
        suite_end_time = time.clock()
        suite_time_take = suite_end_time - suite_start_time
        ExternalProgramTestSuite._test_suites[self.suite_name]['execution_time'] = suite_time_take
        # if a timelimit was set
        # check if it was met
        if self.suite_timelimit is not None:
            self.log("_" * ExternalProgramTestSuite._num_formatting_chars)
            if suite_time_take <= self.suite_timelimit:
                self.log('CHECK PASS: suite completed before time limit of %.4f' %self.suite_timelimit, False, Back.GREEN)
                self._total_checks_passed += 1
            else:
                self.log('CHECK FAIL: suite did not complete before time limit of %.4f' %self.suite_timelimit, True, Back.RED)
                self._suite_timelimit_met = False
            self._total_checks += 1                            
            
        # print test result
        self._print_suite_results()       

    @case_header
    def _run_test_case(self):
        """
        Run an individual test case
        """
        # run test case
        execution_time = timeit.timeit(self.test_case, number=1)
        # if a timelimit was set
        # check if it was met
        if self._timelimit is not None:
            if execution_time <= self._timelimit:
                self.log('CHECK PASS: test completed before time limit of %.4f' %self._timelimit, False, Back.GREEN)
                self._num_checks_passed += 1
            else:
                self.log('CHECK FAIL: test did not complete before time limit of %.4f' %self._timelimit, True, Back.RED)
            self._num_checks += 1         
        # print pass/fail, execution time
        if self._num_checks > 0:
            percentage_passed = (self._num_checks_passed * 1.0 / self._num_checks) * 100
        else:
            percentage_passed = 0 
        output_string = ("%d/%d (%.2f%%) CHECKS in %.4f seconds"
                         %(self._num_checks_passed,
                           self._num_checks,
                           percentage_passed,
                           execution_time))
        if percentage_passed >= self.case_pass_threshold or self._num_checks == 0:
            output_string += " TEST PASS"
            if self.case_pass_threshold != 100:
                output_string += " with %.2f%% threshold" % self.case_pass_threshold
            self.log(output_string, False, Back.GREEN)
            self._num_tests_passed += 1
        else:
            output_string += " TEST FAIL"
            self.log(output_string, False, Back.RED)
        self._total_checks += self._num_checks
        self._total_checks_passed += self._num_checks_passed           

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
        ExternalProgramTestSuite._test_suites[self.suite_name]['num_passed'] = self._num_tests_passed
        ExternalProgramTestSuite._test_suites[self.suite_name]['passed'] = passed
        ExternalProgramTestSuite._test_suites[self.suite_name]['num_checks'] = self._total_checks
        ExternalProgramTestSuite._test_suites[self.suite_name]['num_checks_passed'] = self._total_checks_passed               

    def _print_info_and_status(self, suite_name=""):
        num_tests = len(self.test_cases)
        passed = False
        try:
            if num_tests > 0:
                percentage_tests_passed = (self._num_tests_passed * 1.0 / num_tests) * 100
            else:
                percentage_tests_passed = 0
            if self._total_checks > 0:
                percentage_checks_passed = (self._total_checks_passed * 1.0 / self._total_checks) * 100
            else:
                percentage_checks_passed = 0                
            output_string = ("%s%d/%d (%.2f%%) TESTS with %d/%d (%.2f%%) CHECKS in %.4f seconds"
                             %(suite_name,
                               self._num_tests_passed,
                               num_tests,
                               percentage_tests_passed,
                               self._total_checks_passed,
                               self._total_checks,
                               percentage_checks_passed,
                               ExternalProgramTestSuite._test_suites[self.suite_name]['execution_time']))
            if percentage_tests_passed >= self.suite_pass_threshold and self._suite_timelimit_met:
                output_string += " OK"
                if self.suite_pass_threshold != 100:
                    output_string += " with %.2f%% threshold" % self.suite_pass_threshold
                self.log(output_string, False, Back.GREEN)
                passed = True
            else:
                output_string += " NOT OK"
                self.log(output_string, False, Back.RED)
        except Exception as e:
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        return passed           

    def check_subprocess(self,
                         executable_command,
                         command_arguments,
                         expected_returncode,                        
                         timeout = None,
                         print_process_output = True,
                         stdout_file = None,
                         stderr_file = None,
                         poll_seconds=.100):
        process = None
        try:
            process, execution_time = run_subprocess(executable_command,
                                                     command_arguments,
                                                     timeout,
                                                     print_process_output,
                                                     stdout_file,
                                                     stderr_file,
                                                     poll_seconds)
        except OSError as e:            
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        except ValueError as e:
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        except TimeoutError as e:
            self.log('[%s] %s' %(type(e).__name__, e), True, Fore.RED)
        # print pass/fail, execution time
        if process is not None:                             
            if process.returncode == expected_returncode:
                self.log('CHECK PASS', False, Back.GREEN)
                self._num_checks_passed += 1
            else:
                self.log('CHECK FAIL', True, Back.RED)            
            self.log("%.4f seconds" %(execution_time))   
        else:
             self.log('CHECK FAIL', True, Back.RED)
        self._num_checks += 1

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
        total_checks = 0
        total_checks_passed = 0
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
                    total_checks += results['num_checks']
                    total_checks_passed += results['num_checks_passed']
                    total_execution_time += results['execution_time']
                    self.log("_" * ExternalProgramTestSuite._num_formatting_chars)
                    total_num_suites += 1
            # print cumulative total pass/fail            
            if total_num_tests > 0:
                if total_checks > 0:
                    percentage_checks_passed = (total_checks_passed * 1.0 / total_checks) * 100
                else:
                    percentage_checks_passed = 0                     
                self.log("TOTALS");
                self.log("." * ExternalProgramTestSuite._num_formatting_chars)                      
                percentage_passed = (total_suites_passed * 1.0 / total_num_suites) * 100
                self.log("%d/%d (%.2f%%) SUITES\n%d/%d (%.2f%%) TESTS\n%d/%d (%.2f%%) CHECKS\nin %.4f seconds"
                         %(total_suites_passed,
                           total_num_suites,
                           percentage_passed,
                           total_num_passed,
                           total_num_tests,
                           (total_num_passed * 1.0 / total_num_tests) * 100,
                           total_checks_passed,
                           total_checks,
                           percentage_checks_passed,
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