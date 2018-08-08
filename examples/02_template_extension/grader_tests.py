import unittest
from graderutils.graderunittest import points

class Test(unittest.TestCase):
    @points(1)
    def test1(self):
        # Test cases can be patched with a user_data attribute that should be a JSON serializable dict
        self.user_data = {
            "raw_html": "list of things: <ul>" + "\n".join("<li>{}</li>".format(i) for i in range(10)) + "</ul>",
            "preformatted_feedback": """    - preformatted output

            so much whitespace
        hello-
        yellow
        100001"""
        }

    # Tests without user data

    @points(1)
    def test2(self):
        self.assertTrue(False)

    @points(1)
    def test3(self):
        self.assertTrue(True)
