import unittest
import cv2
import numpy as np
from blank_rows import ink_evidence, classify_row
from parsing import parse_row


class BlankTests(unittest.TestCase):
    def test_white(self):
        self.assertFalse(ink_evidence(np.full((130, 300, 3), 255, np.uint8))["has_ink"])

    def test_unreadable(self):
        self.assertEqual(classify_row({"weight":""}, {"weight":{"has_ink":True}}), "unreadable")

    def test_remark_only(self):
        self.assertEqual(classify_row({"weight":"", "remarks":"待补"}, {}), "content")

    def test_zero_not_blank(self):
        self.assertEqual(classify_row({"weight":"0"}, {}), "content")

    def test_blank(self):
        self.assertEqual(classify_row({"weight":""}, {"weight":{"has_ink":False}}), "blank_candidate")

    def test_digit(self):
        img=np.full((130,300,3),255,np.uint8)
        cv2.putText(img,"1",(100,85),cv2.FONT_HERSHEY_SIMPLEX,1.5,(0,0,0),2)
        self.assertTrue(ink_evidence(img)["has_ink"])

    def test_sequence_from_ocr(self):
        r=parse_row({"row_no":"12","weight":"40.782t","specification":"36mm",
                     "manufacturer_certificate":"浙江万泰特钢有限公司2606042901"},None)
        self.assertEqual(r["issues"],[])


if __name__ == "__main__":
    unittest.main()
