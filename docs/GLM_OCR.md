# GLM-OCR 生产使用与本地测试

当前 Vue 工作台默认使用本地 GLM-OCR（`local-glm`），可在识别配置中切换到本地 Paddle PP-OCRv5（`local-paddle`）。Java 转发 Python 统一提供的模型目录，GLM 使用专用 `.venv-glm` 子进程完成推理；两种模型共用当前表格提取、裁剪、四表匹配及核验规则。模型维护、缓存隔离和独立结果对照见[OCR 模型切换与结果对照](OCR_MODELS.md)。

进场表继续采用原自适应表头、物理单元格行列绑定、关键词提取与四表匹配规则，只把单元格读字替换为 GLM。整页文字不能代替单元格结构，尤其“生产厂家/质量证明书编号”上下两层的单元格需要分别读取。历史结果只复用可校验的几何位置，旧 Paddle 文字和值不进入 GLM 结果。新文件的表格几何由已缓存的本地 Paddle 版面与单元格检测模型测量，该步骤不调用 Paddle 文字 OCR。

前端在“进场表单元格识别”阶段显示所有进场表单元格的累计完成数，单位为单元格；页面分类、整页提取和附件 OCR 继续按页显示。

证号路线使用独立单炉号铭牌。检测报告或未分离卡片的多炉号文字只保留为诊断，不能制造多个铭牌竞争者，挡住已由证号和炉批号确认的完整铭牌。同一页同炉号、相同牌号及规格且几何一一对应的混合文字段与独立裁区合并为一个铭牌视图，保留两份原始证据；不同真实卡片仍保留歧义。铭牌与唯一送货单同页时直接关联供应单位和送货单编号；货物行缺牌号或规格单独提示核验，不清空已读出的送货单表头。

同一 PDF 中重复的非空质保书编号只保留首次物理行，合并后续行的来源和冲突信息，验收数量不累加。GLM 表格几何行的原始单元格及全部业务字段都为空白或横线占位符时，不生成“未识别”台账行；被排除行的原文、页码与位置仍记录在 `certificate_number_deduplication.omitted_placeholder_records`。有实际内容、仅有序号、问号或“无法识别”字样的行继续保留，无证号的规格路线不受此过滤影响。

## 模型与环境

生产部署使用 Linux/WSL。Python 服务安装根目录 `pyproject.toml` 的依赖，并单独安装与硬件兼容的 Paddle 计算后端；即使选择 GLM，自适应表格几何仍需 Paddle/PaddleX 和结构模型。

GLM 推理使用独立解释器，要求 PyTorch 以及提供 `GlmOcrForConditionalGeneration` 的 Transformers。已有可用环境直接通过环境变量引用；全新环境可以按以下步骤准备（先按照 [PyTorch 安装说明](https://pytorch.org/get-started/locally/) 安装适配 CUDA/CPU 的 torch，再安装 Transformers、Pillow 和 pypdfium2）：

```bash
python -m venv .venv-glm
.venv-glm/bin/python -m pip install torch
.venv-glm/bin/python -m pip install 'transformers==5.16.1' Pillow pypdfium2
.venv-glm/bin/python -c 'import torch; from transformers import AutoProcessor, GlmOcrForConditionalGeneration; print(torch.__version__, torch.cuda.is_available())'
```

上面的 torch 安装命令使用包索引默认构建，GPU 用户应替换为官方针对设备/CUDA 的命令。开发机当前实装参考为 Python 3.10、torch 2.11.0+cu128、Transformers 5.16.1；这是环境参考，不是对所有硬件的兼容承诺。本次代码交接没有重新下载或验证一套全新推理环境。

从官方 [ZhipuAI/GLM-OCR](https://modelscope.cn/models/ZhipuAI/GLM-OCR) 或 [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) 获取完整权重到 `models/GLM-OCR/`。运行时只读本地权重，不自动下载；至少需有 `config.json`、`model.safetensors`、`processor_config.json`、`preprocessor_config.json`、`tokenizer.json`、`tokenizer_config.json`、`chat_template.jinja` 和 `generation_config.json`。缺少权重或解释器依赖时，服务可以启动，但识别任务不能成功。

已有模型和解释器位置不同，可在启动服务前配置：

```bash
export MATERIAL_OCR_GLM_PYTHON=/绝对路径/推理环境/bin/python
export MATERIAL_OCR_GLM_MODEL_DIR=/绝对路径/GLM-OCR
```

不要复制开发机 `.venv-glm` 到其他机器；虚拟环境包含机器路径，应使用当地环境重建。模型、环境和权重清单均不提交。

## 前端测试的启动方式

在仓库根目录启动 Python 服务，先激活已有 `ocr` 服务环境（其中已安装 FastAPI），不要使用缺少服务依赖的系统默认 Python。GLM 推理由专用子进程解释器承担，不需要把 Paddle 环境中的依赖再复制一份：

```bash
conda activate ocr
python -m material_ocr serve --port 8000 --data-dir runs/web \
  --model-cache models/paddlex_cache
```

另开终端，在仓库根目录启动 Java：

```bash
OCR_BASE_URL=http://127.0.0.1:8000 bash 前端/bin/start-local.sh
```

再启动当前 Vue 工作台：

```bash
cd 前端/vue
npm run dev
```

Python、Java 或前端已运行旧版本时，需要结束旧进程后按上述方式重新启动。`--model-cache models/paddlex_cache` 保留既有命令兼容性；GLM 权重实际使用共享的 `models/GLM-OCR/`，不会把模型复制到该 Paddle 缓存目录或每个运行目录。历史 `analyze` 命令与 `/api/jobs` 的 Paddle 功能保留；本次切换范围为当前 Vue 使用的 `/api/library` 识别流程。

仓库内默认使用 `.venv-glm/bin/python` 与 `models/GLM-OCR/`。只有实际位置不同时才在启动 Python 服务前设置以下变量，路径指向已有环境和权重，无须另装模型或另建副本：

```bash
export MATERIAL_OCR_GLM_PYTHON=/绝对路径/.venv-glm/bin/python
export MATERIAL_OCR_GLM_MODEL_DIR=/绝对路径/models/GLM-OCR
```

浏览器打开 Vue 终端显示的地址，选择现有四卷并点击「识别整卷 PDF」。识别配置应显示「本地 GLM-OCR + 自动匹配规则」；正常复测保持「强制重跑 OCR」未选中。系统先复用可校验的 GLM JSON checkpoint，只补识别缺失页；旧 Paddle 结果不能冒充 GLM 缓存，模型切换后首次仍可能需要真正推理。无须为测试再次上传同一份 PDF。

「清台账」用于应用当前规则重算匹配，保留可复用 OCR；新台账会使旧人工补正与核验失效。勾选「强制重跑 OCR」会实际重新推理，并覆盖同一稳定生产缓存位置的 JSON checkpoint，不改写历史实验来源；正常使用保持未选中即可复用有效缓存。重新打开页面、重复提交活动任务不应创建另一套大容量运行。

## 缓存与空间

GLM 使用共享离线权重、逐页 JSON checkpoint，并在内存中渲染整页和 ROI；不把每个裁区另存为 PNG，也不为每次匹配复制源 PDF 或模型。相同输入与生效配置可校验通过时复用 OCR 文本，重新匹配只增加必要的文本、诊断和台账。Java 与 Python 原有文件库仍各自保留正常查看需要的文件。

自适应表格几何与 GLM 单元格识别结果同样使用按 PDF 校验的共享 JSON 缓存，单元格裁图仅在内存中存在。完整单元格计划可复用相同裁区的既有 GLM 读数；再次匹配无需重复识别已完成单元格，也不生成裁区图片副本。

共享生产原生 checkpoint 位于 `runs/web/ocr-cache/glm/`，按权重及推理参数指纹、完整 PDF SHA256 保存。各卷 `runs/web/library/` 只保存台账、索引等较小运行产物及来源关联；本地 GLM 实验 checkpoint 仍保留原路径和来源引用，不复制整个实验目录。不要为释放空间手动清空 `runs/`、`experiments/` 或模型目录，旧运行维护见[存储维护说明](storage_maintenance.md)。

GLM 原生输出没有词级坐标。界面可定位来源页与已测量的 ROI；缺少可靠框时显示来源页，不伪造逐字坐标。

## 本机研发工具（最小源码交付不含这些工具）

本节引用的 `tools/check_glm_ocr.py`、`tools/analyze_glm_output.py`、实验数据和存储维护工具只保留在开发机，不随最小源码交付。生产调用所需的 `tools/compare_ocr_ledgers.py` 和包入口会交付。以下命令会执行真正的 OCR，用于已登记的模型实验。日常前端复测使用上面的服务入口，不必另外执行一轮实验：

```bash
.venv-glm/bin/python tools/check_glm_ocr.py \
  --pdf '钢筋报审文件/2025.12.6日钢筋报审表.pdf' \
  --pdf '钢筋报审文件/钢筋报审.pdf' \
  --out experiments/runs/<run-id>/glm \
  --model-dir models/GLM-OCR \
  --geometry-manifest experiments/analyses/glm-input-geometry-20261017.json \
  --device cuda:0
```

独立实验中每个 PDF 必须以 SHA256 匹配 geometry manifest；页面方向只复用已核验的几何信息。原始页和 ROI 图仅在内存中存在，页级 JSON checkpoint 可断点续跑，原始 PDF 不复制。整页 `polygon_page` 保持 `null`，ROI 只记录独立测量输入框，不伪造文字框。

`--skip-regions` 可只跑整页文本。若整页已经完成而需要补做几何候选区域，可使用独立输出目录，不重跑整页：

```bash
.venv-glm/bin/python tools/check_glm_ocr.py \
  --pdf '钢筋报审文件/钢筋报审.pdf' \
  --out experiments/runs/<roi-run-id>/glm \
  --model-dir models/GLM-OCR \
  --geometry-manifest experiments/analyses/glm-input-geometry-20261017.json \
  --reference-full experiments/runs/<full-run-id>/glm \
  --regions-only --device cuda:0
```

`--regions-only` 会严格校验已有全页输出的模型指纹、PDF SHA、DPI、方向、提示词和几何清单 SHA；新目录只写 ROI 文本和对全页 checkpoint 的 SHA 引用。

真实运行及对照结果保存在 `experiments/runs/`，不要把 GLM checkpoint 当作已人工核验的台账。

真实推理、缓存重解析和接口验证分别记录。仅重新解析缓存或测试接口时，不声称重新测得 OCR 效果，也不把旧实验的两份 PDF 结果当作本次四份文件前端实测结果。

## 公司名称的来源

- 生产单位读取独立铭牌顶部公司原文；供应单位读取独立送货单顶部公司原文。正文的生产厂、供货单位等标签只保留为补充候选，不覆盖顶部读数；读数不一致时保留顶部值并标记冲突。
- 铭牌和送货单同页时分别解析各自表头。购货、订货、收货、签章等其他角色不能替代这两个字段。保留用户已确认的送货单标题例外：《2025.12.6日钢筋报审表.pdf》第5页「上海市钢筋混凝土结构用钢筋行业」按顶部原文填作供应单位。其他行业通用标题不据此自动补作公司名。多铭牌的公司名称逐卡保存，不从相邻卡或另一 OCR 模型补字。
- 顶部仅识别英文时保留英文并提示核验；例如“中新钢铁集团”按顶部原文保存，正文中的完整法律名称另存候选，不擅自扩写。
- 裁区漏掉铭牌顶部时，只有同页唯一铭牌的牌号和唯一炉批号与全文完全一致，才允许引用全文顶部公司，并明确记录整页证据。无法满足则留空，提供自身页面/ROI 定位。
- `manufacturer_heading` / `supplier_heading` 保存顶部值、原始文本行、候选、冲突及来源 checkpoint；逻辑行号是 OCR 文本引用，不是虚构的像素文字框。

缓存对比报告使用当前前端的 12 列顺序，展示缺失、冲突、候选和 PDF 页码。Paddle 本地既有结果与 GLM 缓存重解析分别保留；两者版式解析不同，因此这是现有工作流的效果对照，不能当作只替换模型的准确率实验。报告中的 Excel 为实验对比表，正式业务导出仍须在前端完成关键字段核验。

## 本机历史双模型台账对比

已有 `tools/analyze_glm_output.py` 生成的缓存分析后，执行：

```bash
python tools/compare_ocr_ledgers.py \
  --analysis-root experiments/runs/<analysis-run-id>/analysis \
  --out experiments/runs/<comparison-run-id>/comparison
```

输出目录必须为空。工具检查原 PDF、Paddle 清单和台账、GLM checkpoint 的 SHA256，以及 GLM 每项证据的 PDF 和页码归属。按原清单的页码、行号对齐；保留重复页并提示，数量不自动合计。

打开 `index.html` 可以切换文件、显示模型、筛选差异，点击页码跳到原 PDF；`ocr_ledger_comparison.xlsx` 包含各文件和模型的 12 列台账、字段溯源及关联候选。报告使用相对路径引用原 PDF，移动报告时应保留它与原文件的路径关系。工具只写文本、HTML 和 Excel，不调用 OCR、不修改前端已有台账。

清单牌号缺失而铭牌已经读出公司时，公司显示为待核验候选及原页链接，主台账保持未确认。页面分别统计“台账已填字段”和“GLM 顶部公司已读候选”，两者不能混为匹配成功数。
