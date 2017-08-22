"""
Simple file validation for various file formats.
Can be used for checking if a file is valid before starting the grading.
May also be useful as a trivial grader to give points for submitting correct filetypes.
"""
import ast
import collections
import html5lib
import imghdr
import importlib
import re

from graderutils.main import GraderUtilsError
from graderutils import htmlformat


SUPPORTED_VALIDATION_CHOICES = (
        "python_import",
        "image_type",
        "labview",
        "html")


class ValidationError(GraderUtilsError): pass

ForbiddenSyntaxMatch = collections.namedtuple("ForbiddenSyntaxMatch", ["filename", "linenumber", "line_content", "description"])


def _check_python_forbidden_syntax(config, blacklist=True):
    """
    Search all files in config["check_files"] for node names defined in config["node_names"] and node dumps in config["node_dumps"].
    If blacklist is True, return ForbiddenSyntaxMatch objects for every match.
    Else return ForbiddenSyntaxMatch for every miss.
    If linenumbers are not valid for some node (e.g. function arguments node), -1 is used as the linenumber.

    See the test_config.yaml for examples and format.
    """
    matches = []
    if "node_names" in config:
        names = config["node_names"].keys()
    else:
        names = set()
    if "node_dumps" in config:
        dumps = config["node_dumps"].keys()
    else:
        dumps = set()

    for filename in config["check_files"]:
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.read() # Note: may raise OSError

        submitted_ast = ast.parse(source) # Note: may raise SyntaxError
        submitted_lines = source.splitlines()

        # Walk once through the ast of the source of the submitted file, searching for black/whitelisted stuff.
        for node in ast.walk(submitted_ast):
            node_name = node.__class__.__name__
            node_dump = ast.dump(node)
            linenumber = getattr(node, "lineno", -1)
            line_content = submitted_lines[linenumber-1] if linenumber > 0 else ""
            if blacklist:
                if node_dump in dumps:
                    # This node has a dump representation that is not allowed.
                    description = config["node_dumps"][node_dump]
                    matches.append(ForbiddenSyntaxMatch(
                            filename, linenumber,
                            line_content, description))
                elif node_name in names:
                    # This node has a name that is not allowed.
                    description = config["node_names"][node_name]
                    matches.append(ForbiddenSyntaxMatch(
                            filename, linenumber,
                            line_content, description))
            else:
                if node_name not in names and node_dump not in dumps:
                    # This node has a name or dump representation that is not allowed.
                    description = node_name
                    matches.append(ForbiddenSyntaxMatch(
                            filename, linenumber,
                            line_content, description))

    return matches


def _check_plain_text_forbidden_syntax(config, blacklist=True):
    """
    As in _check_python_forbidden_syntax but for plain text strings.
    There is no tokenization of the source text.
    The source text is checked by a simple regular expression and a match happens when that regular expression matches on a line in the source text.
    """
    matches = []
    config_strings = config["strings"].keys()
    ignorecase = config.get("ignorecase", False)

    for filename in config["check_files"]:
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.readlines() # Note: may raise OSError

        pattern_string = "(" + "|".join(config_strings) + ")"
        pattern = re.compile(pattern_string, re.IGNORECASE if ignorecase else 0)

        for line_number, line in enumerate(source, start=1):
            re_matches = re.findall(pattern, line)
            if blacklist:
                for line_match in re_matches:
                    key = line_match if not ignorecase else line_match.lower()
                    description = config["strings"][key]
                    matches.append(ForbiddenSyntaxMatch(
                        line_match, line_number,
                        line, description))
            else:
                if not re_matches:
                    matches.append(ForbiddenSyntaxMatch("", line_number, line, ""))

    return matches


def _get_python_blacklist_matches(blacklist):
    return _check_python_forbidden_syntax(blacklist, blacklist=True)


def _get_python_whitelist_misses(whitelist):
    return _check_python_forbidden_syntax(whitelist, blacklist=False)


def _get_plain_text_blacklist_matches(blacklist):
    return _check_plain_text_forbidden_syntax(blacklist, blacklist=True)


def _get_plain_text_whitelist_misses(whitelist):
    return _check_plain_text_forbidden_syntax(whitelist, blacklist=False)


def check_forbidden_syntax(config):
    """
    If checking for forbidden syntax is configured in the config file,
    check for used forbidden syntax and return the error html template
    rendered with feedback if matches are found.
    Else return an empty string.
    Mutates the given parameter by removing keys which are checked.
    """
    match_feedback = ""
    for forbidden_list_type in ("blacklists", "whitelists"):
        if forbidden_list_type in config:
            forbidden_lists = config[forbidden_list_type]
            if not isinstance(forbidden_lists, list):
                raise ValidationError("Configurations for {} should be given as a list in the configuration file.".format(repr(forbidden_list_type)))
            matches = get_forbidden_syntax_matches(forbidden_lists, forbidden_list_type)
            if matches:
                error_template = config.get("error_template", None)
                match_feedback = htmlformat.blacklist_matches_as_html(
                        matches, error_template)
            del config[forbidden_list_type]
        if match_feedback:
            break
    return match_feedback


def get_forbidden_syntax_matches(forbidden_lists, forbidden_list_type):
    """
    Return a list of matches or an empty list if there are no matches.
    """
    if forbidden_list_type not in {"blacklists", "whitelists"}:
        raise ValidationError("Unknown forbidden syntax list type '{}'".format(forbidden_list_type))

    matches = []
    for forbidden in forbidden_lists:
        if forbidden["type"] == "plain_text":
            if forbidden_list_type == "blacklists":
                get_matches = _get_plain_text_blacklist_matches
            elif forbidden_list_type == "whitelists":
                get_matches = _get_plain_text_whitelist_misses
        elif forbidden["type"] == "python":
            if forbidden_list_type == "blacklists":
                get_matches = _get_python_blacklist_matches
            elif forbidden_list_type == "whitelists":
                get_matches = _get_python_whitelist_misses
        else:
            raise ValidationError("Unknown syntax type '{}', cannot check for forbidden syntax.".format(forbidden["type"]))

        matches = get_matches(forbidden)
        if matches:
            description = forbidden.get("description", "")
            match_data = {"description": description,
                          "matches": matches}
            matches.append(match_data)

    return matches


def ast_dump(source):
    """
    Returns all AST nodes of source, each dumped on its own line.
    You can use this to experiment what AST node names you want to add to the blacklisted nodes.
    Or install more sophisticated utilities from https://greentreesnakes.readthedocs.io/en/latest/.
    """
    return '\n'.join(map(ast.dump, ast.walk(ast.parse(source))))


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


def get_validation_errors(config, validation_types):
    raise NotImplementedError()
    errors = []
    for validation in validation_types:
        if validation == "python_import":
            # import matplotlib
            # matplotlib.use(MATPLOTLIB_RENDERER_BACKEND)
            # module_name = args.python.split(".py")[0]
            # errors = get_import_errors(module_name)
        elif validation == "image_type":
            image_file = args.image
            image_type = image_file.split(".")[-1]
            errors = get_image_type_errors(image_file, image_type)
        elif validation == "labview":
            filename = args.labview
            errors = get_labview_errors(filename)
        elif validation == "html":
            filename = args.html
            errors = get_html_errors(filename)
    return errors
