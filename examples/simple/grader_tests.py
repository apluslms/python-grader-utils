import unittest
import random

from graderutils.graderunittest import points

# Use a model solution model.py to check the correct behaviour for the submitted file primes.py
from model import is_prime as model_is_prime
from primes import is_prime


class TestPrimes(unittest.TestCase):

    @points(5)
    def test1_negative_integers(self):
        """Integers in the range [-100, 0)."""
        for x in range(-100, 0, 5):
            self.assertFalse(is_prime(x), "{} is not a prime number but your function says it is.".format(x))

    @points(10)
    def test2_small(self):
        """Integers in the range [100, 200]."""
        for x in range(100, 201):
            if model_is_prime(x):
                self.assertTrue(is_prime(x), "{} is a prime number but your function says it is not.".format(x))
            else:
                self.assertFalse(is_prime(x), "{} is not a prime number but your function says it is.".format(x))

    @points(20)
    def test3_large_random(self):
        """Randomly picked integers in the range [0, 1 000 000]."""
        for _ in range(1000):
            x = random.randint(0, 10**6)
            if model_is_prime(x):
                self.assertTrue(is_prime(x), "{} is a prime number but your function says it is not.".format(x))
            else:
                self.assertFalse(is_prime(x), "{} is not a prime number but your function says it is.".format(x))
