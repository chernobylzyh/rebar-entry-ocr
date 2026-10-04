# 第二阶段开发交接

## 边界

当前仓库只交付钢筋进场表提取V6。请把它作为可回归的第一阶段，不要把序号改成按物理行位置生成，不要丢弃空白候选和原始证据，不要自动合计重复页重量。

第二阶段目标：以进场表的质量证明书号、重量及辅助规格/厂家信息，在后续附件中检索质量证明书、送货单，定位关联铭牌并读取批号。附件可能共用送货单，不能硬编码三张图一组；重量不是唯一标识。

## 第一阶段模块

| 模块 | 职责 |
|---|---|
| batch.py | 全PDF路由、目标页处理、记录汇总和重复候选 |
| page_router.py / orientation.py | 页头分类规则、整页方向预测与坐标变换 |
| alignment.py | 固定网格自动定位 |
| lab.py | 渲染、预览、人工几何确认、逐格OCR与证据输出 |
| cell_ocr.py | 禁止单元格小图90度旋转；直接识别模块适配 |
| row_retry.py | 序号异常重试、数字区域定位与一致性采纳 |
| parsing.py / validation.py | 结构化解析、序号与核心字段质量状态 |
| blank_rows.py | 空白候选判定 |
| template_entry_full.json | 行列含义和当前版式参数 |
| check_cells.py | 已有序号格小范围GPU验证 |
| check_alignment_pdf.py | 指定页面的CPU几何验证，默认页码仅为样例测试 |

## 读取接口

records_all_pages.json顶层包括schema_version、pdf_sha256、records、duplicate_candidates、review_pages、ready_for_search。

每条record的重要字段：

- record_id、page_no、physical_row_index：来源定位，record_id应和pdf_sha256联合使用以避免跨PDF冲突。
- row_no：OCR业务序号，可为null；不能作为唯一关联键。
- weight_t：吨为单位的十进制字符串，使用Decimal比较，不用二进制浮点直接比较。
- diameter_mm：规格直径字符串，不含HRB牌号；牌号需从后续资料读取，不能凭直径生成。
- manufacturer、certificate_no：厂家与证书号；证书号保留字母和前导零。
- raw_cells：首次OCR原文；effective_cells：解析采用的文本，重试可能只更新序号。
- row_number_source、row_number_retry：序号采纳路径及所有重试证据。
- issues、status、row_number_status、search_fields_status：规则质量状态，不是人工审批结果。
- source_result：相对于batch输出根目录的单页result.json路径。
- source_cells：字段到cell_id的映射，在单页result.json的cells中解析。
- ready_for_search：当前始终false，正式放行规则尚未实现。

单页result.json的cells保留raw_text、blocks、polygon_page、crop_path。polygon_page以原始300DPI渲染页面左上角为原点，即使转正/透视校正也映射回原图。重试blocks的坐标系另有说明，不能混当原页面坐标。

## 第二阶段建议接口（尚未实现）

附件OCR先形成可追溯索引：pdf_sha256、page_no、image/region_id、原始文字、坐标、方向、来源图路径、OCR分数。

检索返回候选而非强制单一命中：matched字段、原文证据、冲突/多候选原因、关联页面或区域。证书号优先精确检索；不将O/0等自动替换为事实。重量检索同时校验单位、规格、厂家和上下文。页面相邻关系只是辅助证据，不能保证同组。

目前page_index的other只是“不是第一阶段固定进场表”，仍包含第二阶段所需附件；review也不能丢弃。不要直接把第一阶段筛选出的方向当作所有附件的已验证正向。

## 验收建议

修改后先运行全部CPU测试。GPU回归须比较目标页、记录数、空白候选数、字段值、source证据和重复候选，而非只看终端没有异常。原始PDF/结果由拥有者通过授权渠道提供，不提交Git。

当前验证样例含两套重复进场记录；12组重复候选不意味着一般情况下可自动合并。建议在第二阶段提供显式冲突与复核输出，保留每条来源。
