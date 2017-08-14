"""
Python grader test runner with pre-grade validation and post-grade feedback styling.
"""
import argparse
import gc
import importlib
import io
import sys
import unittest

import yaml

import graderunittest
import htmlgenerator
import validation


class GraderUtilsError(Exception): pass

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
        result.test_description = test_description
        results.append(result)
    return results


def run_blacklist_validation(blacklists, error_template):
    """
    Search for blacklisted strings as defined in the blacklist objects given as arguments.
    If any match is found, render them using the HTML template for errors and return True.
    """
    blacklist_matches = []

    for blacklist in blacklists:
        if blacklist["type"] == "plain_text":
            get_matches = validation.get_plain_text_blacklist_matches
        elif blacklist["type"] == "python":
            get_matches = validation.get_python_blacklist_matches
        else:
            raise GraderUtilsError("A blacklist was given but validation for '{}' is not defined.".format(blacklist["method"]))

        blacklist_matches.append(get_matches(blacklist))

    # Found matches
    if blacklist_matches:
        error_data = {"blacklist_matches": blacklist_matches}
        errors_html = htmlgenerator.errors_as_html(error_data, error_template)
        print(errors_html, file=sys.stderr)
        return True

    # No matches found
    return False


def main(test_modules_data, error_template=None,
         feedback_template=None, blacklists=None):
    """
    Main runner that:
        - (Optional) Checks for blacklisted matches and returns 1 if matches are found.
        - Runs each module in test_modules_data with unittest.
        If there are no errors:
            - Writes the total result of all test results into stdout for A+ to retrieve the points.
            - Renders the test result objects as HTML using the feedback_template (or a default template if none is given).
            - Writes the rendered HTML into stderr.
            - Returns 0
        If there are errors:
            - Renders the errors as HTML using the error_template (or a default template if none is given).
            - Writes the rendered HTML into stderr.
            - Returns 1
    """
    if blacklists and run_blacklist_validation(blacklists, error_template):
        # At least one file contained blacklisted strings.
        return 1

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
        return 0

    except Exception as error:
        if isinstance(error, MemoryError):
            # Testing used up all provided memory.
            # Attempt to clean up some room for rendering errors as HTML.
            gc.collect()
        error_data = {
            "error": {
                "type": error.__class__.__name__,
                "message": str(error),
                "object": error
            }
        }
        errors_html = htmlgenerator.errors_as_html(error_data, error_template)
        print(errors_html, file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
            "config_file",
            type=str,
            help="Path to a YAML-file containing grading settings.",
    )
    parser.add_argument(
            "--debug",
            type=bool,
            default=False,
            help="By default, exceptions related to improperly configured tests are catched and hidden to prevent course information to be shown to the user. Using this flag will let all such exceptions through."
    )
    args = parser.parse_args()

    if args.debug:
        print("<h1>Warning: Graderutils is running in debug mode, all configuration related exceptions will be shown to the user!</h1>", file=sys.stderr)
    settings_file_path = args.settings_file

    try:
        with open(settings_file_path, encoding="utf-8") as settings_file:
            settings = yaml.safe_load(settings_file)
        sys.exit(main(**settings))

    except:
        if args.debug:
            raise
        else:
            print("<h1>Something went wrong in the grader...</h1>", file=sys.stderr)
            sys.exit(1)

