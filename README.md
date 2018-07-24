# Graderutils

Python library for test suite management, file validation and test feedback formatting for programming courses on [A+](https://github.com/Aalto-LeTech/a-plus) using [MOOC grader](https://github.com/Aalto-LeTech/mooc-grader) for grading exercises.

## Features

* Running `unittest.TestCase` tests for submitted files and showing results and feedback as HTML.
* Filetype validation before running tests.
* Black- and whitelisting forbidden Python syntax with [abstract syntax tree](https://docs.python.org/3/library/ast.html) nodes.
* Providing prettier exceptions and to-the-point feedback using an HTML error template.
* Reducing the length of traceback strings to include only e.g. the assertion message.
* Customizable HTML templates.

## Quickstart

### Install

```
git clone --depth 1 https://github.com/Aalto-LeTech/python-grader-utils.git
cd python-grader-utils
pip install .
```

### Grade an exercise

```
cd examples/simple
python3 -m graderutils.main test_config.yaml --allow_exceptions 2> results.html
```
This should produce the following into standard output:
```
Falsifying example: test3_large_positive_random_integers(self=<grader_tests.TestPrimes testMethod=test3_large_positive_random_integers>, x=0)
TotalPoints: 0
MaxPoints: 35
```
The resulting HTML results were written into standard error, which was redirected to `results.html`.
You can now e.g. open `results.html` in a browser.

Note that the styles might be incomplete, since graderutils assumes all output will be embedded into a document that already has [Bootstrap](https://getbootstrap.com/) available.

## Customizing

* [Custom HTML](graderutils/static/README.md)
* [Test configuration](graderutils/README.md#test-configuration)

