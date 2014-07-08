from external_program_test_framework import *

class Bash(ExternalProgramTestSuite):
    """ Bash test suite
    """
    def setup(self):
        print('setup')
        
    def teardown(self):
        print('teardown')

    def valid_pwd_command(self):
        if (os.name is "nt"):
            self.check_subprocess("cmd", ["/c", "dir"], 0)
        else:
            self.check_subprocess("pwd", [], 0)

    def invalid_ls_command(self):
        self.skip_setup = True
        self.skip_teardown = True
        if (os.name is "nt"):
            self.check_subprocess("cmd", ["/c", "0"], 1)
        else:
            self.check_subprocess("ls", ["0"], 1)

def example_fixture():
    def setup():
        print 'fixture setup'
    def teardown():
        print 'fixture teardown'
    return setup, teardown

class Dummy(ExternalProgramTestSuite):
    def setup(self):
        print('setup')
    
    def teardown(self):
        print('teardown')
    #@skip_teardown  
    @name(1)
    @timelimit('a')
    @description("launch the external SUT program and verify that it returns 0")
    @fixture(example_fixture)
    def valid_sut_launch(self):
        self.check_subprocess("pwd", [], 0)

    @fixture(example_fixture)
    @timelimit(1)
    def valid_pwd_command(self):
        if (os.name is "nt"):
            self.check_subprocess("cmd", ["/c", "cd"], 0)
        else:
            self.check_subprocess("pwd", [], 0)         

class HttpGet(ExternalProgramTestSuite):
    def google(self):
        self.check_subprocess("curl", ["http://www.google.com"], 0)     
        
def main():
    #ExternalProgramTestSuite.color_output_text = False
    #Dummy(suite_name='dummy1').run()
    Bash(stdout_log_file='run.log', suite_description="Bash Unit Tests", suite_name="Bash")
    HttpGet().run()
    Dummy(suite_description="dummy unit tests", suite_timelimit=1)
    ExternalProgramTestSuite.run_all()
"""
import xhtml2pdf
import six
import html5lib
import markupsafe
import jinja2
from jinja2 import Template

from xhtml2pdf import pisa             # import python module

# Define your data
sourceHtml = "<html><body><p>To PDF or not to PDF<p></body></html>"
outputFilename = "test.pdf"

# Utility function
def convertHtmlToPdf(sourceHtml, outputFilename):
    # open output file for writing (truncated binary)
    resultFile = open(outputFilename, "w+b")

    # convert HTML to PDF
    pisaStatus = pisa.CreatePDF(
            sourceHtml,                # the HTML to convert
            dest=resultFile)           # file handle to recieve result

    # close output file
    resultFile.close()                 # close output file

    # return True on success and False on errors
    return pisaStatus.err
"""
if __name__ == "__main__":    
    main()
    """
    template = Template('Hello {{ name }}!')
    print template.render(name='John Doe')
    pisa.showLogging()
    convertHtmlToPdf(sourceHtml, outputFilename)
    """