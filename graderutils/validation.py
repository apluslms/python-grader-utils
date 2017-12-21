"""
Simple file validation for various file formats.
Can be used before grading for checking if a file is valid.
May also be useful as a trivial grader to give a point or points for submitting correct filetypes.
Enable by using the 'validation' key in the test_config.yaml.

Detailed examples available in the readme.
"""
import ast
import collections
import html5lib
import imghdr
import importlib
import re

from graderutils.main import GraderUtilsError


class ValidationError(GraderUtilsError): pass

SUPPORTED_VALIDATION_CHOICES = (
        "python_import",
        "python_syntax",
        "python_blacklist",
        "python_whitelist",
        "plain_text_blacklist",
        "plain_text_whitelist",
        "image_type",
        "labview",
        "html")

RestrictedSyntaxMatch = collections.namedtuple("RestrictedSyntaxMatch", ["filename", "linenumber", "line_content", "message"])


def _check_python_restricted_syntax(config, blacklist=True):
    """
    Read config["file"] and search for restricted syntax.
    If blacklist is True, return RestrictedSyntaxMatch objects for every match.
    Else return RestrictedSyntaxMatch for every miss.
    If linenumbers are not valid for some node (e.g. function arguments node), -1 is used as the linenumber.

    See the test_config.yaml for examples and format.
    """
    if "node_names" in config:
        restricted_names = config["node_names"].keys()
    else:
        restricted_names = set()
    if "node_dumps" in config:
        restricted_dumps = config["node_dumps"].keys()
    else:
        restricted_dumps = set()
    if "node_dump_regexp" in config:
        restricted_regexp = [(re.compile(expr), message) for expr, message in config["node_dump_regexp"].items()]
    else:
        restricted_regexp = []

    filename = config["file"]

    with open(filename, encoding="utf-8") as submitted_file:
        source = submitted_file.read() # Note: may raise OSError

    submitted_ast = ast.parse(source) # Note: may raise SyntaxError
    submitted_lines = source.splitlines()

    matches = []

    # Walk once through the ast of the source of the submitted file, searching for black/whitelisted stuff.
    for node in ast.walk(submitted_ast):
        node_name = node.__class__.__name__
        node_dump = ast.dump(node)
        linenumber = getattr(node, "lineno", -1)
        line_content = submitted_lines[linenumber-1] if linenumber > 0 else ""
        if blacklist:
            if node_dump in restricted_dumps:
                # This node has a dump representation that is not allowed.
                message = config["node_dumps"][node_dump]
                matches.append(RestrictedSyntaxMatch(
                        filename, linenumber,
                        line_content, message))
            if node_name in restricted_names:
                # This node has a name that is not allowed.
                message = config["node_names"][node_name]
                matches.append(RestrictedSyntaxMatch(
                        filename, linenumber,
                        line_content, message))
            for pattern, message in restricted_regexp:
                if re.search(pattern, node_dump):
                    # This node has a dump representation that matches a given node dump regular expression.
                    matches.append(RestrictedSyntaxMatch(
                            filename, linenumber,
                            line_content, message))
        else:
            if (node_name not in restricted_names and
                node_dump not in restricted_dumps and
                not any(re.search(pat, node_dump) for pat, _ in restricted_regexp)):
                # This node has a name or dump representation that is not allowed.
                message = node_name
                matches.append(RestrictedSyntaxMatch(
                        filename, linenumber,
                        line_content, message))

    return matches


def _check_plain_text_restricted_syntax(config, blacklist=True):
    """
    As in _check_python_restricted_syntax but for plain text strings.
    No sophisticated tokenization is done for the source text and it is checked by simple regular expressions.
    If blacklisting, return every line which contains a word which is in config["strings"]
    If whitelisting, return every line which contains a word which is not in config["strings"].
    """
    def re_split_no_keep(pattern, string):
        """Return an iterator over `string` which yields substrings that do not match `pattern`."""
        for word in re.split(pattern, string):
            word = word.strip()
            if word and not re.match(pattern, word):
                yield word

    matches = []
    config_strings = config["strings"].keys()
    ignorecase = config.get("ignorecase", False)

    filename = config["file"]

    with open(filename, encoding="utf-8") as submitted_file:
        source = submitted_file.readlines()

    pattern_string = "(" + "|".join(config_strings) + ")"
    pattern = re.compile(pattern_string, re.IGNORECASE if ignorecase else 0)

    for line_number, line in enumerate(source, start=1):
        if blacklist:
            for line_match in re.findall(pattern, line):
                key = line_match if not ignorecase else line_match.lower()
                message = config["strings"][key]
                matches.append(RestrictedSyntaxMatch(
                    filename, line_number,
                    line, message))
        else:
            # Split at matches and do not keep split strings
            for line_miss in re_split_no_keep(pattern, line):
                matches.append(RestrictedSyntaxMatch(
                    filename, line_number,
                    line, line_miss))

    return matches


def _get_python_blacklist_matches(blacklist):
    return _check_python_restricted_syntax(blacklist, blacklist=True)


def _get_python_whitelist_misses(whitelist):
    return _check_python_restricted_syntax(whitelist, blacklist=False)


def _get_plain_text_blacklist_matches(blacklist):
    return _check_plain_text_restricted_syntax(blacklist, blacklist=True)


def _get_plain_text_whitelist_misses(whitelist):
    return _check_plain_text_restricted_syntax(whitelist, blacklist=False)


def get_restricted_syntax_matches(config, get_matches):
    match_data = {}
    matches = get_matches(config)
    if matches:
        message = config.get("message", "")
        match_data = {"type": "restricted_syntax",
                      "message": message,
                      "matches": matches}
    return match_data


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


def _import_module_from_python_file(filename):
    return importlib.import_module(filename.split(".py")[0])


def get_python_import_errors(filename):
    errors = {}
    try:
        _import_module_from_python_file(filename)
    except Exception as error:
        errors["type"] = error.__class__.__name__
        errors["message"] = str(error)
    return errors


def _hasattr_path(obj, attr_path):
    """
    Return True if obj has some attr path.
    >>> # object().__class__
    >>> _hasattr_path(object(), "__class__")
    True
    >>> # object().__class__.__class__
    >>> _hasattr_path(object(), "__class__.__class__")
    True
    >>> # object().x.y
    >>> _hasattr_path(object(), "x.y")
    False
    """
    for attr in attr_path.split("."):
        obj = getattr(obj, attr, None)
        if obj is None:
            return False
    return True


def get_python_missing_attr_errors(filename, expected_attributes):
    errors = {}
    module = _import_module_from_python_file(filename)
    missing_attrs = [(path, msg) for path, msg in expected_attributes.items()
                     if not _hasattr_path(module, path)]
    if missing_attrs:
        errors["type"] = "missing attributes"
        errors["missing_attrs"] = missing_attrs
    return errors


def get_python_syntax_errors(filename):
    errors = {}
    try:
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.read()
        ast.parse(source)
    except SyntaxError as syntax_error:
        errors["type"] = "SyntaxError"
        errors["filename"] = syntax_error.filename
        errors["lineno"] = syntax_error.lineno
        errors["text"] = syntax_error.text
    except Exception as error:
        errors["type"] = "Exception"
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


def get_validation_errors(validation_configs):
    errors = []
    for config in validation_configs:
        validation_type = config.get("type", None)
        filename = config.get("file", None)
        break_on_fail = config.get("break_on_fail", True)
        if not filename:
            raise ValidationError("No file given to perform validation of validation_type '{}'.".format(validation_type))

        error = {}

        if validation_type == "python_import":
            # import matplotlib
            # matplotlib.use(MATPLOTLIB_RENDERER_BACKEND)
            error = get_python_import_errors(filename)
            if not error and "attrs" in config:
                # Import succeeded, now check that module has all required attributes.
                error = get_python_missing_attr_errors(filename, config["attrs"])

        elif validation_type == "python_syntax":
            error = get_python_syntax_errors(filename)

        elif validation_type == "python_blacklist":
            get_matches = _get_python_blacklist_matches
            error = get_restricted_syntax_matches(config, get_matches)

        elif validation_type == "python_whitelist":
            get_matches = _get_python_whitelist_misses
            error = get_restricted_syntax_matches(config, get_matches)

        elif validation_type == "plain_text_blacklist":
            get_matches = _get_plain_text_blacklist_matches
            error = get_restricted_syntax_matches(config, get_matches)

        elif validation_type == "plain_text_whitelist":
            get_matches = _get_plain_text_whitelist_misses
            error = get_restricted_syntax_matches(config, get_matches)

        elif validation_type == "image_validation_type":
            error = get_image_type_errors(filename)

        elif validation_type == "labview":
            error = get_labview_errors(filename)

        elif validation_type == "html":
            error = get_html_errors(filename)

        else:
            raise ValidationError("Unknown validation_type '{}', choose from '{}'.".format(validation_type, SUPPORTED_VALIDATION_CHOICES))

        if error:
            errors.append(error)
            if break_on_fail:
                break

    return errors

