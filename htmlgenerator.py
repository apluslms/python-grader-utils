"""
Functions for generating result objects as HTML. Uses Jinja2 for rendering.
"""
import itertools
import jinja2
import re
import settings

if settings.HTML_TRACEBACK:
    import sys
    import cgitb
    sys.excepthook = cgitb.Hook(file=sys.stderr, format="html", display=1, context=5)

class HTMLGeneratorError(Exception): pass


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
            result.append(2*"\n   .    ")
            result.append("\n   .    \n")
            result.append("\n  and {0} more hidden lines\n".format(previous_repeat_count))
            result.append(2*"\n   .    ")
            result.append("\n   .    \n\n")
        result.append(line + '\n')
    return ''.join(result)

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

    if not re.search(filename, traceback_string):
        return traceback_string

    # Suffix of traceback_string starting after the first occurrence of `filename`
    traceback_string = ''.join(suffix_after(traceback_string, filename))
    traceback_string = "File \"{:s}".format(filename) + traceback_string
    return traceback_string


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
    if hasattr(test_case, "total_running_time") and hasattr(test_case, "test_count"):
        return {"total_time": test_case.total_running_time,
                "test_count": test_case.test_count}
    if hasattr(test_case, "preformatted_feedback"):
        return {"preformatted_feedback": test_case.preformatted_feedback}
    if hasattr(test_case, "html_feedback"):
        return {"html_feedback": test_case.html_feedback}


def test_result_as_template_context(result_object):
    """Return the attribute values from result_object that are needed for HTML template rendering in a dictionary.
    @param (PointsResultObject) Result object from running PointsTestRunner. Expected to contain attributes:
        successes,
        errors,
        failures,
        stream,
        points,
        max_points,
        testsRun,
        test_type_name,
        module_filename
    @return (dict) Context dictionary for HTML rendering.
    """

    # Create generators for all result types
    # All results in the generators are represented as 5 element tuples:
    # ( <test outcome>,
    #   <test_method docstring>,
    #   <assertion msg/feedback>,
    #   <extra data, JSON for example>,
    #   <full traceback> )

    # Successful tests
    successes = (("SUCCESS", # Test outcome
                  test_case.shortDescription(), # Test title
                  "", # Test feedback
                  extra_data_or_none(test_case), # Extra data, for example JSON
                  "") # Full traceback
                 for test_case in result_object.successes)

    # Tests which failed, i.e. for which AssertionError was raised
    failures = (("FAIL",
                 test_case.shortDescription(),
                 parsed_assertion_message(full_assert_msg, "#TREE"),
                 extra_data_or_none(test_case),
                 "")
                for test_case, full_assert_msg in result_object.failures)

    # Tests which had exceptions other than AssertionError
    errors = (("ERROR",
               test_case.shortDescription(),
               # Shortened traceback has everything 'unrelated' to the file with name
               # module_filename removed from the traceback. See shortened_traceback.
               shortened_traceback(result_object.submit_module_name, full_traceback),
               "",
               full_traceback)
              for test_case, full_traceback in result_object.errors)


    # Generate a list of all results as dictionaries

    results = [{"outcome": outcome,
                "title": title,
                "feedback": feedback,
                "extra_data": extra_data,
                "full_traceback": full_traceback}
               for
               outcome, title, feedback, extra_data, full_traceback
               in
               itertools.chain(successes, failures, errors)]

    # Get unittest console output from the StringIO instance
    unittest_output = result_object.stream.getvalue()


    context = {
        "results": results,
        # test_type_name is expected to have been added manually
        "test_suite_name": result_object.test_type_name,
        "points": result_object.points,
        "max_points": result_object.max_points,
        "tests_run": result_object.testsRun,
        "unittest_output": unittest_output
    }

    return context


def results_as_html(results):
    """Render the list of results as HTML and return the HTML as a string.
    @param results List of TestResult objects.
    @return Raw HTML as a string.
    """

    # Load feedback template from same directory as tests
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
    template = env.get_template("feedback_template.html")

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

    return template.render(context)


#TODO: Refactoring: might be more modular to handle context building in this function
def errors_as_html(errors):
    """Renders the context dictionary errors as html and returns the raw html string."""

    # Load error template from same directory as tests
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
    template = env.get_template("error_template.html")

    return template.render({"errors": errors})


