"""Header/row scoped extraction for entry quantity lists without certificate IDs.

Consumes saved full-page OCR; never guesses a missing model, unit or identifier.
"""
import re
from decimal import Decimal
from statistics import median
from material_ocr.ocr.layout import box

GRADE = r'(?:HRBF|HRB|HPB|RRB|CRB)\d{3,4}[EB]?'


def parse_specification(text):
    text = re.sub(r'\s+', '', str(text or '')).upper()
    grade = re.search(GRADE, text)
    diameter = re.search(r'[ΦФØ⌀∅](\d{1,2}(?:\.\d+)?)', text)
    if not diameter:
        diameter = re.search(r'(?<!\d)(\d{1,2}(?:\.\d+)?)MM', text)
    return (grade.group() if grade else None, diameter.group(1) if diameter else None)


def extract_quantity_lists(index, excluded_pages=()):
    aliases = dict(row_no=('序号',), material_name=('材料名称',), specification=('规格/型号','规格型号','规格'),
                   weight=('进场数量','进场数量(t)','进场数量（t）','进场数量(t）','进场数量（t)'),
                   manufacturer=('生产厂家','生产单位'), entry_date=('进场日期',), usage_location=('使用部位',))
    output = []
    for page in index['pages']:
        if page['page_no'] in excluded_pages:
            continue
        # Primary full-page observations only: focused crops cannot create rows.
        regions = [r for r in page.get('regions', []) if r['region_id'].startswith(f"p{page['page_no']:03d}_full")
                   and not r.get('row_id') and not r.get('priority_field') and not r.get('physical_plate_id')]
        blocks = list({(b['text'],str(b.get('polygon_page'))):b for r in regions for b in r.get('blocks', []) if box(b)}.values())
        text = ''.join(b['text'] for b in blocks)
        if '进场数量清单' not in re.sub(r'\s+', '', text):
            continue
        headers = {}
        for key, names in aliases.items():
            hits = [b for b in blocks if re.sub(r'\s+', '', b['text']).lower() in names]
            if len(hits) == 1:
                headers[key] = hits[0]
        if not {'row_no','specification','weight'} <= headers.keys():
            continue
        def cx(b):
            a=box(b);return (a[0]+a[2])/2
        def cy(b):
            a=box(b);return (a[1]+a[3])/2
        ordered = sorted(headers, key=lambda k:cx(headers[k]))
        centers=[cx(headers[k]) for k in ordered]
        boundaries=[float('-inf')]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[float('inf')]
        serial_idx=ordered.index('row_no');head_bottom=max(box(b)[3] for b in headers.values())
        rows=sorted([b for b in blocks if re.fullmatch(r'[1-9]\d{0,3}',b['text'].strip()) and box(b)[1]>head_bottom
                     and boundaries[serial_idx]<=cx(b)<boundaries[serial_idx+1]],key=cy)
        spacing=median([cy(b)-cy(a) for a,b in zip(rows,rows[1:])]) if len(rows)>1 else max(1,box(headers['row_no'])[3]-box(headers['row_no'])[1])*2
        for anchor in rows:
            raw,ev={},{}
            for i,key in enumerate(ordered):
                hits=sorted([b for b in blocks if abs(cy(b)-cy(anchor))<spacing*.43 and boundaries[i]<=cx(b)<boundaries[i+1]],key=cx)
                raw[key]=' '.join(b['text'] for b in hits)
                points=[p for b in hits for p in (b.get('polygon_page') or [])]
                polygon=None
                if points:
                    xs,ys=zip(*points);polygon=[[min(xs),min(ys)],[max(xs),min(ys)],[max(xs),max(ys)],[min(xs),max(ys)]]
                ev[key]=dict(page_no=page['page_no'],polygon_page=polygon,raw_text=raw[key],source_pixel_size=page.get('pixel_size'),
                             render_dpi=page.get('dpi',180),blocks=hits,method='quantity_list_same_physical_row')
            grade,diameter=parse_specification(raw.get('specification'))
            quantity=re.sub(r'\s+', '',raw.get('weight',''))
            valid=re.fullmatch(r'\d+(?:\.\d+)?',quantity)
            weight=str(Decimal(quantity)) if valid and Decimal(quantity)>0 else None
            issues=[]
            if not grade or not diameter: issues.append('specification_or_grade_unreadable')
            if not weight: issues.append('entry_quantity_unreadable')
            for key,item in ev.items():
                if any(b.get('score') is None or b['score']<.90 for b in item['blocks']): issues.append('low_or_missing_ocr:'+key)
            if weight:raw['weight']=weight+'t' # Header explicitly supplies tonnes.
            output.append(dict(record_id=f"p{page['page_no']:03d}_list_r{anchor['text'].strip()}",page_no=page['page_no'],
                row_no=int(anchor['text']),pdf_sha256=index['pdf_sha256'],grade=grade,diameter_mm=diameter,weight_t=weight,
                material_name=raw.get('material_name'),manufacturer=raw.get('manufacturer'),certificate_no=None,
                entry_date=raw.get('entry_date'),usage_location=raw.get('usage_location'),raw_cells=raw,effective_cells=dict(raw),
                field_evidence=ev,issues=issues,extraction_backend='quantity_list_spatial_v1',ready_for_search=False))
    return output
