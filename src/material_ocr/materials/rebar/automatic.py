"""Automatic evidence-only association. Human review happens on final ledger fields.

A failed/ambiguous link is a structured diagnostic, never an instruction to stop
and manually bundle. No identifier is guessed; all independent plates survive.
"""
from collections import defaultdict
from copy import deepcopy
from .matching import norm, same_number, delivery_rows, heat_valid
from .filling import field, plate_fields, delivery_fields, certificate_fields
from .ledger_sources import inspection_fields, resolve_quantity, resolve_specification

LABELS = dict(material_name='材料名称',specification='规格品种',manufacturer='生产单位',supplier='供应单位',
              supply_date='供货日期',usage_location='使用部位',heat_lot_no='炉批号',quantity_t='验收数量',
              certificate_no='质保书编号',file_no='文件编号')


def evs(info):
    return [deepcopy(ev) for c in info.get('candidates',[])+info.get('alternatives',[]) for ev in c.get('evidence',[])]


def diagnostic(code, field_name, reason, locations=(), **extra):
    return dict(code=code,field=field_name,reason=reason,locations=deepcopy(list(locations)),**extra)


def build_automatic_ledger(result,index,catalog,records):
    pages={p['page_no']:p for p in index['pages']}
    profile=result['filling_profile']; peers=result.get('nameplate_inventory',[])
    # Re-evaluate specification inside the physical card, never from pooled page fields.
    plate_info={c['candidate_id']:plate_fields(pages[c['page_no']],c,peers=[p for p in peers if p['page_no']==c['page_no']]) for c in peers}
    certificates=result.get('certificate_page_inventory',[])
    cert_info={c['candidate_id']:certificate_fields(c,pages[c['page_no']]) for c in certificates}
    deliveries=result.get('delivery_inventory',[])
    delivery_info={c['candidate_id']:delivery_fields(pages[c['page_no']],c) for c in deliveries}
    all_rows=[r for p in pages for r in delivery_rows(catalog,p)]
    pending=[]
    for record in records['records']:
        grade=norm(record.get('grade')); diameter=record.get('diameter_mm'); number=norm(record.get('certificate_no'))
        route='certificate_number' if number else 'specification_grade'
        direct=[c for c in certificates if number and number in {norm(v) for v in c['certificate_numbers']}]
        options=[]
        for c in peers:
            info=plate_info[c['candidate_id']]
            heats={norm(v) for v in c['heat_lots'] if heat_valid(v)}
            # Reject unresolved card boundaries and multi-valued grade/size.
            reliable=not info['specification']['warnings'] and bool(info['grade']['value']) and bool(info['diameter_mm']['value'])
            if route=='certificate_number':
                linked=[q for q in direct if heats & {norm(v) for v in q['heat_lots']}]
                if not linked:continue
                if diameter and info['diameter_mm']['value'] and not same_number(diameter,info['diameter_mm']['value']):continue
                if grade and info['grade']['value'] and grade!=norm(info['grade']['value']):continue
            else:
                if not grade or not diameter or not reliable:continue
                if grade!=norm(info['grade']['value']) or not same_number(diameter,info['diameter_mm']['value']):continue
                linked=[q for q in certificates if heats & {norm(v) for v in q['heat_lots']}]
            if len(heats)!=1: linked=[]
            for q in linked or [None]:
                options.append(dict(plate=c,certificate=q))
        # Quantity may disambiguate only within row/card evidence, never arbitrary nearest page.
        for o in options:
            c=o['plate']; pi=plate_info[c['candidate_id']]
            rows=[]
            for row in all_rows:
                spec_ok=bool(pi['diameter_mm']['value'] and row['diameters_mm']) and all(same_number(pi['diameter_mm']['value'],v) for v in row['diameters_mm'])
                grade_ok=bool(pi['grade']['value'] and row['grades']) and all(norm(v)==norm(pi['grade']['value']) for v in row['grades'])
                # Same-page alone cannot associate several cards to one delivery row.
                if not spec_ok or (row['grades'] and not grade_ok):continue
                rows.append(row)
            exact=[r for r in rows if record.get('weight_t') and len(set(r['quantities_t']))==1 and same_number(record['weight_t'],r['quantities_t'][0])]
            if exact:rows=exact
            o['delivery_rows']=rows
        selected=options[0] if len(options)==1 else None
        pending.append(dict(record=record,route=route,options=options,selected=selected,direct=direct))
    # Resource collisions are diagnosed across the whole batch before finalizing.
    owners=defaultdict(list)
    for p in pending:
        if p['selected']:owners[p['selected']['plate']['candidate_id']].append(p)
    rows=[]
    for p in pending:
        r=p['record']; loc=[deepcopy(r.get('field_evidence',{}).get('specification') or dict(page_no=r.get('page_no'),polygon_page=None,source_role='inspection',record_id=r['record_id']))]
        issues=[diagnostic(x,'匹配关键词','OCR字段或表格未检验成功：'+x,loc) for x in r.get('issues',[])]
        info={};selected=p['selected']; sources={}; alternatives=[]
        contexts=profile.get('approval_contexts',[])
        # Prefer the immediately preceding cover, never pool values across covers.
        preceding=[c for c in contexts if c['page_no']<=r.get('page_no',0)]
        context=max(preceding,key=lambda c:c['page_no']) if preceding else (contexts[0] if len(contexts)==1 else None)
        if context:info.update(deepcopy(context['fields']))
        def record_field(key,raw_key=None):
            value=r.get(key)
            ev=deepcopy(r.get('field_evidence',{}).get(raw_key or key) or loc[0]);ev.setdefault('page_no',r.get('page_no'))
            return field([dict(value=str(value),evidence=[ev])] if value else [])
        if not info.get('material_name',{}).get('value'):info['material_name']=record_field('material_name')
        if not info.get('usage_location',{}).get('value'):info['usage_location']=record_field('usage_location')
        quantity=inspection_fields(r,r['record_id'])['quantity_t']
        info['quantity_t']=quantity
        if selected:
            plate=selected['plate']; pi=deepcopy(plate_info[plate['candidate_id']]);info.update(pi)
            sources['nameplate']=plate
            if selected['certificate']:
                q=selected['certificate'];info.update(deepcopy(cert_info[q['candidate_id']]));sources['certificate']=q
            else:issues.append(diagnostic('certificate_not_found','质保书编号','铭牌炉批号未检索到唯一质量证明书',evs(pi['heat_lot_no'])))
            dr=selected['delivery_rows']
            if len(dr)==1:
                row=dr[0]
                inventory=[c for c in deliveries if (c['page_no'],c.get('entity_key'),c.get('row_id'))==(row['page_no'],row['entity_key'],row['row_id'])]
                if len(inventory)==1:
                    d=inventory[0];di=deepcopy(delivery_info[d['candidate_id']]);sources['delivery']=d
                    info['specification']=resolve_specification(pi,di)
                    info['quantity_t']=resolve_quantity([quantity],di.get('quantity_t',field()))
                    for key in ('supplier','delivery_no'):info[key]=di.get(key,field())
            else:
                issues.append(diagnostic('delivery_not_unique' if dr else 'delivery_not_found','送货单','规格对应多个送货物理行' if dr else '未找到规格对应的送货物理行',loc))
            others=owners[plate['candidate_id']]
            if len(others)>1:
                # Identical records are preserved and explicitly marked; never sum them.
                issues.append(diagnostic('duplicate_resource','铭牌','同一铭牌被多条检验记录命中，可能重复或信息冲突',evs(pi['heat_lot_no']),record_ids=[x['record']['record_id'] for x in others]))
        else:
            code='multiple_match_candidates' if p['options'] else 'match_not_found'
            reason='存在多个独立铭牌/质证书组合，未自动选择' if p['options'] else ('质证编号未命中或炉批号链缺失' if p['route']=='certificate_number' else '未找到同一铭牌内同时匹配规格与牌号的可靠证据')
            issues.append(diagnostic(code,'规格/牌号/质证编号',reason,loc))
            for o in p['options']:
                c=o['plate'];alternatives.append(dict(nameplate=c,certificate=o['certificate'],delivery_rows=o['delivery_rows'],
                    locations=evs(plate_info[c['candidate_id']]['specification'])+evs(plate_info[c['candidate_id']]['heat_lot_no'])))
        if not p['options'] and p['route']=='specification_grade':
            for c in peers:
                pi=plate_info[c['candidate_id']]
                if norm(pi['grade']['value']) != norm(r.get('grade')):continue
                locations=evs(pi['specification'])+evs(pi['heat_lot_no'])
                reason=f"同牌号铭牌的直径为 {pi['diameter_mm']['value'] or '未识别'}，进场记录直径为 {r.get('diameter_mm') or '未识别'}；未作为匹配结果"
                alternatives.append(dict(kind='near_miss',nameplate=c,reason=reason,locations=locations))
            if alternatives:
                issues.append(diagnostic('specification_mismatch_candidates','规格品种','存在同牌号但规格未匹配的铭牌，请核对进场表和原图',loc+[ev for a in alternatives for ev in a['locations']]))
        # Incomplete links still yield an editable, traceable row.
        if not info.get('specification',{}).get('value') and not p['options']:
            if r.get('grade') and r.get('diameter_mm'):
                info['specification']=field([dict(value=f"{r['grade']}/Ф{r['diameter_mm']}",evidence=[deepcopy(r.get('field_evidence',{}).get('specification') or loc[0])])])
        fields={}
        for key,label in LABELS.items():
            f=deepcopy(info.get(key,field()));locations=evs(f)
            if not locations:locations=deepcopy(loc)
            for ev in locations:ev.setdefault('page_no',r.get('page_no'))
            own=[]
            if not f['value'] and key!='file_no':own.append(diagnostic('missing_keyword',label,'关键词未识别到或存在多个值，需核对原图',locations))
            if len(f.get('candidates',[]))>1:own.append(diagnostic('conflicting_values',label,'信息矛盾或存在多个OCR值',locations))
            for warning in f.get('warnings',[]):
                # Certificate OCR warning is generic; report its actual status instead.
                if key=='certificate_no' and warning.startswith('保留质证书编号原 OCR'):continue
                own.append(diagnostic('unverified_keyword',label,warning,locations))
            low=[ev for ev in locations if ev.get('score') is not None and ev['score']<.90]
            if low:own.append(diagnostic('unclear_ocr',label,'OCR置信度不足，识别不清晰',low))
            polygon=next((ev for ev in locations if ev.get('polygon_page')),locations[0])
            fields[label]=dict(value=f['value'],page=polygon.get('page_no'),polygon=polygon.get('polygon_page'),
                source_pixel_size=polygon.get('source_pixel_size') or pages.get(polygon.get('page_no'),{}).get('pixel_size'),
                render_dpi=polygon.get('render_dpi') or pages.get(polygon.get('page_no'),{}).get('dpi'),
                evidence=locations,alternatives=f.get('alternatives',[]) or f.get('candidates',[]),diagnostics=own,status='needs_review' if own else 'observed',
                found_in_ocr=bool(f['value']) and not own)
            issues.extend(own)
        rows.append(dict(record_id=r['record_id'],fields=fields,match_route=p['route'],
            match_status='matched' if selected and len(sources)==3 and not any(i['code']=='duplicate_resource' for i in issues) else 'incomplete_or_ambiguous',
            diagnostics=issues,match_candidates=alternatives,sources=sources,reviewed=False))
    # Every diagnostic/candidate retains its own source pixel axes, including approval crops.
    def annotate(value):
        if isinstance(value,dict):
            if value.get('page_no') in pages:
                page=pages[value['page_no']]
                size=value.get('source_pixel_size') or value.get('page_pixel_size')
                if not size and page.get('pixel_size'):
                    ratio=(value.get('render_dpi') or page.get('dpi') or 180)/(page.get('dpi') or 180)
                    size=[n*ratio for n in page['pixel_size']]
                if size:value['source_pixel_size']=size
            for child in list(value.values()):annotate(child)
        elif isinstance(value,list):
            for child in value:annotate(child)
    annotate(rows)
    result['automatic_ledger']=dict(schema_version='automatic-ledger-v1',pdf_sha256=index['pdf_sha256'],
        pdf_name=index.get('pdf_name'),page_count=len(index['pages']),records=rows,
        diagnostics=deepcopy(records.get('extraction_issues',[])),review_stage='before_excel_export',
        matching_requires_human=False)
    result['metrics']['automatic_ledger_rows']=len(rows)
    result['metrics']['automatic_complete_rows']=sum(r['match_status']=='matched' for r in rows)
    return result['automatic_ledger']
