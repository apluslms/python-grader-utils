# Extending the feedback template

It is possible to insert customized elements (for example JavaScript for test state visualization) into the feedback template by overriding different blocks, using Jinja2 [template inheritance](http://jinja.pocoo.org/docs/2.10/templates/#template-inheritance).

The blocks can be overridden by supplying a child template that extends the feedback template.
In order to extend the feedback template, the child template should begin with the line:

`{% extends feedback_template %}`

To completely replace the feedback template, simply exclude the above line.

In order of appearance in `feedback.html`, the blocks that can be overridden are:

* `feedback_start`: Empty block in the beginning of the template.
* `styles`: Includes a simple, [default stylesheet](default.css).
* `feedback_end`: Empty block at the end of the template.
