
Graderutils
===========

Python library for test suite management, file validation and test feedback formatting for programming courses on [A+](https://github.com/Aalto-LeTech/a-plus) using [MOOC grader](https://github.com/Aalto-LeTech/mooc-grader) for grading exercises.
Originally created during the summer 2016 for an introductory course in data structures and algorithms (CS-A1141 Tietorakenteet ja algoritmit Y) at [Aalto University](http://www.aalto.fi/en).

Features
--------
* Running tests for submitted files and showing results and feedback as HTML.
* Filetype validation before running tests.
* Blacklisting forbidden Python syntax with [abstract syntax tree](https://docs.python.org/3/library/ast.html) nodes.
* Providing prettier exceptions and to-the-point feedback using an HTML error template.
* (TODO) HTML templates, CSS and JavaScript can be customized.
* (TODO) Settings can be included into [MOOC grader](https://github.com/Aalto-LeTech/mooc-grader) exercise configuration files.


Installing
----------

Install as a Python package into the Python virtual environment used by the grader.
```
(TODO) pip install git+https://github.com/Aalto-LeTech/python-grader-utils.git@v1.0
```

TODO
====

* Email error logger

