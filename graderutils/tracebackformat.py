"""
Functions for parsing and cleaning output strings from unittest test case result objects.
"""
import re

# TODO save traceback objects during tests and use the std lib traceback module
# then a lot of code in here can probably be dropped

def _iter_redacted_lines(lines, remove_lines, replacement_string):
    """
    Return an iterator over lines that are not part of line chunks specified by remove_lines.
    remove_lines must be an iterator of pairs (match_begin, match_length), where match_begin indexes are in ascending order.
    If replacement_string is of non-zero length, it is yielded once in place of each removed chunk of lines.
    """
    is_removing = False
    remove_start, left_to_remove = next(remove_lines, (-1, 0))
    for lineno, line in enumerate(lines):
        if is_removing:
            if left_to_remove == 0:
                # All lines of this chunk have been removed
                is_removing = False
                # Take next chunk to be removed, if available
                remove_start, left_to_remove = next(remove_lines, (-1, 0))
                # Replace the removed chunk of lines, if a replacement string was given
                if replacement_string:
                    yield replacement_string
            else:
                # Still removing
                left_to_remove -= 1
                continue
        elif remove_start >= 0 and lineno == remove_start and left_to_remove > 0:
            # Not yet removing, but this is the first line in a chunk to be removed
            is_removing = True
            left_to_remove -= 1
            continue
        # Got this far without a continue, this line is not part of a chunk of lines to be removed
        yield line


def hide_exception_traceback(output, exception_class_name, hide_tracebacks, remove_sentinel=None, replacement_string=None):
    """
    Find all tracebacks in output, caused by exceptions specified by exception_class_name and return a string where all traceback occurrences in traceback_string have been replaced with replacement_string.
    In other words, everything starting with 'Traceback (most recent call last)' up until the exception message is replaced.

    If remove_sentinel is given, then traceback until replacement_string is removed.
    E.g. with [remove-stop]:
    "AssertionError : True is not False : [remove-stop]no it isn't"
    turns into:
    "no it isn't"

    If exception_class_name is '*', all tracebacks are removed.
    """
    cleaned_traceback_string = output

    traceback_header = "Traceback (most recent call last)"
    begin_traceback = re.compile('^' + re.escape(traceback_header))
    if exception_class_name == '*':
        end_traceback = re.compile(r'^\S+')
    else:
        end_traceback = re.compile('^' + re.escape(exception_class_name))

    if hide_tracebacks:
        # Find all lines that match the pattern range

        lines = output.splitlines(keepends=True)

        is_matching = False
        # Pending match, pair of (start_index, line_count)
        match = []
        # Finalized matches to be removed, pairs of (start_index, line_count)
        matches = []

        for lineno, line in enumerate(lines):
            if is_matching:
                if re.match(end_traceback, line):
                    # Fully matched one traceback
                    matches.append(tuple(match))
                    match = []
                    is_matching = False
                elif re.match(begin_traceback, line):
                    # This match overlaps 2 traceback strings, and the first one is from an exception not specified by exception_class_name
                    # Drop first match and start a new one from here
                    match = [lineno, 1]
                else:
                    # Accumulate match with one line
                    match[1] += 1
            elif re.match(begin_traceback, line):
                # Found a traceback header, start accumulating traceback string
                is_matching = True
                match = [lineno, 1]

        # Replace matching line chunks with the replacement_string
        cleaned_traceback_string = ''.join(_iter_redacted_lines(lines, iter(matches), replacement_string))

    # Remove even more starting at the replacement string if a sentinel is given
    if remove_sentinel:
        if replacement_string and not replacement_string.endswith('\n'):
            # Exception names will be on the same line with the last line of the replacement string, which starts the line
            begin_pattern_str = '^' + re.escape(replacement_string.splitlines()[-1]) + end_traceback.pattern[1:]
        else:
            # Exception names will start new lines immediately below the last line of the replacement string
            begin_pattern_str = end_traceback.pattern
        remove_pattern = re.compile(begin_pattern_str + r'(.|[\r\n])*?' + re.escape(remove_sentinel), re.MULTILINE)
        cleaned_traceback_string = re.sub(remove_pattern, '', cleaned_traceback_string)

    return cleaned_traceback_string


def clean_feedback(result_groups, config):
    """
    Run traceback cleaning for finished grading feedback.
    """
    for group in result_groups:
        # Clean tracebacks for each test suite
        for result in group["testResults"]:
            # Run all cleaning tasks for traceback
            for task in config:
                hide_tracebacks = task.get('hide_tracebacks', False)
                remove_sentinel = task.get('remove_sentinel', '')
                if hide_tracebacks or remove_sentinel:
                    # This task defines that exceptions from some class must be hidden

                    # DEPRECATED:
                    # remove_more_sentinel allowed for traceback removal only when hide_tracebacks was set to true.
                    # remove_sentinel replaces the old remove_more_sentinel and it does not have the described limitation.
                    # The new remove_sentinel does not change old behaviour of remove_more_sentinel.
                    # Once next major version is released, delete the following two lines.
                    if task.get("remove_more_sentinel", ''):
                        remove_sentinel = task.get("remove_more_sentinel", '')

                    exception_class_name = task["class_name"].strip()
                    result["testOutput"] = hide_exception_traceback(
                        result["testOutput"],
                        exception_class_name,
                        hide_tracebacks=hide_tracebacks,
                        remove_sentinel=remove_sentinel,
                        replacement_string=task.get("hide_tracebacks_replacement", '')
                    )
                    if not task.get("hide_tracebacks_short_only", False):
                        # This task defines that full, unformatted output should also be formatted
                        result["fullTestOutput"] = result["testOutput"]
        # Now for the full output from running the test suite
        for task in config:
            hide_tracebacks = task.get("hide_tracebacks", False)
            hide_tracebacks_short_only = task.get("hide_tracebacks_short_only", False)
            if hide_tracebacks and not hide_tracebacks_short_only:
                remove_sentinel = task.get("remove_sentinel", '')

                # DEPRECATED:
                # remove_more_sentinel allowed for traceback removal only when hide_tracebacks was set to true.
                # remove_sentinel replaces the old remove_more_sentinel and it does not have the described limitation.
                # The new remove_sentinel does not change old behaviour of remove_more_sentinel.
                # Once next major version is released, delete the following two lines.
                if task.get("remove_more_sentinel", ''):
                    remove_sentinel = task.get("remove_more_sentinel", '')

                exception_class_name = task["class_name"].strip()
                group["fullOutput"] = hide_exception_traceback(
                    group["fullOutput"],
                    exception_class_name,
                    hide_tracebacks=hide_tracebacks,
                    remove_sentinel=remove_sentinel,
                    replacement_string=task.get("hide_tracebacks_replacement", '')
                )
