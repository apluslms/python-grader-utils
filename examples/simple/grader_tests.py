"""
Grader tests that give points and feedback for successful tests.
Random data generation is handled by a property based testing library called Hypothesis:
https://hypothesis.readthedocs.io/en/latest/
"""
import unittest

# Specify test method points and test method level feedback with the points decorator
from graderutils.graderunittest import points
# Strategies for generating random data, more info:
from hypothesis import strategies, given, settings, PrintSettings, Verbosity

# Use a model solution model.py to check the correct behaviour for the submitted file primes.py
from model import is_prime as model_is_prime
from primes import is_prime


# The only requirement for graderutils test classes is that they inherit the standard library unittest.TestCase
class TestPrimes(unittest.TestCase):
    """
    Compare the output of a simple prime number checker to the corresponding model solution.
    """

    # Give 5 points if the method passes, else 0
    # If the test fails, replace the default "The test failed, reason:" with a custom header
    @points(5, msg_on_fail="Test failed, recall that primes are natural numbers")
    def test1_negative_integers(self):
        """Integers in the range [-100, 0)."""
        # Arbitrary unittest test method body
        for x in range(-100, 0, 5):
            self.assertFalse(is_prime(x), "{} is not a prime number but your function says it is.".format(x))

    @points(10)
    def test2_small_positive_integers(self):
        """Integers in the range [100, 200]."""
        for x in range(100, 201):
            if model_is_prime(x):
                self.assertTrue(is_prime(x), "{} is a prime number but your function says it is not.".format(x))
            else:
                self.assertFalse(is_prime(x), "{} is not a prime number but your function says it is.".format(x))

    @points(20)
    # Use Hypothesis to generate random integers and pass them to the test method as argument x
    # Hypothesis uses interal heuristics to choose data distributions and known edge cases depending on the data type
    # https://hypothesis.readthedocs.io/en/latest/data.html
    @given(x=strategies.integers(min_value=0, max_value=10**6))
    # Hypothesis attempts to cause this test method to fail with different x.
    # This falsification process ends when 100 instances of x have been found that did not fail the test, i.e. max_examples.
    # We also disable the Hypothesis database, i.e. cache, because we are not interested in remembering how the tests behaved for data generated on previous test executions
    # https://hypothesis.readthedocs.io/en/latest/settings.html#available-settings
    @settings(max_examples=100, database=None, print_blob=PrintSettings.NEVER, verbosity=Verbosity.quiet)
    def test3_large_positive_random_integers(self, x):
        """Randomly picked integers in the range [0, 1 000 000]."""
        if model_is_prime(x):
            self.assertTrue(is_prime(x), "{} is a prime number but your function says it is not.".format(x))
        else:
            self.assertFalse(is_prime(x), "{} is not a prime number but your function says it is.".format(x))

    # Optionally, if you need setUp and tearDown:

    # If hypothesis.given is used on a test method, Hypothesis runs several iterations on the method.
    # Then, using TestCase.setUp and TestCase.tearDown might appear to behave inconsistently.
    # To solve this, Hypothesis provides setup_example and teardown_example for finer granularity:

    def setUp(self):
        # From unittest, runs once before running each test method
        # e.g. once for test3_large_positive_random_integers
        pass

    def setup_example(self):
        # From Hypothesis, runs once before running each Hypothesis example
        # e.g. 100 times for test3_large_positive_random_integers
        pass

    def tearDown(self):
        # From unittest, runs once after running each test method
        # e.g. once for test3_large_positive_random_integers
        pass

    def teardown_example(self, example):
        # From Hypothesis, runs once after running each Hypothesis example
        # e.g. 100 times for test3_large_positive_random_integers
        pass


# Graderutils will use its own test runners for grading, which means this module will not executed as main.
# You can of course use the unittest.main runner if you want to run the tests locally without graderutils
if __name__ == "__main__":
    unittest.main(verbosity=2)
