# Graderutils

Python library that handles grader test suite management, file validation and test feedback formatting.
Originally developed to enable HTML feedback for programming exercise grading output for courses served on the [A+](https://github.com/Aalto-LeTech/a-plus) platform.
However, A+ is not a dependency for running graderutils.

## Features

* Running `unittest.TestCase` tests and displaying results and feedback as HTML.
* [Validation tasks](graderutils#validation-tasks) before running tests.
* Restricting allowed Python syntax using black- and whitelists of [AST](https://docs.python.org/3/library/ast.html) node names.
* Formatting tracebacks and exception messages to include only essential information (by default the full, unformatted traceback is also available).

## Quickstart

### Install

```
git clone --depth 1 https://github.com/Aalto-LeTech/python-grader-utils.git
cd python-grader-utils
pip install .
```

### Grade an exercise

A minimal exercise can be found in `examples/01_simple`.
The task is to write a Python function `is_prime`, that returns `True` if a given (small) integer is prime.

Run `grader_tests.py`, which tests that (an incorrect solution) `primes.py` behaves exactly as `model.py`:
```
cd examples/01_simple
python3 -m graderutils.main test_config.yaml --develop-mode 2> results.html
```
This should produce the following into standard output:
```
TotalPoints: 5
MaxPoints: 35
```
Unittest output was rendered as HTML and written into standard error and redirected to `results.html`, which you can now open in a browser.

Note that the styles might be incomplete, since for now graderutils assumes all output will be embedded into a document that already has [Bootstrap](https://getbootstrap.com/) available.

## Customizing the output HTML

It is possible to extend or replace the current feedback template, see e.g. this [example](examples/02_template_extension).

In the future, it would be nice to have all HTML rendering capabilities in a separate library that renders generic test result JSON into arbitrary HTML templates.
Feedback visualization features could be added as generic plugins instead of relying only on injecting raw html into the default template.

## Convert arbitrary test output JSON to HTML

It is possible to convert any test result into HTML if the result is a JSON string that validates successfully against the ["Grading feedback"](schemas/grading_feedback.schema.json) [JSON schema](http://json-schema.org/).

E.g.
```
cat results.json | python3 -m graderutils.htmlformat
```

To produce JSON results with graderutils, run with the flag `--json-output`, or set the environment variable `GRADERUTILS_JSON_RESULTS` to 1.
```
python3 -m graderutils.main test_config.yaml --json-output > results.json
```
