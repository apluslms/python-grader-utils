"""
Serialize unittest result objects as JSON, conforming to the "Grading feedback" schema.
"""


def result_as_dict(test_case, output):
    """
    Return a JSON serializable dict of a "Test result" JSON objects.
    """
    data = {
        "name": test_case.shortDescription(),
        "state": None,
        "points": test_case.points,
        "maxPoints": test_case.maxPoints,
        "testOutput": output,
    }
    if hasattr(test_case, "_short_message"):
        data["header"] = test_case._short_message
    if hasattr(test_case, "user_data"):
        data["userData"] = test_case.user_data
    return data


def results_as_dicts(result_object):
    """
    Return an iterator over JSON serializable dicts of "Test result" JSON objects.
    """
    # Successful tests, no exceptions thrown
    for test_case in result_object.successes:
        yield {"state": "pass", **result_as_dict(test_case, '')}
    # Failed tests, AssertionError thrown
    for test_case, full_assert_msg in result_object.failures:
        yield {"state": "fail", **result_as_dict(test_case, full_assert_msg)}
    # Errored tests, exceptions other than AssertionError thrown
    for test_case, full_traceback in result_object.errors:
        yield {"state": "error", **result_as_dict(test_case, full_traceback)}


def test_group_results_as_dict(test_group_result):
    """
    Return a JSON serializable dict of a "Test result group" JSON object.
    """
    results = list(results_as_dicts(test_group_result))
    # Get unittest console output from the StringIO instance
    unittest_output = test_group_result.stream.getvalue()
    return {
        "points": test_group_result.points,
        "maxPoints": test_group_result.max_points,
        "testResults": results,
        "testsRun": test_group_result.testsRun,
        "testOutput": unittest_output
    }
