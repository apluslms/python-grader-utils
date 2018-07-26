"""
Functions for parsing and cleaning output strings from unittest test case result objects.
"""
import re


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


def collapse_traceback(traceback_string):
    if re.search(r"RecursionError|MemoryError", traceback_string):
        traceback_string = collapse_max_recursion_exception(traceback_string)
    return traceback_string


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


def hide_exception_traceback(traceback_string, exception_names, remove_more_sentinel, replacement_string):
    """
    Find all tracebacks caused by exceptions specified in exception_names and return a string where all traceback occurrences in traceback_string have been replaced with replacement_string.
    In other words, everything starting with 'Traceback (most recent call last)' up until the exception message is replaced.

    If remove_more_sentinel is given, then even more is removed.
    E.g. with [remove-stop]:
    "AssertionError : True is not False : [remove-stop]no it isn't"
    turns into:
    "no it isn't"
    """
    traceback_header = "Traceback (most recent call last)"
    begin_traceback = re.compile('^' + re.escape(traceback_header))
    end_traceback = re.compile('^(' + '|'.join(re.escape(e) for e in exception_names) + ')')

    # Find all lines that match the pattern range

    is_matching = False
    # Pending match, pair of (start_index, line_count)
    match = []
    # Finalized matches to be removed, pairs of (start_index, line_count)
    matches = []

    traceback_lines = traceback_string.splitlines(keepends=True)

    for lineno, line in enumerate(traceback_lines):
        if is_matching:
            if re.match(end_traceback, line):
                # Fully matched one traceback
                matches.append(tuple(match))
                match = []
                is_matching = False
            elif re.match(begin_traceback, line):
                # This match overlaps 2 traceback strings, and the first one is from an exception not specified in exception_names
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
    cleaned_traceback_string = ''.join(_iter_redacted_lines(traceback_lines, iter(matches), replacement_string))

    # Remove even more starting at the replacement string if a sentinel is given
    if remove_more_sentinel:
        if replacement_string and not replacement_string.endswith('\n'):
            # Exception names will be on the same line with the last line of the replacement string, which starts the line
            begin_pattern_str = '^' + re.escape(replacement_string.splitlines()[-1]) + end_traceback.pattern[1:]
        else:
            # Exception names will start new lines immediately below the last line of the replacement string
            begin_pattern_str = end_traceback.pattern
        remove_pattern = re.compile(begin_pattern_str + '(.|[\r\n])*?' + re.escape(remove_more_sentinel), re.MULTILINE)
        cleaned_traceback_string = re.sub(remove_pattern, '', cleaned_traceback_string)

    return cleaned_traceback_string


def parsed_assertion_message(assertion_error_traceback, split_at=None):
    """
    Remove traceback and 'AssertionError: ' starting from assertion_error_traceback.
    Optionally split the resulting string at split_at and return the prefix.
    """
    without_traceback = suffix_after(assertion_error_traceback, "AssertionError: ")
    if split_at:
        without_traceback = prefix_before(without_traceback, split_at)
    return without_traceback
