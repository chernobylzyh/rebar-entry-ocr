import unittest
from pathlib import Path
import cv2
import numpy as np
from lab import geometry,read_json
from alignment import locate_body
from orientation import rotate_page


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.config=read_json(Path(__file__).with_name('template_entry_full.json'))

    def sample(self):
        im=np.full((1800,1300,3),255,np.uint8)
        cv2.rectangle(im,(120,80),(1220,1680),(0,0,0),3)
        for y in [200,260]+list(range(400,1171,70))+[1500]:
            cv2.line(im,(120,y),(1220,y),(0,0,0),3)
        for f in self.config['column_boundaries'][1:-1]:
            x=round(120+1100*f)
            cv2.line(im,(x,260),(x,1170),(0,0,0),3)
        return im

    def test_same_layout_shift_scale_skew(self):
        im=self.sample()
        for angle,scale,dx,dy in [(0,1,0,0),(0,.90,20,40),(3,.95,10,20),(-3,.95,-10,10)]:
            with self.subTest(angle=angle,scale=scale):
                m=cv2.getRotationMatrix2D((650,900),angle,scale)
                m[:,2]+=[dx,dy]
                transformed=cv2.warpAffine(im,m,(1300,1800),borderValue=(255,255,255))
                self.assertEqual(geometry(transformed,self.config)[4],[])

    def test_blank_page_rejected(self):
        with self.assertRaisesRegex(ValueError,'auto_alignment_unresolved'):
            locate_body(np.full((1800,1300,3),255,np.uint8),self.config)

    def test_wrong_column_layout_rejected(self):
        im=self.sample()
        im[270:1160,365:385]=255
        with self.assertRaises(ValueError):
            locate_body(im,self.config)

    def test_rotation_coordinates_exact(self):
        im=np.arange(7*9).reshape(7,9)
        for angle in (0,90,180,270):
            rotated,m=rotate_page(im,angle)
            for y,x in [(0,0),(3,4),(6,8)]:
                xx,yy,_=m@np.array([x,y,1])
                self.assertEqual(rotated[int(yy),int(xx)],im[y,x])

    def test_perspective(self):
        im=self.sample()
        m=cv2.getPerspectiveTransform(np.float32([[0,0],[1299,0],[1299,1799],[0,1799]]),
                                      np.float32([[20,20],[1260,40],[1280,1760],[45,1740]]))
        warped=cv2.warpPerspective(im,m,(1300,1800),borderValue=(255,255,255))
        self.assertEqual(geometry(warped,self.config)[4],[])


if __name__=='__main__':
    unittest.main()
