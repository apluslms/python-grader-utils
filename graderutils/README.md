## Test configuration

The functionality of the pipeline is customized by supplying a [yaml](http://yaml.org/) file containing the desired configuration.
The accepted keys are:

* `test_modules`: List of Python test modules and their descriptions.
  * `module`: Name of an importable module. This should be unique since it is also used as a key for this test in graderutils.
  * `description`: Short description for this test type.
* `feedback_template`: (Optional) Defaults to `static/feedback_template.html`. Customized feedback template shown when there are no unexpected errors during grading. See [this](static/README.md) for details about extending or overriding.
* `error_template`: (Optional) Defaults to `static/error_template.html`. Customized error template shown when there are unexpected errors during grading.
* `no_default_css`: (Optional) Defaults to `False`. If given and `True`, do not include the [default styles](static/feedback.css) when rendering templates. Default styles can be disabled also by overriding the `styles` block in a child template.

* `validation`: (Optional) List of validation tasks to be performed before the tests defined in `test_modules` are executed.

### Validation tasks

Examples of all available validation task types accepted by the [validation](validation.py) module.
Common keys for all task types:

* `type`: Validation type
* `file`: File which should be validated with the given validation type.
* `break_on_fail`: (Optional) Defaults to `True`. If given and `False`, and if the validation task fails, the feedback is not shown directly, but aggregated with the next failed validation task feedback.

#### Python import

Attempt to import `file` as a Python module and catch all exceptions during import.
Show exceptions with the error template if there are any.
Do nothing if import succeeds.

```
  type: python_import
  file: my_solution.py
```

If the import succeeds, it is possible to check that the module contains some required attributes.
This is specified as a list of attribute names.
For example, if you want to assert that a submitted module `my_solution` contains the attributes `GLOBAL_VAR`, `MyClass.value` and `my_function`, they can be specified like this:
```
  type: python_import
  file: my_solution.py
  attrs:
    - GLOBAL_VAR
    - MyClass.value
    - my_function
```
All missing attributes will be shown using the error template.
Does nothing if the module contains all names listed in `attrs`.


#### Python syntax check

Read the contents of `file`, attempt to parse the contents using `ast.parse` and catch all exceptions.
Show exceptions with the error template if there are any.
Do nothing if there are no exceptions during parsing.

```
  type: python_syntax
  file: my_solution.py
```

#### Python blacklist

Read the contents of `file` and parse the contents using `ast.parse`.
Walk once through all syntax nodes in the syntax tree for the parsed module.
Syntax can be restricted using the following keys:
  * `node_names`: Dict of node name - message pairs. Node names should be the class names of ast nodes. E.g. an ast.Call node would be matched if `node_names` contains a key that is equal to `Call`.
  * `node_dumps`: Dict of node dump - message pairs. Node dumps are the string output of ast.dump.
  * `node_dump_regexp`: Dict of escaped regexp string - message pairs. The regexp patterns are matched to the output of ast.dump.

For each found match, the filename, line number, line content and the short message for the node are recorded.
Matches are shown with the error template using the given message in `message`.
Do nothing if there are no matches.

```
  type: python_blacklist
  file: my_solution.py
  message: "You are not allowed to use looping constructs or the list builtin."
  node_names:
    For: For loops
    While: While loops
    ListComp: List comprehensions
    # etc.
  node_dumps:
    "Name(id='list', ctx=Load())": Loading the list builtin
  node_dump_regexp:
    "^Name\\(id\\=\\'list\\'": Loading the list builtin
```

#### Python whitelist

Similar to Python blacklist, but instead of searching for matches, search for all node names or node dumps that do *not* match a syntax node given in the configuration.
The short descriptions of `node_names`, `node_dumps` and `node_dump_regexp` are ignored and instead the name of the syntax node not found is used as a short description.
In the below example, finding for example an `ast.Call` node would be a match with the short description `"Call"`.

```
  type: python_whitelist
  file: my_solution.py
  message: "In this exercise, you are only allowed to use numbers and binary operators for addition and subtraction."
  node_names:
    Module: Module
    Expr: Expression
    BinOp: Binary operator
    Num: Number
    Sub: Subtraction
    Add: Addition
```


#### Plain text blacklist

TODO

#### Plain text whitelist

TODO

#### Image header check

TODO

#### LabView header check

TODO

#### HTML validation

TODO
