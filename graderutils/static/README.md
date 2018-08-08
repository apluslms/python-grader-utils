# Templates


Two kinds of HTML templates may be used for rendering the feedback of a grading result, depending on the state at which grading was terminated.

## Feedback template

[This template](feedback_template.html) is chosen when grading succeeds in the sense that if there are exceptions, they are caused by the runtime logic of the submitted solution and not pre-grading validation errors or improper grader test configuration.


## Error template

[This template](error_template.html) is chosen when grading fails, for example due to invalid syntax in the submitted solution, use of restricted syntax, configuration errors in the test suite or other unexpected errors that prevent grading of the contents of submitted solution.


## Extending

It is possible to insert customized elements (for example JavaScript for test state visualization) into the feedback template by overriding different blocks, using Jinja2 [template inheritance](http://jinja.pocoo.org/docs/2.9/templates/#template-inheritance).

The blocks can be overridden by supplying a child template that extends the feedback template.
In order to extend the feedback template, the child template must (should) begin with the line:

`{% extends feedback_template %}`

In order of appearance in this template, the blocks that can be overridden are:

* `feedback_start`: Empty block in the beginning of the template.
* `styles`: Includes a simple, [default stylesheet](feedback.css). If you are using a course-wide stylesheet, you can disable the default styles by passing a child template with an empty `styles` block or set the `no_default_css` key to `True` in the test configuration yaml.
* `success_panel_body`: (scoped) Collapsible body of test feedback panels of passed tests.
* `failed_panel_body_feedback`:  (scoped) Feedback for the failed test. I.e. the message of an `AssertionError` instance that caused the test to fail.
* `failed_panel_body_user_data`:  (scoped) Rest of the body of test feedback panels of failed tests.
* `error_panel_body`:  (scoped) Collapsible body of test feedback panels of tests during which other than `AssertionError` exceptions were raised.
* `feedback_end`: Empty block at the end of the template.

Inserting custom elements works similar to the principle of inversion of control in the sense that the contents of the overriding, custom blocks will be evaluated during the rendering of the base template.
The [scoped blocks](http://jinja.pocoo.org/docs/2.9/templates/#block-nesting-and-scope) retain the variables from the base template and can be used in the custom blocks.
For example, the loop variables of the base template can be referenced in the overriding blocks in the supplied child template.

TODO see [this]() example course on how to insert custom blocks into the feedback template.

## Replacing

It is possible to rewrite the whole feedback template by simply excluding the `extends` statement from the beginning of the supplied custom template.

## JavaScript

There are currently no sophisticated capabilities for loading external JavaScript within the feedback template.
If a child template uses JavaScript, proper loading of possible external resources must be implemented in the child template.
