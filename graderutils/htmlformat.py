"""
Functions for parsing TestResult objects into HTML.
Uses Jinja2 for template rendering.
"""
import collections
import itertools
import re

import jinja2

from graderutils.main import GraderUtilsError


class HTMLFormatError(GraderUtilsError): pass


def suffix_after(string, split_at):
    """Return suffix of string after first occurrence of split_at."""
    return string.split(split_at, 1)[-1]

def prefix_before(string, split_at):
    """Return prefix of string before first occurrence of split_at."""
    return string.split(split_at, 1)[0]

def collapse_max_recursion_exception(string, repeat_threshold=20):
    """Replace identical lines in a max recursion error traceback
    with a message and the amount lines removed."""
    # Well this turned out to be quite awful.
    result = []
    repeats = 0
    previous_repeat_count = 0
    found_lines = set()
    is_repeating = False
    for line in string.splitlines():
        if line in found_lines:
            repeats += 1
        else:
            if is_repeating:
                found_lines = set()
                previous_repeat_count = repeats
            repeats = 0
            found_lines.add(line)
        if repeats > repeat_threshold:
            # Continue until we find an unique line
            is_repeating = True
            continue
        if is_repeating:
            is_repeating = False
            # TODO localize message
            msg = (
                2*"\n   .    " +
                "\n   .    \n"
                "\n  and {0} more hidden lines\n".format(previous_repeat_count) +
                2*"\n   .    " +
                "\n   .    \n\n"
            )
            result.append(msg)
        result.append(line + '\n')
    return ''.join(result)

# TODO this feature is probably a bit questionable as it modifies the expected traceback message
# it can be argued whether a custom traceback message without infrastructure specific clutter really is better than a standard traceback message which is not modified
def shortened_traceback(filename, traceback_string):
    """Strips traceback_string from all data unrelated to a file named filename.

    @param (str) filename: Filename which occurs in the path shown in traceback_string.
    @return (str) Shortened version of traceback_string.

    For example:

        'Traceback ...
         ...
         ..several lines...
         ...
         File "/srv/folder/sandbox/stuff/hashstring1231FFasdgZ/primes.py", line 6, in is_prime
             if a/0:
         ZeroDivisionError: division by zero'

     turns into:

        'File "primes.py", line 6, in is_prime
             if a/0:
         ZeroDivisionError: division by zero'
    """

    if re.search(r"RecursionError|MemoryError", traceback_string):
        traceback_string = collapse_max_recursion_exception(traceback_string)

    # TODO
    # if not filename or not re.search(filename, traceback_string):
    #     return traceback_string

    # # Suffix of traceback_string starting after the first occurrence of `filename`
    # traceback_string = ''.join(suffix_after(traceback_string, filename))
    # traceback_string = "File \"{:s}".format(filename) + traceback_string
    # return traceback_string


def parsed_assertion_message(assertion_error_traceback, split_at=""):
    """
    Remove traceback and 'AssertionError: ' starting from assertion_error_traceback.
    Optionally split the resulting string at split_at and return the prefix.
    """
    without_traceback = suffix_after(assertion_error_traceback, "AssertionError: ")
    return prefix_before(without_traceback, split_at)


def data_from_string_or_empty_json(string, data_tag):
    """Return suffix of string after first occurrence of data_tag or an empty json string if string does not contain data_tag."""
    if data_tag not in string:
        return "{}"
    return suffix_after(string, data_tag)


def extra_data_or_none(test_case):
    """Return dict with extra feedback data, if available."""
    # TODO hardcoded
    EXTRA_FEEDBACK_ATTRS = (
        "total_time",
        "test_count",
        "preformatted_feedback",
        "html_feedback",
        "image_path",
        "svg_xml",
    )
    feedback_data = {}
    for attribute in EXTRA_FEEDBACK_ATTRS:
        if hasattr(test_case, attribute):
            feedback_data[attribute] = getattr(test_case, attribute)

    return feedback_data if feedback_data else None


ParsedTestResult = collections.namedtuple("ParsedTestResult",
        ("test_outcome", "method_name",
         "assertion_message", "user_data",
         "full_traceback"))


def test_result_as_template_context(result_object):
    """Return the attribute values from result_object that are needed for HTML template rendering in a dictionary.
    @param (PointsResultObject) Result object from running PointsTestRunner. Expected to contain attributes:
        errors,
        failures,
        testsRun,
        successes,
        stream,
        points,
        max_points,
        test_description,
    @return (dict) Context dictionary for HTML rendering.
    """
    # Create generators for all result types

    successes = (ParsedTestResult("SUCCESS",
                    test_case.shortDescription(),
                    "",
                    getattr(test_case, "user_data", None),
                    "")
                 for test_case in result_object.successes)

    failures = (ParsedTestResult("FAIL",
                    test_case.shortDescription(),
                    full_assert_msg,
                    getattr(test_case, "user_data", None),
                    "")
                for test_case, full_assert_msg in result_object.failures)

    # Tests which had exceptions other than AssertionError
    errors = (ParsedTestResult("ERROR",
                   test_case.shortDescription(),
                   shortened_traceback(full_traceback),
                   getattr(test_case, "user_data", None),
                   full_traceback)
              for test_case, full_traceback in result_object.errors)

    # Evaluate all generators into a single list
    results = list(itertools.chain(successes, failures, errors))

    # Get unittest console output from the StringIO instance
    unittest_output = result_object.stream.getvalue()

    context = {
        "results": results,
        "test_description": result_object.test_description,
        "points": result_object.points,
        "max_points": result_object.max_points,
        "tests_run": result_object.testsRun,
        "unittest_output": unittest_output
    }

    return context


def results_as_html(results, feedback_template=None):
    """Render the list of results as HTML and return the HTML as a string.
    @param results List of TestResult objects.
    @return Raw HTML as a string.
    """
    if feedback_template is None:
        feedback_template = "feedback_template.html"
        template_loader = jinja2.PackageLoader("graderutils", "static")
    else:
        template_loader = jinja2.FileSystemLoader("./")

    env = jinja2.Environment(loader=template_loader)
    template = env.get_template(feedback_template)

    result_context_dicts = []
    total_points = total_max_points = total_tests_run = 0

    for res in results:
        result_context = test_result_as_template_context(res)
        result_context_dicts.append(result_context)

        total_points += result_context["points"]
        total_max_points += result_context["max_points"]
        total_tests_run += result_context["tests_run"]

    context = {
        "all_results": result_context_dicts,
        "total_points": total_points,
        "total_max_points": total_max_points,
        "total_tests_run": total_tests_run
    }

    return template.render(**context)


def errors_as_html(error_data, error_template=None):
    """
    Renders the context dictionary errors as html using the given error template and returns the raw html string.
    """
    if error_template is None:
        error_template = "error_template.html"
        template_loader = jinja2.PackageLoader("graderutils", "static")
    else:
        template_loader = jinja2.FileSystemLoader("./")

    env = jinja2.Environment(loader=template_loader)
    template = env.get_template(error_template)
    return template.render(errors=error_data)


def wrap_div_alert(string):
    return r"<div class='alert alert-danger'>{}</div>".format(string)

