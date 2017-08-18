"""
Simple file validation for various file formats.
Can be used for checking if a file is valid before starting the grading.
May also be useful as a trivial grader to give points for submitting correct filetypes.
"""
import argparse
import ast
import collections
import html5lib
import imghdr
import importlib
import re
import sys

import htmlformat


class ValidationError(Exception): pass


BlacklistMatch = collections.namedtuple("BlacklistMatch", ["filename", "linenumber", "line_content", "description"])


def _get_python_blacklist_matches(blacklist):
    """
    Search all files in blacklist["check_files"] for blacklisted node names defined in blacklist["node_names"] and blacklisted node dumps in blacklist["node_dumps"].
    See the settings.yaml for examples and format.

    Matches are returned in a list of BlacklistMatch objects/namedtuples.
    If linenumbers are not valid for some node (e.g. function arguments node), -1 is used as the linenumber.
    """
    matches = []
    blacklisted_names = blacklist["node_names"].keys()
    blacklisted_dumps = blacklist["node_dumps"].keys()

    for filename in blacklist["check_files"]:
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.read() # Note: may raise OSError

        submitted_ast = ast.parse(source) # Note: may raise SyntaxError
        submitted_lines = source.splitlines()

        # Walk once through the ast of the source of the submitted file, searching for blacklisted stuff.
        for node in ast.walk(submitted_ast):
            node_name = node.__class__.__name__
            node_dump = ast.dump(node)
            linenumber = getattr(node, "lineno", -1)
            line_content = submitted_lines[linenumber-1] if linenumber > 0 else ""
            if node_dump in blacklisted_dumps:
                description = blacklist["node_dumps"][node_dump]
                matches.append(BlacklistMatch(
                        filename, linenumber,
                        line_content, description))
            elif node_name in blacklisted_names:
                description = blacklist["node_names"][node_name]
                matches.append(BlacklistMatch(
                        filename, linenumber,
                        line_content, description))

    return matches


def _get_plain_text_blacklist_matches(blacklist):
    """
    Simple blacklist matching, which searches all files in blacklist["check_files"] for strings defined in blacklist["strings"].
    """
    matches = []
    blacklisted_strings = blacklist["strings"].keys()
    ignorecase = blacklist.get("ignorecase", False)

    for filename in blacklist["check_files"]:
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.readlines() # Note: may raise OSError

        pattern_string = "(" + "|".join(blacklisted_strings) + ")"
        pattern = re.compile(pattern_string, re.IGNORECASE if ignorecase else 0)

        for line_number, line in enumerate(source, start=1):
            for line_match in re.findall(pattern, line):
                key = line_match if not ignorecase else line_match.lower()
                description = blacklist["strings"][key]
                matches.append(BlacklistMatch(
                    line_match, line_number,
                    line, description))

    return matches


def get_blacklist_matches(blacklists):
    """
    Search for blacklisted strings as defined in the blacklist objects given as arguments.
    Return a list of matches or an empty list if there are no matches.
    """
    blacklist_matches = []
    for blacklist in blacklists:
        if blacklist["type"] == "plain_text":
            get_matches = _get_plain_text_blacklist_matches
        elif blacklist["type"] == "python":
            get_matches = _get_python_blacklist_matches
        else:
            raise ValidationError("A blacklist was given but validation for '{}' is not defined.".format(blacklist["method"]))
        blacklist_matches.append(get_matches(blacklist))
    return blacklist_matches


def get_image_type_errors(image, expected_type):
    errors = {}
    actual_type = imghdr.what(image)
    if actual_type != expected_type:
        errors["type"] = "filetype error"
        errors["message"] = "Expected type '{}' but got '{}'.".format(expected_type, actual_type)
    return errors


def get_import_errors(module):
    errors = {}
    try:
        importlib.import_module(module)
    except Exception as error:
        errors["type"] = error.__class__.__name__
        errors["message"] = str(error)
    return errors


def get_labview_errors(filename):
    errors = {}
    with open(filename, "rb") as f:
        header = f.read(16)
        if header != b'RSRC\r\n\x00\x03LVINLBVW':
            errors["type"] = "filetype error"
            errors["message"] = "The file wasn't a proper labVIEW-file"
    return errors


def get_html_errors(filename):
    errors = {}
    with open(filename, "r") as f:
        parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"), strict=True)
        err = ""
        try:
            document = parser.parse(f)
        except:
            for e in parser.errors:
                err += "Line {0}: {1}: {2} \n".format(e[0][0], e[1], e[2])

        if err:
            errors["type"] = "html style error"
            errors["message"] = err

    return errors


# # Non-interactive rendering to png
# MATPLOTLIB_RENDERER_BACKEND = "AGG"

SUPPORTED_ARGS = ("python", "image", "labview", "html")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in SUPPORTED_ARGS:
        parser.add_argument("--{}".format(flag))

    args = parser.parse_args()

    errors = {}

    if args.python:
        # import matplotlib
        # matplotlib.use(MATPLOTLIB_RENDERER_BACKEND)
        module_name = args.python.split(".py")[0]
        errors = get_import_errors(module_name)
    elif args.image:
        image_file = args.image
        image_type = image_file.split(".")[-1]
        errors = get_image_type_errors(image_file, image_type)
    elif args.labview:
        filename = args.labview
        errors = get_labview_errors(filename)
    elif args.html:
        filename = args.html
        errors = get_html_errors(filename)

    # elif args.css:
    #     filename = args.css
    #     raise NotImplementedError("css validation not available")
    # elif args.xlsx:
    #     filename = args.xlsx
    #     raise NotImplementedError("xlsx validation not available")
    # elif args.pdf:
    #     filename = args.pdf
    #     raise NotImplementedError("pdf validation not available")

    if errors:
        print(htmlformat.errors_as_html(errors), file=sys.stderr)
        sys.exit(1)

