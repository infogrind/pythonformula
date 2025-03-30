import unittest
import io
from unittest.mock import patch
from main import main


class TestMain(unittest.TestCase):
    def test_script(self):
        test_input = """\
Hello, world!
Bumbum
"""

        expected_output = """\
* Hello, world!
* Bumbum
"""

        with (
            patch("sys.stdin", io.StringIO(test_input)),
            patch("sys.stdout", new=io.StringIO()) as fake_out,
        ):
            main()

            actual_output = fake_out.getvalue()

        self.assertEqual(expected_output, actual_output)


if __name__ == "__main__":
    unittest.main()
