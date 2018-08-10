# Graderutils

Python library that handles grader test suite management, file validation and test feedback formatting.
Originally developed to enable HTML feedback for programming exercise grading output for courses served on the [A+](https://github.com/Aalto-LeTech/a-plus) platform.
The A+ platform is not required to run graderutils.

## Features

* Running `unittest.TestCase` tests and producing generic JSON results that may be converted into HTML.
* [Validation tasks](graderutils#validation-tasks) before running tests.
* Restricting allowed Python syntax using black- and whitelists of [AST](https://docs.python.org/3/library/ast.html) node names.
* Formatting tracebacks and exception messages to include only essential information (by default the full, unformatted traceback is also available).

Results from `examples/01_simple` rendered with the default theme:

![Grading feedback screenshot](screen_v3.0.png "Grading feedback")

## Quickstart

### Install

```
git clone --depth 1 https://github.com/Aalto-LeTech/python-grader-utils.git
cd python-grader-utils
pip install .
```

### Examples

See [this](examples/01_simple) for a minimal graderutils exercise.

For exercises with random input data generation, see [this](examples/02_property_based_testing) example.

If you want to extend or replace the current feedback template, see [this](examples/03_template_extension) example.

For embedding JavaScript into the feedback template, see [this](examples/04_embedded_plot) example.

## Using `feedbackformat` without graderutils

Any JSON strings that validate successfully against the ["Grading feedback"](feedbackformat/schemas/grading_feedback.schema.json) [JSON schema](http://json-schema.org/) can be converted to human readable form using `feedbackformat`.

E.g.
```
cat results.json | python3 -m feedbackformat.html > results.html
```

Outline of the grading feedback JSON contents:

![Grading feedback JSON schema object diagram](feedbackformat/schemas/grading_feedback.png "Grading feedback JSON")
