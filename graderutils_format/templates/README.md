# Extending the feedback template

It is possible to insert customized elements (for example JavaScript for test state visualization) into the feedback template by overriding different blocks, using Jinja2 [template inheritance](http://jinja.pocoo.org/docs/2.10/templates/#template-inheritance).

The blocks can be overridden by supplying a child template that extends the feedback template.
In order to extend the feedback template, the child template should begin with the line:

`{% extends feedback_template %}`

To completely replace the feedback template, simply exclude the above line.

## Overriding blocks

In order of appearance in `feedback.html`, the blocks that can be overridden are:

* `body`: Used only with the [base template](base.html) to insert the feedback into the body of the base template.
* `styles`: Includes a simple, [default stylesheet](default.css).
* `feedback_start`: Empty block above all feedback.
* `result_panel` (scoped): Panel body of a test result. Override this to completely replace the body of a result.
* `result_panel_after_output` (scoped): Empty block inside the panel of a test result, after the pre-element containing the test output. Insert custom HTML here.
* `feedback_end`: Empty block after all feedback.

### Scoped blocks

Scoped blocks retain the namespace of the extended template during extension.
E.g. we can extend `feedback.html` with some custom template and reference each test result variable as the default template is being rendered:
```
{% extends feedback_template %}


{% block result_panel_after_output %}

{# For all failed tests, add a 'failed' text #}
{% if result.state == "fail" %}
<p>failed</p>
{% endif %}

{# Get the loop indexes #}
{{ result_group_loop.index }}
{{ result_result_loop.index }}

{% endblock %}
```
