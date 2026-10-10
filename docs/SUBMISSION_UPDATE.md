# 固定版式报审表提取与重复候选

这次更新基于主分支已合并的材料 OCR 工作台（8cf83a4），将已验证的 V7.1 报审表功能接入包结构。网页、附件识别、四表匹配、六行/十一行模板选择与台账接口沿用原工程入口。

## 流程与输出

第一阶段现在同时筛选检验表（target）和报审表（submission）。报审表经标题及正文锚点确认后，按完整表框和正文三条填写下划线定位，读取文件编号、正文进场日期、使用部位及材料名称。使用部位保留原始分行；手写编号保留低置信度及人工核对标记。严重断线、不同版式或无法唯一定位时，记录该页失败，后续检验表仍继续。

第一阶段汇总 `work/inspection/records_all_pages.json` 的 schema_version 为 v7，新增：

- `submission_forms`：每份报审表的 values、原文、置信度、问题及原图坐标；原进场记录仍在 records。
- `submission_duplicate_candidates`：同 PDF、同模板下供货日期、使用部位及材料名称完整一致且字段规则通过的重复候选。编号不作为匹配条件；两页编号及差异均保留。

另输出 `work/inspection/submission_forms.json` 和 `pages/page_XXX/submission_ocr/review.html`。第一阶段 index.html 展示报审表分类与重复候选。

同日同部位的多批报审也可能命中候选，不能据此自动删页、合并或替换编号。候选不代表已人工确认。

## 台账接入

`build_filling_profile` 支持传入报审表提取结果，在相同来源页上优先使用固定区域 OCR。旧记录没有 submission_forms 时，继续使用既有附件全文匹配。

| 固定区域提取键 | 现有网页台账键 |
|---|---|
| document_no | file_no |
| supply_date | supply_date |
| use_location | usage_location |
| material_name | material_name |

审核上下文 ID 仍为 approval:页码。两份重复候选分别保留为上下文，编号不会跨页复制；重复和编号问题出现在字段来源警告中。网页已有的默认来源及人工字段确认规则沿用。match_results.json 和 filling_profile 也保留报审重复候选。

报审字段证据的 polygon_page 以原始 300DPI 渲染页为坐标系，并保存 render_dpi / page_pixel_size；附件 OCR 的图片可能为 180DPI，不能直接拿同一像素坐标框选附件图。

## 运行

在已有兼容的 Paddle 环境中，从仓库根目录安装更新：

```bash
python -m pip install -e .
python -m material_ocr analyze --pdf data/input.pdf --out runs/submission_update --material rebar
```

网页仍用 README 中的 serve 命令。若只测试首页：

```bash
python -m material_ocr.materials.rebar.submission \
  --pdf data/input.pdf --page 1 --out runs/cover_update --device gpu:0
```

复用之前已保存的完整 records_all_pages.json 和 attachment_index.json，可用公开 replay 命令验证网页台账衔接，不执行新 OCR。旧 V6 记录没有报审表字段时只能验证旧全文匹配路径。

## 验证

原独立 V7.1 已在用户 AutoDL 环境跑通 29 页样例：报审 1/4 页、检验 2/3/5/6 页、24 条检验记录、12 组检验重复候选及 1 组报审重复候选。

迁移到新工程后完成 25 项本地 CPU 测试，覆盖：报审路由及附件类型提示兼容、真实格式裁剪与多行解析、编号缺失/冲突、重复候选、旋转坐标、台账键映射、同 PDF 校验、旧 V6 全文匹配兼容、六行失败后十一行成功的模板回退、报审页失败后继续检验页、进度回调。复用已保存的用户 GPU 输出，确认两份台账上下文保留各自编号并得到 1 组重复候选。

本地没有 Paddle GPU 环境，迁移版尚需在 AutoDL 或同伴环境完成新 OCR 与网页端到端回归。业务文件与处理结果、开发测试按仓库现有交付规则保留本地，不随代码上传。

## 修改位置

新增 materials/rebar/submission.py、submission_duplicates.py、config/submission_b06.json；在 extraction/batch.py 接入报审分支，并保留多模板试验与进度；routing.py 保留旧 classify_header 并新增 classify_page_header；filling.py / review.py 接入台账；adapter.py 将新模板加入材料指纹，使配置变化进入运行版本记录。
