"""
GRAMMAR_NAMES:
Dictionary containing sets of all possible 'synonyms' for names returned by the AST.
It is used to block the execution of submitted files that contain forbidden words,
such as use of the list class in a linked list exercise.

The actual Python syntax for which the names correspond to is shown as comments.

This could and should be expanded when new exploits are discovered.

HYPOTHESIS:
Hypothesis settings.
"""

# from hypothesis import HealthCheck

# TODO:
# known exploits not covered:
# * redefining function name references: rvrsd = reversed; srtd = sorted; etc.
# * inheritance: class lst(list); class dct(dict); etc.

GRAMMAR_NAMES = {
    "list": {
        "Call:list", # lst = list()
        "List",      # lst = []
        "ListComp"   # lst = [i for i in range(0)]
    },
    "dict": {
        "Call:dict", # d = dict()
        "Dict",      # d = {"a": 0}
        "DictComp"   # d = {"a": i for i in range(1)]
    },
    "sequence_reversing": {
        "Call:reversed",     # reversed(<anything>)
        "Call::reverse",     # lst.reverse()
        # Not implemented
        #"SliceReverse"       # sequence[::-a], where a is an positive integer
    },
    "sorting": {
        "Call:sorted",
        "Call::sort"
    },
    "min_function": {
        "Call:min"
    },
    "sum_builtin": {
        "Call:sum"
    },
    "import_collections_module": {
        "Import:collections",          # import module, ... , collections
        "ImportFrom:collections",      # from collections imp...

        "Import:collections.abc",      # import module, ... , collections.abc
        "ImportFrom:collections.abc"   # from collections.abc imp...
    },
    "import_inorder": {
        "Import:inorder",          # import module, ... , inorder
        "ImportFrom:inorder",      # from inorder imp...
    },
    "import_heapq_module": {
        "Import:heapq",          # import module, ... , heapq
        "ImportFrom:heapq",      # from heapq imp...
    },
    "import_sys": {
        "Import:sys",
        "ImportFrom:sys",
    },
    # The MOOC grader action which runs tests in a sandbox should copy all of these
    # modules into the same folder
    "inspecting_grader_tests": {
        "Import:grader_tests",      # import module, ... , grader_tests
        "ImportFrom:grader_tests",  # from grader_tests imp...

        "Import:importvalidator",      # import module, ... , importvalidator
        "ImportFrom:importvalidator",  # from importvalidator imp...

        "Import:astparser",      # import module, ... , astparser
        "ImportFrom:astparser",  # from astparser imp...

        # For example model solutions
        "Import:model",      # import module, ... , model
        "ImportFrom:model",  # from model imp...

        "Import:htmlgenerator",      # import module, ... , htmlgenerator
        "ImportFrom:htmlgenerator",  # from htmlgenerator imp...

        "Import:constants",      # import module, ... , constants
        "ImportFrom:constants",  # from constants imp...

        "Import:graderunittest",        # import module, ... , graderunittest
        "ImportFrom:graderunittest",    # from graderunittest imp...

        "Import:inspect",               # import module, ... , inspect
        "ImportFrom:inspect"            # from inspect imp...
    }
}

# For convenience
GRAMMAR_NAMES["builtin_containers"] = GRAMMAR_NAMES["list"] | GRAMMAR_NAMES["dict"]


################
#  Hypothesis  #
################

# Customized settings for specified exercise tests
HYPOTHESIS = {
    "all": {
        "max_examples": 100, # Number of test values
        "database": None, # Hypothesis database
        "max_shrinks": 1, # How many times the dataset is shrinked when a test fails
        # "suppress_health_check": [HealthCheck.too_slow] # Keep running tests even if data generation is slow
    },
    "sorting": {
        "max_examples": 10
    },
    "bst_remove": {
        "max_examples": 50
    },
    "network": {
        "max_examples": 200
    }
}
# The hypothesis database allows dataset generation to continue from the
# previous failed values.
# It's set to None here because the MOOC grader destroys its sandboxes after each
# grading task. So the hypothesis database would be deleted also.
# You can read more about the hypothesis example database here:
# https://hypothesis.readthedocs.io/en/latest/database.html

def update_settings_profile(test_key, settings):
    """
    Updates an imported settings module with predefined settings.

    @type test_key: C{str}
    @param test_key: Settings key for a specific test settings defined in HYPOTHESIS.
    @type settings: hypothesis.settings module
    @param settings: Settings which are being overridden.
    """
    custom_settings = HYPOTHESIS["all"].copy()

    if test_key in HYPOTHESIS.keys() and test_key != "all":
        custom_settings.update(HYPOTHESIS[test_key])

    # As of 07/2016 hypothesis does not seem to provide loading custom settings
    # without first registering a profile and then loading the same profile
    settings.register_profile(test_key, settings(**custom_settings))
