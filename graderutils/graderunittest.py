"""
Extensions for unittest tests.
"""
import functools
import importlib
import io
import itertools
import logging
import re
import signal
import time
import unittest


logger = logging.getLogger("warnings")


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


def points(points_on_success, msg_on_success='', msg_on_fail='', msg_on_error=''):
    """
    Return a decorator for unittest.TestCase test methods, which patches each test method with a graderutils_points attribute.
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
            return testmethod(case, *args, **kwargs)
        return points_patching_testmethod
    return points_decorator


def get_points(test_case):
    return test_case.graderutils_points["points"], test_case.graderutils_points["max_points"]


def set_full_points(test_case):
    """
    Award full points for a given test case by updating graderutils_points["points"] with max points of the test case.
    Return the amount of points set.
    """
    _, max_points = get_points(test_case)
    test_case.graderutils_points["points"] = max_points
    return max_points


def check_deprecated_points_syntax(test_case):
    points_pattern = PointsTestRunner.points_pattern
    docstring = test_case.shortDescription().strip()
    if docstring:
        match = points_pattern.search(docstring)
        if match:
            msg = (
                "Found deprecated points syntax in test case {!r} in its docstring: {!r}. "
                .format(test_case, match.group(0)) +
                "Since version 3, points are no longer parsed from the docstrings. "
                "Consider replacing the docstring points with a decorated test method: e.g. `from graderutils.graderunittest import points` and then decorate {!r} with `@points({})`"
                .format(test_case, match.group(1)))
            logger.warning(msg)


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
            check_deprecated_points_syntax(success)
            points = set_full_points(success)
            suite_points += points
            suite_max_points += points
        for nosuccess, _ in itertools.chain(result.failures, result.errors):
            check_deprecated_points_syntax(nosuccess)
            _, max_points = get_points(nosuccess)
            suite_max_points += max_points
        return suite_points, suite_max_points

    def run(self, test):
        """Run the result object through all test cases in a test suite."""
        result = unittest.TextTestRunner.run(self, test)
        result.points, result.max_points = self.handle_points(result)
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


def run_test_suite_in_named_module(module_name):
    """
    Load all test cases as a test suite from a test module with the given name.
    Run the loaded test suite with a runner that gathers points, traceback objects, and stdout/err into a stringstream.
    Return a PointsTestResult containing the results.
    """
    loader = unittest.defaultTestLoader
    test_module = importlib.import_module(module_name)
    test_suite = loader.loadTestsFromModule(test_module)
    # Redirect output to string stream, increase verbosity, and retain all traceback objects
    runner = PointsTestRunner(stream=io.StringIO(), verbosity=2, tb_locals=True)
    result = runner.run(test_suite)
    return result


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
