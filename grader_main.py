import unittest
import graderunittest
import argparse
import io
import htmlgenerator
import sys

# import test_config

from collections import OrderedDict

# OrderedDict instead of dict to ensure public tests are executed first
TEST_NAMES = OrderedDict([
    ("public_tests.py", "Local tests"),
    ("grader_tests.py", "Grader tests")
])


def run_points_test(test_name_pattern):
    """Discover test with exact filename test_name_pattern and run tests collecting points.

    @param (str) test_name_pattern: Filename of a module containing tests.
    @return (TextTestResult): A TestResult object after tests discovered
        with pattern test_name_pattern have been run.
    """

    stream = io.StringIO()
    runner = graderunittest.PointsTestRunner(stream=stream, verbosity=2)
    suite = unittest.defaultTestLoader.discover(
        start_dir=".",
        pattern=test_name_pattern,
        top_level_dir="."
    )
    # TODO instead of monkey patching, pass state during test loading
    import pprint
    for case in suite._tests:
        case.SQLMODEL = "SELECT * FROM WORLD"
        print(case)
        pprint.pprint(dir(case))
        print()
    result = runner.run(suite)
    return result


def run_tests_and_get_results(test_names, extra_state):
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

    # Name of the submitted module, for example primes.py
    # Used for formatting traceback messages
    # submit_module_name = test_config.MODULE["name"] + ".py"
    submit_module_name = "asd"

    for test_filename, test_type_name in test_names.items():
        result = run_points_test(test_filename) # TODO extra_state

        result.test_type_name = test_type_name
        result.submit_module_name = submit_module_name

        results_data["result_objects"].append(result)
        results_data["total_points"] += result.points
        results_data["total_max_points"] += result.max_points

    return results_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra_state")
    args = parser.parse_args()

    extra_state = args.extra_state

    #TODO argparse to accept print nulling by wrapping stdout and stderr into os.devnull

    # Run tests with the custom test runner which gathers points.
    import gc
    try:
        results = run_tests_and_get_results(TEST_NAMES, extra_state)
    except MemoryError:
        # Running the tests used up all memory allocated for the sandbox,
        # cleanup everything that caused the error,
        # print error feedback and mark the solution as an error.
        gc.collect()
        errors = {"memory_error": "Too much memory was used during testing.\n\nDoes your solution use data structures in an inefficient way or where they are not needed?"}
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

