"""
Python grader test runner with pre-grade validation and post-grade feedback styling.
"""
import argparse
import ast
import importlib
import io
import os
import sys
import traceback
import unittest
import logging

# Log deprecation warnings into a single, global stream
logger = logging.getLogger("warnings")
logger.addHandler(logging.StreamHandler(stream=io.StringIO()))
multiline_repr_prefix = "#MULTILINE-REPR#"

import yaml
import jsonschema


from graderutils import graderunittest, schemaobjects, validation
# TODO move to independent library
from graderutils import htmlformat


def parse_warnings(logger):
    """
    Return an iterator over all warnings written into the stream handler of a logger.
    """
    stream = logger.handlers[0].stream
    stream.seek(0)
    for warning in stream:
        if warning.startswith(multiline_repr_prefix):
            # warning contains a multiline string wrapped with repr, eval into string with newlines
            warning = ast.literal_eval(warning.lstrip(multiline_repr_prefix))
        yield warning.strip()


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


def run_test_groups(config):
    """
    Generator that runs all test groups specified by the given configuration and yields test group result dicts.
    """
    test_groups_data = config["test_groups"]
    for test_group in test_groups_data:
        # Load suite of tests from module
        test_suite = _load_tests_from_module_name(test_group["module"])
        # Run all test cases in suite, producing a result with points
        points_results = _run_suite(test_suite)
        # Convert all test results in group results into JSON schema serializable dicts
        group_result = schemaobjects.test_group_result_as_dict(points_results)
        group_result["name"] = test_group["display_name"]
        yield group_result


def do_everything(config):
    """
    Run test pipeline using a given configuration and aggregate results into a dict.
    If validation is specified, it is run before tests.
    If validation is run and any task fails, no tests are run.
    Returns a JSON serializable dict of a "Grading feedback" JSON object.
    """
    if "validation" in config:
        # Validation specified, run all tasks
        errors = list(validation.run_validation_tasks(config["validation"]["tasks"]))
        if errors:
            # Pre-grading validation failed, convert validation errors into a test result group with no points
            validation_results = {
                "name": config["validation"]["display_name"],
                "testResults": list(schemaobjects.validation_errors_as_test_results(errors)),
            }
            # Will not run tests since a validation task failed
            return {"resultGroups": [validation_results]}
    # Validation not specified, or all validation tasks succeeded, run tests
    result_groups = []
    points_total = max_points_total = tests_run = 0
    for group_result in run_test_groups(config):
        result_groups.append(group_result)
        points_total += group_result["points"]
        max_points_total += group_result["maxPoints"]
        tests_run += group_result["testsRun"]
    return {
        "resultGroups": result_groups,
        "points": points_total,
        "maxPoints": max_points_total,
        "testsRun": tests_run,
    }


def run(config_file, novalidate, container, json_results, develop_mode, quiet):
    """
    Graderutils main entrypoint.
    Runs the full test pipeline and writes results and points to standard stream.
    For accepted arguments, see make_argparser.
    """
    if develop_mode:
        logger.warning("Graderutils is running in develop mode, all unhandled exceptions will be displayed unformatted. Run with --quiet to continue running in develop mode, while disabling these warnings.")

    feedback_out = sys.stdout if container else sys.stderr
    points_out = sys.stdout

    schemas = schemaobjects.build_schemas()

    grading_data = {}

    # Run tests and hide infrastructure exceptions (not validation exceptions) if develop_mode is given and True.
    try:
        # Load and validate the configuration yaml
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not novalidate:
            try:
                jsonschema.validate(config, schemas["test_config"]["schema"])
            except jsonschema.ValidationError as e:
                logger.warning("Graderutils was given an invalid configuration file {}, the validation error was: {}".format(config_file, e.message))
        # Config file is valid, run validation and all test groups
        grading_data = do_everything(config)
    except Exception as e:
        if container:
            raise
        if develop_mode:
            # Format e as a string
            tb_object = traceback.TracebackException.from_exception(e)
            # Wrap multiline traceback string with repr and add prefix flag
            error_msg = multiline_repr_prefix + repr(''.join(tb_object.format()))
        else:
            # Develop mode not enabled, hide traceback
            error_msg = "Unhandled exceptions occured during testing, unable to complete tests. Please notify the author of the tests."
        logger.warning(error_msg)

    if not quiet:
        warning_messages = list(parse_warnings(logger))
        if warning_messages:
            grading_data["warningMessages"] = warning_messages

    # Serialize grading data into JSON, with validation against the "Grading feedback" schema
    grading_json = schemaobjects.full_serialize(schemas, grading_data)

    if json_results or os.environ.get("GRADER_EATS_JSON_RESULTS", '0').strip() in ('1', 'true', 'True'):
        print(grading_json, file=points_out)
    else:
        # Backward compatible, good ol' "HTML to stderr and points to stdout"
        html_output = htmlformat.json_to_html(grading_json)
        print(html_output, file=feedback_out)
        print("TotalPoints: {}\nMaxPoints: {}".format(grading_data["points"], grading_data["maxPoints"]), file=points_out)


def make_argparser():
    parser = argparse.ArgumentParser(
        description="Graderutils runner",
        epilog=__doc__
    )
    parser.add_argument(
            "config_file",
            type=str,
            help="Path to a YAML-file containing runtime settings for grader tests. An example file is provided at graderutils/test_config.yaml and examples/simple/test_config.yaml",
    )
    parser.add_argument(
            "--novalidate",
            action="store_true",
            help="Skip validation of config_file"
    )
    parser.add_argument(
            "--container",
            action="store_true",
            help="This flag should be used when running graderutils inside docker container based on apluslms/grading-base"
    )
    parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Suppress warnings."
    )
    parser.add_argument(
            "--json-results",
            action="store_true",
            help="Print results as a JSON schema 'Grading results' string into standard stream. If used with --container, stream is stderr, else stdout."
    )
    parser.add_argument(
            "--develop-mode", '-d',
            action="store_true",
            help="Display all unhandled exceptions unformatted. By default, exceptions related to improperly configured tests are catched and hidden behind a generic error message. This is to prevent unwanted leaking of grader test details, which might reveal e.g. parts of the model solution, if one is used."
    )
    return parser


if __name__ == "__main__":
    args = vars(make_argparser().parse_args())
    config_file = args.pop("config_file")
    run(config_file, **args)
