import sys
import os
import inspect
import importlib
import importlib.util as import_util
import itertools

import astparser
import htmlgenerator
from constants import GRAMMAR_NAMES

TEST_CONFIG_NAME = "test_config"

class ImportValidationError(Exception): pass


def inspect_forbidden_names(imported_module, blacklist):
    """Inspects if an imported module contains syntax names given in blacklist (set of strings).
    Returns a dictionary of errors containing the forbidden name, line number
    where it was encountered and the content of that line.
    If there are no errors, returns an empty dictionary.

    If blacklist contains a key which does not exist in GRAMMAR_NAMES, insert
    that key into GRAMMAR_NAMES with the value as a set with the key as the only element.

    For example:

    blacklist contains a string that makes importing the module 'model_solution' forbidden:
    "Import:model_solution". If this string has not been added to GRAMMAR_NAMES,
    "Import:model_solution" will be inserted to GRAMMAR_NAMES at key "Import:model_solution"
    with the value { "Import:model_solution" }.

    This allows the dynamical addition of blacklisted names for which there is no
    reason to add into constants.GRAMMAR_NAMES.
    """
    errors = []

    # Whole source as string, except if it is empty
    try:
        source = inspect.getsource(imported_module)
    except OSError:
        # getsouce could not read anything, the module is probably empty
        return

    # If set blacklist contains elements which are not in GRAMMAR_NAMES.keys(),
    # add them temporarily to GRAMMAR_NAMES
    for new_name in blacklist - GRAMMAR_NAMES.keys():
        GRAMMAR_NAMES[new_name] = { new_name }

    # Source as lines for extracting specific lines at a given line number
    sourcelines, linenostart = inspect.getsourcelines(imported_module)
    # Parse source string and get a dictionary with keys being names
    # used in source and values set of linenumbers where name was used in source
    name_at_lines = astparser.traverse_source_string(source)

    for forbidden_name in blacklist:
        # Intersect set of the names of all possible representations of the
        # forbidden_name with all names that were used in source
        used_forbidden_names = GRAMMAR_NAMES[forbidden_name] & name_at_lines.keys()

        if used_forbidden_names:
            # Iterator of all linenumbers where forbidden_name was used
            iter_all_linenumbers = itertools.chain(*(name_at_lines[f_name] for f_name in used_forbidden_names))

            for lineno in iter_all_linenumbers:
                # The ast parser returns linenumbers starting from 1 while
                # inspect getsourcelines starts from 0
                line_number_index = linenostart + lineno - 1

                errors.append({
                    "name": forbidden_name,
                    "lineno": line_number_index,
                    "line_content": sourcelines[line_number_index].strip()
                })

    return errors


# NOTE: validate_module_attributes checks only the module root.
def validate_module_attributes(imported_module, module_data):
    """Validate that an imported module contains all attributes at its root as given in module_data.
    Returns a list of error messages for each attribute which does not exist in the module.
    Returns an empty list if the module contains all required attributes.

    module_data should be a dictionary with the required attributes:

    { "name":
        "module_one",

      "functions": [
        "function_one",
        "function_two", #...
      ],

      "classes": [
        "class_one",
        "class_two", #...
      ]}
    """

    errors = []

    def validate_attribute(attr_key, attr_type_name, inspect_method):
        """Iterate list of attribute names which are mapped to key attr_key
        in module_data and append error messages to import_errors if an
        attribute name is not found in the imported module."""
        def recur_getattr(obj, attrs):
            """Recursively get an attribute from a list of attribute names.
            For example, calling recur_getattr(module, ['A', 'b'])
            returns module.A.b, if it exists."""
            if len(attrs) < 1:
                return obj
            if hasattr(obj, attrs[0]):
                return recur_getattr(getattr(obj, attrs[0]), attrs[1:])
            else:
                return None

        for attr_name in module_data[attr_key]:
            attr_names = attr_name.split(".")
            attr = recur_getattr(imported_module, attr_names)
            if attr is None or not inspect_method(attr):
                error = { "type": attr_type_name, "attribute_name": attr_name }
                errors.append(error)

    if "functions" in module_data:
        validate_attribute("functions", "function", inspect.isfunction)

    if "classes" in module_data:
        validate_attribute("classes", "class", inspect.isclass)

    if "generators" in module_data:
        validate_attribute("generators", "generator function", inspect.isgeneratorfunction)

    return errors


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
            error_message = "Could not get source of the submitted file, is it empty?"

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

