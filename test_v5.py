import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from batch import duplicate_candidates
from row_retry import choose,needs_retry,retry_row
from validation import validation_states
from lab import extract,save_image,write_json,read_json,digest


def block(text='1',score=.99):
    return {'text':text,'score':score,'poly_crop':[[10,10],[20,10],[20,30],[10,30]]}


def attempt(text,score=.99):
    return {'text':text,'blocks':[block(text,score)] if text else []}


class V5Tests(unittest.TestCase):
    def test_consensus(self):
        self.assertEqual(choose('一',[attempt('1'),attempt('1')],.95)[0],'1')

    def test_no_replacement(self):
        self.assertIsNone(choose('一',[attempt('一'),attempt('一')],.95)[0])

    def test_disagreement(self):
        self.assertIsNone(choose('',[attempt('4'),attempt('9')],.95)[0])

    def test_original_conflict(self):
        self.assertIsNone(choose('7',[attempt('4'),attempt('4')],.95)[0])

    def test_low_confidence(self):
        self.assertIsNone(choose('',[attempt('4',.8),attempt('4')],.95)[0])

    def test_single_success_insufficient(self):
        self.assertIsNone(choose('',[attempt('4'),attempt('')],.95)[0])

    def test_retry_triggers(self):
        self.assertFalse(needs_retry('1',[block()],.95))
        self.assertTrue(needs_retry('1',[block(score=.8)],.95))
        self.assertTrue(needs_retry('1',[block()],.95,2))
        self.assertTrue(needs_retry('',[],.95))

    def test_retry_exception_retained(self):
        def bad(*args):
            raise RuntimeError('mock OCR failure')
        with tempfile.TemporaryDirectory() as d:
            result=retry_row(None,np.full((40,40,3),255,np.uint8),'',Path(d)/'retries','cell',.95,bad)
        self.assertIsNone(result['selected_text'])
        self.assertEqual(len(result['attempts']),2)
        self.assertIn('error',result['attempts'][0])

    def sample_record(self):
        return {'record_id':'a','row_no':None,'diameter_mm':'6','weight_t':'39.590',
                'manufacturer':'测试公司','certificate_no':'0012345678',
                'issues':['row_number_missing_or_invalid','low_or_missing_ocr:row_no']}

    def test_separate_validation(self):
        state=validation_states(self.sample_record())
        self.assertEqual(state['row_number_status'],'needs_review')
        self.assertEqual(state['search_fields_status'],'rule_pass_review_required')
        self.assertFalse(state['ready_for_search'])

    def test_core_low_confidence_blocked(self):
        r=self.sample_record()
        r['issues'].append('low_or_missing_ocr:weight')
        self.assertEqual(validation_states(r)['search_fields_status'],'needs_review')

    def test_duplicate_without_sequence(self):
        a=self.sample_record()
        b=dict(a,record_id='b',row_no=1,weight_t='39.59',diameter_mm='6.0')
        result=duplicate_candidates([a,b])
        self.assertEqual(result[0]['record_ids'],['a','b'])
        self.assertFalse(result[0]['row_number_used'])
        self.assertIsNone(a['row_no'])

    def test_distinct_documents_and_certificate(self):
        a=self.sample_record()
        self.assertEqual(duplicate_candidates([dict(a,pdf_sha256='a'),dict(a,pdf_sha256='b')]),[])
        self.assertEqual(duplicate_candidates([a,dict(a,certificate_no='12345678')]),[])

    def test_invalid_keys_skipped(self):
        a=self.sample_record()
        for key,value in [('certificate_no',None),('weight_t','NaN'),('weight_t','bad')]:
            self.assertEqual(duplicate_candidates([a,dict(a,**{key:value})]),[])

    def test_extract_keeps_raw_skips_blank_retries(self):
        fields=['row_no','material_name','specification','weight','manufacturer_certificate',
                'inspection_item','inspection_result','remarks']
        texts=['一','热轧带肋钢筋','6mm','39.590t','测试公司0012345678','原材料','合格','']
        calls=[]
        def fake(engine,crop,path):
            calls.append(path.name)
            save_image(path,crop)
            if path.parent.name=='retries':
                return '1',[block()]
            if '_r02_' in path.name:
                return '',[]
            field=path.stem.split('_',2)[2]
            text=texts[fields.index(field)]
            return text,[block(text)] if text else []
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            save_image(folder/'page.png',np.full((200,800,3),255,np.uint8))
            config={'column_names':fields,'target_size':[800,200],'crop_inset_px':4,'min_ocr_score':.95,'template_id':'test'}
            write_json(folder/'geometry.json',{'template':config,'geometry_errors':[],
                'image_sha256':digest(folder/'page.png'),'matrix_page_to_table':np.eye(3).tolist(),
                'xs':list(range(0,801,100)),'ys':[0,100,200]})
            write_json(folder/'page_meta.json',{'page_no':2})
            with patch('lab.ocr_cell',fake),contextlib.redirect_stdout(io.StringIO()):
                extract(SimpleNamespace(run=d,result_dir='out',device='cpu',allow_draft=True),engine=object())
            r=read_json(folder/'out/result.json')
            self.assertEqual(r['records'][0]['raw_cells']['row_no'],'一')
            self.assertEqual(r['records'][0]['effective_cells']['row_no'],'1')
            self.assertEqual(r['records'][0]['row_no'],1)
            self.assertFalse(r['records'][0]['ready_for_search'])
            self.assertEqual(r['summary']['blank_candidate_count'],1)
            self.assertEqual(r['summary']['row_retry_count'],1)
            self.assertEqual(len(calls),18)


if __name__=='__main__':
    unittest.main()
