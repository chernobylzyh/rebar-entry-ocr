import unittest
from parsing import compact, parse_weight, parse_manufacturer_certificate, parse_row


class ParsingTests(unittest.TestCase):
    def test_decimal(self):
        self.assertEqual(parse_weight("38. 840t"), ("38.840", None))

    def test_kg(self):
        self.assertEqual(parse_weight("38840kg"), ("38.84", None))

    def test_no_unit(self):
        self.assertIsNone(parse_weight("38.840")[0])

    def test_no_guess(self):
        self.assertIsNone(parse_weight("38.O40t")[0])

    def test_two_weights(self):
        self.assertIsNone(parse_weight("38.840t 39.3t")[0])

    def test_zero(self):
        self.assertIsNone(parse_weight("0t")[0])

    def test_fullwidth(self):
        self.assertEqual(compact("１２３\n４"), "1234")

    def test_company_certificate(self):
        self.assertEqual(parse_manufacturer_certificate("浙江万泰特钢有限公\n司2607142902"),
                         ("浙江万泰特钢有限公司", "2607142902", None))

    def test_wrapped_certificate(self):
        self.assertEqual(parse_manufacturer_certificate("安徽长江钢铁股份有\n限公司CJ1260626177\n8")[1],
                         "CJ12606261778")

    def test_leading_zero(self):
        self.assertEqual(parse_manufacturer_certificate("测试公司0012345678")[1], "0012345678")

    def test_no_separator(self):
        self.assertIsNotNone(parse_manufacturer_certificate("2607142902")[2])

    def test_punctuation_rejected(self):
        self.assertIsNotNone(parse_manufacturer_certificate("测试公司2607?42902")[2])

    def test_row(self):
        result = parse_row({"row_no":"11","weight":"38.840t","specification":"36mm",
                            "manufacturer_certificate":"浙江万泰特钢有限公司2607142902"},11)
        self.assertEqual(result["issues"], [])

    def test_row_mismatch(self):
        self.assertIn("row_number_mismatch", parse_row({"row_no":"10"},11)["issues"])


if __name__ == "__main__":
    unittest.main()
