"""
Convert test result objects into JSON serializable dicts conforming to the JSON schemas in the graderutils_format package.
"""
import os.path

from graderutils_format import schemabuilder
from graderutils import graderunittest

SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "schemas"))


def build_schemas():
    """
    Build all feedback schemas and the graderutils test_config schema.
    """
    # Build test config schema
    schemas_data = {"test_config": os.path.join(SCHEMA_DIR, "test_config.yaml")}
    test_config_schema = schemabuilder.build_schemas(schemas_data)
    # Build all feedback schemas
    feedback_schemas = schemabuilder.build_feedback_schemas()
    # Merge schemas
    return dict(feedback_schemas, **test_config_schema)


def test_result_as_dict(test_case, output):
    """
    Return a JSON serializable dict of a "Test result" JSON object.
    """
    # graderunittest.PointsTestRunner has handled all points
    points, max_points = graderunittest.get_points(test_case)
    data = {
        "name": test_case.shortDescription() or str(test_case),
        "state": None,
        "points": points,
        "maxPoints": max_points,
        "testOutput": output,
        "fullTestOutput": output,
    }
    # Optional data
    if hasattr(test_case, "graderutils_msg") and test_case.graderutils_msg:
        data["header"] = test_case.graderutils_msg
    if hasattr(test_case, "user_data") and test_case.user_data:
        data["userData"] = test_case.user_data
    return data


def test_results_as_dicts(result_object):
    """
    Return an iterator over JSON serializable dicts of "Test result" JSON objects.
    """
    # Convert test case results into dicts and add 'state' key depending on test outcome.
    # Successful tests, no exceptions raised
    for test_case in result_object.successes:
        yield dict(test_result_as_dict(test_case, ''), state="success")
    # Failed tests, AssertionError raised
    for test_case, full_assert_msg in result_object.failures:
        yield dict(test_result_as_dict(test_case, full_assert_msg), state="fail")
    # Tests that raised exceptions other than AssertionError
    for test_case, full_traceback in result_object.errors:
        yield dict(test_result_as_dict(test_case, full_traceback), state="error")


def test_group_result_as_dict(test_group_result):
    """
    Return a JSON serializable dict of a "Test result group" JSON object.
    """
    # Convert all test case results in the test group into dicts
    test_results = list(test_results_as_dicts(test_group_result))
    # Get unittest console output from the StringIO instance
    unittest_output = test_group_result.stream.getvalue()
    return {
        "points": test_group_result.points,
        "maxPoints": test_group_result.max_points,
        "testResults": test_results,
        "testsRun": test_group_result.testsRun,
        "fullOutput": unittest_output
    }


def validation_errors_as_test_results(errors):
    """
    Return an iterator over file validation errors as JSON serializable dicts of "Test result" objects.
    """
    for error in errors:
        result = {
            "name": error.get("display_name", error["type"]),
            "testOutput": error["message"],
            "state": "fail",
        }
        if "description" in error:
            # Additional, user-defined messages
            result["header"] = error["description"]
        yield result


def full_serialize(grading_feedback_schema, grading_data):
    """
    Serialize grading_data as a "Grading feedback" JSON schema object and return the resulting JSON string.
    """
    GradingFeedback = grading_feedback_schema["classes"].GradingFeedback
    schema_object = GradingFeedback(**grading_data)
    return schema_object.serialize(sort_keys=True)
