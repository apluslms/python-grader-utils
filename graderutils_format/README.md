Convert ["Grading feedback"](schemas/grading_feedback.schema.json) JSON schema objects into HTML.

Convert `results.json` into a full HTML5 document with styles using [Bootstrap](https://getbootstrap.com/docs/5.3/getting-started/introduction/):
```
cat results.json | python3 -m graderutils_format.html --full-document > results.html
```
Omit `--full-document` to render without the [base template](templates/base.html).
