Minimal example of a graderutils exercise.

After installing graderutils, run the below command in this directory to run the tests.
Test feedback is rendered as HTML into stderr.
```
python3 -m graderutils.main test_config.yaml --allow_exceptions 2> results.html
```
View `results.html` in a browser.

Note that it is assumed that the results will be embedded into a document (A+) that already has [Bootstrap](https://getbootstrap.com/) available.
