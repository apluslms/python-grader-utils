"""
Extensions for unittest tests.
"""
import contextlib
import functools
import importlib
import io
import itertools
import logging
import re
import signal
import sys
import time
import unittest

from graderutils import GraderUtilsError
from graderutils import remote
from graderutils.remote import GraderConnClosedError


logger = logging.getLogger("warnings")

testmethod_timeout = 60

'''Maximum string length of the stderr stream for one test module.
If the output is longer, the rest is not included in the grading payload.
The python_import validation task also uses this maximum limit.'''
TEST_MODULE_STDERR_MAX_SIZE = 50000


class PointsTestResult(unittest.TextTestResult):
    """
    Adds storing of successes for text result.
    """

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []

    def patch_message(self, case, key):
        """
        If the finished test method `case` had a user-defined short message, extract it from the points data and shove it into `case`.
        """
        if hasattr(case, "graderutils_points"):
            case.graderutils_msg = case.graderutils_points["messages"][key]

    def addSuccess(self, test, *args, **kwargs):
        super().addSuccess(test, *args, **kwargs)
        self.successes.append(test)
        self.patch_message(test, "on_success")

    def addFailure(self, test, *args, **kwargs):
        super().addFailure(test, *args, **kwargs)
        self.patch_message(test, "on_fail")

    def addError(self, test, *args, **kwargs):
        super().addError(test, *args, **kwargs)
        self.patch_message(test, "on_error")


def points(points_on_success, msg_on_success="The test was a success!", msg_on_fail="The test failed, reason:", msg_on_error="An error occurred:"):
    """
    Return a decorator for unittest.TestCase test methods, which patches each test method with a graderutils_points attribute.
    This has to be the uppermost decorator if multiple decorators are used on a test method.
    """
    graderutils_points = {
        "points": 0,
        "max_points": points_on_success,
        "messages": {
            "on_success": msg_on_success,
            "on_fail": msg_on_fail,
            "on_error": msg_on_error,
        }
    }
    def points_decorator(testmethod):
        @functools.wraps(testmethod)
        def points_patching_testmethod(case, *args, **kwargs):
            case.graderutils_points = graderutils_points
            return run_testmethod(testmethod, case, *args, **kwargs)
        return points_patching_testmethod
    return points_decorator


def get_points(test_case):
    return test_case.graderutils_points["points"], test_case.graderutils_points["max_points"]


def check_points(test_case):
    if not hasattr(test_case, "graderutils_points"):
        logger.warning(
            "Found a test case with no points defined: {!r}.".format(test_case) +
            " Use the graderunittest.points decorator to define non-zero points for test cases."
        )
        return False
    return True


def set_full_points(test_case):
    """
    Award full points for a given test case by updating graderutils_points["points"] with max points of the test case.
    Return the amount of points set.
    """
    _, max_points = get_points(test_case)
    test_case.graderutils_points["points"] = max_points
    return max_points


class PointsTestRunner(unittest.TextTestRunner):
    """
    unittest.TextTestRunner that extract points from test methods.
    Points are added to unittest.TestCase test method with the points decorator, e.g.
    @graderunittest.points(100)
    def test_and_get_100_points(self):
        pass
    """
    points_pattern = re.compile(".*\((\d+)p\)$")

    def _makeResult(self):
        return PointsTestResult(self.stream, self.descriptions, self.verbosity)

    def handle_points(self, result):
        """
        For all test case results, set points and max points according to final test state.
        Successes get points == max_points, while failures and errors get points == 0.
        Return a 2-tuple of (points, max_points) for all points in the test suite.
        """
        # Award points, while computing total points for this test suite
        suite_points = suite_max_points = 0
        for success in result.successes:
            if not check_points(success):
                continue
            points = set_full_points(success)
            suite_points += points
            suite_max_points += points
        for nosuccess, _ in itertools.chain(result.failures, result.errors):
            if not check_points(nosuccess):
                continue
            _, max_points = get_points(nosuccess)
            suite_max_points += max_points
        return suite_points, suite_max_points

    def run(self, test):
        """Run the result object through all test cases in a test suite."""
        result = unittest.TextTestRunner.run(self, test)
        result.points, result.max_points = self.handle_points(result)
        return result


def timeout(timeout=testmethod_timeout):
    """
    Return a decorator for unittest.TestCase test methods, which patches each test method with a graderutils_timeout attribute.
    Using this decorator allows each test method to have their own timeout.
    Make sure that the points decorator is above this one or the default testmethod_timeout will be used.
    """
    def timeout_decorator(testmethod):
        testmethod.graderutils_timeout = timeout
        @functools.wraps(testmethod)
        def timeout_patching_testmethod(*args, **kwargs):
            return testmethod(*args, **kwargs)
        return timeout_patching_testmethod
    return timeout_decorator


# TimeoutExit will not be suppressed by libraries that do `except Exception: pass` because it inherits from BaseException
class TimeoutExit(BaseException):
    pass


def result_or_timeout(timed_function, args=(), kwargs=None, timeout=1, timer=time.perf_counter):
    """
    Call timed_function with args and kwargs and benchmark the execution time with timer.
    If resulting time was less than timeout, return the resulting time and the value returned by timed_function.
    If the resulting time was larger or equal to timeout, terminate execution of timed_function and return timeout and None.
    Adapted from: http://stackoverflow.com/a/13821695
    """
    if kwargs is None:
        kwargs = dict()

    def handler(*h_args, **h_kwargs):
        raise TimeoutExit()

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)

    try:
        start_time = timer()
        result = timed_function(*args, **kwargs)
        running_time = timer() - start_time
    except TimeoutExit:
        running_time = timeout
        result = None
    finally:
        signal.alarm(0)

    return running_time, result


def run_testmethod(testmethod, case, *args, **kwargs):
    """
    Patch test method with a graderutils_running_time attribute and run it while recording the running time.
    """
    case.graderutils_running_time = 0.0
    result = None
    # SystemExit and KeyboardInterrupt kill grader if not caught
    try:
        # Check if the timeout decorator was used to set a timeout for this test method
        timeout = getattr(testmethod, "graderutils_timeout", testmethod_timeout)
        if remote.conn:
            # Update rpyc timeout so that it doesn't timeout before result_or_timeout
            remote.conn._config.update({"sync_request_timeout": timeout})
            # Check if remote connection was closed earlier
            conn_closed_earlier = remote.conn.closed
        start_time = time.perf_counter()
        try:
            running_time, result = result_or_timeout(testmethod, (case, *args), kwargs, timeout)
        except:
            # Record running time in case of an exception
            case.graderutils_running_time = time.perf_counter() - start_time
            raise
        case.graderutils_running_time = running_time
        if running_time == timeout and result is None:
            if remote.conn and not remote.conn.closed:
                # Close remote connection, student process is stuck in an infinite loop or it runs too slowly.
                # Rest of the tests run after this will fail with GraderConnClosedError.
                remote.conn.close()
            raise TimeoutError(
                "Test timed out after {} seconds. Your code may be "
                "stuck in an infinite loop or it runs very slowly.".format(timeout)
            )
    except EOFError as e: # Rpyc raises an EOFError when connection to the remote server does not work
        if remote.conn and conn_closed_earlier:
            raise GraderConnClosedError(
                "Grader cannot complete this test because connection to the child process was "
                "closed earlier. Your code may have got stuck in an infinite loop, it runs very slowly "
                "or KeyboardInterrupt was raised."
            ) from None
        elif remote.conn and str(e) in ["[Errno 32] Broken pipe", "stream has been closed"]:
            # Student code most likely raised KeyboardInterrupt.
            # str(e) is "[Errno 32] Broken pipe" if it was raised inside a function.
            # str(e) is "stream has been closed" if it was raised on module level.
            # Close remote connection if it is still open (in case of broken pipe).
            # Rest of the tests run after this will fail with GraderConnClosedError.
            remote.conn.close()
            raise GraderUtilsError("Grader does not support raising KeyboardInterrupt.") from None
        # Raise the EOFError if it was not caused by remote connection being closed
        raise
    except SystemExit as e:
        raise GraderUtilsError("Grader does not support the usage of sys.exit(), exit() or quit().") from e
    except KeyboardInterrupt as e: # Non-rpyc KeyboardInterrupt
        raise GraderUtilsError("Grader does not support raising KeyboardInterrupt.") from e

    return result


class ModuleLevelError(GraderUtilsError):
    def __init__(self, other):
        self.cause = other


def run_test_suite_in_named_module(module_name):
    """
    Load all test cases as a test suite from a test module with the given name.
    Run the loaded test suite with a runner that gathers points, traceback objects, and stdout/err into a stringstream.
    Return a PointsTestResult containing the results.
    """
    loader = unittest.defaultTestLoader
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            # Module output must be suppressed during import and run, since grading json is printed to stdout as well
            with contextlib.redirect_stdout(None):
                try: # Catch module-level errors
                    test_module = importlib.import_module(module_name)
                except BaseException as e:
                    raise ModuleLevelError(e)
                test_suite = loader.loadTestsFromModule(test_module)
                # Redirect output to string stream and increase verbosity
                runner = PointsTestRunner(stream=io.StringIO(), verbosity=2)
                # Test suite running time is recorded
                start_time = time.perf_counter()
                result = runner.run(test_suite)
                running_time = time.perf_counter() - start_time
    finally:
        # Limit maximum size of the stderr output of this test group
        sys.stderr.write(err.getvalue()[:TEST_MODULE_STDERR_MAX_SIZE])

    return result, running_time


# disgusting monkey patch hacks

# TODO
class ParameterTestCaseLoader(unittest.TestLoader):
    """
    Initializes test cases with arbitrary extra parameters.
    """

    def __init__(self, test_parameters):
        super().__init__()
        self.test_parameters = test_parameters

    def loadTestsFromTestCase(self, parameterTestCaseClass):
        if issubclass(parameterTestCaseClass, unittest.suite.TestSuite):
            raise TypeError("Test cases should not be derived from "
                            "TestSuite. Maybe you meant to derive from "
                            "TestCase?")
        testCaseNames = self.getTestCaseNames(parameterTestCaseClass)
        if not testCaseNames and hasattr(parameterTestCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        test_instances = (parameterTestCaseClass(name, self.test_parameters) for name in testCaseNames)
        loaded_suite = self.suiteClass(test_instances)
        return loaded_suite

# TODO
class ParameterTestCase(unittest.TestCase):
    """
    Inherit this to access the config data.
    """

    def __init__(self, name, test_config_name):
        super().__init__(name)
        from plain_text_validator import read_yaml
        self.test_config_data = read_yaml(test_config_name)
