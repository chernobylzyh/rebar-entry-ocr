# V6：固定表格禁用细长文字旋转，异常序号绕过检测兜底

## 本次证据

用户确认第2页序号1的内部识别小图已被旋转。第5页序号4的原始JSON中dt_polys为空，第2页序号4则有检测框且识别分数0.999639。这是两个环节的问题：误旋转与文字检测漏检。没有检测概率图/过滤前候选，不能断言第5页的漏检具体由哪个阈值造成。

## 修改范围

1. FixedCellOCR适配器仅包围固定表格单元格OCR。保留文字检测与透视裁剪，去掉细长文字小图的90度旋转。单元格重试同样使用该适配器。
2. 整页转正、页头OCR、模板对齐、核心字段解析、空白行逻辑不变。第25/26页仍可能review，本版不修页头分类。
3. 序号初次异常时仍先进行2倍/3倍重试；仍无结论，再用简单连通域定位内部数字区域，去除接触边缘的框线，保留所有内部有效连通域（不是只取最大块，以免12变成1）。这是限定序号列的图像规则，不应用到其他列。
4. 把上述区域交给独立TextRecognition模块，跳过文字检测器与裁剪器旋转。原尺寸和2倍尺寸两次读数必须相同、均达到0.95，且不与已有有效初次数字/高分候选冲突，才写入草稿。不是按物理行号猜数，不降低阈值。
5. 独立识别器仍为PP-OCRv5_server_rec；只在兜底时按需加载，同一batch跨页缓存。比原流程可能额外占用一份识别模型显存，但不增加训练或新的模型权重种类。

只临时替换当前Python进程里的裁剪方法，每次调用结束或异常都会恢复。不编辑site-packages。不支持同一进程里并发运行其他OCR线程；现有batch是顺序执行。启动时检查预期裁剪接口，不兼容时停止而非默默忽略修复。

## 上传解压

上传rebar_table_batch_v6.zip到/root/autodl-tmp，V5结果保持不动：

```bash
conda activate rebar-ocr
cd /root/autodl-tmp
unzip rebar_table_batch_v6.zip
cd rebar_table_batch_v6
python -m unittest discover -p 'test_*.py'
```

继续用已有PaddleOCR 3.3.2、PaddleX 3.3.13环境，不需要重装。

## 先只测试三个异常格（推荐）

```bash
python check_cells.py \
  --images \
  ../rebar_table_batch_v5/runs/pdf_draft_v5/pages/page_002/ocr_draft/cells/p2_r01_row_no.png \
  ../rebar_table_batch_v5/runs/pdf_draft_v5/pages/page_005/ocr_draft/cells/p5_r01_row_no.png \
  ../rebar_table_batch_v5/runs/pdf_draft_v5/pages/page_005/ocr_draft/cells/p5_r04_row_no.png \
  --out runs/cell_check_v6 \
  --device gpu:0
```

此命令不会改旧文件、不会扫描PDF。检查cell_report.json及每格目录中的*_rec_input_001.png。这些PNG是修复后的内部识别图片（模型缩放归一化前），1应保持竖直。没检测到文字时不会有rec_input；若触发直接识别兜底，查看retries/*_direct1.png和*_direct2.png以及其JSON。

终端initial表示本次禁用旋转后的初次结果，effective表示重试决策后的文本，不代表人工确认。未通过条件时不会强行输出1或4。

## 然后重跑整份PDF

```bash
python batch.py \
  --pdf '../rebar_table_lab/data/0814钢筋02.pdf' \
  --out runs/pdf_draft_v6 \
  --device gpu:0 \
  --extract-draft
```

输出目录必须是新目录。启动逐格识别时会打印：

```text
cell OCR: preserve upright text; automatic 90-degree crop rotation disabled
```

结果schema_version为v6；单页result.json增加cell_crop_policy。其他字段与V5保持兼容；row_number_source新增direct_recognition_consensus表示直接识别兜底的双次一致结果。所有ready_for_search仍为false。

每格生成*_crop_audit.json。所有序号格及其常规重试还保存*_rec_input_XXX.png，用于确认修复有效，不必再用旧debug_ocr_crop.py（旧脚本仍调用原始未修复OCR流程）。

## 回传与验证

- 先回传runs/cell_check_v6/cell_report.json；若仍有异常，附相应小图及原始JSON。
- 全PDF完成后回传records_all_pages.json和page_index.json，重点检查核心字段是否与V5一致、重复候选是否仍为12组。
- 66项CPU回归测试已通过：禁止旋转、宽文字图不变、异常后恢复原方法、直接识别模拟、低分/冲突拒绝、多位数字区域保留，以及前代所有测试。
- 已用用户上传的第2页1、第2页4、第5页4验证图像定位可产生内部数字区域；本地没有Paddle GPU环境，真实模型结果、接口运行及速度仍需AutoDL实测。不能承诺修复后三格一定全部通过。

独立识别API依据官方文档：https://www.paddleocr.ai/v3.3.2/en/version3.x/module_usage/text_recognition.html
