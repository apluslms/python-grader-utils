Example of a graderutils exercise, where the problem is to implement a simple prime number checker `primes.is_prime`.
An incorrect solution can be found in `primes.py`, which is compared against the reference solution `model.py`.

Running:
```
python3 -m graderutils.main test_config.yaml --allow_exceptions 2> results.html
```
Which should produce into standard output:
```
Falsifying example: test3_large_positive_random_integers(self=<grader_tests.TestPrimes testMethod=test3_large_positive_random_integers>, x=0)
TotalPoints: 0
MaxPoints: 35
```
