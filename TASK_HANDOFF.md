# 报审表 OCR 台账项目：协作交接

更新日期：2026-10-19。本文面向从 Git 克隆仓库的新合作者；不包含开发机业务库、PDF、缓存路径、进程号或历史实验产物。完整安装与启动命令见根目录 [README.md](README.md)。

## 当前目标与已实现范围

目标流程：扫描 PDF 上传 → 本地 OCR 与字段提取 → 进场清单、质量证明书、铭牌、送货单四表自动匹配 → 展示字段、诊断和原图证据 → 导出 Excel 前集中人工补正与核验。

目前钢筋业务主路径已实现：

- 识别报审表、进场数量清单/进场检验记录、质量证明书、铭牌和送货单；保留来源页、可用坐标、原文和字段证据。
- 进场表支持自适应结构及单元格读取；报审表提供公共字段。
- 清单有质保书编号时，按“清单编号 → 质量证明书 → 炉批号 → 铭牌 → 送货单”关联；清单没有编号时，按“清单牌号/规格 → 铭牌及送货单 → 炉批号 → 质量证明书”关联。
- 规格跨页匹配要求一致；牌号按有效强度数字匹配。送货单与铭牌同页且候选唯一时共享送货表头字段；多铭牌逐卡记录。
- 质量证明书与铭牌炉批号等长且仅一位数字不同，并且证书该炉批行与铭牌完整规格一致时，可唯一关联并采用铭牌炉批号原文；证书/铭牌原值、差异及来源保留待核验。多个同规格铭牌仅可按唯一相邻附件组定位，否则保留候选。
- 重复的非空证号行合并且不累加数量；保守排除全占位模板行。缺失、未匹配、多候选和真实字段冲突保留诊断和定位，不静默猜值。
- Vue 提供 PDF 上传、识别进度、历史、单卷台账、总台账、来源原图定位、字段补正和核验。Java 保存业务状态并支持 Excel/CSV 导出。
- OCR 默认 `local-glm`，可选 `local-paddle`；模型目录由服务统一提供，同卷运行中禁止切换模型。两者共用相同字段提取、匹配和核验逻辑。
- 识别任务排队并按卷复用；结果与模型/输入/规则身份校验。诊断派生图片可按需从本地源 PDF 恢复。

这些功能已由开发环境的单元测试、构建、历史缓存回放和浏览器验证覆盖。覆盖字段数不是准确率，未见版式、模糊扫描和相互矛盾的原始单据仍需人工核验。协作者应对自己环境的构建及业务 PDF 重新验证，不把历史记录当作新环境已通过的证据。

## 服务结构与启动

- Python：`src/material_ocr/`，OCR、字段提取、匹配和本地 API，端口 8000。
- Java：`前端/java/business/`，业务 API、文件/状态持久化和核验导出，端口 8080；本地使用 H2。
- Vue：`前端/vue/`，开发界面，默认端口 5173。
- Python 生产匹配器依赖 `tools/compare_ocr_ledgers.py`，该文件属于运行代码并随仓库交付。

从仓库根目录分别运行：

```bash
# Python 环境已安装项目和硬件兼容的 Paddle 后端
python -m pip install -e .
PYTHONPATH=src:. python -m material_ocr serve \
  --port 8000 --data-dir runs/web --model-cache models/paddlex_cache
```

```bash
# Java：需要 JDK 17+ 和 Maven
OCR_BASE_URL=http://127.0.0.1:8000 bash 前端/bin/start-local.sh
```

```bash
# Vue：Node.js 20.19+（建议按 .nvmrc 使用 Node 24）
npm --prefix 前端/vue ci
cd 前端/vue && npm run dev
```

访问 Vue 开发服务器输出的地址，通常为 `http://localhost:5173`。CPU 服务可在 Python 命令后增加 `--device cpu --profile complete`。Java 生产构建使用 Maven，Vue 构建使用 `npm --prefix 前端/vue run build`。

GLM 推理依赖单独安装到本机环境，权重放在本地 `models/GLM-OCR/`。`pip install -e .` 不包含 PyTorch/Transformers，也不下载 GLM 权重。新机器按 [GLM-OCR 环境准备](docs/GLM_OCR.md#模型与环境) 安装并配置 `MATERIAL_OCR_GLM_PYTHON`、`MATERIAL_OCR_GLM_MODEL_DIR`；缺少权重时识别任务无法运行。Paddle几何/可选 OCR 模型权重也需本地准备。不要复制开发机虚拟环境或模型目录。

## 重要业务约束

- 有清单证号但未确认到证书时，不能静默切换无编号路线或清空原编号。
- 生产单位来自铭牌；供应单位和送货单号来自送货单。来源候选冲突时保留冲突和证据。
- 验收数量来自对应进场清单行；不以送货重量替换，也不累加重复行。
- 未匹配、多候选、OCR不确定和真实冲突保持待核验；成功关联说明本身不作为冲突标红。
- GLM没有词框时只给来源页/实测 ROI，不伪造字级坐标。
- 重新识别前确认没有正在运行的同卷任务或待保存人工补正。普通规则重算优先复用有效 OCR 缓存，强制重跑才重新推理。

## 维护入口

- `src/material_ocr/materials/rebar/glm_production.py`：Vue 生产流程和 GLM/Paddle 后端调度。
- `src/material_ocr/materials/rebar/glm_entry_bridge.py`、`coordinate_match.py`：单元格读数和自适应进场行/字段解析。
- `src/material_ocr/materials/rebar/glm_experiment.py`、`automatic.py`、`matching.py`：资源解析、四表关联和冲突诊断。
- `src/material_ocr/materials/rebar/review_policy.py`、`glm_web_contract.py`：台账字段核验状态与 Web 数据结构。
- `src/material_ocr/ocr/backends.py`：模型注册表、权重目录和解释器选择。
- `src/material_ocr/web/library.py`、`recognition.py`：文件库、识别队列和 Python API。
- `前端/java/business/src/main/java/.../LibraryService.java`：Java 同步、人工补正、核验及导出。
- `前端/vue/src/views/ResultView.vue`：单卷结果、证据导航和核验界面。

四表约束和字段语义详见 [自动台账说明](docs/AUTOMATIC_LEDGER.md)；模型配置见 [OCR 模型说明](docs/OCR_MODELS.md)；接口进度见 [识别任务说明](docs/RECOGNITION_JOBS.md)。

## 仓库交付边界

随仓库提交运行源码、配置、依赖锁和通用文档。PDF、`runs/` OCR/台账缓存、`models/` 模型权重、`前端/image/library/`、`前端/runtime/`、日志、构建缓存和本机实验/测试产物都留在运行者本地。新合作者使用自己的材料和缓存。提交前用 `git diff --cached --name-only` 检查清单，不能强制加入被忽略的运行数据。

研究代码改动和实验运行按项目 `AGENTS.md` 及 `research-experiment` 记录规范处理；无新运行时不要创建声称已运行的记录。当前工作区原有的实验档案是开发者本机材料，不是本次代码交接的一部分。

## 本次交付检查

在只包含明确交付文件的临时源码副本中，77 个 Python 文件编译/模块导入、生产匹配器及模型目录路由直接检查通过；Java 33 个源码文件离线编译和 Vue 生产构建通过。依赖复用开发机已安装环境，未重新安装全新依赖；Vue 保留已有构建告警。未运行 OCR、未重算业务数据，也未把历史浏览器/算法验证当作本次新执行结果。普通工程检查日志留在开发机，不随仓库上传。
