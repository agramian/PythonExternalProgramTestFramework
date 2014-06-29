#!/usr/bin/python
# Filename: external_program_test_framework.py

import sys
import os
import shutil
import timeit
from sets import Set
from assert_variable_type import *
from run_subprocess import run_subprocess, TimeoutError

class ExternalProgramTestSuite:
    """ A Class for creating Test Suites with
    test cases which call external programs 
    """
    _test_suites = {}
    _num_formatting_chars = 100
    _all_log_files = Set()
    _has_run = False    
    
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
                                                                         'execution_time': 0}
            else:
                raise ValueError('A suite with the name "%s" already exists. '
                                 'Please rename one of suite classes or pass a unique "suite_name" argument to one or both of the constructors.')
        except ValueError as e:
             raise Exception('ERROR\n[%s] %s' %(type(e).__name__, e))
    
    def log(self, print_string, error=False):
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
        # print the output to the stdout
        print(print_string)
        
    def _set_suite_defaults(self):
        """Set the suite variables to their defaults
        """
        # set the default suite variables
        # default suite name and description
        self.suite_name = None        
        self.suite_description = None
        # number of passed test cases
        self.num_tests_passed = 0
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
        # subprocess timout
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
                self.log("TEST SUITE: %s" %suite_name)
                if self.suite_description:
                    self.log("Description: %s" %(str(ExternalProgramTestSuite._test_suites[suite_name]['description'])))            
            self.log("-" * ExternalProgramTestSuite._num_formatting_chars)
            self.log("CASE: %s" %case)
            # validate args and run the test case
            try:
                self._validate_test_arguments()
                self._run_test_case()
            except Exception as e:
                self.log('ERROR\n[%s] %s' %(type(e).__name__, e), True)
            ExternalProgramTestSuite._has_run = True         
        self.log( "_" * ExternalProgramTestSuite._num_formatting_chars)
        # print test result
        num_tests = len(self.test_cases)
        try:      
            self.log("RESULT: %d/%d (%.2f%%) PASSED"
                  %(self.num_tests_passed,
                    num_tests,
                    (self.num_tests_passed * 1.0 / num_tests) * 100))
        except Exception as e:
            self.log('ERROR\n[%s] %s' %(type(e).__name__, e), True)
        self.log("=" * ExternalProgramTestSuite._num_formatting_chars)
        # add test result to class static suite list
        ExternalProgramTestSuite._test_suites[self.suite_name]['num_tests'] = num_tests
        ExternalProgramTestSuite._test_suites[self.suite_name]['num_passed'] = self.num_tests_passed        

    def _run_test_case(self):
        """
        Run an individual test case
        """
        # print description if any
        if self.description:
            self.log("Description: %s" %(str(self.description)))
        self.log("-" * ExternalProgramTestSuite._num_formatting_chars)
        try:
            process, execution_time = run_subprocess(self.executable_command,
                                                     self.command_arguments,
                                                     self.print_process_output,
                                                     self.stdout_file,
                                                     self.stderr_file,
                                                     self.timeout)

            stdout, stderr = process.communicate()                              
            if process.returncode == self.expected_return_value:
                self.log('PASS')
                self.num_tests_passed += 1
            else:
                self.log('FAIL')
            self.log("%.4f seconds" %(execution_time))
        except OSError as e:
            self.log('ERROR\n[%s] %s' %(type(e).__name__, e), True)
        except ValueError as e:
            self.log('ERROR\n[%s] %s' %(type(e).__name__, e), True)
        except TimeoutError as e:
            self.log('ERROR\n[%s] %s' %(type(e).__name__, e), True)
        # suite setup routine
        if not self.skip_teardown:
            self._end_case()

    @staticmethod
    def run_all():
        """
        Run all registered test suites
        """
        ExternalProgramTestSuite._has_run = False
        for suite, properties in ExternalProgramTestSuite._test_suites.items():
            ExternalProgramTestSuite.run(properties['self'], properties['name'])
        
    @staticmethod
    def print_total_results():
        """
        Print the cumulative results from all suites
        """        
        self.log("*" * ExternalProgramTestSuite._num_formatting_chars)
        self.log("ALL SUITES RESULTS")
        self.log("*" * ExternalProgramTestSuite._num_formatting_chars)
        # print results for each suite on one line
        # keep track of test results info for totals
        total_num_tests = 0
        total_num_passed = 0
        total_suites_passed = 0
        total_num_suites = len(ExternalProgramTestSuite._test_suites)
        for suite, results in ExternalProgramTestSuite._test_suites.items():
            try:      
                print ("%s: %d/%d (%.2f%%) tests PASSED"
                        %(suite,
                          results['num_passed'],
                          results['num_tests'],
                          (results['num_passed'] * 1.0 / results['num_tests']) * 100))
                total_num_tests += results['num_tests']
                total_num_passed += results['num_passed']
                if total_num_tests > 0 and total_num_tests == total_num_passed: 
                    total_suites_passed += 1
                self.log("-" * ExternalProgramTestSuite._num_formatting_chars)
                # print cumulative total pass/fail
                print ("TOTALS:\n%d/%d (%.2f%%) suites PASSED\n%d/%d (%.2f%%) tests PASSED\n"
                        %(total_suites_passed,
                          total_num_suites,
                          (total_suites_passed * 1.0 / total_num_suites) * 100,
                          total_num_passed,
                          total_num_tests,
                          (total_num_passed * 1.0 / total_num_tests) * 100))       
                self.log("*" * ExternalProgramTestSuite._num_formatting_chars)
            except Exception as e:
                self.log('ERROR\n[%s] %s' %(type(e).__name__, e), True)