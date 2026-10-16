"""OCR service contract consumed by the current Vue/Spring application.

The Java service owns editing/review/export. This service owns immutable PDF,
local OCR, automatic matching and source coordinates.
"""
import base64
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import threading
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from material_ocr.workflow import run_pipeline, write_json, configure_environment
from material_ocr.materials.base import RuntimeOptions, ExtractedDocuments

GPU_LOCK = threading.Lock()
COLUMNS=['供应商是否报审','文件编号','材料名称','规格品种','生产单位','供应单位',
         '供货日期与工程材料报审签认日期','使用部位','送货单编号','炉批号','验收数量','质保书编号']


def render_pdf(content,dpi=180,fmt='png'):
    import pypdfium2 as pdfium
    fmt=fmt.lower()
    if not 72<=dpi<=400 or fmt not in ('png','jpg','jpeg'):raise HTTPException(422,'DPI须在72至400，图片格式须为png或jpg')
    result=[]
    pdf = pdfium.PdfDocument(content)
    try:
        for i in range(len(pdf)):
            page=pdf[i]
            try:
                bitmap=page.render(scale=dpi/72)
                try:
                    im=bitmap.to_pil();buffer=io.BytesIO();im.save(buffer,format='PNG' if fmt=='png' else 'JPEG')
                    result.append(dict(page=i+1,width=im.width,height=im.height,format=fmt,image_base64=base64.b64encode(buffer.getvalue()).decode()))
                    im.close()
                finally:bitmap.close()
            finally:page.close()
    finally:pdf.close()
    return dict(page_count=len(result),format=fmt,pages=result)


def normalize_ledger(ledger,name):
    value=deepcopy(ledger);value['pdf_name']=name;checks=[]
    for ri,record in enumerate(value['records']):
        fields=record['fields']
        if '供货日期' in fields:fields['供货日期与工程材料报审签认日期']=fields.pop('供货日期')
        for col in COLUMNS:
            if col not in fields:
                fields[col]=dict(value='',page=None,polygon=None,evidence=[],found_in_ocr=False,status='missing',
                    diagnostics=[dict(code='missing_keyword',field=col,reason='该字段未可靠提取',locations=[])])
            item=fields[col]
            checks.append(dict(path=f'records[{ri}].{col}',**deepcopy(item)))
    value['consistency']=dict(field_count=len(checks),field_checks=checks,
        hallucination_count=sum(not c['found_in_ocr'] for c in checks),summary=f"自动生成{len(value['records'])}条记录；请在导出Excel前集中核验")
    value['summary']=value['consistency']['summary']
    return value


def create_library_router(root,model_cache,device,profile):
    router=APIRouter();root=Path(root)/'library';root.mkdir(parents=True,exist_ok=True)
    locks={};locks_guard=threading.Lock()
    def folder(name):
        if not name or len(name)>180 or name in ('.','..') or re.search(r'[/\\\x00-\x1f]',name):raise HTTPException(422,'无效PDF标识')
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()):raise HTTPException(422,'无效PDF标识')
        return p
    def existing(name):
        p=folder(name)
        if not (p/'source.pdf').is_file():raise HTTPException(404,'PDF不存在')
        return p
    @contextmanager
    def exclusive(name):
        with locks_guard: lock=locks.setdefault(name,threading.Lock())
        if not lock.acquire(blocking=False):raise HTTPException(409,'该PDF正在处理，请等待完成')
        try:yield
        finally:lock.release()
    def save_pages(p,content,dpi,fmt):
        data=render_pdf(content,dpi,fmt);(p/'pages').mkdir(exist_ok=True)
        for page in data['pages']:
            # Stable PNG endpoints regardless of requested source encoding.
            im=Image.open(io.BytesIO(base64.b64decode(page.pop('image_base64'))));im.save(p/'pages'/f"{page['page']}.png");im.close()
        write_json(p/'manifest.json',dict(page_count=data['page_count'],dpi=dpi,pages=data['pages'],rotations={}))
        return data
    async def pdf_bytes(file):
        content=await file.read(256*1024*1024+1)
        if len(content)>256*1024*1024:raise HTTPException(413,'PDF过大')
        if b'%PDF-' not in content[:1024]:raise HTTPException(422,'不是PDF文件')
        return content
    @router.post('/api/pdf/to_images')
    async def to_images(file:UploadFile=File(...),dpi:int=Form(180),image_format:str=Form('png')):
        content=await pdf_bytes(file)
        return render_pdf(content,dpi,image_format)
    @router.post('/api/library/upload')
    async def upload(file:UploadFile=File(...),name:str=Form(''),dpi:int=Form(180),image_format:str=Form('png'),overwrite:bool=Form(False)):
        name=name or Path(file.filename or 'upload.pdf').stem;p=folder(name);content=await pdf_bytes(file)
        with exclusive(name):
            if (p/'source.pdf').exists() and not overwrite:raise HTTPException(409,'同名PDF已存在')
            # Build before replacing existing data, so bad uploads cannot destroy it.
            staging=root/('staging-'+uuid.uuid4().hex);staging.mkdir()
            try:
                data=save_pages(staging,content,dpi,image_format);(staging/'source.pdf').write_bytes(content)
                write_json(staging/'original.json',dict(original_name=file.filename))
                if p.exists():
                    archive=root/('archive-'+uuid.uuid4().hex);p.rename(archive)
                staging.rename(p)
            finally:
                if staging.exists():shutil.rmtree(staging)
        return dict(name=name,pdf_name=name,page_count=data['page_count'])
    @router.get('/api/library')
    def listing():
        return dict(pdfs=[dict(name=p.name,page_count=json.loads((p/'manifest.json').read_text())['page_count'])
                         for p in sorted(root.iterdir()) if (p/'source.pdf').exists() and not p.name.startswith(('archive-','staging-'))])
    @router.get('/api/library/{name}/pages/{page}/image')
    def image(name:str,page:int):
        p=existing(name)/'pages'/f'{page}.png'
        if not p.is_file():raise HTTPException(404,'页面不存在')
        return FileResponse(p)
    @router.get('/api/library/{name}/ledger')
    def ledger(name:str):
        p=existing(name)/'ledger.json'
        if not p.is_file():raise HTTPException(404,'台账尚未生成')
        return json.loads(p.read_text())
    @router.post('/api/library/{name}/recognize')
    def recognize(name:str,prompt:str=Form(''),ocr_prompt:str=Form(''),model:str=Form(''),force_ocr_refresh:bool=Form(False)):
        p=existing(name)
        with exclusive(name),GPU_LOCK:
            if (p/'ledger.json').is_file() and not force_ocr_refresh:return ledger(name)
            configure_environment(model_cache)
            out=p/('run-'+uuid.uuid4().hex)
            replay=None
            if not force_ocr_refresh and (p/'latest.json').is_file():
                previous=p/json.loads((p/'latest.json').read_text())['run']
                replay=ExtractedDocuments(previous/'work/inspection/records_all_pages.json',previous/'work/attachments/attachment_index.json')
            result=run_pipeline(p/'source.pdf',out,options=RuntimeOptions(device=device,ocr_profile=profile,inspection_layout='adaptive'),replay_documents=replay)
            data=normalize_ledger(result['automatic_ledger'],name)
            data.update(run_directory=out.name,source_pdf_sha256=hashlib.sha256((p/'source.pdf').read_bytes()).hexdigest())
            data['revision']=hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            write_json(p/'ledger.json',data)
            if replay is None:write_json(p/'latest.json',dict(run=out.name))
            return data
    @router.get('/api/library/{name}/pages/{page}/ocr')
    def page_ocr(name:str,page:int):
        p=existing(name);meta=json.loads((p/'manifest.json').read_text())
        if not 1<=page<=meta['page_count']:raise HTTPException(404,'页面不存在')
        if not (p/'latest.json').is_file():raise HTTPException(404,'OCR尚未生成')
        run=json.loads((p/'latest.json').read_text())['run']
        index=json.loads((p/run/'work/attachments/attachment_index.json').read_text())
        source=next(x for x in index['pages'] if x['page_no']==page)
        with Image.open(p/'pages'/f'{page}.png') as im:w,h=im.size
        sw,sh=source.get('pixel_size') or [w,h]
        # Rendered original pixel axes; account for requested display DPI/rotation.
        rotation=int(meta.get('rotations',{}).get(str(page),0))%360
        ow,oh=(h,w) if rotation in (90,270) else (w,h)
        def mapped(poly,size=None,dpi=None):
            if not poly:return None
            bw,bh=size or (sw,sh)
            output=[]
            for x,y in poly:
                x,y=x*ow/bw,y*oh/bh
                if rotation==90:x,y=oh-y,x
                elif rotation==180:x,y=ow-x,oh-y
                elif rotation==270:x,y=y,ow-x
                output.extend([x,y])
            return output
        items=[];seen=set()
        for region in source.get('regions',[]):
            for b in region.get('blocks',[]):
                key=(b['text'],str(b.get('polygon_page')))
                if key in seen:continue
                seen.add(key);items.append(dict(text=b['text'],confidence=b.get('score'),location=mapped(b.get('polygon_page'))))
        data=ledger(name)
        for ri,rec in enumerate(data['records']):
            for label,f in rec['fields'].items():
                for ev in f.get('evidence',[]):
                    if ev.get('page_no')!=page or not ev.get('polygon_page'):continue
                    size=ev.get('source_pixel_size')
                    if not size and ev.get('render_dpi') and source.get('dpi'):
                        ratio=ev['render_dpi']/source['dpi'];size=[sw*ratio,sh*ratio]
                    items.append(dict(text=f['value'],location=mapped(ev['polygon_page'],size),
                        path=f'records[{ri}].{label}',field=label,diagnostics=f.get('diagnostics',[]),kind='ledger'))
        return dict(schema_version="automatic-ledger-v1",page=page,image_width=w,image_height=h,original_width=sw,original_height=sh,rotation_cw=rotation,items=items,text='\n'.join(b['text'] for b in items if b.get('kind')!='ledger'),ocr_status=source.get('ocr_status','completed'))
    @router.post('/api/library/{name}/pages/{page}/ocr')
    def run_page(name:str,page:int,prompt:str=Form('')):
        # Association requires cross-page context, so a first request recognizes the volume.
        if not (existing(name)/'latest.json').exists():recognize(name,prompt,'','',False)
        return page_ocr(name,page)
    @router.post('/api/library/{name}/cache')
    def clear_cache(name:str,scope:str=Form('ledger')):
        if scope not in ('all','ledger'):raise HTTPException(422,'未知缓存范围')
        p=existing(name)
        with exclusive(name):
            (p/'ledger.json').unlink(missing_ok=True)
            if scope=='all':(p/'latest.json').unlink(missing_ok=True)
        return dict(scope=scope,cleared=True)
    @router.post('/api/library/{name}/resplit')
    def resplit(name:str,dpi:int=Form(180),image_format:str=Form('png')):
        p=existing(name)
        with exclusive(name):
            result=save_pages(p,(p/'source.pdf').read_bytes(),dpi,image_format)
            for filename in ('ledger.json','latest.json'):(p/filename).unlink(missing_ok=True)
        return dict(page_count=result['page_count'])
    @router.post('/api/library/{name}/pages/{page}/rotate')
    def rotate(name:str,page:int,angle:int=Form(...)):
        if angle not in (90,180,270,-90):raise HTTPException(422,'旋转角度须为90度的倍数')
        p=existing(name)
        with exclusive(name):
            path=p/'pages'/f'{page}.png'
            if not path.exists():raise HTTPException(404,'页面不存在')
            with Image.open(path) as im:im.rotate(angle,expand=True).save(path)
            meta=json.loads((p/'manifest.json').read_text());meta['rotations'][str(page)]=(meta['rotations'].get(str(page),0)-angle)%360
            write_json(p/'manifest.json',meta)
        return dict(page=page,angle=angle)
    return router
