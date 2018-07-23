# Graderutils

Python library for test suite management, file validation and test feedback formatting for programming courses on [A+](https://github.com/Aalto-LeTech/a-plus) using [MOOC grader](https://github.com/Aalto-LeTech/mooc-grader) for grading exercises.

## Features

* Running tests for submitted files and showing results and feedback as HTML.
* Filetype validation before running tests.
* Black- and whitelisting forbidden Python syntax with [abstract syntax tree](https://docs.python.org/3/library/ast.html) nodes.
* Providing prettier exceptions and to-the-point feedback using an HTML error template.
* Customizable HTML templates.


## Quickstart

```
git clone --depth 1 https://github.com/Aalto-LeTech/python-grader-utils.git
cd python-grader-utils
pip install .
cd examples/simple
python3 -m graderutils.main test_config.yaml --allow_exceptions 2> results.html
```
View `results.html` in a browser.

Note that the styles might be incomplete, since graderutils assumes all output will be embedded into a document that already has [Bootstrap](https://getbootstrap.com/) available.

## Customizing

* [Custom HTML](graderutils/static/README.md)
* [Test configuration](graderutils/README.md#test-configuration)

