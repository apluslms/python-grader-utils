import ast
import copy
import functools
import importlib
import inspect
import operator
import os
import random
import re
import sys
import traceback
from contextlib import contextmanager
from io import StringIO

from graderutils import GraderUtilsError
from graderutils import remote
from graderutils.diff_match_patch import diff_match_patch
from graderutils.graderunittest import result_or_timeout
from graderutils.remote import GraderConnClosedError
from graderutils.remote import GraderImportError
from graderutils.remote import GraderIOError
from graderutils.remote import GraderOpenError


exercise_path = os.getenv("EXERCISE_PATH", "/exercise")
generated_path = os.getenv("GENERATED_PATH", "/generated")
model_path = os.getenv("MODEL_PATH", "/model")
student_path = os.getenv("PWD", "/submission/user")

DEFAULT_SETTINGS = {
    # Maximum amount that floating-point numbers are allowed to differ (+-)
    # in submission output/return value and model output/return value
    "max_float_delta": 0.02,
    # Maximum amount that integer numbers are allowed to differ (+-)
    # in submission output/return value and model output/return value
    "max_int_delta": 0,
    # Maximum student/model program execution time in seconds (integer)
    "max_exec_time": 30,
    # Characters that should not trigger an AssertionError when comparing outputs
    "ignored_characters": ['.', ',', '!', '?', ':', ';', '\''],
    # Libraries that are allowed to be imported. Use list ['*'] to whitelist all libraries.
    "import_whitelist": [
        "collections",
        "copy",
        "csv",
        "datetime",
        "decimal",
        "functools",
        "itertools",
        "math",
        "numbers",
        "random",
        "re",
        "statistics",
        "string",
        "time",
    ],
    # Libraries that are not allowed to be imported. Use list ['*'] to blacklist all libraries.
    "import_blacklist": [],
    # Files that are allowed to be opened. Use list ['*'] to whitelist all files.
    "open_whitelist": [],
    # Files that are not allowed to be opened. Use list ['*'] to blacklist all files.
    "open_blacklist": ['*'],
}

# Feedback fields separator string
SEPARATOR_STRING = '=' * 55

# Feedback fields separator string with html class for coloring
SEPARATOR = '<span class="iotester-basic">{:s}</span>'.format(SEPARATOR_STRING)

# Maximum number of output characters shown (timeout or not)
MAX_OUTPUT_LENGTH = 100000

# Maximum number of output lines shown when program execution is not timed out
MAX_OUTPUT_LINES = 1000

# Maximum number of output lines shown when program execution is timed out
MAX_OUTPUT_LINES_ON_TIMEOUT = 50

# Marker used for finding where user input begins in a given output
IOTESTER_INPUT_BEGIN = "[iotester-input-begin]"

# Marker used for finding where user input ends in a given output
IOTESTER_INPUT_END = "[iotester-input-end]"

# Placeholder replaced with < in output html
IOTESTER_NO_ESCAPE_LT = "[iotester-no-escape-lt]"

# Placeholder replaced with > in output html
IOTESTER_NO_ESCAPE_GT = "[iotester-no-escape-gt]"

# Placeholder replaced with a space in output html
IOTESTER_NO_ESCAPE_NBSP = "[iotester-no-escape-nbsp]"

# Used for replacing numbers in complete_output_test
IOTESTER_NUMBER = "[iotester-number]"

# Used for replacing numbers in complete_output_test where a minus check has to be performed
IOTESTER_MINUS_CHECK = "[iotester-minus-check]"

# This constant can be used when passing inputs to a test.
# It represents inputting nothing (pressing the Enter key).
ENTER = "[iotester-enter]"

# This string is shown in feedback in places where the ENTER constant was used as input
ENTER_STRING = (
    '{0}kbd{1}Enter{0}/kbd{1}'.format(
        IOTESTER_NO_ESCAPE_LT,
        IOTESTER_NO_ESCAPE_GT,
    )
)

# Feedback colors info
MSG_COLOR_INCORRECT = "Incorrect"
MSG_COLOR_CORRECT = "Correct/Missing"
MSG_COLOR_INPUT = "Input"

# Feedback messages
MSG_MODEL_ERROR = (
    "Above exception occurred during execution of\n"
    "the model program. Please notify course staff."
)

MSG_BASIC_ERROR = "An error occurred during the tests."

MSG_BASIC_FAIL = "Your program did not pass this test."

MSG_BASIC_ASSERT = (
    "Your program did not pass the assertion "
    "(comparison) of values."
)

MSG_TEXT = "The text in your output didn't match the expected output."

MSG_NUMBERS = "The numbers in your output didn't match the expected numbers."

MSG_RETURN_VALUE = "A return value didn't match the expected return value."

MSG_FILE_DATA = (
    "The data in the file your program created\n"
    "didn't match the expected data."
)

MSG_FILE_NOT_FOUND = "Your program didn't create a file with the correct name."

MSG_OSERROR = "The file created by your program could not be read."

MSG_WHITESPACE = (
    "The whitespace (spaces and line breaks) in your output\n"
    "didn't match the expected whitespace."
)

MSG_NO_OUTPUT = "Your program should not print anything."

MSG_RANDOM_STATE = (
    "The state of the random number generator didn't match the expected state.\n"
    "Check that the seed is converted into an integer "
    "before setting it."
)

MSG_FUNCS_AMOUNT_GT = (
    "Your program was expected to have more than {:d} functions,\n"
    "but only {:d} were found."
)

MSG_FUNCS_AMOUNT_LT = (
    "Your program was expected to have less than {:d} functions,\n"
    "but {:d} were found."
)

MSG_FUNCS_AMOUNT_GE = (
    "Your program was expected to have at least {:d} functions,\n"
    "but only {:d} were found."
)

MSG_FUNCS_AMOUNT_LE = (
    "Your program was expected to have at most {:d} functions,\n"
    "but {:d} were found."
)

MSG_FUNCS_AMOUNT_EQ = (
    "Your program was expected to have exactly {:d} functions,\n"
    "but {:d} were found."
)

MSG_FUNCS_AMOUNT_PASS = (
    "The amount of functions in your program\n"
    "fulfilled the requirements."
)

MSG_OBJECT_ATTRS = "The attributes of your object did not match the expected attributes."

MSG_OBJECT_ATTRS_PASS = "The attributes of your object matched the expected attributes."

MSG_STRUCTURE_PASS = "The structure of your class fulfilled the requirements."

MSG_OBJECT_ATTRS_MISSING = "Your object is missing one or more of the required attributes."

MSG_OBJECT_ATTRS_TYPE = (
    "One or more of the required attributes\n"
    "in your object are of the wrong type."
)

MSG_CLASS_ATTRS_MISSING = (
    "Your class is missing one or more of the\n"
    "required methods, functions or variables."
)

MSG_CLASS_ATTRS_TYPE = (
    "One or more of the required methods, functions or\n"
    "variables in your class are of the wrong type."
)

MSG_EXTRA_OBJECT_ATTRS = (
    "Your object has extra attributes that are not allowed:"
    "{:s}"
)

MSG_EXTRA_CLASS_ATTRS = (
    "Your class has extra methods, functions or variables that are not allowed:"
    "{:s}"
)

MSG_INIT_DESC = "Creating a {!r} object."

MSG_SYSTEMEXIT = (
    "Grader does not support the usage of sys.exit(), exit() or quit().\n"
    "Try changing your code so that you don't need to use those."
)

MSG_KEYBOARDINTERRUPT = "Grader does not support raising KeyboardInterrupt."

MSG_MAIN_CALL_NOT_FOUND = (
    "Function main() was found but it was not called.\n"
    "Make sure that you remember to call the main() function\n"
    "and that the function call is correctly indented."
)

MSG_FUNCTION_NOT_FOUND = (
    "Function {!r} was not found. Make sure that you\n"
    "have defined the function with the correct name."
)

MSG_CLASS_NOT_FOUND = (
    "Class {!r} was not found. Make sure that you\n"
    "have defined the class with the correct name."
)

MSG_ATTRIBUTEERROR = (
    "There was an error in calling a function.\n"
    "Make sure that the function has been defined\n"
    "and that you are calling it with the correct name."
)

MSG_UNBOUNDLOCALERROR = (
    "A variable was referenced before it was assigned.\n"
    "Make sure that you have assigned a value for the variable before using it."
)

MSG_NAMEERROR = (
    "A variable was referenced before it was defined.\n"
    "Make sure that you have defined the variable before using it."
)

MSG_EOFERROR = (
    "Your program most likely asked the user for input\n"
    "more times than it should have."
)

MSG_VALUEERROR_1 = "The element you tried to remove from a list didn't exist in the list."

MSG_VALUEERROR_2 = "Your code contains null characters, which you have to remove."

MSG_VALUEERROR_3 = (
    "You probably made a mistake in the conversion\n"
    "to a numerical value or in the formatting of the output.\n"
    "Check that the variables you are trying to\n"
    "convert/format are of the correct type."
)

MSG_GRADER_TIMEOUT = (
    "The execution of your program timed out after {:d} seconds.\n"
    "Your code may be stuck in an infinite loop or it runs very slowly."
)

MSG_GRADER_BUFFER = (
    "Allocated buffer space for output exceeded.\n"
    "The output of your program is too long.\n"
    "Your code may be stuck in an infinite loop."
)

MSG_GRADER_CONN_CLOSED = (
    "Grader cannot complete this test because connection\n"
    "to the child process was closed earlier.\n"
    "Your code may have got stuck in an infinite loop,\n"
    "it runs very slowly or KeyboardInterrupt was raised."
)

MSG_GRADER_IMPORT = (
    "An error occured while executing an import command:\n"
    "Use of the module {!r} is forbidden."
)

MSG_GRADER_OPEN_READ = (
    "An error occurred while opening a file:\n"
    "File {!r} does not exist\n"
    "or read permissions for it are denied."
)

MSG_GRADER_OPEN_WRITE = (
    "An error occurred while opening a file:\n"
    "File {!r} does not exist\n"
    "or write permissions for it are denied."
)

MSG_GRADER_OPEN_MODE = (
    "An error occurred while opening a file:\n"
    "Invalid file mode: {!r}"
)

MSG_TIMEOUTERROR = (
    "A TimeoutError occurred.\n"
    "Make sure that your code performs as expected."
)

MSG_INDEXERROR_LIST = (
    "There was an error when attempting to retrieve an element from a list.\n"
    "Make sure that you are not indexing past the length of the list."
)

MSG_INDEXERROR_TUPLE = (
    "There was an error when attempting to retrieve an element from a tuple.\n"
    "Make sure that you are not indexing past the length of the tuple."
)

MSG_INDEXERROR_STRING = (
    "There was an error when attempting to retrieve a character from a string.\n"
    "Make sure that you are not indexing past the length of the string."
)

MSG_KEYERROR = (
    "Your program attempted to retrieve a value from a dictionary\n"
    "but the key was not in the dictionary."
)

MSG_UNICODEDECODEERROR = (
    "Your code contains non-ASCII characters (å, ä, ö, etc.)\n"
    "that are not supported."
)

MSG_SYNTAXERROR = "Your code contains invalid syntax."

MSG_INDENTATIONERROR = "Your code is indented incorrectly."

MSG_TABERROR = (
    "You have mixed together spaces and tabs in the indentations of your code.\n"
    "Use one or the other."
)

MSG_ZERODIVISIONERROR = (
    "An error occurred during number division.\n"
    "Make sure you are not trying to divide by zero."
)

MSG_TYPEERROR = (
    "A TypeError occurred when calling a function/operator.\n"
    "Check that a correct amount of parameters is given\n"
    "and that they are of the correct type."
)

MSG_RECURSIONERROR = (
    "Maximum recursion depth exceeded.\n"
    "Check that your program doesn't get stuck in a recursive loop."
)

MSG_IMPORTERROR = "An error occured while executing an import statement."

MSG_MODULENOTFOUNDERROR = (
    "An error occured while executing an import statement:\n"
    "{:s}"
)

MSG_FILENOTFOUNDERROR = (
    "An error occured while attempting to open a file:\n"
    "{:s}"
)

MSG_STR_CALL_TEST = (
    "You have called the __str__ method in your code directly!\n"
    "The __str__ method is not meant to be used this way.\n\n"
    "For example, by writing print({:s})\n"
    "the string returned by the __str__ method of\n"
    "the object {:s} is printed.\n\n"
    "The method has such a weird name so that the Python\n"
    "interpreter finds it automatically."
)

# Messages to be formatted
MSG_CLASS_NAME = "Tested class: {:s}"

MSG_NAME_TESTED = "Tested function/method: {:s}"

MSG_FILE_NAME = "Tested file: {:s}"

MSG_OUTPUT = (
    "Your output:"
    "{:s}"
)

MSG_ASSERT_REASON = (
    "Reason of failure:"
    "{:s}"
)

MSG_ASSERT_LINE = (
    "Failed assertion/line:"
    "{:s}"
)

MSG_ASSERT_RESULT = (
    "Result:"
    "{:s}"
)

MSG_DESCRIPTION = (
    "Description of test:"
    "{:s}"
)

MSG_FUNCS_FOUND = (
    "Found functions:"
    "{:s}"
)

MSG_OUTPUT_DIFF = (
    "Your output:"
    "{:s}"
    "\n" + SEPARATOR + "\n"
    "Expected output:"
    "{:s}"
)

MSG_RETURN_VALUE_DIFF = (
    "Your return value:"
    "{:s}"
    "\n" + SEPARATOR + "\n"
    "Expected return value:"
    "{:s}"
)

MSG_FILE_DATA_DIFF = (
    "Data in your file:"
    "{:s}"
    "\n" + SEPARATOR + "\n"
    "Expected data:"
    "{:s}"
)

MSG_OBJECT_ATTRS_DIFF = (
    "Attributes of your object:"
    "{:s}"
    "\n" + SEPARATOR + "\n"
    "Expected attributes of the object:"
    "{:s}"
)

MSG_CLASS_ATTRS_DIFF = (
    "Attributes of your class:"
    "{:s}"
    "\n" + SEPARATOR + "\n"
    "Expected attributes of the class:"
    "{:s}"
)

MSG_USED_INPUTS_AND_PARAMS = (
    "Used input:"
    "{:s}"
    "\n" + SEPARATOR + "\n"
    "Used parameter values:"
    "{:s}"
)

MSG_PYTHON_VERSION = (
    '<span class="grader-info">Python {:d}.{:d}.{:d}</span>'.format(
        sys.version_info[0],
        sys.version_info[1],
        sys.version_info[2],
    )
)

MSG_COLORS = (
    '<span class="iotester-incorrect">  </span><span> {:s}       </span>'
    '<span class="iotester-correct">  </span><span> {:s}       </span>'
    '<span class="iotester-input">  </span><span> {:s}</span>'.format(
        MSG_COLOR_INCORRECT,
        MSG_COLOR_CORRECT,
        MSG_COLOR_INPUT,
    )
)

_builtin_import = __builtins__["__import__"]
_builtin_open = __builtins__["open"]
_builtin_input = __builtins__["input"]


def _combine_feedback(strings=[]):
    feedback = ""
    add_separator = False
    for string in strings:
        if len(string) > 0:
            if add_separator:
                feedback += "\n{:s}\n".format(SEPARATOR)
            feedback += string
            add_separator = True
    return feedback


def _escape_html_chars(string):
    escaped_string = string.replace("&", "&amp;")
    escaped_string = escaped_string.replace("<", "&lt;")
    escaped_string = escaped_string.replace(">", "&gt;")
    escaped_string = escaped_string.replace(" ", "&nbsp;")
    escaped_string = escaped_string.replace(IOTESTER_NO_ESCAPE_LT, "<")
    escaped_string = escaped_string.replace(IOTESTER_NO_ESCAPE_GT, ">")
    escaped_string = escaped_string.replace(IOTESTER_NO_ESCAPE_NBSP, " ")
    return escaped_string


# Customized diff_prettyHtml from diff_match_patch
def _diff_prettyHtml(dmp, diffs, type, hide_newlines):
    diff_html = []
    for (op, data) in diffs:
        data = _escape_html_chars(data)
        if hide_newlines:
            data = data.replace('\n', "<br>")
        else:
            data = data.replace('\n', '<span class="iotester-basic">\\n</span><br>')
        if op == dmp.DIFF_INSERT and type == "insert":
            diff_html.append('<span class="iotester-correct">%s</span>' % data)
        elif op == dmp.DIFF_DELETE and type == "delete":
            diff_html.append('<span class="iotester-incorrect">%s</span>' % data)
        elif op == dmp.DIFF_EQUAL:
            diff_html.append('<span>%s</span>' % data)
    diff_html = ''.join(diff_html)
    return diff_html


def _get_diff_html(output, expected_output, type, hide_newlines):
    dmp = diff_match_patch()
    dmp.Match_Threshold = 0.0
    dmp.Match_Distance = 0
    dmp.Patch_DeleteThreshold = 0.0
    diff_html = ""
    output_split = output.split(IOTESTER_INPUT_END)
    expected_output_split = expected_output.split(IOTESTER_INPUT_END)
    for i in range(len(output_split)):
        part = output_split[i]
        part_split = part.split(IOTESTER_INPUT_BEGIN)
        try:
            expected_part = expected_output_split[i]
            expected_part_split = expected_part.split(IOTESTER_INPUT_BEGIN)
        except IndexError:
            expected_part = ""
            expected_part_split = [""]
        if len(part_split) == 2:
            output_before = part_split[0]
            expected_output_before = expected_part_split[0]
            diffs = dmp.diff_main(output_before, expected_output_before)
            dmp.diff_cleanupSemantic(diffs)
            diff_html += _diff_prettyHtml(dmp, diffs, type, hide_newlines)
            if type == "delete":
                inputs = part_split[1]
                inputs = _escape_html_chars(inputs)
                diff_html += inputs
            elif type == "insert" and len(expected_part_split) == 2:
                expected_inputs = expected_part_split[1]
                expected_inputs = _escape_html_chars(expected_inputs)
                diff_html += expected_inputs
        else:
            output_after = part_split[0]
            expected_output_after = (
                ''.join(expected_output_split[i:])
                    .replace(IOTESTER_INPUT_BEGIN, '')
                    .replace(IOTESTER_INPUT_END, '')
            )
            diffs = dmp.diff_main(output_after, expected_output_after)
            dmp.diff_cleanupSemantic(diffs)
            diff_html += _diff_prettyHtml(dmp, diffs, type, hide_newlines)

    # Remove last <br>
    if diff_html.endswith("<br>"):
        diff_html = diff_html[:-4]
    if len(diff_html) >= 11 and diff_html[-11:-7] == "<br>":
        diff_html = diff_html[:-11] + diff_html[-7:]

    return diff_html


def _get_numbers_from_string(string):
    """
    Return a list of numbers (strings) that appear in parameter string.
    Match integers, decimals and numbers such as +1, 2e9, +2E+09, -2.0e-9.
    """
    numbers = re.findall(r"[-+]?(?:(?:\d+\.\d+)|(?:\d+))(?:[Ee][+-]?\d+)?", string)
    return numbers


def _strip_string(
        string,
        numbers,
        ignored_characters,
        strip_numbers,
        strip_whitespace,
        minus_check_indexes=[],
        ):
    chars_to_skip = ignored_characters.copy()
    if strip_whitespace:
        chars_to_skip.extend([' ', '\n'])
    stripped_string = ""
    for i in range(len(numbers)):
        s = 0
        e = len(numbers[i])
        while string[s:e] != numbers[i]:
            s += 1
            e += 1
        substring = string[0:s]
        for char in chars_to_skip:
            if char in substring:
                substring = substring.replace(char, '')
        stripped_string += substring
        if not strip_numbers:
            if i in minus_check_indexes:
                stripped_string += IOTESTER_MINUS_CHECK
            else:
                stripped_string += IOTESTER_NUMBER
        string = string[e:]
    if string != "":
        substring = string
        for char in chars_to_skip:
            if char in substring:
                substring = substring.replace(char, '')
        stripped_string += substring
    return stripped_string


def _whitespace_minus_check_patch(string1, string2):
    pattern = re.compile("(\s*" + re.escape(IOTESTER_MINUS_CHECK) + "\s*)")
    match1 = re.findall(pattern, string1)
    match2 = re.findall(pattern, string2)
    for i in range(len(match1)):
        if match2[i].count(' ') - match1[i].count(' ') in [-1, 0, 1]:
            string1 = string1.replace(match1[i], match2[i])
    return string1, string2


def _prepend_newline(string):
    if string:
        return '\n' + string
    return ""


def _remove_last_newline(string):
    if string.endswith('\n'):
        # rstrip() is not used because we want to remove only one newline
        return string[:-1]
    return string


def _inputs_to_str(inputs=[]):
    inputs_str = '\n'.join(str(elem) if elem is not ENTER else ENTER_STRING for elem in inputs)
    inputs_str = _escape_html_chars(inputs_str)
    return inputs_str


def _params_to_str(args=(), kwargs={}):
    params = []
    for arg in args:
        params.append(repr(arg))
    for key, value in kwargs.items():
        params.append(str(key) + '=' + repr(value))
    params_str = ", ".join(params)
    params_str = _escape_html_chars(params_str)
    return params_str


def _verify_permissions(name, whitelist, blacklist):
    # Check if name is allowed to be imported/opened
    whitelist_enabled = bool(whitelist)
    if whitelist_enabled:
        all_whitelisted = '*' in whitelist
        allowed = all_whitelisted or name in whitelist
    else: # Blacklist is enabled
        all_blacklisted = '*' in blacklist
        allowed = not all_blacklisted and name not in blacklist
    return allowed


def _get_import(module_name, model):
    if model:
        # Inserting model_path to sys.path allows the model to import other modules from model_path
        sys.path.insert(0, model_path)
        # Using spec so model answer can be imported from model_path
        path = os.path.join(model_path, module_name + ".py")
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        # Rpyc does not execute student answer in a separate process when using spec like above.
        # This imports student answer from student_path using rpyc.
        module = importlib.import_module(module_name)
        # Alternative code that works with rpyc:
        #path = os.path.join(student_path, module_name + ".py")
        #for meta_path_finder in sys.meta_path:
        #   if type(meta_path_finder) is RPCImport: # from graderutils.remote import RPCImport
        #       meta_path_finder.find_module(module_name, path)
        #       return meta_path_finder.create_module(None)
    return module


class MainCallNotFoundError(GraderUtilsError):
    pass


class FunctionNotFoundError(GraderUtilsError):
    pass


class ClassNotFoundError(GraderUtilsError):
    pass


class GraderTimeoutError(GraderUtilsError):
    pass


class LimitedBuffer(StringIO):

    def __init__(self, buffer=None, max_size=100000):
        super().__init__(buffer)
        self.max_size = max_size


    def write(self, string):
        if self.tell() + len(string) > self.max_size:
            raise GraderIOError(MSG_GRADER_BUFFER)
        return StringIO.write(self, string)


class IOTester:

    def __init__(self, settings={}):
        self.settings = DEFAULT_SETTINGS.copy()
        # Overwrite some or all of the default settings with provided settings
        self.update_settings(settings)
        # Maximum program execution time in seconds (stops test in case of an infinite while-loop)
        self._used_model_modules = []
        self._created_files = set()
        self._out = LimitedBuffer(max_size=MAX_OUTPUT_LENGTH)
        self._save()


    def update_settings(self, settings={}):
        if "import_whitelist" in settings or "import_blacklist" in settings:
            # Clear previous import_whitelist and import_blacklist if they are provided by the user
            self.settings["import_whitelist"] = []
            self.settings["import_blacklist"] = []
        if "open_whitelist" in settings or "open_blacklist" in settings:
            # Clear previous open_whitelist and open_blacklist if they are provided by the user
            self.settings["open_whitelist"] = []
            self.settings["open_blacklist"] = []

        # Overwrite previous settings with the provided settings keeping
        # previous values for the settings that are not given.
        self.settings.update(settings)
        self._verify_settings()


    def _verify_settings(self):
        assert isinstance(self.settings["max_float_delta"], float), (
            "Setting 'max_float_delta' should be a float"
        )
        assert isinstance(self.settings["max_int_delta"], int), (
            "Setting 'max_int_delta' should be an integer"
        )
        assert isinstance(self.settings["max_exec_time"], int), (
            "Setting 'max_exec_time' should be an integer"
        )
        assert isinstance(self.settings["ignored_characters"], list), (
            "Setting 'ignored_characters' should be a list"
        )
        assert isinstance(self.settings["import_whitelist"], list), (
            "Setting 'import_whitelist' should be a list"
        )
        assert isinstance(self.settings["import_blacklist"], list), (
            "Setting 'import_blacklist' should be a list"
        )
        assert isinstance(self.settings["open_whitelist"], list), (
            "Setting 'open_whitelist' should be a list"
        )
        assert isinstance(self.settings["open_blacklist"], list), (
            "Setting 'open_blacklist' should be a list"
        )
        # Verify that import_whitelist or import_blacklist is active
        assert self.settings["import_whitelist"] or self.settings["import_blacklist"], (
            "Use list ['*'] to whitelist or blacklist all imports"
        )
        # Verify that open_whitelist or open_blacklist is active
        assert self.settings["open_whitelist"] or self.settings["open_blacklist"], (
            "Use list ['*'] to whitelist or blacklist opening of all files "
            "outside of the module's directory"
        )
        # Verify that both import_whitelist and import_blacklist are not active at the same time
        assert (bool(self.settings["import_whitelist"])
            and bool(self.settings["import_blacklist"])) == False, (
            "Only 'import_whitelist' or 'import_blacklist' should contain elements"
        )
        # Verify that both open_whitelist and open_blacklist are not active at the same time
        assert (bool(self.settings["open_whitelist"])
            and bool(self.settings["open_blacklist"])) == False, (
            "Only 'open_whitelist' or 'open_blacklist' should contain elements"
        )


    def _save(self):
        """
        Save random number generator state, sys.path, sys.modules in grader and student
        process, and student process built-in input() since they will be restored
        before and after importing and executing student/model code.

        TestCase's tearDown should call restore() to make sure that these variables
        are correctly set after running a test method that did not use IOTester.
        """
        self.previous = {
            "random_state": random.getstate(),
            "sys_path": sys.path.copy(),
            "sys_modules": sys.modules.copy(),
            "remote_random_state": remote.conn.modules.sys.modules["random"].getstate() if remote.conn else None,
            "remote_sys_path": remote.conn.modules.sys.path.copy() if remote.conn else [],
            "remote_sys_modules": remote.conn.modules.sys.modules.copy() if remote.conn else {},
            "remote_builtin_input": remote.conn.builtins.input if remote.conn else None,
        }
        if remote.conn:
            # These are needed in _iotester_import so they are bound to remote.conn instead
            remote.conn._builtin_import = remote.conn.builtins.__import__
            # The below line causes importlib to be imported in student process
            # so that we can avoid RecursionError later in _iotester_import.
            remote.conn._importlib = remote.conn.modules.importlib


    def restore(self, clean_up_files=True):
        # Restore built-in __import__()
        __builtins__["__import__"] = _builtin_import
        # Restore built-in open()
        __builtins__["open"] = _builtin_open
        # Restore built-in input()
        __builtins__["input"] = _builtin_input
        # Restore previous sys.path
        sys.path = self.previous["sys_path"].copy()
        # Remove imported modules from sys.modules.
        # Modules are unloaded so that input/output can be fed/captured on
        # module-level again by doing a complete re-import.
        modules_to_unload = []
        for m in sys.modules:
            if m not in self.previous["sys_modules"]:
                modules_to_unload.append(m)
        for m in modules_to_unload:
            del sys.modules[m]

        if remote.conn and not remote.conn.closed:
            try:
                # Restore built-in __import__() in student process
                remote.conn.builtins.__import__ = remote.conn._builtin_import
                # Restore built-in input() in student process
                remote.conn.builtins.input = self.previous["remote_builtin_input"]
                # Restore previous random state in student process
                remote.conn.modules.sys.modules["random"].setstate(self.previous["remote_random_state"])
                # Restore previous sys.path in student process
                remote.conn.modules.sys.path = self.previous["remote_sys_path"].copy()
                # Remove imported modules from sys.modules in student process.
                # Modules are unloaded so that input/output can be fed/captured on
                # module-level again by doing a complete re-import.
                modules_to_unload = []
                for m in remote.conn.modules.sys.modules:
                    if m not in self.previous["remote_sys_modules"]:
                        modules_to_unload.append(m)
                for m in modules_to_unload:
                    del remote.conn.modules.sys.modules[m]
                    # Remove imported modules from rpyc cache if found
                    remote.conn.modules._ModuleNamespace__cache.pop(m, None)
            except TimeoutError:
                # Should never go here because the remote connection
                # is closed in _run_program when the executed module times out.
                remote.conn.close()

        random.setstate(self.previous["random_state"])
        os.chdir(student_path)

        if clean_up_files:
            # Delete files previously created by the submission and model
            for file in self._created_files:
                try:
                    os.remove(file)
                except OSError:
                    pass
            self._created_files = set()


    def _setup(self):
        self.restore(clean_up_files=True)
        self.test_case.iotester_data = {}
        self.desc = ""
        self.name_tested = ""
        self.used_inputs_and_params = ""
        self.diff = ""
        self._verify_settings()


    def _find_main_func_and_call(self):
        self.main_func_found = False
        self.main_call_found = False
        path = os.path.join(student_path, self.module_to_test + ".py")
        try:
            with open(path, encoding="utf-8") as file: # Check for UnicodeDecodeError
                data = file.read()
            ast.parse(data) # Check for SyntaxError
            main_func_pattern = re.compile(r"^def\s+main\s*\(.*\)\s*:\s*$", re.MULTILINE)
            main_call_pattern = re.compile(r"^main\s*\(.*\)\s*$", re.MULTILINE)
            if re.search(main_func_pattern, data):
                self.main_func_found = True
            if re.search(main_call_pattern, data):
                self.main_call_found = True
        except SyntaxError as e:
            e.filename = path # Fixes '<unknown>' filename
            return e
        except BaseException as e:
            return e


    def prepare(self, test_case, module_to_test, used_model_modules=[]):
        self.test_case = test_case
        self.module_to_test = module_to_test
        self.prepare_exception = self._find_main_func_and_call()
        self._used_model_modules = (
            used_model_modules
            + [module_name + "_nomain" for module_name in used_model_modules]
        )


    @contextmanager
    def model_directory(self):
        """
        Move to model directory so that model modules can be imported and take care of restoring
        sys.path etc. after so that subsequent imports work correctly.
        Use together with feedback decorator in unit tests that need to manually use model.
        """
        os.chdir(model_path)
        sys.path.insert(0, model_path)
        try:
            yield
        finally:
            self.restore(clean_up_files=False)
            # Built-in functions are restored later by the feedback decorator
            self._override_builtin_import(model=True)
            self._override_builtin_import(model=False)
            self._override_builtin_open(model=True)
            self._override_builtin_open(model=False)


    def _set_description(self, string):
        if string:
            escaped_string = _escape_html_chars(string)
            self.desc = MSG_DESCRIPTION.format(_prepend_newline(escaped_string))
        else:
            self.desc = ""


    def _set_name_tested(self, string):
        self.name_tested = MSG_NAME_TESTED.format(string)


    def _set_diff(self, message, string, expected_string, hide_newlines=False):
        diff_html1 = _get_diff_html(string, expected_string, "delete", hide_newlines)
        diff_html2 = _get_diff_html(string, expected_string, "insert", hide_newlines)
        self.diff = message.format(_prepend_newline(diff_html1), _prepend_newline(diff_html2))


    def _set_used_inputs_and_params(self, inputs, args, kwargs):
        inputs_str = _prepend_newline(_inputs_to_str(inputs))
        params_str = _prepend_newline(_params_to_str(args, kwargs))
        self.used_inputs_and_params = MSG_USED_INPUTS_AND_PARAMS.format(inputs_str, params_str)


    def _iotester_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        module_name = name.split('.')[0] # Imported module name
        # Get importing module name
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if module is None:
            # In case that inspect.getmodule fails to guess the module
            importer = os.path.splitext(os.path.basename(inspect.getfile(frame[0])))[0]
        else:
            importer = module.__name__
        module_path = os.path.abspath(module_name + ".py")

        if module_name == "graderutils":
            # Students should never be allowed to import graderutils.
            # Preventing rpyc.core.control from importing graderutils also causes rpyc
            # to use rpyc.core.vinegar serializer for exceptions.
            allowed_to_import = False
        else:
            allowed_to_import = (
                module_name == "_io" # Python3.8 >= imports _io along with the module that was imported
                or _verify_permissions(
                    module_name,
                    self.settings["import_whitelist"],
                    self.settings["import_blacklist"]
                )
            )
        if allowed_to_import and not os.path.exists(module_path):
            # Import module immediately if allowed (performing os.listdir for no reason is slow).
            # Temporarily restore built-in __import__ since whitelisted imports
            # are allowed to perform their own imports.
            if remote.conn and importer == "rpyc.core.protocol":
                remote.conn.builtins.__import__ = remote.conn._builtin_import
                try:
                    return remote.conn._importlib.__import__(name, globals, locals, fromlist, level)
                finally:
                    remote.conn.builtins.__import__ = self._iotester_import
            else:
                __builtins__["__import__"] = _builtin_import
                try:
                    return importlib.__import__(name, globals, locals, fromlist, level)
                finally:
                    __builtins__["__import__"] = self._iotester_import

        restricted_modules = {"rpyc.core.protocol"} # Modules that are not allowed to import freely
        try:
            for f in os.listdir(student_path) + os.listdir(model_path): # slow
                if os.path.splitext(os.path.basename(f))[1] == ".py":
                    restricted_modules.add(os.path.splitext(os.path.basename(f))[0])
        except OSError:
            raise GraderUtilsError("Failed os.listdir in _iotester_import.")

        # Allow importing of whitelisted imports and restricted_modules.
        # Student code cannot import model modules because model_path is not in sys.path.
        # However, model is able to import student modules if it can't find the module in model_path.
        not_allowed_to_import = (
            importer in restricted_modules
            and not allowed_to_import
            and module_name not in restricted_modules
        )
        if name in self._used_model_modules:
            # Import model version of the module
            path = os.path.join(model_path, name + ".py")
            spec = importlib.util.spec_from_file_location(name, path)
            model_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(model_module)
            return model_module
        elif not_allowed_to_import:
            # Check if the module can be found
            if remote.conn and importer == "rpyc.core.protocol":
                # Using find_spec causes a RecursionError with rpyc, so we use find_loader instead
                #spec = remote.conn._importlib.util.find_spec(name)
                loader = remote.conn._importlib.find_loader(name)
            else:
                #spec = importlib.util.find_spec(name)
                loader = importlib.find_loader(name)
            found = loader is not None
            if found:
                msg_grader_import = MSG_GRADER_IMPORT.format(module_name)
                raise GraderImportError(msg_grader_import)
        # Importer is unrestricted or importer is restricted and allowed to import
        # or it is importing another restricted module
        if remote.conn and importer == "rpyc.core.protocol":
            return remote.conn._importlib.__import__(name, globals, locals, fromlist, level)
        return importlib.__import__(name, globals, locals, fromlist, level)


    def _iotester_open(
            self,
            file,
            mode="r",
            buffering=-1,
            encoding=None,
            errors=None,
            newline=None,
            closefd=True,
            opener=None,
            ):
        # Get opener module name
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if module is None:
            # In case that inspect.getmodule fails to guess the module
            opener_name = os.path.splitext(os.path.basename(inspect.getfile(frame[0])))[0]
        else:
            opener_name = module.__name__
        if opener_name == "rpyc.core.protocol":
            opener_dir = student_path
        else:
            opener_dir = os.path.dirname(os.path.abspath(inspect.getfile(frame[0])))

        restricted_modules = {"rpyc.core.protocol"} # Modules that are not allowed to open freely
        try:
            for f in os.listdir(student_path) + os.listdir(model_path): # slow
                if os.path.splitext(os.path.basename(f))[1] == ".py":
                    restricted_modules.add(os.path.splitext(os.path.basename(f))[0])
        except OSError:
            raise GraderUtilsError("Failed os.listdir in _iotester_open")

        read_modes = ["r", "rt", "rb"]
        write_modes = [
            "x", "xt", "xb", "x+", "xt+", "xb+",
            "w", "wt", "wb", "w+", "wt+", "wb+",
            "a", "at", "ab", "a+", "at+", "ab+",
            "r+", "rt+", "rb+"
        ]
        path = os.path.abspath(file)
        name = os.path.basename(path)
        dir = os.path.dirname(path)
        msg_grader_open_read = MSG_GRADER_OPEN_READ.format(file)
        msg_grader_open_write = MSG_GRADER_OPEN_WRITE.format(file)

        if dir == opener_dir and mode not in write_modes or opener_name not in restricted_modules:
            try:
                # Attempt to open the file.
                # File might not exist unless the student created it.
                return _builtin_open(file, mode, buffering, encoding, errors, newline, closefd, opener)
            except FileNotFoundError:
                found_file = None
                try:
                    # Check if the file is found in exercise_path
                    for fname in os.listdir(exercise_path):
                        if name == fname:
                            found_file = os.path.join(exercise_path, name)
                            break
                    if not found_file:
                        # Check if the file is found in generated_path
                        for fname in os.listdir(generated_path):
                            if name == fname:
                                found_file = os.path.join(generated_path, name)
                                break
                except OSError:
                    raise GraderUtilsError("Failed os.listdir in _iotester_open.")
                if not found_file:
                    # File was not found
                    raise
                elif found_file.startswith(generated_path):
                    # Generated data files are always allowed to be opened
                    return _builtin_open(found_file, mode, buffering, encoding, errors, newline, closefd, opener)
                elif opener_name in restricted_modules:
                    if _verify_permissions(name, self.settings["open_whitelist"], self.settings["open_blacklist"]):
                        # Open the file that was found (read)
                        return _builtin_open(found_file, mode, buffering, encoding, errors, newline, closefd, opener)
                    # No permission to read the found file
                    raise GraderOpenError(msg_grader_open_read) from None
                else:
                    # Open the file that was found (read or write)
                    return _builtin_open(found_file, mode, buffering, encoding, errors, newline, closefd, opener)

        elif dir == opener_dir and not os.path.exists(path) and mode in write_modes:
            # Allow creation of a new file in opener_dir
            stream = _builtin_open(file, mode, buffering, encoding, errors, newline, closefd, opener)
            self._created_files.add(path)
            return stream
        elif dir == opener_dir and os.path.exists(path) and mode in write_modes:
            if path in self._created_files:
                # Allow overwriting of files created by submission/model
                return _builtin_open(file, mode, buffering, encoding, errors, newline, closefd, opener)
            # Deny overwriting of submission/model files
            raise GraderOpenError(msg_grader_open_write)
        elif mode in write_modes:
            # Deny writing of files outside of opener_dir
            raise GraderOpenError(msg_grader_open_write)
        elif dir == generated_path or _verify_permissions(name, self.settings["open_whitelist"], self.settings["open_blacklist"]):
            # Deny reading of files outside of opener_dir unless the file is whitelisted or in generated_path
            return _builtin_open(file, mode, buffering, encoding, errors, newline, closefd, opener)
        elif mode in read_modes:
            # No permission to read file
            raise GraderOpenError(msg_grader_open_read)
        else:
            # Invalid mode
            raise GraderOpenError(MSG_GRADER_OPEN_MODE.format(mode))


    def _iotester_input(self, prompt=""):
        result = line = _builtin_input(prompt)
        if line == ENTER:
            result = ""
            line = (
                "{0}{4}{2}br{3}{1}".format(
                    IOTESTER_INPUT_BEGIN,
                    IOTESTER_INPUT_END,
                    IOTESTER_NO_ESCAPE_LT,
                    IOTESTER_NO_ESCAPE_GT,
                    ENTER_STRING,
                )
            )
        else:
            line = (
                '{0}{2}span{4}class="iotester-input"{3}{5}{2}/span{3}{2}br{3}{1}'.format(
                    IOTESTER_INPUT_BEGIN,
                    IOTESTER_INPUT_END,
                    IOTESTER_NO_ESCAPE_LT,
                    IOTESTER_NO_ESCAPE_GT,
                    IOTESTER_NO_ESCAPE_NBSP,
                    line,
                )
            )
        self._out.write(line)
        return result


    def _override_builtin_import(self, model):
        # We override inside a function so that importing iotester doesn't change builtins
        if not remote.conn or model:
            __builtins__["__import__"] = self._iotester_import
        elif not remote.conn.closed:
            # Override __import__() in student process
            remote.conn.builtins.__import__ = self._iotester_import
        else:
            raise GraderConnClosedError(MSG_GRADER_CONN_CLOSED)


    def _override_builtin_open(self, model):
        # We override inside a function so that importing iotester doesn't change builtins
        if not remote.conn or model:
            __builtins__["open"] = self._iotester_open
        elif not remote.conn.closed:
            # Override open() in student process
            remote.conn.builtins.open = self._iotester_open
        else:
            raise GraderConnClosedError(MSG_GRADER_CONN_CLOSED)


    def _override_builtin_input(self, model):
        # We override inside a function so that importing iotester doesn't change builtins
        if not remote.conn or model:
            __builtins__["input"] = self._iotester_input
        elif not remote.conn.closed:
            # Override input() in student process
            remote.conn.builtins.input = self._iotester_input
        else:
            raise GraderConnClosedError(MSG_GRADER_CONN_CLOSED)


    @contextmanager
    def _captured_output(self, inputs=[]):
        self._out.seek(0)
        self._out.truncate(0)
        inputs_str = '\n'.join(str(elem) for elem in inputs)
        new_in, new_out = StringIO(inputs_str), self._out
        old_in, old_out = sys.stdin, sys.stdout
        try:
            sys.stdin, sys.stdout = new_in, new_out
            yield sys.stdout
        finally:
            sys.stdin, sys.stdout = old_in, old_out


    def _run_program(self, func_name, args, kwargs, inputs, prog, model):
        """
        Run the student or model program's function named func_name
        (or the prog function if provided) with args, kwargs and inputs fed to it.
        Return a dict containing data collected from running the program.
        """
        data = {
            "module": None,
            "class": None,
            "return_value": None,
            "exception": None,
            "output": "",
            "random_state": None,
            "used_args": copy.deepcopy(args),
            "used_kwargs": copy.deepcopy(kwargs),
        }

        seed = random.randrange(sys.maxsize)
        random.seed(seed)
        if remote.conn:
            remote.conn.modules.sys.modules["random"].seed(seed)
        os.chdir(model_path) if model else os.chdir(student_path)

        with self._captured_output(inputs) as out:
            try:
                self._override_builtin_import(model)
                self._override_builtin_open(model)
                self._override_builtin_input(model)
                timeout = self.settings["max_exec_time"]
                if remote.conn:
                    # Update rpyc timeout so that it matches result_or_timeout
                    remote.conn._config.update({"sync_request_timeout": timeout})
                if prog:
                    # Run the prog function
                    if model:
                        # Make import statements in prog function import from model_path
                        sys.path.insert(0, model_path)
                    running_time, return_value = result_or_timeout(prog, data["used_args"], data["used_kwargs"], timeout=timeout)
                    if running_time == timeout and return_value is None:
                        if remote.conn and not remote.conn.closed and not model:
                            remote.conn.close()
                        raise GraderTimeoutError(MSG_GRADER_TIMEOUT.format(timeout))
                    data["return_value"] = return_value
                else:
                    # Run self.module_to_test's function named func_name
                    running_time, module = result_or_timeout(_get_import, (self.module_to_test + "_nomain", model), timeout=timeout)
                    if running_time == timeout and module is None:
                        if remote.conn and not remote.conn.closed and not model:
                            remote.conn.close()
                        raise GraderTimeoutError(MSG_GRADER_TIMEOUT.format(timeout))
                    data["module"] = module
                    if func_name == "main" and self.main_func_found and not self.main_call_found and not model:
                        raise MainCallNotFoundError(MSG_MAIN_CALL_NOT_FOUND)
                    if func_name.endswith(".__init__"):
                        # Run a class's __init__ method.
                        # NOTE: Breaks with rpyc.
                        class_name = func_name.split('.', 1)[0]
                        try:
                            C = getattr(module, class_name)
                        except AttributeError as e:
                            raise ClassNotFoundError(MSG_CLASS_NOT_FOUND.format(class_name)) from e
                        data["class"] = C
                        running_time, obj = result_or_timeout(C, data["used_args"], data["used_kwargs"], timeout=timeout)
                        if running_time == timeout and obj is None:
                            raise GraderTimeoutError(MSG_GRADER_TIMEOUT.format(timeout))
                        data["return_value"] = obj
                    elif func_name:
                        # Run a module's function named func_name
                        try:
                            func = getattr(module, func_name)
                        except AttributeError as e:
                            raise FunctionNotFoundError(MSG_FUNCTION_NOT_FOUND.format(func_name)) from e
                        running_time, return_value = result_or_timeout(func, data["used_args"], data["used_kwargs"], timeout=timeout)
                        if running_time == timeout and return_value is None:
                            if remote.conn and not remote.conn.closed and not model:
                                remote.conn.close()
                            raise GraderTimeoutError(MSG_GRADER_TIMEOUT.format(timeout))
                        data["return_value"] = return_value
                    # Save the state of the random number generator for checking that it matches with model
                    if hasattr(module, "random"):
                        data["random_state"] = module.random.getstate()
            except TimeoutError as e:
                # If an infinite loop is on module-level, result_or_timeout has to wait
                # for TimeoutError from rpyc because it is unable to return.
                # Rpyc also uses time.time() timer and sometimes it raises TimeoutError
                # before result_or_timeout, so we take care of that here.
                if remote.conn and str(e) == "result expired" and not model:
                    remote.conn.close()
                    e = GraderTimeoutError(MSG_GRADER_TIMEOUT.format(timeout))
                data["exception"] = e
            except EOFError as e:
                if remote.conn and str(e) in ["[Errno 32] Broken pipe", "stream has been closed"] and not model:
                    # Student code most likely raised KeyboardInterrupt.
                    # str(e) is "[Errno 32] Broken pipe" if it was raised inside a function.
                    # str(e) is "stream has been closed" if it was raised on module level.
                    # Close remote connection if it is still open (in case of broken pipe).
                    # Rest of the tests run after this will fail with GraderConnClosedError.
                    remote.conn.close()
                    e = KeyboardInterrupt()
                data["exception"] = e
            except BaseException as e:
                data["exception"] = e
            finally:
                if data["exception"] and type(data["exception"]) is GraderTimeoutError:
                    # Maximum number of lines shown when program execution was timed out
                    max_num_lines = MAX_OUTPUT_LINES_ON_TIMEOUT
                else:
                    # Maximum number of lines shown when program execution was not timed out
                    max_num_lines = MAX_OUTPUT_LINES
                lines = out.getvalue().splitlines(keepends=True)
                data["output"] = ''.join(lines[:min(max_num_lines, len(lines))])
                data["output"] = data["output"].replace('\xa0', ' ').replace('\x00', r"\x00")

        self.restore(clean_up_files=False) # Files created by the module are deleted later

        return data


    def _raise_exception_with_feedback(self, exception, show_diff, model):
        msg_colors = MSG_COLORS
        if not show_diff:
            msg_colors = ""
            self.diff = ""
        # Exception class is checked based on name because using type()
        # does not behave normally when using rpyc.
        exception_name = exception.__class__.__name__
        if exception_name == "GraderConnClosedError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                str(exception),
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "GraderImportError":
            exception_str = str(exception)
            if remote.conn and not model:
                # Clean the exception string of possible irrelevant rpyc traceback
                message_lines_amount = len(MSG_GRADER_IMPORT.splitlines())
                exception_str = '\n'.join(exception_str.splitlines()[:message_lines_amount])
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                exception_str,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "GraderOpenError":
            exception_str = str(exception)
            if remote.conn and not model:
                # Clean the exception string of possible irrelevant rpyc traceback
                message_lines_amount = len(MSG_GRADER_OPEN_READ.splitlines())
                exception_str = '\n'.join(exception_str.splitlines()[:message_lines_amount])
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                exception_str,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "GraderTimeoutError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_GRADER_TIMEOUT.format(self.settings["max_exec_time"]),
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "GraderIOError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_GRADER_BUFFER,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "FunctionNotFoundError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                str(exception),
                self.name_tested,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "ClassNotFoundError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                str(exception),
                self.name_tested,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "ModuleNotFoundError":
            exception_str = str(exception).rstrip()
            if remote.conn and not model:
                # Clean the exception string of possible irrelevant rpyc traceback
                message_line_found = False
                for line in exception_str.splitlines(keepends=True):
                    if line.startswith("ModuleNotFoundError:"):
                        exception_str = line.split(": ", 1)[1]
                        message_line_found = True
                    elif message_line_found:
                        exception_str += line
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_MODULENOTFOUNDERROR.format(exception_str),
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "FileNotFoundError":
            exception_str = str(exception).rstrip()
            if remote.conn and not model:
                # Clean the exception string of possible irrelevant rpyc traceback
                message_line_found = False
                for line in exception_str.splitlines(keepends=True):
                    if line.startswith("FileNotFoundError:"):
                        exception_str = line.split(": ", 1)[1]
                        message_line_found = True
                    elif message_line_found:
                        exception_str += line
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_FILENOTFOUNDERROR.format(exception_str),
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "TimeoutError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_TIMEOUTERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "EOFError":
            exception_str = "EOFError: " + str(exception).rstrip()
            if remote.conn and not model:
                # Clean the exception string of possible irrelevant rpyc traceback
                exception_str = str(exception).rstrip()
                message_line_found = False
                for line in exception_str.splitlines(keepends=True):
                    if line.startswith("EOFError:"):
                        exception_str = line
                        message_line_found = True
                    elif message_line_found:
                        exception_str += line
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                exception_str,
                MSG_EOFERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "MainCallNotFoundError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_MAIN_CALL_NOT_FOUND,
                self.name_tested,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "ImportError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_IMPORTERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "SystemExit":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_SYSTEMEXIT,
                self.name_tested,
                self.desc,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "KeyboardInterrupt":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_KEYBOARDINTERRUPT,
                self.name_tested,
                self.desc,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "ValueError":
            if str(exception) == "list.remove(x): x not in list":
                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    msg_colors,
                    MSG_VALUEERROR_1,
                    self.name_tested,
                    self.desc,
                    self.diff,
                    self.used_inputs_and_params,
                ])
            elif str(exception) == "source code string cannot contain null bytes":
                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    MSG_VALUEERROR_2,
                ])
                self.test_case.iotester_data["hideTraceback"] = True
            else:
                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    msg_colors,
                    MSG_VALUEERROR_3,
                    self.name_tested,
                    self.desc,
                    self.diff,
                    self.used_inputs_and_params,
                ])
        elif exception_name == "AttributeError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_ATTRIBUTEERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "UnboundLocalError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_UNBOUNDLOCALERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "NameError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_NAMEERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "ZeroDivisionError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_ZERODIVISIONERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "TypeError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_TYPEERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "RecursionError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_RECURSIONERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        elif exception_name == "UnicodeDecodeError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_UNICODEDECODEERROR,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
        elif exception_name == "SyntaxError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_SYNTAXERROR,
            ])
        elif exception_name == "IndentationError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_INDENTATIONERROR,
            ])
        elif exception_name == "TabError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_TABERROR,
            ])
        elif exception_name == "IndexError":
            if "list" in str(exception):
                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    msg_colors,
                    MSG_INDEXERROR_LIST,
                    self.name_tested,
                    self.desc,
                    self.diff,
                    self.used_inputs_and_params,
                ])
            elif "tuple" in str(exception):
                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    msg_colors,
                    MSG_INDEXERROR_TUPLE,
                    self.name_tested,
                    self.desc,
                    self.diff,
                    self.used_inputs_and_params,
                ])
            elif "string" in str(exception):
                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    msg_colors,
                    MSG_INDEXERROR_STRING,
                    self.name_tested,
                    self.desc,
                    self.diff,
                    self.used_inputs_and_params,
                ])
            else:
                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    msg_colors,
                    MSG_BASIC_ERROR,
                    self.name_tested,
                    self.desc,
                    self.diff,
                    self.used_inputs_and_params,
                ])
        elif exception_name == "KeyError":
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_KEYERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
        else:
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_colors,
                MSG_BASIC_ERROR,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            if exception_name == "AssertionError":
                self.test_case.failureException = GraderUtilsError
        if model:
            warning_msg = '<span class="iotester-warning">{:s}</span>'.format(MSG_MODEL_ERROR)
            self.test_case.iotester_data["warning"] = warning_msg
            self.test_case.iotester_data["hideTraceback"] = False

        raise exception


    def text_test(
            self,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            prog=None,
            prog_args=(),
            prog_kwargs={},
            prog_inputs=[],
            desc="",
            compare_capitalization=False,
            ):
        """
        Run the model program and the student program and compare the text outputs.
        Ignore numbers, whitespace and characters specified in self.settings["ignored_characters"].
        """
        self._setup()
        used_args = prog_args if prog else args
        used_kwargs = prog_kwargs if prog else kwargs
        used_inputs = prog_inputs if prog else inputs
        name_tested = func_name
        if not func_name:
            name_tested = "main" if self.main_func_found else ""
        self._set_name_tested(name_tested)
        self._set_description(desc)
        self._set_used_inputs_and_params(inputs, args, kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, used_args, used_kwargs, used_inputs, prog, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(name_tested, used_args, used_kwargs, used_inputs, prog, model=False)
        #print(data, file=sys.stderr) # Debug print
        self._set_diff(MSG_OUTPUT_DIFF, data["output"], expected_data["output"])
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=True, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=True, model=False)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            MSG_TEXT,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Get numbers from both outputs
        numbers = _get_numbers_from_string(data["output"])
        expected_numbers = _get_numbers_from_string(expected_data["output"])
        # Strip numbers and whitespace from both outputs
        stripped_output = _strip_string(
            data["output"],
            numbers,
            self.settings["ignored_characters"],
            strip_numbers=True,
            strip_whitespace=True,
        )
        expected_stripped_output = _strip_string(
            expected_data["output"],
            expected_numbers,
            self.settings["ignored_characters"],
            strip_numbers=True,
            strip_whitespace=True,
        )
        # Example:
        # data["output"] = "Numbers   are 3.68 and 82.\nThat's it."
        # stripped_output = "NumbersareandThatsit"
        if compare_capitalization:
            self.test_case.assertEqual(stripped_output, expected_stripped_output)
        else:
            self.test_case.assertEqual(stripped_output.lower(), expected_stripped_output.lower())
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Return the data that was collected when running the two programs
        return data, expected_data


    def numbers_test(
            self,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            prog=None,
            prog_args=(),
            prog_kwargs={},
            prog_inputs=[],
            desc="",
            compare_formatting=False,
            ):
        """
        Run the model program and the student program and compare the numbers in the outputs.
        Ignore everything except numbers.
        Match integers, decimals and numbers such as +1, 2e9, +2E+09, -2.0e-9.
        """
        self._setup()
        used_args = prog_args if prog else args
        used_kwargs = prog_kwargs if prog else kwargs
        used_inputs = prog_inputs if prog else inputs
        name_tested = func_name
        if not func_name:
            name_tested = "main" if self.main_func_found else ""
        self._set_name_tested(name_tested)
        self._set_description(desc)
        self._set_used_inputs_and_params(inputs, args, kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, used_args, used_kwargs, used_inputs, prog, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(name_tested, used_args, used_kwargs, used_inputs, prog, model=False)
        #print(data, file=sys.stderr) # Debug print
        self._set_diff(MSG_OUTPUT_DIFF, data["output"], expected_data["output"])
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=True, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=True, model=False)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            MSG_NUMBERS,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Get numbers (as strings) from both outputs
        numbers = _get_numbers_from_string(data["output"])
        expected_numbers = _get_numbers_from_string(expected_data["output"])
        # Check that the same amount of numbers exist in both outputs
        self.test_case.assertEqual(len(numbers), len(expected_numbers))
        # Compare numbers
        try:
            for number, expected_number in zip(numbers, expected_numbers):
                if 'e' in expected_number.lower():
                    # Expected number is in scientific format
                    self.test_case.assertEqual(number.lower(), expected_number.lower())
                elif '.' not in expected_number:
                    # Expected number is an integer
                    self.test_case.assertAlmostEqual(int(number), int(expected_number), delta=self.settings["max_int_delta"])
                    if compare_formatting:
                        # Compare formatting of integers
                        self.test_case.assertEqual(len(number), len(expected_number))
                else:
                    # Expected number is a float
                    self.test_case.assertAlmostEqual(float(number), float(expected_number), delta=self.settings["max_float_delta"])
                    if compare_formatting:
                        # Compare formatting of floats
                        self.test_case.assertEqual(len(number.split('.')[0]), len(expected_number.split('.')[0]))
                        self.test_case.assertEqual(len(number.split('.')[1]), len(expected_number.split('.')[1]))
        except (ValueError, IndexError):
            self.test_case.fail(MSG_NUMBERS)

        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Return the data that was collected when running the two programs
        return data, expected_data


    def return_value_test(
            self,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            prog=None,
            prog_args=(),
            prog_kwargs={},
            prog_inputs=[],
            desc="",
            show_output=False,
            ):
        """
        Run a function from the model program and the student program and compare the return values
        of the two functions.
        """
        self._setup()
        used_args = prog_args if prog else args
        used_kwargs = prog_kwargs if prog else kwargs
        used_inputs = prog_inputs if prog else inputs
        name_tested = func_name
        if not func_name:
            name_tested = "main" if self.main_func_found else ""
        self._set_name_tested(name_tested)
        self._set_description(desc)
        self._set_used_inputs_and_params(inputs, args, kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, used_args, used_kwargs, used_inputs, prog, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(name_tested, used_args, used_kwargs, used_inputs, prog, model=False)
        #print(data, file=sys.stderr) # Debug print
        self._set_diff(MSG_OUTPUT_DIFF, data["output"], expected_data["output"])
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=False, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=False, model=False)

        def return_value_to_str(return_value):
            return_value_str = repr(return_value)
            # Strip memory address information
            matches = re.findall(" at 0x[0123456789abcdef]+", return_value_str)
            for match in matches:
                return_value_str = return_value_str.replace(match, '')
            return return_value_str

        return_value_str = return_value_to_str(data["return_value"])
        expected_return_value_str = return_value_to_str(expected_data["return_value"])
        self._set_diff(MSG_RETURN_VALUE_DIFF, return_value_str, expected_return_value_str)
        feedback_parts = [
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            MSG_RETURN_VALUE,
            self.name_tested,
            self.desc,
            self.diff,
        ]
        # Hack...
        msg_output_html = ""
        escaped_output = _escape_html_chars(_remove_last_newline(data["output"]))
        if show_output and escaped_output:
            msg_output_html = "</pre>" + MSG_OUTPUT.format("<p><pre>" + _prepend_newline(escaped_output))
        feedback_parts.append(self.used_inputs_and_params + msg_output_html)
        self.test_case.iotester_data["feedback"] = _combine_feedback(feedback_parts)

        # Compare return values with each other
        def compare_elems(elem1, elem2):
            # Check that return values are of the same type.
            # The __class__ attribute is used because type() returns rpyc.core.netref.type when using rpyc.
            # Calling repr() below allows elements to be from different modules.
            self.test_case.assertEqual(repr(elem1.__class__), repr(elem2.__class__))
            if isinstance(elem2, bool) or isinstance(elem2, str):
                self.test_case.assertEqual(elem1, elem2)
            elif isinstance(elem2, int):
                self.test_case.assertAlmostEqual(elem1, elem2, delta=self.settings["max_int_delta"])
            elif isinstance(elem2, float):
                self.test_case.assertAlmostEqual(elem1, elem2, delta=self.settings["max_float_delta"])
            elif isinstance(elem2, list) or isinstance(elem2, tuple):
                self.test_case.assertEqual(len(elem1), len(elem2))
                for i in range(len(elem2)):
                    compare_elems(elem1[i], elem2[i])
            elif isinstance(elem2, set):
                self.test_case.assertEqual(len(elem1), len(elem2))
                diff1 = elem2.difference(elem1)
                self.test_case.assertEqual(len(diff1), 0)
                diff2 = elem1.difference(elem2)
                self.test_case.assertEqual(len(diff2), 0)
            elif isinstance(elem2, dict):
                self.test_case.assertEqual(len(elem1), len(elem2))
                for key in elem2:
                    if key not in elem1:
                        self.test_case.fail(MSG_RETURN_VALUE)
                    else:
                        compare_elems(elem1[key], elem2[key])
            elif inspect.isclass(elem2):
                self.test_case.assertEqual(repr(elem1), repr(elem2))
            else:
                # Compare other objects
                pass

        compare_elems(data["return_value"], expected_data["return_value"])

        feedback_parts = [
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            self.name_tested,
            self.desc,
            self.diff,
        ]
        # Hack...
        feedback_parts.append(self.used_inputs_and_params + msg_output_html)
        self.test_case.iotester_data["feedback"] = _combine_feedback(feedback_parts)

        # Return the data that was collected when running the two programs
        return data, expected_data


    def complete_output_test(
            self,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            prog=None,
            prog_args=(),
            prog_kwargs={},
            prog_inputs=[],
            desc="",
            compare_capitalization=False,
            ):
        """
        Run the model program and the student program and compare the text, numbers and whitespace.
        Ignore characters specified in self.settings["ignored_characters"].
        """
        # Text and numbers in output are tested first
        self.text_test(func_name, args, kwargs, inputs, prog, prog_args, prog_kwargs, prog_inputs, desc, compare_capitalization)
        self.numbers_test(func_name, args, kwargs, inputs, prog, prog_args, prog_kwargs, prog_inputs, desc, compare_formatting=True)
        # Begin testing of whitespace
        self._setup()
        used_args = prog_args if prog else args
        used_kwargs = prog_kwargs if prog else kwargs
        used_inputs = prog_inputs if prog else inputs
        name_tested = func_name
        if not func_name:
            name_tested = "main" if self.main_func_found else ""
        self._set_name_tested(name_tested)
        self._set_description(desc)
        self._set_used_inputs_and_params(inputs, args, kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, used_args, used_kwargs, used_inputs, prog, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(name_tested, used_args, used_kwargs, used_inputs, prog, model=False)
        #print(data, file=sys.stderr) # Debug print
        self._set_diff(MSG_OUTPUT_DIFF, data["output"], expected_data["output"])
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=True, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=True, model=False)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            MSG_WHITESPACE,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Get numbers (as strings) from both outputs
        numbers = _get_numbers_from_string(data["output"])
        expected_numbers = _get_numbers_from_string(expected_data["output"])
        minus_check_indexes = []
        for i in range(len(numbers)):
            if numbers[i].startswith('-') != expected_numbers[i].startswith('-'):
                # Whitespace minus check has to be performed for these numbers
                minus_check_indexes.append(i)
        # Compare outputs
        stripped_output = _strip_string(
            data["output"],
            numbers,
            self.settings["ignored_characters"],
            strip_numbers=False,
            strip_whitespace=False,
            minus_check_indexes=minus_check_indexes,
        )
        expected_stripped_output = _strip_string(
            expected_data["output"],
            expected_numbers,
            self.settings["ignored_characters"],
            strip_numbers=False,
            strip_whitespace=False,
            minus_check_indexes=minus_check_indexes,
        )
        # Example:
        # data["expected_output"] = "Numbers   are  0.00 and 82.\nThat's it."
        # data["output"]          = "numbers   are -0.00 and 82.\nthat's it."
        # expected_stripped_output = "Numbers   are  [iotester-minus-check] and [iotester-number]\nThats it"
        # stripped_output          = "numbers   are [iotester-minus-check] and [iotester-number]\nthats it"
        output, expected_output = _whitespace_minus_check_patch(
            stripped_output.lower(),
            expected_stripped_output.lower(),
        )
        # expected_output = "numbers   are  [iotester-minus-check] and [iotester-number]\nthats it"
        # output          = "numbers   are  [iotester-minus-check] and [iotester-number]\nthats it"
        self.test_case.assertEqual(output, expected_output)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Return the data that was collected when running the two programs
        return data, expected_data


    def no_output_test(
            self,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            prog=None,
            prog_args=(),
            prog_kwargs={},
            prog_inputs=[],
            desc="",
            ):
        """
        Run the student program and test that nothing is printed.
        """
        self._setup()
        used_args = prog_args if prog else args
        used_kwargs = prog_kwargs if prog else kwargs
        used_inputs = prog_inputs if prog else inputs
        name_tested = func_name
        if not func_name:
            name_tested = "main" if self.main_func_found else ""
        self._set_name_tested(name_tested)
        self._set_description(desc)
        self._set_used_inputs_and_params(inputs, args, kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        data = self._run_program(name_tested, used_args, used_kwargs, used_inputs, prog, model=False)
        #print(data, file=sys.stderr) # Debug print
        self._set_diff(MSG_OUTPUT_DIFF, data["output"], "")
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=True, model=False)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            MSG_NO_OUTPUT,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        self.test_case.assertEqual(data["output"], "")
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Return the data that was collected when running the student program
        return data


    def created_file_test(
            self,
            file_name,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            prog=None,
            prog_args=(),
            prog_kwargs={},
            prog_inputs=[],
            desc="",
            ):
        """
        Run the model program and the student program and compare the data in the file they create.
        The data in the two files has to be identical.
        """
        self._setup()
        used_args = prog_args if prog else args
        used_kwargs = prog_kwargs if prog else kwargs
        used_inputs = prog_inputs if prog else inputs
        name_tested = func_name
        if not func_name:
            name_tested = "main" if self.main_func_found else ""
        self._set_name_tested(name_tested)
        self._set_description(desc)
        self._set_used_inputs_and_params(inputs, args, kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, used_args, used_kwargs, used_inputs, prog, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(name_tested, used_args, used_kwargs, used_inputs, prog, model=False)
        #print(data, file=sys.stderr) # Debug print
        self._set_diff(MSG_OUTPUT_DIFF, data["output"], expected_data["output"])
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=True, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=True, model=False)
        os.chdir(model_path)
        try:
            with open(file_name) as expected_file:
                expected_file_data = expected_file.read()
        except OSError as e:
            expected_data["exception"] = e
        os.chdir(student_path)
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=True, model=True)
        try:
            with open(file_name) as file:
                file_data = file.read()
        except FileNotFoundError:
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_FILE_NOT_FOUND,
                self.name_tested,
                MSG_FILE_NAME.format(file_name),
                self.desc,
                self.used_inputs_and_params,
            ])
            self.test_case.iotester_data["hideTraceback"] = True
            raise
        except OSError:
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_OSERROR,
                self.name_tested,
                MSG_FILE_NAME.format(file_name),
                self.desc,
                self.used_inputs_and_params,
            ])
            raise
        self._set_diff(MSG_FILE_DATA_DIFF, file_data, expected_file_data)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            MSG_FILE_DATA,
            self.name_tested,
            MSG_FILE_NAME.format(file_name),
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Compare file data
        self.test_case.assertEqual(file_data, expected_file_data)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            self.name_tested,
            MSG_FILE_NAME.format(file_name),
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Return the data that was collected when running the two programs
        return data, expected_data


    def random_state_test(
            self,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            prog=None,
            prog_args=(),
            prog_kwargs={},
            prog_inputs=[],
            desc="",
            ):
        """
        Run the model program and the student program and compare Python's pseudo-random number
        generator states. Used to test a function that sets random seed and to check that a program
        generates pseudo-random numbers the correct amount of times.
        """
        self._setup()
        used_args = prog_args if prog else args
        used_kwargs = prog_kwargs if prog else kwargs
        used_inputs = prog_inputs if prog else inputs
        name_tested = func_name
        if not func_name:
            name_tested = "main" if self.main_func_found else ""
        self._set_name_tested(name_tested)
        self._set_description(desc)
        self._set_used_inputs_and_params(inputs, args, kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, used_args, used_kwargs, used_inputs, prog, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(name_tested, used_args, used_kwargs, used_inputs, prog, model=False)
        #print(data, file=sys.stderr) # Debug print
        self._set_diff(MSG_OUTPUT_DIFF, data["output"], expected_data["output"])
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=True, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=True, model=False)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_RANDOM_STATE,
            self.name_tested,
            self.desc,
            self.used_inputs_and_params,
        ])
        self.test_case.assertEqual(data["random_state"], expected_data["random_state"])
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            self.name_tested,
            self.desc,
            self.used_inputs_and_params,
        ])
        # Return the data that was collected when running the two programs
        return data, expected_data


    def amount_of_functions_test(self, op, amount, desc=""):
        """
        Test that the student program contains the required amount of functions.
        Parameter op should be one of the following strings: '>', '<', '>=', '<=', '=='
        NOTE: Breaks if using rpyc and the student's Python module contains custom classes.
        """
        self._setup()
        self._set_description(desc)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        data = self._run_program(func_name="", args=(), kwargs={}, inputs=[], prog=None, model=False)
        #print(data, file=sys.stderr) # Debug print
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=False, model=False)
        ops_msgs = {
            ">": (operator.gt, MSG_FUNCS_AMOUNT_GT),
            "<": (operator.lt, MSG_FUNCS_AMOUNT_LT),
            ">=": (operator.ge, MSG_FUNCS_AMOUNT_GE),
            "<=": (operator.le, MSG_FUNCS_AMOUNT_LE),
            "==": (operator.eq, MSG_FUNCS_AMOUNT_EQ),
        }
        funcs = [o for o in inspect.getmembers(data["module"]) if inspect.isfunction(o[1])]
        result = ops_msgs[op][0](len(funcs), amount)
        msg_funcs_amount = ops_msgs[op][1].format(amount, len(funcs))
        funcs_str = ""
        for name, func in funcs:
            funcs_str += '\n' + name
        msg_funcs = MSG_FUNCS_FOUND.format(funcs_str)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            msg_funcs_amount,
            msg_funcs,
            self.desc,
        ])
        self.test_case.assertTrue(result)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            self.desc,
            MSG_FUNCS_AMOUNT_PASS,
        ])
        # Return the found functions for further testing
        return funcs


    def class_structure_test(self, class_name, args=(), kwargs={}, checks=[], desc=""):
        """
        Create an instance of the model class and the student class and compare the structure of the classes and objects.
        Parameter checks is a list containing strings, which specify the tests performed on the class structure.
        "object_attrs": Check required instance/object attributes exist and that they are of the correct type
        "class_attrs": Check required methods, functions and variables exist in the class and that they are of the correct type
        "no_extra_object_attrs": Check that no extra instance/object attributes are found
        "no_extra_class_attrs": Check that no extra methods, functions or variables are found in the class
        NOTE: Breaks if using rpyc.
        """
        self._setup()
        func_name = "{}.__init__".format(class_name)
        self._set_name_tested(func_name)
        self._set_description(MSG_INIT_DESC.format(class_name))
        self._set_used_inputs_and_params(inputs=[], args=args, kwargs=kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, args, kwargs, inputs=[], prog=None, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(func_name, args, kwargs, inputs=[], prog=None, model=False)
        #print(data, file=sys.stderr) # Debug print
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=False, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=False, model=False)

        expected_object_attrs = expected_data["return_value"].__dict__
        object_attrs = data["return_value"].__dict__
        expected_class_attrs = expected_data["class"].__dict__
        class_attrs = data["class"].__dict__

        def get_attrs_str(attrs_dict):
            attrs_list = []
            keys = sorted(attrs_dict.keys())
            for key in keys:
                value = attrs_dict[key]
                if key.startswith("_" + class_name + "__"):
                    key = key[len(class_name) + 1:]
                attrs_list.append(key + " : " + repr(type(value)))
            string = '\n'.join(attrs_list)
            return string

        if "object_attrs" in checks:
            # Check required object attributes exist and that they are of the correct type
            object_attrs_str = get_attrs_str(object_attrs)
            expected_object_attrs_str = get_attrs_str(expected_object_attrs)
            self._set_description(MSG_INIT_DESC.format(class_name))
            self._set_name_tested(func_name)
            self._set_used_inputs_and_params(inputs=[], args=args, kwargs=kwargs)
            self._set_diff(MSG_OBJECT_ATTRS_DIFF, object_attrs_str, expected_object_attrs_str, hide_newlines=True)
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_COLORS,
                MSG_OBJECT_ATTRS_MISSING,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            self.test_case.assertTrue(all([key in object_attrs for key in expected_object_attrs]))
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_COLORS,
                MSG_OBJECT_ATTRS_TYPE,
                self.name_tested,
                self.desc,
                self.diff,
                self.used_inputs_and_params,
            ])
            for key in expected_object_attrs:
                # Calling repr() below allows items to be from different modules
                self.test_case.assertEqual(repr(type(object_attrs[key])), repr(type(expected_object_attrs[key])))
        if "class_attrs" in checks:
            # Check required methods, functions and variables exist and that they are of the correct type
            class_attrs_str = get_attrs_str(class_attrs)
            expected_class_attrs_str = get_attrs_str(expected_class_attrs)
            self._set_description(desc)
            self._set_diff(MSG_CLASS_ATTRS_DIFF, class_attrs_str, expected_class_attrs_str, hide_newlines=True)
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_COLORS,
                MSG_CLASS_ATTRS_MISSING,
                MSG_CLASS_NAME.format(class_name),
                self.desc,
                self.diff,
            ])
            self.test_case.assertTrue(all([key in class_attrs for key in expected_class_attrs]))
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_COLORS,
                MSG_CLASS_ATTRS_TYPE,
                MSG_CLASS_NAME.format(class_name),
                self.desc,
                self.diff,
            ])
            for key in expected_class_attrs:
                # Calling repr() below allows items to be from different modules
                self.test_case.assertEqual(repr(type(class_attrs[key])), repr(type(expected_class_attrs[key])))

        def get_extras(student_dict, model_dict):
            extra_list = []
            extra_str = ""
            student_keys = sorted(student_dict.keys())
            model_keys = sorted(model_dict.keys())
            for key in student_dict:
                if key not in model_keys:
                    extra_list.append(key)
            for key in extra_list:
                value = student_dict[key]
                if key.startswith("_" + class_name + "__"):
                    key = key[len(class_name) + 1:]
                extra_str += "\n{:s} : {:s}".format(repr(key), repr(type(value)))
            extra_str = _escape_html_chars(extra_str)
            return extra_list, extra_str

        if "no_extra_object_attrs" in checks:
            # Check that no extra object attributes are found
            self._set_description(MSG_INIT_DESC.format(class_name))
            self._set_name_tested(func_name)
            self._set_used_inputs_and_params(inputs=[], args=args, kwargs=kwargs)
            extra_object_attrs_list, extra_object_attrs_str = get_extras(object_attrs, expected_object_attrs)
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                self.name_tested,
                self.desc,
                MSG_EXTRA_OBJECT_ATTRS.format(extra_object_attrs_str),
                self.used_inputs_and_params,
            ])
            self.test_case.assertEqual(len(extra_object_attrs_list), 0)
        if "no_extra_class_attrs" in checks:
            # Check that no extra methods, functions or variables are found
            self._set_description(desc)
            extra_class_attrs_list, extra_class_attrs_str = get_extras(class_attrs, expected_class_attrs)
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                MSG_CLASS_NAME.format(class_name),
                self.desc,
                MSG_EXTRA_CLASS_ATTRS.format(extra_class_attrs_str),
            ])
            self.test_case.assertEqual(len(extra_class_attrs_list), 0)

        self._set_description(desc)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_CLASS_NAME.format(class_name),
            self.desc,
            MSG_STRUCTURE_PASS,
        ])

        # Return the found object attributes and class attributes that were found
        data = {"object_attrs": object_attrs, "class_attrs": class_attrs}
        expected_data = {"object_attrs": expected_object_attrs, "class_attrs": expected_class_attrs}
        return data, expected_data


    def class_init_test(
            self,
            class_name,
            args=(),
            kwargs={},
            run_text_test=False,
            run_numbers_test=False,
            run_complete_output_test=False,
            run_no_output_test=False,
            compare_capitalization=False,
            compare_formatting=False,
            desc=""
            ):
        """
        Create an instance of the model class and the student class by running their __init__()
        functions and compare the values assigned to the objects' attributes.
        The output of __init__() can be tested in different ways by setting the corresponding
        parameters to True.
        NOTE: Breaks if using rpyc.
        """
        self._setup()
        func_name = "{}.__init__".format(class_name)
        self._set_name_tested(func_name)
        if desc:
            self._set_description(desc)
        else:
            self._set_description(MSG_INIT_DESC.format(class_name))
        self._set_used_inputs_and_params(inputs=[], args=args, kwargs=kwargs)
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        expected_data = self._run_program(func_name, args, kwargs, inputs=[], prog=None, model=True)
        #print(expected_data, file=sys.stderr) # Debug print
        data = self._run_program(func_name, args, kwargs, inputs=[], prog=None, model=False)
        #print(data, file=sys.stderr) # Debug print
        if expected_data["exception"]:
            self._raise_exception_with_feedback(expected_data["exception"], show_diff=False, model=True)
        if data["exception"]:
            self._raise_exception_with_feedback(data["exception"], show_diff=False, model=False)

        # Check required object attributes exist
        expected_object_attrs = expected_data["return_value"].__dict__
        object_attrs = data["return_value"].__dict__

        def get_attrs_str(attrs_dict):
            attrs_list = []
            keys = sorted(attrs_dict.keys())
            for key in keys:
                value = attrs_dict[key]
                if key.startswith("_" + class_name + "__"):
                    key = key[len(class_name) + 1:]
                attrs_list.append(key + " = " + repr(value))
            string = '\n'.join(attrs_list)
            return string

        object_attrs_str = get_attrs_str(object_attrs)
        expected_object_attrs_str = get_attrs_str(expected_object_attrs)

        self._set_diff(MSG_OBJECT_ATTRS_DIFF, object_attrs_str, expected_object_attrs_str, hide_newlines=True)
        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_COLORS,
            MSG_OBJECT_ATTRS,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        self.test_case.assertTrue(all([key in object_attrs for key in expected_object_attrs]))

        # Check required object attributes have correct values
        for key in expected_object_attrs:
            expected_value = expected_object_attrs[key]
            value = object_attrs[key]
            self.test_case.assertEqual(value, expected_value)

        previous_diff = self.diff
        previous_desc = self.desc

        if run_no_output_test:
            # Runs complete_output_test, which runs text_test and numbers_test
            self.no_output_test(func_name, args, kwargs, desc=desc)
        elif run_complete_output_test:
            # Runs text_test and numbers_test
            self.complete_output_test(func_name, args, kwargs, desc=desc, compare_capitalization=compare_capitalization)
        else:
            if run_text_test:
                self.text_test(func_name, args, kwargs, desc=desc, compare_capitalization=compare_capitalization)
            if run_numbers_test:
                self.numbers_test(func_name, args, kwargs, desc=desc, compare_formatting=compare_formatting)

        # Clear possible self.desc and self.diff set in other tests
        self.diff = previous_diff
        self.desc = previous_desc

        self.test_case.iotester_data["feedback"] = _combine_feedback([
            MSG_PYTHON_VERSION,
            MSG_OBJECT_ATTRS_PASS,
            self.name_tested,
            self.desc,
            self.diff,
            self.used_inputs_and_params,
        ])
        # Return the created objects for further testing
        return data["return_value"], expected_data["return_value"]


    def _preorder(self, node):
        if node.__class__ == ast.Call:
            if hasattr(node.func, "attr") and node.func.attr == "__str__":
                if not self.str_call_test_result:
                    self.str_call_test_result = True
                    return
        for child in ast.iter_child_nodes(node):
            self._preorder(child)


    def class_str_call_test(self, object_name):
        """
        Test that an object's __str__() method is not called directly,
        i.e., check that print(obj) is used instead of print(obj.__str__()).
        """
        self._setup()
        self.str_call_test_result = False
        if self.prepare_exception:
            self._raise_exception_with_feedback(self.prepare_exception, show_diff=False, model=False)
        with open(self.module_to_test + ".py") as f:
            # UnicodeDecodeError and SyntaxError already checked in prepare
            tree = ast.parse(f.read())
        for child in ast.iter_child_nodes(tree):
            self._preorder(child)
        if self.str_call_test_result:
            msg_str_call_test = MSG_STR_CALL_TEST.format(object_name, object_name)
            self.test_case.iotester_data["feedback"] = _combine_feedback([
                MSG_PYTHON_VERSION,
                msg_str_call_test,
            ])
            self.test_case.fail(msg_str_call_test)


    def feedback(
            self,
            func_name="",
            args=(),
            kwargs={},
            inputs=[],
            simple=False,
            show_used_inputs_and_params=False,
            message="",
            desc="",
            ):
        """
        Return a decorator for displaying better feedback than just the AssertionError message or traceback.
        Do not call other IOTester tests inside a method that has been decorated with this.
        Can be used to improve the feedback of a normal test method that does basic assertion tests.
        """
        def decorator(testmethod):
            @functools.wraps(testmethod)
            def wrapper(*testmethod_args, **testmethod_kwargs):
                if hasattr(testmethod, "__self__"):
                    self.test_case = testmethod.__self__
                else:
                    self.test_case = testmethod_args[0]
                self._setup()
                self._set_description(desc)
                if func_name:
                    self._set_name_tested(func_name)
                if show_used_inputs_and_params:
                    self._set_used_inputs_and_params(inputs, args, kwargs)
                if message:
                    msg_feedback = message
                elif simple:
                    msg_feedback = MSG_BASIC_FAIL
                else:
                    msg_feedback = MSG_BASIC_ASSERT

                return_value = None
                try:
                    with self._captured_output(inputs) as out:
                        # Built-in __import__() and open() should be overridden for both model and student
                        self._override_builtin_import(model=True)
                        self._override_builtin_import(model=False)
                        self._override_builtin_open(model=True)
                        self._override_builtin_open(model=False)
                        timeout = self.settings["max_exec_time"]
                        if remote.conn:
                            # Update rpyc timeout so that it matches result_or_timeout
                            remote.conn._config.update({"sync_request_timeout": timeout})
                        running_time, return_value = result_or_timeout(testmethod, testmethod_args, testmethod_kwargs, timeout=timeout)
                        if running_time == timeout and return_value is None:
                            if remote.conn and not remote.conn.closed:
                                remote.conn.close()
                            raise GraderTimeoutError(MSG_GRADER_TIMEOUT.format(timeout))
                except AssertionError as e:
                    tb_str = ''.join(
                        traceback.format_exception(
                            type(e),
                            e,
                            e.__traceback__
                        )
                    ).rstrip()
                    tb = StringIO(tb_str)

                    exercise_string = '  File "' + exercise_path + '/'
                    exercise_line_found = False
                    for line in tb:
                        if line.startswith(exercise_string):
                            exercise_line_found = True
                            break
                    if exercise_line_found:
                        assert_line = tb.readline().strip()
                    else:
                        assert_line = tb_str
                    msg_assert_line = MSG_ASSERT_LINE.format(_prepend_newline(assert_line))

                    submission_string = '  File "' + student_path + '/'
                    submission_line_found = False
                    for line in tb: # Continue reading the traceback
                        if line.startswith(submission_string):
                            submission_line_found = True
                            break
                    if submission_line_found:
                        # AssertionError was raised by student code
                        self._raise_exception_with_feedback(e, show_diff=False, model=False)

                    try:
                        # Reason of failure is the string given to the assert function
                        assert_reason = str(e).split(" : ", 1)[1]
                    except IndexError:
                        # If no string was given, reason of failure is the error message produced by the assert function
                        assert_reason = str(e)
                    msg_assert_reason = MSG_ASSERT_REASON.format(_prepend_newline(_escape_html_chars(assert_reason)))

                    assert_result = str(e).split(" : ", 1)[0]
                    if assert_result == assert_reason:
                        msg_assert_result = ""
                    else:
                        msg_assert_result = MSG_ASSERT_RESULT.format(
                            _prepend_newline(
                                _escape_html_chars(
                                    "AssertionError: " + assert_result
                                )
                            )
                        )

                    if simple:
                        self.test_case.iotester_data["feedback"] = _combine_feedback([
                            MSG_PYTHON_VERSION,
                            msg_feedback,
                            self.name_tested,
                            self.desc,
                            msg_assert_reason,
                            self.used_inputs_and_params,
                        ])
                    else:
                        self.test_case.iotester_data["feedback"] = _combine_feedback([
                            MSG_PYTHON_VERSION,
                            msg_feedback,
                            self.name_tested,
                            self.desc,
                            msg_assert_reason,
                            msg_assert_line,
                            msg_assert_result,
                            self.used_inputs_and_params,
                        ])
                    raise
                except TimeoutError as e:
                    # If an infinite loop is on module-level, result_or_timeout has to wait
                    # for TimeoutError from rpyc because it is unable to return.
                    # Rpyc also uses time.time() timer and sometimes it raises TimeoutError
                    # before result_or_timeout, so we take care of that here.
                    if remote.conn and str(e) == "result expired":
                        remote.conn.close()
                        e = GraderTimeoutError(MSG_GRADER_TIMEOUT.format(timeout))
                    self._raise_exception_with_feedback(e, show_diff=False, model=False)
                except EOFError as e:
                    if remote.conn and str(e) in ["[Errno 32] Broken pipe", "stream has been closed"]:
                        # Student code most likely raised KeyboardInterrupt.
                        # str(e) is "[Errno 32] Broken pipe" if it was raised inside a function.
                        # str(e) is "stream has been closed" if it was raised on module level.
                        # Close remote connection if it is still open (in case of broken pipe).
                        # Rest of the tests run after this will fail with GraderConnClosedError.
                        remote.conn.close()
                        e = KeyboardInterrupt()
                    self._raise_exception_with_feedback(e, show_diff=False, model=False)
                except BaseException as e:
                    self._raise_exception_with_feedback(e, show_diff=False, model=False)
                finally:
                    self.restore(clean_up_files=False)

                self.test_case.iotester_data["feedback"] = _combine_feedback([
                    MSG_PYTHON_VERSION,
                    self.name_tested,
                    self.desc,
                    self.used_inputs_and_params,
                ])
                return return_value
            return wrapper
        return decorator
