"""CPU几何合成测试，不调用OCR。"""
import unittest
import cv2
import numpy as np
from lab import geometry


class GeometryTests(unittest.TestCase):
    def sample(self):
        image = np.full((700, 1000, 3), 255, np.uint8)
        for y in [100, 200, 300, 400, 500]:
            cv2.line(image, (100, y), (900, y), (0, 0, 0), 3)
        for x in [100, 300, 500, 700, 900]:
            cv2.line(image, (x, 100), (x, 500), (0, 0, 0), 3)
        config = {"quad_normalized": [[.1,100/700],[.9,100/700],[.9,500/700],[.1,500/700]],
                  "target_size": [800,400], "column_boundaries":[0,.25,.5,.75,1],
                  "expected_rows":4, "line_coverage":.55}
        return image, config

    def test_grid(self):
        image, config = self.sample()
        _, _, xs, ys, errors, _, _ = geometry(image, config)
        self.assertEqual(errors, [])
        self.assertEqual((len(xs),len(ys)),(5,5))

    def test_wrong_rows_blocked(self):
        image, config = self.sample()
        config["expected_rows"] = 5
        self.assertTrue(geometry(image, config)[4])

    def test_missing_vertical_blocked(self):
        image, config = self.sample()
        image[103:498,497:504] = 255
        self.assertTrue(geometry(image, config)[4])

    def test_inverse_coordinates(self):
        image, config = self.sample()
        matrix = geometry(image, config)[1]
        points = np.float32([[[250,250],[500,300]]])
        restored = cv2.perspectiveTransform(cv2.perspectiveTransform(points,matrix), np.linalg.inv(matrix))
        np.testing.assert_allclose(restored, points, atol=.01)


if __name__ == "__main__":
    unittest.main()
