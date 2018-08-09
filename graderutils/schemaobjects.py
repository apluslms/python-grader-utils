"""
Create Python objects that can be serialized into JSON conforming to defined JSON schemas.
"""
import json
import os.path

from python_jsonschema_objects import ObjectBuilder

from graderutils import graderunittest, GraderUtilsError


class SchemaError(GraderUtilsError): pass


SCHEMA_KEYS = (
    "test_config",       # No references
    "test_result",       # No references
    "test_result_group", # Depends on test_result
    "grading_feedback",  # Depends on test_result_group
)

SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), os.path.pardir, "schemas")


def build_schemas():
    """
    Build all schemas from files and resolve schema dependencies.
    """
    schemas = {}
    classes = {}
    for schema_key in SCHEMA_KEYS:
        # Get schema file from graderutils repo root
        schema_path = os.path.join(SCHEMAS_DIR, schema_key + ".schema.json")
        if not os.path.exists(schema_path):
            raise SchemaError("Cannot build JSON schema object {}, schema path does not exist: {}".format(schema_key, schema_path))
        # Load schema file contents
        with open(schema_path) as schema_file:
            schema = json.load(schema_file)
        schemas[schema_key] = schema
        # Build all abstract base classes for instantiating the properties of current schema
        classes[schema_key] = ObjectBuilder(schema, resolved=schemas).build_classes()
    # Merge schema dicts and classes under one schema key
    return {key: {"schema": schemas[key], "classes": classes[key]} for key in schemas}


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


def full_serialize(schemas, grading_data):
    """
    Serialize grading_data as a "Grading feedback" JSON schema object and return the resulting JSON string.
    """
    GradingFeedback = schemas["grading_feedback"]["classes"].GradingFeedback
    schema_object = GradingFeedback(**grading_data)
    return schema_object.serialize(sort_keys=True)
