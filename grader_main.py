import unittest
import graderunittest
import argparse
import importlib
import io
import htmlgenerator
import sys
import gc

# try:
#     import settings
#     if settings.HTML_TRACEBACK:
#         import cgitb
#         sys.excepthook = cgitb.Hook(file=sys.stderr, format="html", display=1, context=5)
# except:
#     pass


def _load_tests_from_module_name(module_name):
    """
    Load all tests from the named module into a TestSuite and return it.
    """
    loader = unittest.defaultTestLoader
    test_module = importlib.import_module(module_name)
    return loader.loadTestsFromModule(test_module)


def _run_suite(test_suite):
    """
    Run given TestSuite with a runner gathering points and results into a stringstream and return the TestResult.
    """
    runner = graderunittest.PointsTestRunner(stream=io.StringIO(), verbosity=2)
    return runner.run(test_suite)


def _run_test_modules(modules_data):
    """
    Load and run all test modules and their descriptions given as parameter.
    Return a list of TestResult objects.
    """
    results = []
    for module_name, test_description in modules_data:
        suite = _load_tests_from_module_name(module_name)
        result = _run_suite(suite)
        result.user_data = {"test_description": test_description}
        results.append(result)
    return results


def main(settings):
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_parameters")
    args = parser.parse_args()

    test_parameters = args.test_parameters

    # TODO settings/parameters
    modules_data = None
    error_template = None
    feedback_template = None

    # If there are any exceptions during running, render the traceback into HTML using the provided error_template.
    try:
        results = _run_test_modules(modules_data)
    except Exception as error:
        if isinstance(error, MemoryError):
            # Testing used up all provided memory.
            # Attempt to clean up some room for rendering HTML.
            # Not guaranteed to succeed as the memory limit set into the mooc grader sandbox might have been exceeded.
            gc.collect()
        error_data = {
            "type": error.__class__.__name__,
            "message": str(error)
        }
        html_errors = htmlgenerator.errors_as_html(error_data, error_template)
        print(html_errors, file=sys.stderr)
        sys.exit(1)

    html_results = htmlgenerator.results_as_html(results, feedback_template)

    total_points = total_max_points = 0
    for result in results:
        total_points += result.points
        total_max_points += result.max_points

    # A+ gives these points to the student if the two last lines written to stdout after grading are in the following format.
    print("TotalPoints: {}\nMaxPoints: {}".format(total_points, total_max_points))

    # Show feedback.
    print(html_results, file=sys.stderr)

