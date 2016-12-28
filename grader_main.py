import unittest
import graderunittest
import argparse
import importlib
import io
import htmlgenerator
import sys

try:
    import settings
    if settings.HTML_TRACEBACK:
        import cgitb
        sys.excepthook = cgitb.Hook(file=sys.stderr, format="html", display=1, context=5)
except:
    pass

from collections import OrderedDict

# TODO should be retrieved from a conf file
# OrderedDict instead of dict to ensure public tests are executed first
TEST_NAMES = OrderedDict([
    # ("public_tests", "Local tests"),
    ("grader_tests", "Grader tests"),
    ("coverage_tests", "Coverage tests")
])


def run_points_test(module_name, test_parameters=None):
    """Import 'module_name' which contains TestCase instances to be run.
    If test_parameters is defined, parse it using ast.literal_eval and
    create all test cases with the parsed test_parameters as their instance variable.
    Finally, run all tests and return a TestResult object.

    @param (str) test_name_pattern: Filename of a module containing tests.
    @param test_parameters: optional, arbitrary parameters which should be available
        as instance variables of every test_case instantiated from 'module_name' tests.
    @return (TextTestResult): A TestResult object after tests discovered
        with pattern test_name_pattern have been run.
    """
    runner = graderunittest.PointsTestRunner(stream=io.StringIO(), verbosity=2)
    if test_parameters:
        loader = graderunittest.ParameterTestCaseLoader(test_parameters)
    else:
        loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()

    test_module = importlib.import_module(module_name)
    suite = loader.loadTestsFromModule(test_module)

    result = runner.run(suite)

    return result


def run_tests_and_get_results(test_names, test_parameters):
    """Iterate test_names, running tests for all its keys and return a dictionary containing a list of result objects, total points and max points for all tests.
    Note that this function adds to attributes to the test objects: test_type_name and module_filename (val-key in test_names).
    @param (dict) test_names: Dictionary with keys being filenames
        that should be discovered for testing and the corresponding values being
        names of the tests which are shown in the grading result.
    @return Dictionary containing a list of all test results, total points and max points.
    """

    results_data = {
        "result_objects": [],
        "total_points": 0,
        "total_max_points": 0
    }

    # TODO cleanup try-except chewing gum by moving obsolete
    # test_config functionality into a rst directive
    try:
        import test_config
        # Name of the submitted module, for example primes.py
        # Used for formatting traceback messages
        submit_module_name = test_config.MODULE["name"] + ".py"
    except ImportError:
        submit_module_name = None

    for test_filename, test_type_name in test_names.items():
        try:
            result = run_points_test(test_filename, test_parameters)
        except ImportError:
            #This test isn't configured for this exercise, skip
            continue

        result.test_type_name = test_type_name
        result.submit_module_name = submit_module_name

        results_data["result_objects"].append(result)
        results_data["total_points"] += result.points
        results_data["total_max_points"] += result.max_points

    return results_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_parameters")
    args = parser.parse_args()

    test_parameters = args.test_parameters

    # Run tests with the custom test runner which gathers points.
    import gc
    try:
        results = run_tests_and_get_results(TEST_NAMES, test_parameters)
    except MemoryError:
        # Running the tests used up all memory allocated for the sandbox,
        # cleanup everything that caused the error,
        # print error feedback and mark the solution as an error.
        gc.collect()
        errors = {"memory_error": "Too much memory was used during testing"}
        html_errors = htmlgenerator.errors_as_html(errors)
        print(html_errors, file=sys.stderr)
        sys.exit(1)

    html_results = htmlgenerator.results_as_html(results["result_objects"])

    total_points = results["total_points"]
    total_max_points = results["total_max_points"]
    # The MOOC grader gives points based on this output line
    print("TotalPoints: {}\nMaxPoints: {}".format(total_points, total_max_points))

    # Using the MOOC grader action sandbox_python_test, stderr is shown as stdout
    print(html_results, file=sys.stderr)

