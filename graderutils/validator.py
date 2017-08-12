import ast
import sys
import os
import inspect
import importlib
import importlib.util as import_util
import collections

import htmlgenerator


BlacklistMatch = collections.namedtuple("BlacklistMatch", ["filename", "linenumber", "description"])

# TODO: in debug mode, show warning when supplying a blacklist with no check_files, use an assert for now
def get_blacklist_matches(blacklist):
    """
    Search all files in blacklist["check_files"] for blacklisted node names defined in blacklist["node_names"] and blacklisted node dumps in blacklist["node_dumps"].
    See the settings.yaml for examples and format.

    Matches are returned in a list of BlacklistMatch objects/namedtuples.
    If linenumbers are not valid for some node (e.g. function arguments node), -1 is used as the linenumber.
    """
    assert blacklist["check_files"]

    matches = []
    blacklisted_names = blacklist["node_names"].keys()
    blacklisted_dumps = blacklist["node_dumps"].keys()

    for filename in blacklist["check_files"]:
        # TODO: OSErrors not catched
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.read()

        # TODO: SyntaxErrors not catched
        submitted_ast = ast.parse(source)

        # Walk once through the ast of the source of the submitted file, searching for blacklisted stuff.
        for node in ast.walk(submitted_ast):
            node_name = node.__class__.__name__
            node_dump = ast.dump(node)
            linenumber = getattr(node, "lineno", -1)
            if node_name in blacklisted_names:
                matches.append(BlacklistMatch(
                        filename=filename,
                        linenumber=linenumber,
                        description=blacklist["node_names"][node_name]))
            if node_dump in blacklisted_dumps:
                matches.append(BlacklistMatch(
                        filename=filename,
                        linenumber=linenumber,
                        description=blacklist["node_dumps"][node_dump]))

    return matches


def import_module_or_errors(module_name, discard_import_output=False):
    """Tries to import a module named module_name.

    @param: (str) module_name - name of the module to be imported, without file extensions.
    @param: (bool) discard_import_output - (optional) if True, output to stdout and stderr
        at the root of the module will be temporarily directed into devnull.

    @returns: Tuple with 2 elements;
        The imported module and an empty string if the import was successful.
        If the import was not successful, return None and a non-empty string describing
        the error.
    """

    imported_module = None
    error_message = ""

    # Check that an importable module exists
    if import_util.find_spec(module_name) is None:
        # Probably a bit redundant, the MOOC grader should
        # rename submitted files correctly
        # Might be useful for debugging though.
        error_message = "No module named {:s} found on submission server, please contact course staff.".format(module_name)

    else:
        try:
            if discard_import_output:
                # Temporarily redirect stdout and stderr to devnull
                # TODO: maybe save the output to a StringIO instance
                # so it would be possible to notify the submitter that
                # the output has been nulled?
                sys_stdout, sys_stderr = sys.stdout, sys.stderr
                try:
                    devnull = open(os.devnull, "w")
                    sys.stdout, sys.stderr = devnull, devnull
                    imported_module = importlib.import_module(module_name)
                finally:
                    # Make sure stdout and stderr are always switched back.
                    sys.stdout, sys.stderr = sys_stdout, sys_stderr
                    devnull.close()
            else:
                imported_module = importlib.import_module(module_name)

            # Raises OSError if the imported module contains no lines
            inspect.getsource(imported_module)

        except SyntaxError as syntax_error:
            error_message = "The submitted file contains invalid Python syntax at line {:d}:\n".format(syntax_error.lineno) + syntax_error.text

        except OSError:
            error_message = "Could not get source of the submitted file ({}), is it empty?".format(module_name)


        #TODO add more errors here if needed
        except Exception as e:
            error_message = "{}.\n".format(e) +\
                            "Did you return the correct file? Make sure you submitted a text file and not for example compiled bytecode, such as a .pyc file.\n" +\
                            "Check also that you are returning your file to the correct assignment."

    return imported_module, error_message


def validate_module(module_data, blacklist):
    """
    Validates that the module named module_data["name"]:
        * can be imported
        * contains all attribute names as specified in module_data
    If the module can be imported, validate that:
        * the module source does not contain any syntax names as
        specified in the set of strings blacklist

    Returns: dictionary of error messages if there were errors, else empty dictionary.
    """

    errors = dict()

    imported_module, import_error = import_module_or_errors(module_data["name"])

    if imported_module is None:
        errors["import_error"] = import_error
    else:
        attribute_errors = validate_module_attributes(imported_module, module_data)
        if attribute_errors:
            errors["attribute_errors"] = attribute_errors

        forbidden_names = inspect_forbidden_names(imported_module, blacklist)
        if forbidden_names:
            errors["forbidden_names"] = forbidden_names

    return errors


def get_validation_errors(config_module):
    module_data = getattr(config_module, "MODULE", None)
    modules = getattr(config_module, "MODULES", None)
    if not modules:
        if not module_data:
            return None
        modules = [module_data]
    validation_errors = dict()
    # Get set of blacklisted names or an empty set if there are none in config_module
    blacklist = getattr(config_module, "BLACKLIST", set())

    # By default, prevent inspecting of anything in the util directory
    blacklist.add("inspecting_grader_tests")
    for module in modules:
        # Update dict with different modules error messages
        validation_errors.update(validate_module(module, blacklist))
    return validation_errors


if __name__ == "__main__":
    test_config = None
    if import_util.find_spec(TEST_CONFIG_NAME):
        test_config = importlib.import_module(TEST_CONFIG_NAME)

    validation_errors = get_validation_errors(test_config)

    if validation_errors:
        # Render dict with html template
        html_errors = htmlgenerator.errors_as_html(validation_errors)
        print(html_errors, file=sys.stderr)

        # Signal MOOC grader of errors
        sys.exit(1)
