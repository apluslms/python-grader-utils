
Graderutils
===========

Python library for test suite management, file validation and test feedback formatting for programming courses on [A+](https://github.com/Aalto-LeTech/a-plus) using [MOOC grader](https://github.com/Aalto-LeTech/mooc-grader) for grading exercises.

Features
--------
* Running tests for submitted files and showing results and feedback as HTML.
* Filetype validation before running tests.
* Black- and whitelisting forbidden Python syntax with [abstract syntax tree](https://docs.python.org/3/library/ast.html) nodes.
* Providing prettier exceptions and to-the-point feedback using an HTML error template.
* HTML templates can be customized.


Installing
----------

Install as a Python package into the Python virtual environment used by the grader.
```
pip install git+https://github.com/Aalto-LeTech/python-grader-utils.git
```

