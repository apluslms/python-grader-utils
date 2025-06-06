## Test configuration

The functionality of the test runner is customized by supplying a [yaml](http://yaml.org/) file containing the desired configuration.
The file must conform to [this](schemas/test_config_v1_4.yaml) JSON schema.
Graderutils will output JSON schema validation errors if a given test configuration file is invalid.
Examples of possible test configurations are found below and in [this](test_config.yaml) example file.


### Feedback template

Path to a [Jinja2](http://jinja.pocoo.org/docs/2.10/api/) HTML template.
For replacing or extending the [default](../graderutils_format/templates/feedback.html) feedback template.
See [this](../examples/03_template_extension) for an example.

### Validation tasks

Pre-testing validation.
Testing will run only if all validation tasks pass.
Common keys for all task types:

* `type`: Validation type
* `display_name`: Name of the validation task, e.g. as a requirement: The file is a Python module that can be imported
* `file`: File which should be validated with the given validation type.
* `break_on_fail`: (Optional) Defaults to `True`. If given and `False`, and if the validation task fails, the feedback is not shown directly, but aggregated with the next failed validation task feedback.

#### Python import

Attempt to import `file` as a Python module and catch all exceptions during import.
Do nothing if import succeeds.

```
validation:
    tasks:
        - type: python_import
          display_name: "The file is a Python module that can be imported"
          file: my_solution.py
```

If the import succeeds, it is possible to check that the module contains some required attributes.
This is specified as a dictionary of attribute names with messages that are shown if the name is not found.
For example, if you want to assert that a submitted module `my_solution` contains the attributes `GLOBAL_VAR`, `MyClass.value` and `calculate`, they can be specified like this:
```
        - type: python_import
          display_name: "The file contains the required attributes"
          file: my_solution.py
          attrs:
              GLOBAL_VAR: global variable
              MyClass.value: class variable
              calculate: function
```
Does nothing if the module contains all names listed in `attrs`.


#### Python syntax check

Read the contents of `file`, attempt to parse the contents using `ast.parse` and catch all exceptions.
Do nothing if there are no exceptions during parsing.

```
        - type: python_syntax
          display_name: "The file has correct Python syntax"
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
Do nothing if there are no matches.

```
        - type: python_blacklist
          display_name: "Module does not contain restricted syntax"
          description: "You are not allowed to use looping constructs or the list builtin."
          file: my_solution.py
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
        - type: python_whitelist
          display_name: "Module does not contain restricted syntax"
          description: "In this exercise, you are only allowed to use numbers and binary operators for addition and subtraction."
          file: my_solution.py
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

### IOTester

Input and output of a program can be compared against the input and output of a model program by using the test methods provided by `IOTester`.

`IOTester` can be used to feed inputs and/or parameters to a program/function. The output of the student program and model program are captured and compared in different ways depending on the used tests (`text_test`, `numbers_test`, etc.) and colored feedback showing the differences is given. Google's `diff_match_patch` is used for the detection and coloring of the differences. Tools for testing things like return values and classes/objects are also available, among other things.

The full list of useful tests/tools is as follows:

* `text_test`
  * Compare the text in the two outputs
* `numbers_test`
  * Compare the numbers in the two outputs
* `return_value_test`
  * Compare some function's return value in the two programs
* `complete_output_test`
  * Compare the text, numbers and whitespace in the two outputs
* `no_output_test`
  * Test that a program/function prints nothing
* `created_file_test`
  * Compare the data in the files that the two programs create
* `random_state_test`
  * Compare Python's pseudo-random number generator states in the two programs
* `amount_of_functions_test`
  * Test that the student program contains the required amount of functions
* `class_structure_test`
  * Create an instance of the model class and the student class and compare the structure of the classes and objects based on the desired restrictions
* `class_init_test`
  * Create an instance of the model class and the student class by running their `__init__()` function and compare the values assigned to the objects' attributes
* `class_str_call_test`
  * Test that an object's `__str__()` method is not called directly
* `feedback`
  * A decorator for displaying better feedback than just the AssertionError message or traceback. Can be used to improve the feedback of a normal test method that does basic assertion tests.
* `model_directory`
  * Context manager for moving to the model directory so that model modules can be imported in test methods that use the feedback decorator

Examples and explanations of unit tests using the IOTester can be found in the aplus-manual [git repository](https://github.com/apluslms/aplus-manual) and the corresponding [A+ site](https://plus.cs.aalto.fi/aplus-manual/master/).


### Traceback formatting
