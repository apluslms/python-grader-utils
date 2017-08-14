"""
Simple file validation for various file formats.
Can be used for checking a file is valid before starting the grading.
"""
import ast
import collections
import importlib.util
import importlib
import htmlgenerator
import sys
import argparse
import imghdr
import html5lib

BlacklistMatch = collections.namedtuple("BlacklistMatch", ["filename", "linenumber", "line_content", "description"])

# TODO: in debug mode, show warning when supplying a blacklist with no check_files, use an assert for now
def get_blacklist_matches(blacklist):
    """
    Search all files in blacklist["check_files"] for blacklisted node names defined in blacklist["node_names"] and blacklisted node dumps in blacklist["node_dumps"].
    See the settings.yaml for examples and format.

    Matches are returned in a list of BlacklistMatch objects/namedtuples.
    If linenumbers are not valid for some node (e.g. function arguments node), -1 is used as the linenumber.
    """
    assert blacklist["check_files"] # TODO

    matches = []
    blacklisted_names = blacklist["node_names"].keys()
    blacklisted_dumps = blacklist["node_dumps"].keys()

    for filename in blacklist["check_files"]:
        # TODO: OSErrors not catched
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.read()

        # TODO: SyntaxErrors not catched
        submitted_ast = ast.parse(source)
        submitted_lines = source.splitlines()

        # Walk once through the ast of the source of the submitted file, searching for blacklisted stuff.
        for node in ast.walk(submitted_ast):
            node_name = node.__class__.__name__
            node_dump = ast.dump(node)
            linenumber = getattr(node, "lineno", -1)
            line_content = submitted_lines[linenumber-1] if linenumber > 0 else ""
            if node_name in blacklisted_names:
                matches.append(BlacklistMatch(
                        filename=filename,
                        linenumber=linenumber,
                        line_content=line_content,
                        description=blacklist["node_names"][node_name]))
            if node_dump in blacklisted_dumps:
                matches.append(BlacklistMatch(
                        filename=filename,
                        linenumber=linenumber,
                        line_content=line_content,
                        description=blacklist["node_dumps"][node_dump]))

    return matches


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--python")
    parser.add_argument("--image")
    parser.add_argument("--labview")
    parser.add_argument("--html")
    parser.add_argument("--css")
    parser.add_argument("--xlsx")
    parser.add_argument("--pdf")
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
    elif args.css:
        filename = args.css
        raise NotImplementedError("css validation not available")
    elif args.xlsx:
        filename = args.xlsx
        raise NotImplementedError("xlsx validation not available")
    elif args.pdf:
        filename = args.pdf
        raise NotImplementedError("pdf validation not available")

    if errors:
        print(htmlgenerator.errors_as_html(errors), file=sys.stderr)
        sys.exit(1)

