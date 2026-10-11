"""Rebar ledger fields from the selected physical plate, delivery row and certificate.

Saved OCR remains immutable. Specification uses the selected nameplate's grade
and diameter, with its selected delivery row as fallback. Inspection arrival
quantity takes priority over delivery weight; conflicts remain for field review.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import re


COLUMNS = [
    dict(key='material_name', label='材料名称', role='approval', required=True),
    dict(key='specification', label='规格品种', role='nameplate', required=True),
    dict(key='manufacturer', label='生产单位', role='nameplate', required=True),
    dict(key='supplier', label='供应单位', role='delivery', required=True),
    dict(key='supply_date', label='供货日期', role='approval', required=True, type='date'),
    dict(key='usage_location', label='使用部位', role='approval', required=True),
    dict(key='heat_lot_no', label='送货单位编号炉批号', role='nameplate', required=True),
    dict(key='quantity_t', label='验收数量', role='inspection', required=True, type='number', unit='t'),
    dict(key='certificate_no', label='质保书编号', role='certificate', required=True),
    dict(key='file_no', label='文件编号', role='approval', required=False),
]
COMPANY = re.compile(r'[\u4e00-\u9fffA-Za-z（）()·]{3,}(?:有限责任公司|股份有限公司|有限公司)')
# Unicode word boundaries treat Chinese labels and Ф as letters. ASCII-only
# guards allow ``牌号HRB400EФ10`` and delivery cells ``16*12HRB500E`` without
# accepting a damaged prefix or a four-digit OCR grade.
GRADE = re.compile(r'(?<![A-Z])(?:HRBF?(?:335|400|500|600|700)E?|HPB(?:235|300))(?![A-Z0-9])', re.I)
DIAMETER = re.compile(r'(?:[ΦφФØ⌀]\s*(\d{1,2}(?:\.\d+)?)(?![\d.])|(?<!\d)(\d{1,2}(?:\.\d+)?)\s*mm)', re.I)
SIZE_LABEL = re.compile(r'^(?:钢筋规格|公称直径|直径|规格(?:型号)?|SIZE)[:：]?', re.I)
DATE = re.compile(r'(20\d{2})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*日?')


def compact(value):
    return re.sub(r'\s+', '', str(value or ''))


def decimal_text(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            return None
        return format(number, 'f').rstrip('0').rstrip('.') if '.' in format(number, 'f') else format(number, 'f')
    except InvalidOperation:
        return None


def date_text(value):
    match = DATE.fullmatch(compact(value))
    if not match:
        return None
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return None


def bbox(block):
    polygon = block.get('polygon_ocr') or block.get('polygon_page')
    if not polygon:
        return None
    xs, ys = zip(*polygon)
    return min(xs), min(ys), max(xs), max(ys)


def center(block):
    box = bbox(block)
    return ((box[0]+box[2])/2, (box[1]+box[3])/2) if box else None


def page_blocks(page, candidate=None):
    # Use page/entity OCR rather than tiny field crops with different local axes.
    regions = [r for r in page.get('regions', []) if r['region_id'] == f"p{page['page_no']:03d}_full"]
    entity = candidate.get('entity_key') if candidate else None
    if entity and entity != 'full' and entity != 'raw-labelled':
        scoped = [r for r in page.get('regions', []) if r.get('entity_key') == entity
                  and ('_field_' not in r['region_id'])]
        if scoped:
            regions = scoped
    if not regions and candidate and candidate.get('entity_key') not in (None, 'full', 'raw-labelled'):
        # Some older saved inventories encoded the entity only in the region ID.
        token = str(candidate['entity_key'])
        regions = [r for r in page.get('regions', []) if token in r['region_id'] and '_field_' not in r['region_id']]
    if not regions:
        # Classification replay can replace full-page OCR with split entities.
        # Those entities cover the original page once; adding full-form retries
        # would duplicate headings at slightly different coordinates.
        regions = [r for r in page.get('regions', [])
                   if re.fullmatch(r'p\d+_full_entity\d+', r['region_id'])]
    if not regions:
        regions = [r for r in page.get('regions', []) if '_full' in r['region_id'] and not r.get('row_id')]
    if not regions:
        regions = page.get('regions', [])
    unique = {}
    for region in regions:
        for block in region.get('blocks', []):
            key = compact(block.get('text')), str(block.get('polygon_page'))
            unique.setdefault(key, dict(block, region_id=region['region_id']))
    return list(unique.values())


def evidence(page, block, method):
    return dict(page_no=page['page_no'], region_id=block.get('region_id'),
                polygon_page=block.get('polygon_page'), polygon_ocr=block.get('polygon_ocr'),
                source_image=page.get('source_image'), rotation_ccw=page.get('rotation_ccw', 0),
                raw_text=block.get('text'), score=block.get('score'), method=method)


def observation_evidence(candidate, observation):
    return dict(deepcopy(observation.get('value_evidence') or {}),
                page_no=candidate['page_no'], candidate_id=candidate['candidate_id'],
                row_id=candidate.get('row_id'), raw_text=observation.get('ocr_raw_value') or observation.get('raw_value'),
                method='selected_inventory_observation')


def field(candidates=(), warnings=()):
    """Keep every distinct OCR value and all its evidence, never pick a best guess."""
    unique = {}
    for item in candidates:
        if not item or not item.get('value'):
            continue
        value = str(item['value'])
        slot = unique.setdefault(value, dict(value=value, evidence=[]))
        for ev in item.get('evidence', []):
            if ev not in slot['evidence']:
                slot['evidence'].append(deepcopy(ev))
    values = list(unique.values())
    return dict(value=values[0]['value'] if len(values) == 1 else '', candidates=values,
                status='missing' if not values else ('ambiguous' if len(values) > 1 else 'observed'),
                warnings=list(warnings))


def candidate_value(page, block, value, method):
    return dict(value=value, evidence=[evidence(page, block, method)])


def diameter_text(value):
    value = decimal_text(value)
    return value if value and Decimal('5') <= Decimal(value) <= Decimal('50') else None


def specification_field(grades, sizes, warnings=()):
    return field([dict(value=f"{g['value']}/Ф{d['value']}", evidence=g['evidence']+d['evidence'])
                  for g in grades['candidates'] for d in sizes['candidates']], warnings)


def bind_source(fields, candidate, role):
    for value in fields.values():
        value['source_role'] = role
        for item in value.get('candidates', []):
            for ev in item.get('evidence', []):
                ev.update(source_role=role, candidate_id=candidate['candidate_id'], row_id=candidate.get('row_id'))
    return fields


def specification_parts(page, blocks, method, *, specification_column=False):
    """Read explicit diameter/grade text; plain sizes need a size label or cell.

    The first number in ``16*12HRB500E`` is diameter; its second number is
    length. Numbers beside length, weight and piece-count labels are excluded.
    """
    grades, sizes = [], []
    for block in blocks:
        text = compact(block['text'])
        grades.extend(candidate_value(page, block, match.group().upper(), method+'_grade')
                      for match in GRADE.finditer(text))
        diameter_matches = () if re.match(r'^(?:长度|重量|件重|单重|支数|件数|LENGTH|WEIGHT)[:：]?', text, re.I) else DIAMETER.finditer(text)
        for match in diameter_matches:
            value = diameter_text(match.group(1) or match.group(2))
            if value:
                sizes.append(candidate_value(page, block, value, method+'_diameter'))
        label = SIZE_LABEL.match(text)
        suffix = text[label.end():] if label else (text if specification_column else '')
        plain = re.match(r'^[ΦφФØ⌀]?(\d{1,2}(?:\.\d+)?)(?=$|mm|毫米|[*×xX+/]|盘螺|盘圆|螺纹钢|螺纹|圆钢|钢筋|HRBF?|HPB)', suffix, re.I)
        if plain and diameter_text(plain.group(1)):
            sizes.append(candidate_value(page, block, diameter_text(plain.group(1)), method+'_size_cell'))
        # A grade-first specification can also spell ``HRB400E/10``.
        if specification_column or label:
            for match in GRADE.finditer(text):
                number = re.match(r'^[/／:：][ΦφФØ⌀]?(\d{1,2}(?:\.\d+)?)(?=$|mm|毫米|[*×xX])', text[match.end():], re.I)
                if number and diameter_text(number.group(1)):
                    sizes.append(candidate_value(page, block, diameter_text(number.group(1)), method+'_grade_size_cell'))
        # ``规格`` and its plain value may occupy separate OCR boxes. Choose
        # the nearest value on that line, keeping both label and value evidence.
        if label and not suffix and bbox(block):
            right = [b for b in same_line(blocks, block) if b is not block and bbox(b)
                     and bbox(b)[0] >= bbox(block)[2]-8]
            if right:
                neighbour = right[0]
                raw = compact(neighbour['text'])
                number = re.match(r'^[ΦφФØ⌀]?(\d{1,2}(?:\.\d+)?)(?=$|mm|毫米|[*×xX+/])', raw, re.I)
                gap = bbox(neighbour)[0]-bbox(block)[2]
                if number and diameter_text(number.group(1)) and gap < max(160, (bbox(block)[3]-bbox(block)[1])*8):
                    sizes.append(dict(value=diameter_text(number.group(1)), evidence=[
                        evidence(page, block, method+'_size_label'), evidence(page, neighbour, method+'_labelled_size')]))
        # An unlabelled ``18`` followed immediately by ``mm`` remains explicit.
        if not specification_column and re.fullmatch(r'\d{1,2}(?:\.\d+)?', text) and bbox(block):
            right = [b for b in same_line(blocks, block) if b is not block and bbox(b)
                     and bbox(b)[0] >= bbox(block)[2]-8]
            if right and re.match(r'^mm(?:$|[*×xX/])', compact(right[0]['text']), re.I) and bbox(right[0])[0]-bbox(block)[2] < 80:
                value = diameter_text(text)
                if value:
                    sizes.append(dict(value=value, evidence=[evidence(page, block, method+'_split_mm'),
                        evidence(page, right[0], method+'_diameter_unit')]))
    return field(grades), field(sizes)


def same_line(blocks, label):
    box = bbox(label)
    if not box:
        return [label]
    yc, height = (box[1]+box[3])/2, box[3]-box[1]
    return sorted((b for b in blocks if center(b) and abs(center(b)[1]-yc) <= max(15, height*.8)),
                  key=lambda b: bbox(b)[0])


def approval_context(page):
    blocks = page_blocks(page)
    fields = {key: field() for key in ('material_name', 'usage_location', 'supply_date', 'file_no')}
    anchors = [b for b in blocks if '进场' in compact(b.get('text')) and '工程' in compact(b.get('text'))]
    for anchor in anchors:
        line = same_line(blocks, anchor)
        text = ''.join(compact(b['text']) for b in line)
        usage = re.search(r'(?:拟用于工程|用于工程)(.*?)部位的', text)
        material = re.search(r'部位的([^,，。；;]+)', text)
        for key, match in [('usage_location', usage), ('material_name', material)]:
            if match and match.group(1):
                value = match.group(1).strip(':：')
                fields[key] = field([dict(value=value, evidence=[evidence(page, b, 'approval_arrival_clause')
                                                              for b in line if compact(b['text']) in value or value in compact(b['text'])])])
        dates = [candidate_value(page, b, date_text(m.group()), 'approval_arrival_date')
                 for b in line for m in DATE.finditer(compact(b['text'])) if date_text(m.group())]
        fields['supply_date'] = field(dates)
    # Older OCR may retain labelled clause values although the line is split.
    for key in ('material_name', 'usage_location'):
        if fields[key]['candidates']:
            continue
        values = []
        for region in page.get('regions', []):
            for item in region.get('extracted_fields', {}).get(key, []):
                if item.get('validation_status') == 'accepted':
                    values.append(dict(value=item.get('value'), evidence=[dict(item.get('evidence') or {},
                        page_no=page['page_no'], raw_text=item.get('raw_value'), method='approval_labelled_field')]))
        fields[key] = field(values)
    numbers = []
    for block in blocks:
        text = compact(block['text'])
        if not re.match(r'^编号[:：]?$', text) and not re.match(r'^编号[:：].+', text):
            continue
        inline = re.sub(r'^编号[:：]?', '', text)
        values = [block] if inline else [b for b in same_line(blocks, block)
            if bbox(b)[0] >= bbox(block)[2]-5 and bbox(b)[0]-bbox(block)[2] < 12*(bbox(block)[3]-bbox(block)[1])]
        for value_block in values[:1]:
            value = inline or compact(value_block['text'])
            if value:
                numbers.append(candidate_value(page, value_block, value, 'approval_file_number_label'))
    fields['file_no'] = field(numbers, ['文件编号如有手写或 OCR 残缺，请按报审原图补正。'] if numbers else [])
    return dict(context_id=f"approval:{page['page_no']}", page_no=page['page_no'], fields=fields)


def heat_anchor(blocks, heat):
    pattern = re.compile(r'(?<![A-Z0-9])'+re.escape(compact(heat).upper())+r'(?![A-Z0-9])')
    matches = [b for b in blocks if pattern.search(compact(b['text']).upper()) and center(b)]
    return min(matches, key=lambda b: len(compact(b['text']))) if matches else None


def plate_scope(page, candidate, peers):
    blocks = page_blocks(page, candidate)
    heats = candidate.get('heat_lots', [])
    if len(heats) != 1:
        return [], ['铭牌炉批号未唯一定位，请按原图补正字段。']
    anchors = [(p, heat_anchor(blocks, p['heat_lots'][0])) for p in peers if len(p.get('heat_lots', [])) == 1]
    target = heat_anchor(blocks, heats[0])
    unique_entity = candidate.get('entity_key') not in (None, 'full', 'raw-labelled') and all(
        p['candidate_id'] == candidate['candidate_id'] or p.get('entity_key') != candidate['entity_key'] for p in peers)
    if len(peers) <= 1 or unique_entity:
        global_blocks = page_blocks(page)
        # Layout splitting can put a plate's company header in the delivery crop.
        # Recall only a nearby header below the delivery title and above this heat.
        if target and not any(COMPANY.search(compact(b['text'])) for b in blocks):
            ty = center(target)[1]
            titles_before = [center(b)[1] for b in global_blocks if '送货单' in b['text'] and center(b) and center(b)[1] < ty]
            low = max(titles_before) if titles_before else float('-inf')
            headers = [b for b in global_blocks if COMPANY.search(compact(b['text'])) and center(b)
                       and low < center(b)[1] < ty and ty-center(b)[1] < 550]
            if headers:
                blocks = blocks + [min(headers, key=lambda b: ty-center(b)[1])]
        # A mixed sheet contains a plate above its delivery title.
        titles = [bbox(b)[1] for b in global_blocks if '送货单' in b['text'] and bbox(b)]
        if titles and target and center(target)[1] < min(titles):
            title_y = min(titles)
            supplier_headers = [bbox(b)[1] for b in blocks if COMPANY.search(compact(b['text']))
                                and center(b) and 0 < title_y-center(b)[1] < 240]
            boundary = max(supplier_headers) if supplier_headers else title_y
            return [b for b in blocks if center(b) and center(b)[1] < boundary-15], []
        if titles and target and center(target)[1] > max(titles):
            preceding_title = max(y for y in titles if y < center(target)[1])
            headers = [bbox(b)[1] for b in blocks if COMPANY.search(compact(b['text'])) and center(b)
                       and preceding_title < center(b)[1] < center(target)[1]
                       and center(target)[1]-center(b)[1] < 550]
            if headers:
                return [b for b in blocks if center(b) and center(b)[1] >= max(headers)-15], []
        return blocks, []
    if not target or any(a is None for _, a in anchors) or len(anchors) != len(peers):
        return [], ['同页多个铭牌的 OCR 范围未可靠区分，请核验原图后填写。']
    # Each card starts with a company header before its labelled heat.
    companies = [b for b in blocks if COMPANY.search(compact(b['text'])) and center(b)]
    starts = []
    for peer, anchor in anchors:
        ax, ay = center(anchor)
        headers = [b for b in companies if center(b)[1] < ay and abs(center(b)[0]-ax) < max(450, bbox(b)[2]-bbox(b)[0])]
        if not headers:
            return [], ['同页多个铭牌缺少独立边界，请核验原图后填写。']
        header = min(headers, key=lambda b: (ay-center(b)[1])**2+(ax-center(b)[0])**2)
        starts.append((peer['candidate_id'], header))
    if len({str(bbox(b)) for _, b in starts}) != len(starts):
        return [], ['同页铭牌边界重叠，请核验原图后填写。']
    xs, ys = [center(b)[0] for _, b in starts], [center(b)[1] for _, b in starts]
    axis = 1 if max(ys)-min(ys) >= max(xs)-min(xs) else 0
    ordered = sorted(starts, key=lambda pair: center(pair[1])[axis])
    pos = next(i for i, pair in enumerate(ordered) if pair[0] == candidate['candidate_id'])
    if axis == 1:
        low = bbox(ordered[pos][1])[1]-15
        high = bbox(ordered[pos+1][1])[1]-15 if pos+1 < len(ordered) else float('inf')
    else:
        low = (center(ordered[pos-1][1])[0]+center(ordered[pos][1])[0])/2 if pos else float('-inf')
        high = (center(ordered[pos+1][1])[0]+center(ordered[pos][1])[0])/2 if pos+1 < len(ordered) else float('inf')
    return [b for b in blocks if center(b) and low <= center(b)[axis] < high], []


def plate_fields(page, candidate, peers):
    blocks, warnings = plate_scope(page, candidate, peers)
    grade_field, size_field = specification_parts(page, blocks, 'selected_plate')
    grades, sizes = grade_field['candidates'], size_field['candidates']
    manufacturers = []
    labelled_manufacturers = []
    for block in blocks:
        text = compact(block['text'])
        for company in COMPANY.findall(text):
            item = candidate_value(page, block, company, 'selected_plate_company')
            manufacturers.append(item)
            if re.search(r'生产(?:厂|单位|企业)|制造商', text):
                labelled_manufacturers.append(item)
    if labelled_manufacturers:
        manufacturers = labelled_manufacturers
    # Only one physical plate permits inventory fallback. Multi-card page fields
    # can contain another card's diameter or its length in metres.
    if len(peers) == 1:
        for key, dest in [('grade', grades), ('diameter_mm', sizes)]:
            if dest:
                continue
            for obs in candidate.get('field_observations', []):
                if obs.get('field') == key and obs.get('accepted'):
                    value = obs.get('normalized_value')
                    if key == 'diameter_mm':
                        value = diameter_text(value)
                    elif not GRADE.fullmatch(compact(value)):
                        value = None
                    else:
                        value = compact(value).upper()
                    if value:
                        dest.append(dict(value=value, evidence=[observation_evidence(candidate, obs)]))
    grade_field, size_field = field(grades), field(sizes)
    specs = specification_field(grade_field, size_field, warnings)
    if not specs['candidates']:
        specs['warnings'].append('铭牌牌号或直径未完整提取，请核对关联送货单规格或原图。')
    heats = []
    for heat in candidate.get('heat_lots', []):
        anchor = heat_anchor(blocks, heat)
        evs = [evidence(page, anchor, 'selected_plate_heat')] if anchor else [observation_evidence(candidate, o)
            for o in candidate.get('field_observations', []) if o.get('field') == 'heat_lot_no']
        heats.append(dict(value=heat, evidence=evs))
    return bind_source(dict(specification=specs, grade=grade_field, diameter_mm=size_field,
                heat_lot_no=field(heats, warnings), manufacturer=field(manufacturers, warnings)), candidate, 'nameplate')


def delivery_table_rows(page):
    """Read physical specification/weight rows, excluding totals and signatures."""
    blocks = page_blocks(page)
    titles = [b for b in blocks if '送货单' in b['text'] and center(b)]
    if len(titles) != 1:
        return []
    title_y = center(titles[0])[1]
    headers = [b for b in blocks if center(b) and center(b)[1] > title_y
               and re.fullmatch(r'(?:规格(?:型号)?(?:[/／]材质)?|格?[/／]材质)', compact(b['text']))]
    if len(headers) > 1:
        return []
    if headers:
        header = headers[0]
    else:
        # Left-edge clipped scans retain the weight and neighbouring headings.
        weights = [b for b in blocks if center(b) and re.search(r'^重量[（(](?:吨|t)[）)]$', compact(b['text']), re.I)]
        if len(weights) != 1:
            return []
        line = same_line(blocks, weights[0])
        if sum(any(k in b['text'] for k in ['件重','件数','产地','签收']) for b in line) < 2:
            return []
        header = min(line,key=lambda b:center(b)[0])
    columns = same_line(blocks, header)
    weight_headers = [b for b in columns if re.search(r'^重量[（(](?:吨|t)[）)]$', compact(b['text']), re.I)]
    if len(weight_headers) != 1:
        return []
    weight_header = weight_headers[0]
    wx, hy = center(weight_header)
    positions = sorted({center(b)[0] for b in columns if center(b) and re.search(
        r'件重|签收件数|签收数量|重量|规格|件数|产地|备注', b['text'])})
    left = max((x for x in positions if x < wx), default=wx-180)
    right = min((x for x in positions if x > wx), default=wx+180)
    xmin, xmax = (left+wx)/2, (wx+right)/2
    sx = center(header)[0]
    spec_left = max((center(b)[0] for b in columns if center(b) and center(b)[0] < sx), default=sx-220)
    spec_right = min((center(b)[0] for b in columns if center(b) and center(b)[0] > sx), default=sx+220)
    sxmin, sxmax = (spec_left+sx)/2, (sx+spec_right)/2
    footers = [center(b)[1] for b in blocks if center(b) and center(b)[1] > hy and
               re.match(r'合计|送货地址|联系电话|数量[（(]大写|金额',compact(b['text']))]
    bottom = min(footers) if footers else hy+350
    spec_cells = [b for b in blocks if center(b) and hy+12 < center(b)[1] < bottom
                  and sxmin <= center(b)[0] < sxmax]
    specs = []
    for cell in spec_cells:
        grade, diameter = specification_parts(page, [cell], 'delivery_specification_column', specification_column=True)
        if grade['candidates'] or diameter['candidates'] or re.search(
                r'(?:HRBF|HRB|HPB|RB|B)[0-9O]{3}E?', compact(cell['text']), re.I):
            specs.append(cell)
    unique_specs = []
    for spec in sorted(specs, key=lambda b:center(b)[1]):
        if not unique_specs or abs(center(spec)[1]-center(unique_specs[-1])[1]) > max(12,(bbox(spec)[3]-bbox(spec)[1])*.65):
            unique_specs.append(spec)
    # A damaged specification cell must not remove a physical row and shift
    # every later row ID. Positive numbers in the goods-weight column provide
    # an independent row anchor; totals are outside the footer boundary.
    weight_blocks = [b for b in blocks if center(b) and hy+12 < center(b)[1] < bottom
                     and xmin <= center(b)[0] < xmax
                     and re.fullmatch(r'\d{1,6}(?:[.,]\d{1,6})?', compact(b['text']))
                     and Decimal(compact(b['text']).replace(',', '.')) > 0]
    # Clipped scans may omit the "合计" label. A weight-only line cannot
    # establish a goods row: require a specification or an adjacent numeric
    # piece-count/piece-weight cell on that line.
    weight_blocks = [b for b in weight_blocks if any(
        s in same_line(blocks, b) for s in unique_specs) or any(
            center(other) and sx+80 < center(other)[0] < xmin
            and re.fullmatch(r'\d{1,6}(?:[.,]\d{1,6})?', compact(other['text']))
            and Decimal(compact(other['text']).replace(',', '.')) > 0
            for other in same_line(blocks, b))]
    anchors = sorted(unique_specs+weight_blocks, key=lambda b: center(b)[1])
    lines = []
    for anchor in anchors:
        if not lines or abs(center(anchor)[1]-center(lines[-1][0])[1]) > max(
                15, (bbox(anchor)[3]-bbox(anchor)[1])*.65):
            lines.append([anchor])
        else:
            lines[-1].append(anchor)
    rows = []
    for line in lines:
        anchor = line[0]
        cells = [b for b in spec_cells if abs(center(b)[1]-center(anchor)[1]) <= max(
            15, (bbox(anchor)[3]-bbox(anchor)[1])*.65, (bbox(b)[3]-bbox(b)[1])*.65)]
        cells.sort(key=lambda b: bbox(b)[0])
        raw_specification = ''.join(b['text'] for b in cells)
        grade, diameter = specification_parts(page, cells, 'delivery_specification_column', specification_column=True)
        spec_field = specification_field(grade, diameter)
        for value in (grade, diameter, spec_field):
            for item in value['candidates']:
                for ev in item['evidence']:
                    ev.update(label=header['text'], label_polygon_page=header.get('polygon_page'),
                              physical_row_index=len(rows)+1)
        values = [b for b in line if b in weight_blocks]
        candidates = []
        for value_block in values:
            raw = compact(value_block['text'])
            value = decimal_text(raw.replace(',', '.'))
            if value and Decimal(value) > 0:
                ev = evidence(page,value_block,'delivery_goods_weight_column')
                ev.update(label=weight_header['text'],label_polygon_page=weight_header.get('polygon_page'),
                          specification_raw_text=raw_specification or None,
                          specification_polygon_page=cells[0].get('polygon_page') if cells else None,
                          column_unit='t', physical_row_index=len(rows)+1)
                candidates.append(dict(value=value,evidence=[ev]))
        rows.append(dict(physical_row_index=len(rows)+1, specification=raw_specification,
                         specification_field=spec_field, grade=grade, diameter_mm=diameter,
                         quantity=field(candidates)))
    return rows


def delivery_fields(page, candidate):
    blocks = page_blocks(page, candidate)
    all_blocks = page_blocks(page)
    suppliers = []
    titles = [b for b in blocks if '送货单' in compact(b['text']) and center(b)]
    if not titles:
        global_titles = [b for b in all_blocks if '送货单' in compact(b['text']) and center(b)]
        if len(global_titles) == 1:
            titles = global_titles
    for title in titles:
        before = [b for b in all_blocks if COMPANY.search(compact(b['text'])) and center(b)
                  and 0 < center(title)[1]-center(b)[1] < 240]
        if before:
            header = min(before, key=lambda b: center(title)[1]-center(b)[1])
            suppliers.extend(candidate_value(page, header, value, 'delivery_company_heading')
                             for value in COMPANY.findall(compact(header['text'])))
    explicit = [candidate_value(page, b, company, 'delivery_explicit_supplier') for b in blocks
                if re.search(r'供应单位|供货单位|供方', b['text'])
                for company in COMPANY.findall(compact(b['text']))]
    if explicit:
        suppliers = explicit
    quantities = []
    grade, diameter = field(), field()
    table_rows = delivery_table_rows(page)
    row_number = re.search(r'row(\d+)$', candidate.get('row_id') or '')
    selected_rows = [r for r in table_rows if r['physical_row_index'] == int(row_number.group(1))] if row_number else (
        table_rows if len(table_rows) == 1 else [])
    if len(selected_rows) == 1:
        quantities = selected_rows[0]['quantity']['candidates']
        grade, diameter = selected_rows[0]['grade'], selected_rows[0]['diameter_mm']
    observations = candidate.get('field_observations', []) if candidate.get('row_id') else []
    weight_obs = [o for o in observations if o.get('field') in ('quantity_t', 'weight_t') and o.get('accepted')]
    # Prefer the goods weight column over a separate received-quantity column.
    goods_weight = [o for o in weight_obs if '重量' in str((o.get('value_evidence') or {}).get('label', ''))]
    for obs in ([] if quantities else goods_weight or weight_obs):
        value = decimal_text(obs.get('value_t') or obs.get('normalized_value'))
        if value and Decimal(value) > 0:
            quantities.append(dict(value=value, evidence=[observation_evidence(candidate, obs)]))
    # Inventory observations are row-scoped. Never borrow a page-wide grade or
    # diameter when the selected delivery has several physical goods rows.
    for key, target in [('grade', grade), ('diameter_mm', diameter)]:
        if target['candidates']:
            continue
        values = []
        for obs in observations:
            if obs.get('field') != key or not obs.get('accepted'):
                continue
            raw = compact(obs.get('normalized_value'))
            value = diameter_text(raw) if key == 'diameter_mm' else (raw.upper() if GRADE.fullmatch(raw) else None)
            if value:
                values.append(dict(value=value, evidence=[observation_evidence(candidate, obs)]))
        target.update(field(values))
    specs = specification_field(grade, diameter)
    if not candidate.get('row_id') and len(selected_rows) != 1:
        specs['warnings'].append('送货单包含多个货物行且未定位所选行，不能借用其他行规格。')
    return bind_source(dict(supplier=field(suppliers), grade=grade, diameter_mm=diameter,
        specification=specs, quantity_t=field(quantities,
        ['送货行未定位，请按所选铭牌对应规格核对送货原图后填写重量（吨）。'] if not candidate.get('row_id') and not quantities else [])), candidate, 'delivery')


CERT_ID = re.compile(r'(?<![A-Z0-9])(?:[A-Z]{1,4}[A-Z0-9._/-]{5,}|\d{7,})(?![A-Z0-9])', re.I)


def certificate_fields(candidate, page=None):
    numbers = []
    raw_values = [(value, None, 'selected_certificate_inventory') for value in candidate.get('certificate_numbers', [])]
    if page is not None:
        # Compare label neighbours inside each OCR region. Cross-region
        # deduplication otherwise keeps only one of several conflicting reads
        # at the same label/value coordinates.
        for region in page.get('regions', []):
            blocks = [dict(b, region_id=region['region_id']) for b in region.get('blocks', [])]
            for block in blocks:
                raw_values.extend(certificate_label_values(page, block, blocks))
    dedup = {}
    for value, block, method in raw_values:
        if not value:
            continue
        evs = []
        if block is not None:
            evs = [evidence(page, block, method)]
        else:
            evs = [observation_evidence(candidate, o) for o in candidate.get('field_observations', [])
                   if o.get('field') == 'certificate_no' and compact(o.get('normalized_value') or o.get('raw_value')) == compact(value)]
        dedup.setdefault(value, []).extend(evs)
    for value, evs in dedup.items():
        if not evs:
            evs = [observation_evidence(candidate, o) for o in candidate.get('field_observations', [])
                   if o.get('field') == 'certificate_no']
        numbers.append(dict(value=value, evidence=evs))
    return dict(certificate_no=field(numbers, ['保留质证书编号原 OCR 值；缺字、多点等情况需核对原图补正。']))


def certificate_label_values(page, block, blocks):
    values, result = [], []
    text = compact(block.get('text'))
    # Keep the exact OCR token beside an explicit certificate label.
    label = re.search(r'(?:质量证明书编号|质保书编号|质编号|证明书号|货编号|(?<![A-Z])NO)\s*[:：.]?', text, re.I)
    if label:
        values.extend(CERT_ID.findall(text[label.end():]))
        if not values and bbox(block):
            box = bbox(block); yc=(box[1]+box[3])/2; h=max(1,box[3]-box[1])
            neighbours = []
            for other in blocks:
                obox=bbox(other)
                if other is block or not obox or obox[0] < box[2]-h*.25:
                    continue
                if abs((obox[1]+obox[3])/2-yc) <= h*.9 and obox[0]-box[2] < h*14:
                    neighbours.append((obox[0]-box[2], other))
            if neighbours:
                value_block=min(neighbours,key=lambda x:x[0])[1]
                for value in CERT_ID.findall(compact(value_block.get('text'))):
                    result.append((value,value_block,'certificate_label_neighbour'))
    # Some scans merge ``No`` with the value (for example ``NOK...``).
    if re.match(r'^NO', text, re.I):
        values.extend(CERT_ID.findall(re.sub(r'^NO[:：.]?', '', text, flags=re.I)))
    result.extend((value,block,'certificate_label_inline') for value in dict.fromkeys(values))
    return result


def build_filling_profile(result, index, classification, *, inspection_evidence=None):
    from .ledger_sources import inspection_fields
    pages = {p['page_no']: p for p in index['pages']}
    contexts = [approval_context(pages[p['page_no']]) for p in classification['pages']
                if 'approval_form' in p['classification']]
    resources = {role: {} for role in ('nameplate', 'delivery', 'certificate', 'inspection')}
    for entry in result.get('entries', []):
        resources['inspection'][entry['record_id']] = inspection_fields(
            entry['record'], entry['record_id'], (inspection_evidence or {}).get(entry['record_id']))
    for candidate in result.get('nameplate_inventory', []):
        page = pages[candidate['page_no']]
        peers = [c for c in result['nameplate_inventory'] if c['page_no'] == candidate['page_no']]
        resources['nameplate'][candidate['candidate_id']] = plate_fields(page, candidate, peers)
    for candidate in result.get('delivery_inventory', []):
        resources['delivery'][candidate['candidate_id']] = delivery_fields(pages[candidate['page_no']], candidate)
    for candidate in result.get('certificate_page_inventory', []):
        resources['certificate'][candidate['candidate_id']] = certificate_fields(candidate, pages[candidate['page_no']])
    return dict(schema_version='rebar-ledger-evidence-v2', material_id='rebar', columns=deepcopy(COLUMNS),
                approval_contexts=contexts, resources=resources,
                template_reference='报审表字文字内容提取项目说明.docx / word/media/image2.png',
                quantity_unit='t', row_identity='one_selected_physical_nameplate')
