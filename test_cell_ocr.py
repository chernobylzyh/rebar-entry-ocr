import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from cell_ocr import FixedCellOCR,crop_without_quarter_turn
from row_retry import retry_row,number_region


class FakeCropper:
    def get_rotate_crop_image(self,image,points):
        out=crop_without_quarter_turn(image,points)
        return np.rot90(out) if out.shape[0]/out.shape[1]>=1.5 else out


class CellOCRTests(unittest.TestCase):
    def setUp(self):
        self.image=np.full((70,70,3),255,np.uint8)
        cv2.line(self.image,(20,10),(20,48),(0,0,0),2)
        self.points=np.float32([[10,5],[35,5],[35,55],[10,55]])

    def test_tall_character_stays_upright(self):
        crop=crop_without_quarter_turn(self.image,self.points)
        self.assertEqual(crop.shape[:2],(50,25))
        yy,xx=np.where(crop[:,:,0]<100)
        self.assertGreater(np.ptp(yy),np.ptp(xx))

    def test_wide_crop_identical_to_original(self):
        points=np.float32([[5,5],[60,5],[60,30],[5,30]])
        np.testing.assert_array_equal(crop_without_quarter_turn(self.image,points),FakeCropper().get_rotate_crop_image(self.image,points))

    def test_degenerate_rejected(self):
        with self.assertRaises(ValueError):
            crop_without_quarter_turn(self.image,np.zeros((4,2)))

    def test_patch_applies_to_generator_and_restores(self):
        image,points=self.image,self.points
        class Engine:
            def predict(self,input,**kwargs):
                yield FakeCropper().get_rotate_crop_image(image,points)
        original=FakeCropper.get_rotate_crop_image
        with tempfile.TemporaryDirectory() as directory,patch('cell_ocr.checked_cropper_class',return_value=FakeCropper):
            path=Path(directory)/'p2_r01_row_no.png'
            result=FixedCellOCR(Engine()).predict(input=str(path))
            self.assertEqual(result[0].shape[:2],(50,25))
            self.assertTrue(path.with_name('p2_r01_row_no_rec_input_001.png').exists())
            self.assertTrue(path.with_name('p2_r01_row_no_crop_audit.json').exists())
        self.assertIs(FakeCropper.get_rotate_crop_image,original)
        self.assertEqual(FakeCropper().get_rotate_crop_image(image,points).shape[:2],(25,50))

    def test_exception_restores_original(self):
        class Engine:
            def predict(self,input,**kwargs):
                raise RuntimeError('test failure')
        original=FakeCropper.get_rotate_crop_image
        with tempfile.TemporaryDirectory() as directory,patch('cell_ocr.checked_cropper_class',return_value=FakeCropper):
            with self.assertRaises(RuntimeError):
                FixedCellOCR(Engine()).predict(input=str(Path(directory)/'cell.png'))
        self.assertIs(FakeCropper.get_rotate_crop_image,original)

    def test_number_region_ignores_edge_line(self):
        image=self.image.copy()
        image[:,0:2]=0
        region,box=number_region(image)
        self.assertGreater(box[0],2)
        self.assertLess(region.shape[1],image.shape[1])

    def test_number_region_keeps_two_digits(self):
        image=self.image.copy()
        cv2.line(image,(40,10),(40,48),(0,0,0),2)
        _,box=number_region(image)
        self.assertLess(box[0],20)
        self.assertGreater(box[2],40)

    def test_empty_number_region_rejected(self):
        with self.assertRaises(ValueError):
            number_region(np.full((50,50,3),255,np.uint8))

    def test_direct_fallback_consensus(self):
        def no_detection(*args):
            return '',[]
        def direct(*args):
            return '4',[{'text':'4','score':.99}]
        with tempfile.TemporaryDirectory() as d:
            r=retry_row(None,self.image,'',Path(d)/'retries','p5_r04_row_no',.95,no_detection,direct)
        self.assertEqual(r['selected_text'],'4')
        self.assertEqual(r['method'],'direct_recognition_consensus')
        self.assertEqual(len(r['attempts']),4)

    def test_direct_conflict_rejected(self):
        def no_detection(*args):
            return '',[]
        def direct(*args):
            return '4',[{'text':'4','score':.99}]
        with tempfile.TemporaryDirectory() as d:
            r=retry_row(None,self.image,'7',Path(d)/'retries','cell',.95,no_detection,direct)
        self.assertIsNone(r['selected_text'])

    def test_direct_low_score_rejected(self):
        def no_detection(*args):
            return '',[]
        def direct(*args):
            return '4',[{'text':'4','score':.8}]
        with tempfile.TemporaryDirectory() as d:
            r=retry_row(None,self.image,'',Path(d)/'retries','cell',.95,no_detection,direct)
        self.assertIsNone(r['selected_text'])


if __name__=='__main__':
    unittest.main()
