import unittest
from page_router import classify_header
from batch import duplicate_candidates


def b(text,y=20,score=.99):
    return {"text":text,"score":score,"poly_crop":[[0,y],[200,y],[200,y+20],[0,y+20]]}


class RouterTests(unittest.TestCase):
    def headers(self):
        return [b("序号 规格 进场 数量 生产厂家 合格证号 检验项目",200)]

    def test_target(self):
        self.assertEqual(classify_header([b("材料、构配件进场检验记录")]+self.headers(),500)["decision"],"target")

    def test_body_reference_not_target(self):
        self.assertNotEqual(classify_header([b("材料构配件进场检验记录",350)]+self.headers(),500)["decision"],"target")

    def test_split_title(self):
        self.assertEqual(classify_header([b("材料、构配件",20),b("进场检验记录",45)]+self.headers(),500)["decision"],"target")

    def test_typo_review(self):
        self.assertEqual(classify_header([b("材料构配件进场检验记求")]+self.headers(),500)["decision"],"review")

    def test_no_headers_review(self):
        self.assertEqual(classify_header([b("材料构配件进场检验记录")],500)["decision"],"review")

    def test_empty_review(self):
        self.assertEqual(classify_header([],500)["decision"],"review")

    def test_other(self):
        self.assertEqual(classify_header([b("质量证明书")],500)["decision"],"other")

    def test_other_title_over_body_keyword(self):
        self.assertEqual(classify_header([b('工程材料设备报审表'),b('本批材料已进场',300)],500)['decision'],'other')

    def test_title_conflict_review(self):
        self.assertEqual(classify_header([b('报审表'),b('材料构配件进场检验记录',50)]+self.headers(),500)['decision'],'review')

    def test_low_score_review(self):
        self.assertEqual(classify_header([b("材料构配件进场检验记录",score=.6)]+self.headers(),500)["decision"],"review")

    def test_duplicate_candidate_only(self):
        a={"record_id":"p2_r1","row_no":1,"diameter_mm":"36","weight_t":"39.960","manufacturer":"厂","certificate_no":"001"}
        b2=dict(a,record_id="p5_r1",weight_t="39.96")
        self.assertEqual(len(duplicate_candidates([a,b2])),1)
        self.assertEqual(len([a,b2]),2)


if __name__ == "__main__":
    unittest.main()
