import unittest
import random
import string

from graderutils.graderunittest import points

# ASCII letters with significant probability of spaces
char_distribution = 10*' ' + string.ascii_letters

def random_string(n):
    return ''.join(random.choice(char_distribution) for _ in range(n))

def noisy_copy(s, copy_prob):
    """Create a copy of s by copying each character with a given probability, else draw random character"""
    return ''.join(c if random.random() < copy_prob else random.choice(char_distribution) for c in s)


class Test(unittest.TestCase):
    def setUp(self):
        self.user_data = {}

    def set_marked_and_assert_equal(self, a, b):
        marked_b = [(b_char, a_char == b_char) for a_char, b_char in zip(a, b)]
        self.user_data = {"string_a": a, "marked_b": marked_b}
        if a != b:
            self.fail("Strings were not equal")

    @points(1)
    def test1_strings_equal(self):
        # Expected
        a = "The sand was yellow"
        # Compared
        b = "The song was mellow"
        self.set_marked_and_assert_equal(a, b)

    @points(1)
    def test2_strings_equal(self):
        a = "The sand was yellow"
        b = a
        self.set_marked_and_assert_equal(a, b)

    @points(1)
    def test3_random_strings_equal(self):
        a = random_string(200)
        b = noisy_copy(a, 0.8)
        self.set_marked_and_assert_equal(a, b)
