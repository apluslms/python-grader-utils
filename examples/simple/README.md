Example of a graderutils exercise, where the problem is to implement a simple prime number checker `primes.is_prime`.
An incorrect solution can be found in `primes.py`, which is compared against the reference solution `model.py`.

Running:
```
python3 -m graderutils.main test_config.yaml --allow_exceptions 2> results.html
```
Which should produce into standard output:
```
TotalPoints: 5
MaxPoints: 35
```
HTML results were written to standard error and directed to `results.html`.
