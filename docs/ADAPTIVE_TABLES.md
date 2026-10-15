# 自适应钢筋进场表提取

本次把已在 AutoDL 两种钢筋样本上运行的自适应提取接入现有 `material_ocr` 包。不用把独立实验目录的 `batch.py` 覆盖到仓库；不改变同伴的附件识别、关联和台账取值规则。

## 使用方法

沿用已成功运行 TableRecognitionPipelineV2 的环境，仓库内安装项目：

```bash
python -m pip install -e .
```

不需要为本次更新升级 Paddle 后端。仓库要求 PaddleOCR 3.3.2；表格模块需要对应 PaddleX 的表格/布局依赖。沿用单页实验的 PaddleX 3.3 系列配置，模型缺失时流水线会下载到配置的缓存目录。普通 OCR 环境不一定已准备好表格依赖，先运行下方第一阶段测试。配置：PP-DocLayout-L、PP-LCNet 表格分类、RT-DETR-L 单元格检测、SLANeXt 结构模块、PP-OCRv5 检测/识别。

只测试第一阶段（页筛选、首页与进场表）：

```bash
python -m material_ocr.worker inspection \
  --pdf data/input.pdf \
  --out runs/adaptive_inspection \
  --device gpu:0 \
  --model-cache models/paddlex_cache \
  --layout adaptive
```

完整流程，包括原有附件关联与审核：

```bash
python -m material_ocr analyze \
  --pdf data/input.pdf \
  --out runs/adaptive_full \
  --material rebar \
  --layout adaptive \
  --device gpu:0 \
  --model-cache models/paddlex_cache
```

网页重启服务后，在钢筋的「检验记录版式」下选择「自适应表格模型（钢筋）」。默认仍是旧模板自动选择；不要把 `auto` 误认为自适应模型。

所有运行使用新的输出目录。完整流程的汇总位于 `work/inspection/records_all_pages.json`；仅第一阶段运行则位于输出目录根部。

## 流程与接口

整 PDF 页头分类 → 报审首页沿用固定模板 / 进场表进入自适应分支 → 整页方向与小角度纠偏 → 表格单元格框及 OCR 文字框 → 坐标配对 → 表头和合并单元格关系组装 → JSON 汇总。

- 表格模型在每个 PDF 的检验阶段初始化一次并复用。
- `fields` 保留原文字、规范化值、单元格框、OCR 框和置信度；不依赖模型生成的 HTML。
- 顶层保留 `row_no/diameter_mm/weight_t/manufacturer/certificate_no` 等后续关联接口。重量使用十进制字符串。
- 为兼容当前台账的进场数量来源，补充 `raw_cells/effective_cells/source_cells/field_evidence`；所有 `polygon_page` 已用逆变换回到原始 300 DPI 页坐标，不把校正图坐标直接画到原页上。`fields` 中仍保留校正图坐标及来源说明。
- 报审首页和重复候选沿用原逻辑。记录跨页 ID 唯一；重复记录不自动删除、不自动累加。
- 校正图、变换矩阵、模型原始输出及配对诊断分别在 `pages/page_NNN/adaptive/input.png`、`calibration.json`、`result.json`、`coordinate_result.json`。

## 告警与边界

已测试两种样式：厂家/证书同格，以及厂家/证书上下独立子行；续表空行不会自动生成产品。不声称适配所有表格。

页面分类不确定仍保留 `review_pages`；此轮没有扩充附件分类词表或修复手写报审编号。报审字段告警在 `submission_forms` 内，`extraction_review_pages` 不替代它。所有输出保持待人工审核，不直接作为正式放行数据。

自适应页无产品、表级结构冲突、关键字段问题或校正不确定时，完整流程停止在检验阶段并保留诊断。只有序号置信度告警、或微小点噪声空白候选等不涉及业务字段的问题，可继续原附件阶段；原记录告警仍保留。不会为降低复核数而修改 OCR 阈值或猜改字符。

目前只做有足够横竖长线支持的小角度纠偏，不做透视拉正；无标题续页、多张独立表混在同页、缺少必需表头等仍需复核。若只有普通 OCR 依赖、缺少表格模块，初始化失败会出现在逐页错误信息中，不伪装成空表。

## 验证与交付

独立版本已由用户在两份整 PDF 上验证第一阶段输出；本次包结构移植另做 CPU 回归、模型调用模拟和台账证据接口检查。没有在本地重新运行 GPU 端到端识别；完整的附件/台账联动需接收方在现有环境试跑。

移植后本地通过 84 项回归测试，并复放两份已保存的模型原始 JSON，6 条/11 条记录的全部字段值与原实验结果一致。Windows 测试开启 UTF-8，并用等内容复制模拟旧模板流程的硬链接；模型推理采用模拟调用，不算新的 GPU 精度测试。

只提交运行代码与当前说明。业务扫描件、OCR 结果、缓存模型和本地测试按原仓库约定留在本地。
