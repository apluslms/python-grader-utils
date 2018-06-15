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


class GraderUtilsError(Exception): pass


from graderutils import graderunittest
from graderutils import htmlformat
from graderutils import validation


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
    for test_module in test_modules_data:
        test_module_name = test_module["module"]
        suite = _load_tests_from_module_name(test_module_name)
        result = _run_suite(suite)
        result.test_key = test_module_name
        result.test_description = test_module["description"]
        results.append(result)
    return results


def main(test_modules_data, error_template, feedback_template, no_default_css, feedback_out, points_out, exceptions_to_hide):
    """TODO docs"""
    # If there are any exceptions during running, render the traceback into HTML using the provided error_template.
    try:
        if test_modules_data:
            results = _run_test_modules(test_modules_data)
            total_points = total_max_points = 0
            for result in results:
                total_points += result.points
                total_max_points += result.max_points
            html_results = htmlformat.test_results_as_html(results, feedback_template, no_default_css, exceptions_to_hide)
        else:
            total_points = total_max_points = 1
            html_results = htmlformat.no_tests_html(feedback_template, no_default_css)

        # Show feedback.
        print(html_results, file=feedback_out)

        # A+ gives these points to the student if the two last lines written to stdout after grading are in the following format.
        print("TotalPoints: {}\nMaxPoints: {}".format(total_points, total_max_points), file=points_out)

    except MemoryError:
        # Testing used up all provided memory.
        # Attempt to clean up some room for rendering errors as HTML.
        gc.collect()
        raise
    else:
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
            "config_file",
            type=str,
            help="Path to a YAML-file containing grading settings. Example settings provided in graderutils/test_config.yaml",
    )
    parser.add_argument(
            "--allow_exceptions",
            action="store_true",
            default=False,
            help="By default, exceptions related to improperly configured tests are catched and hidden behind a generic error message to prevent possible grader test information to be shown to the user. This flag lets them through unformatted."
    )
    parser.add_argument(
            "--container",
            action="store_true",
            help="This flag should be used when running graderutils inside docker container based on apluslms/grading-base"
    )
    args = parser.parse_args()

    feedback_out = sys.stdout if args.container else sys.stderr
    points_out = sys.stdout

    if args.allow_exceptions:
        debug_warning = "Graderutils main module called with the <code>--allow_exceptions</code> flag, all graderutils exceptions will be shown to the user!"
        print(htmlformat.wrap_div_alert(debug_warning), file=feedback_out)

    # Starting from here, hide infrastructure exceptions (not validation exceptions) if args.allow_exceptions is given and True.
    try:
        config_file_path = args.config_file

        with open(config_file_path, encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        error_template = config.get("error_template", None)
        feedback_template = config.get("feedback_template", None)
        no_default_css = config.get("no_default_css", False)
        exceptions_to_hide = config.get("exceptions_to_hide", [])
        test_modules_data = config.get("test_modules_data", [])
        if not test_modules_data:
            test_modules_data = config.get("test_modules", [])

        if "validation" in config:
            errors = validation.get_validation_errors(config["validation"])
            # Pre-grading validation failed, print errors and exit.
            if errors:
                print(htmlformat.errors_as_html(errors, error_template, no_default_css), file=feedback_out)
                sys.exit(1)

        sys.exit(main(test_modules_data, error_template, feedback_template, no_default_css, feedback_out, points_out, exceptions_to_hide))

    except Exception as e:
        if args.allow_exceptions or args.container:
            raise
        else:
            error_msg = "Something went wrong during the grader tests... Please contact course staff."
            print(htmlformat.wrap_div_alert(error_msg), file=feedback_out)
            sys.exit(1)

