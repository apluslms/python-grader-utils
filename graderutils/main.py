"""
Python grader test runner with pre-grade validation and post-grade feedback styling.
"""
import argparse
import ast
import io
import logging
import os
import pprint
import traceback

# Log all library errors into a single, global stream
logger = logging.getLogger("warnings")
logger.addHandler(logging.StreamHandler(stream=io.StringIO()))
# Add prefix to multiline errors that have been repr'd in order to fit into a single line
multiline_repr_prefix = "#MULTILINE-REPR#"

import yaml
import jsonschema

from graderutils import graderunittest, schemaobjects, validation, tracebackformat

BASECONFIG = os.path.join(os.path.dirname(__file__), "baseconfig.yaml")


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


def run_test_groups(test_groups):
    """
    Generator that runs all test groups specified by the given configuration and yields test group result dicts.
    """
    for test_group in test_groups:
        # Run all test cases in module, producing a result with points
        points_results = graderunittest.run_test_suite_in_named_module(test_group["module"])
        # Convert all test results in group results into JSON schema serializable dicts
        group_result = schemaobjects.test_group_result_as_dict(points_results)
        group_result["name"] = test_group["display_name"]
        if "description" in test_group:
            group_result["description"] = test_group["description"]
        yield group_result


def do_validation_tasks(validation_config):
    """
    Run all specified validation tasks and return errors as a "Grading feedback" JSON object without points.
    Return an empty dict if all validation tasks pass.
    """
    validation_result = {}
    errors = list(validation.run_validation_tasks(validation_config["tasks"]))
    if errors:
        # Pre-grading validation failed, convert validation errors into a test result group with no points
        validation_result["resultGroups"] = [
            {
                "name": validation_config.get("display_name", "Input validation"),
                "testResults": list(schemaobjects.validation_errors_as_test_results(errors))
            }
        ]
    return validation_result


def do_tests(config):
    """
    Run test pipeline using a given configuration and aggregate results into a dict.
    Returns a JSON serializable dict of a "Grading feedback" JSON object.
    """
    result_groups = []
    points_total = max_points_total = tests_run = 0
    for group_result in run_test_groups(config["test_groups"]):
        result_groups.append(group_result)
        points_total += group_result["points"]
        max_points_total += group_result["maxPoints"]
        tests_run += group_result["testsRun"]
    if "format_tracebacks" in config:
        # Traceback formatting specified, run all formatting on all results
        # Unmodified traceback strings are backed up into key fullTestOutput for each test result,
        # unless the full test output has also been specified to be removed.
        tracebackformat.clean_feedback(result_groups, config["format_tracebacks"])
    return {
        "resultGroups": result_groups,
        "points": points_total,
        "maxPoints": max_points_total,
        "testsRun": tests_run,
    }


def run(config_path, novalidate=False, container=False, show_config=False, develop_mode=False):
    """
    Graderutils main entrypoint.
    Runs the full test pipeline and returns a Grading feedback JSON schema object as a dict.
    For accepted arguments, see make_argparser.
    """
    if develop_mode:
        logger.warning("Graderutils is running in develop mode, all unhandled exceptions will be displayed unformatted here as messages.")

    # Build Python JSON schema object classes from schema files in package
    schemas = schemaobjects.build_schemas()
    # Kwargs dict for top level "Grading feedback" JSON schema object
    grading_feedback = {}

    config = None

    # Run tests and hide infrastructure exceptions (not validation exceptions) if develop_mode is given and True.
    try:
        # Load and validate the configuration yaml
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not novalidate:
            try:
                jsonschema.validate(config, schemas["test_config"]["schema"])
            except jsonschema.ValidationError as e:
                logger.warning("Graderutils was given an invalid configuration file {}, the validation error was: {}".format(config_path, e.message))
                raise
        # Config file is valid, merge with baseconfig
        with open(BASECONFIG, encoding="utf-8") as f:
            config = dict(yaml.safe_load(f), **config)
        # Run input validation
        if "validation" in config:
            grading_feedback = do_validation_tasks(config["validation"])
        # Run tests, unless input validation produced errors
        if not grading_feedback:
            grading_feedback = do_tests(config)
    except Exception as e:
        if container:
            raise
        if develop_mode:
            # Wrap multiline traceback string with repr and add prefix flag
            error_msg = multiline_repr_prefix + repr(traceback.format_exc())
        else:
            # Develop mode not enabled, hide traceback
            error_msg = "Unhandled exceptions occured during testing, unable to complete tests. Please notify the author of the tests."
        logger.warning(error_msg)

    if develop_mode or show_config:
        if config is None:
            logger.warning("Unable to load config file {}".format(config_path))
        else:
            msg = "The test configuration was:\n" + pprint.PrettyPrinter(indent=2).pformat(config)
            logger.warning(multiline_repr_prefix + repr(msg))
    warning_messages = list(parse_warnings(logger))
    if warning_messages:
        grading_feedback["warningMessages"] = warning_messages

    # Serialize grading data into JSON, with validation against the "Grading feedback" schema
    return schemaobjects.full_serialize(schemas, grading_feedback)


def make_argparser():
    parser = argparse.ArgumentParser(
        description="Graderutils runner",
        epilog=__doc__
    )
    parser.add_argument(
            "config_path",
            type=str,
            help="Path to a YAML-file containing runtime settings for grader tests. An example file is provided at graderutils/test_config.yaml and examples/simple/test_config.yaml",
    )
    flags = (
        ("novalidate",
            "Skip validation of config_path"),
        ("container",
            "This flag should be used when running graderutils inside docker container based on apluslms/grading-base"),
        ("show-config",
            "Print test configuration into warnings."),
        ("develop-mode",
            "Display all unhandled exceptions unformatted."
            " Also implies --show-config."
            " By default, exceptions related to improperly configured tests are catched and hidden behind a generic error message."
            " This is to prevent unwanted leaking of grader test details, which might reveal e.g. parts of the model solution, if one is used."),
    )
    for flag, help in flags:
        parser.add_argument('--' + flag, action="store_true", help=help)
    return parser


if __name__ == "__main__":
    cli_args = vars(make_argparser().parse_args())
    # Remove required command line argument, leaving only optional arguments
    config_path = cli_args.pop("config_path")
    grading_json = run(config_path, **cli_args)
    print(grading_json)
