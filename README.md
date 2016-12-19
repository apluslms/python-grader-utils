Miscellaneous tools and templates for showing more specific and hopefully
slightly prettier feedback than just the console output produced by ``unittest.main`` after
running Python grader tests in MOOC grader.
Created during the summer 2016 for CS-A1141 Tietorakenteet ja algoritmit Y.

## ``astparser.py``

Provides crude capabilities of inspecting the syntax of a submitted Python file.

## ``constants.py``

Mappings of names to ``astparser``-output.
These names should be included in a ``test_config.py``-file in the ``user``-directory in the temporary ``uploads``-directory of the MOOC grader sandbox.

## ``error_template.html``

Rendered by ``importvalidator.py`` if the submitted file does not conform to the
specs as defined in ``test_config.py``.

## ``feedback.css``

Styles for the rendered templates.

## ``feedback.js``

Used for drawing for example graphs from ``JSON`` generated from the grader
tests.
The figures are drawn into ``feedback_template_en.html``.

## ``feedback_template_en.html``

Contains bootstrap styled versions of unittest test results.
Rendered by ``grader_main.py`` after running all the tests.

## ``grader_main.py``

Main test runner and discoverer.

## ``graderunittest.py``

Base ``TestCase``-class for MOOC grader tests.
Added a timed test case class with timeout for individual test methods.
(The default MOOC grader timeout is to sigkill the Python interpreter.)

## ``htmlgenerator.py``

Renders ``unittest`` test result objects as HTML using
[Jinja2](http://jinja.pocoo.org/docs/dev/).

## ``importvalidator.py``

Checks that the submitted file does not contain invalid syntax and that it
conforms to the specs defined in the ``test_config.py`` file for the exercise.

## ``testcoveragemeta.py``

Can be used to generate coverage-tests for user uploaded tests

To create a new coverage-test create a ``coverage_tests.py`` with necessary imports and class TestCoverage with TestCoverageMeta as it's metaclass. Example:

```python
class TestCoverage(unittest.TestCase, metaclass=TestCoverageMeta, test="usertest", filename="userfile", points=[8, 10, 12]):
    pass
```
The keyword arguments are:

Argument  | Function
--------  | --------
testmodule| the name of the test module user uploaded
filename  | the name of the file that you check the coverage for
points    | list of points for different coverage amounts

This example would run usertest (from test import Test as usertest) and check coverages for userfile.py.
It would give 8 points if 33.33% of userfile.py would be covered, 10 points more if 66.66% and 12 points if 100%
totaling 30 points.
If you give a list with 5 point amounts it would check coverage in 20% intervals.
It will give 0 points out of the total if all of the users tests won't succeed

Because you don't want grader to run users tests as graded tests (because crafty users could add (1000p) to their tests and it shows up ugly) you should also add

```python
def load_tests(*args, **kwargs):
    return unittest.TestLoader().loadTestFromTestCase(TestCoverage)
```
in ``coverage_tests.py``