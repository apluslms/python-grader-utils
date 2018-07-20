# Original from
# https://github.com/Aalto-LeTech/mooc-grader-course/blob/master/exercises/hello_python/graderunittest.py

import functools
import re
import signal
import time
import unittest


class _PointsTestResult(unittest.TextTestResult):
    """
    Adds storing of successes for text result.
    """

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []


    def addSuccess(self, test, *args, **kwargs):
        super().addSuccess(test, *args, **kwargs)
        if hasattr(test, "_points_data"):
            test._short_message = test._points_data["messages"]["on_success"]
        self.successes.append(test)

    def addFailure(self, test, *args, **kwargs):
        super().addFailure(test, *args, **kwargs)
        if hasattr(test, "_points_data"):
            test._short_message = test._points_data["messages"]["on_fail"]

    def addError(self, test, *args, **kwargs):
        super().addError(test, *args, **kwargs)
        if hasattr(test, "_points_data"):
            test._short_message = test._points_data["messages"]["on_error"]


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


def points(points_on_success, msg_on_success='', msg_on_fail='', msg_on_error=''):
    points_data = {
        "points": points_on_success,
        "messages": {
            "on_success": msg_on_success,
            "on_fail": msg_on_fail,
            "on_error": msg_on_error,
        }
    }
    def points_decorator(testmethod):
        @functools.wraps(testmethod)
        def points_patching_testmethod(case, *args, **kwargs):
            case._points_data = points_data
            return testmethod(case, *args, **kwargs)
        return points_patching_testmethod
    return points_decorator


class PointsTestRunner(unittest.TextTestRunner):
    """
    Prints out test grading points in addition to normal text test runner.
    Passing a test will grant the points added to the end of the test
    docstring in following format. (10p)
    """

    def _makeResult(self):
        return _PointsTestResult(self.stream, self.descriptions, self.verbosity)


    def get_points(self, result):
        """Parse points as integers and return a 2-tuple (points, max_points)."""
        # If a test case does not have a _points_data attribute, patched by the points-decorator, parse points from test case docstring for backwards compability
        # Search for (Np), where N is an integer
        point_re = re.compile('.*\((\d+)p\)$')
        def parse_points(case):
            if hasattr(case, "_points_data"):
                return case._points_data["points"]
            if case.shortDescription():
                match = point_re.search(case.shortDescription().strip())
            else:
                match = None
            return int(match.group(1)) if match else 0

        points = sum(parse_points(case) for case in result.successes)
        max_points = points\
            + sum(parse_points(case) for case, exc in result.failures)\
            + sum(parse_points(case) for case, exc in result.errors)

        return points, max_points


    def run(self, test):
        """Run the result object through all test cases."""
        result = unittest.TextTestRunner.run(self, test)
        result.points, result.max_points = self.get_points(result)
        return result


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
        raise TimeoutError()

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)

    try:
        start_time = timer()
        result = timed_function(*args, **kwargs)
        running_time = timer() - start_time
    except TimeoutError:
        running_time = timeout
        result = None
    finally:
        signal.alarm(0)

    return running_time, result


