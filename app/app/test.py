"""
Sample test
"""
from django.test import SimpleTestCase

from . import cal

class CalcTest(SimpleTestCase):
        """Test cal module"""
        def test_add_number(self):
            x = 1
            y = 1
            res = cal.add(x,y)
            self.assertEqual(res,2)

        def test_substract_numbers(self):
            """Test subtract numbers."""
            res = cal.subtract(10, 15)

            self.assertEqual(res, 5)        