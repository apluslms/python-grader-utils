import argparse
import gc
import importlib
import io
import sys
import unittest

import yaml

import graderunittest
import htmlgenerator

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


def _run_test_modules(test_modules_data):
    """
    Load and run all test modules and their descriptions given as parameter.
    Return a list of TestResult objects.
    """
    results = []
    for module_name, test_description in test_modules_data:
        suite = _load_tests_from_module_name(module_name)
        result = _run_suite(suite)
        result.user_data = {"test_description": test_description}
        results.append(result)
    return results


# TODO: exceptions thrown during blacklist checks will be shown to the user
def main(test_modules_data, error_template=None,
         feedback_template=None, blacklist=None):
    # Check for blacklisted names if a blacklist is supplied.
    if blacklist is not None:
        blacklist_matches = validation.get_blacklist_matches(blacklist)
        # If matches are found, show feedback with the error template and return.
        if blacklist_matches:
            error_data = {"blacklist_matches": blacklist_matches}
            errors_html = htmlgenerator.errors_as_html(error_data, error_template)
            print(errors_html, file=sys.stderr)
            return 1 if blacklist.get("expect_success", False) else 0

    # If there are any exceptions during running, render the traceback into HTML using the provided error_template.
    try:
        results = _run_test_modules(test_modules_data)

        total_points = total_max_points = 0
        for result in results:
            total_points += result.points
            total_max_points += result.max_points

        # A+ gives these points to the student if the two last lines written to stdout after grading are in the following format.
        print("TotalPoints: {}\nMaxPoints: {}".format(total_points, total_max_points))

        # Show feedback.
        html_results = htmlgenerator.results_as_html(results, feedback_template)
        print(html_results, file=sys.stderr)

    except Exception as error:
        if isinstance(error, MemoryError):
            # Testing used up all provided memory.
            # Attempt to clean up some room for rendering errors as HTML.
            gc.collect()
        error_data = {
            "error": {
                "type": error.__class__.__name__,
                "message": str(error)
            }
        }
        errors_html = htmlgenerator.errors_as_html(error_data, error_template)
        print(errors_html, file=sys.stderr)
        return 1

    else:
        return 0


# TODO: wrap main runner into a try-except block with debug switch
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python grader test runner with pregrade validation and postgrade feedback styling.")
    parser.add_argument(
            "--config_file",
            type=str,
            help="Path to a YAML-file containing grading settings. Defaults to 'settings.yaml' found in the package source.",
    )
    args = parser.parse_args()

    settings_file_path = args.settings_file

    with open(settings_file_path, encoding="utf-8") as settings_file:
        settings = yaml.load(settings_file)

    sys.exit(main(**settings))

