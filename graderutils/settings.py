# False hides all traceback messages and instead shows a generic error message if there is an error in the test infrastructure, i.e. not in the grading tests
debug = False

# Optional paths to all Python modules containing TestCases that should be executed as grading tests.
# grader_tests.py (if it exists) will be run by default
test_modules = [
    "local_tests.py",
    "coverage_tests.py"
]

# HTML templates which are rendered after grading.
# Paths should be relative to the directory where grading happens

# Used when all tests exit with a zero error code
feedback_template = "feedback_template.html"
# Used when some test exits with a non-zero error code
error_template = "error_template.html"

