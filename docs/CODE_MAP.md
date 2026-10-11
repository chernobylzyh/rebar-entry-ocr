# 代码结构与维护入口

本文对应当前 `phase2-form-matching` 的运行交付版本，说明代码职责、调用关系和修改入口。交付范围为完整业务代码包、安装入口和当前使用说明；开发实验、业务样本和处理结果保留本地。实际使用步骤、匹配规则和导出内容见 [完整流程](WORKFLOW.md)，启动网页见 [网页使用说明](WEB_USAGE.md)，新增材料的接口约定见 [材料扩展说明](MATERIALS.md)。

文中的路径均相对于项目根目录。新环境应先按 [README](../README.md) 安装项目，再使用 `material-ocr` 或 `python -m material_ocr` 入口。

## 目录地图

```text
github_project/
├── README.md                         # 项目能力、环境安装和使用入口
├── pyproject.toml                    # Python 包、依赖、CLI 和包内静态资源
├── requirements.txt                  # 运行依赖入口
├── .gitignore                        # 排除本地输入、运行产物和模型缓存
├── src/material_ocr/                 # 可安装的业务代码包
│   ├── __main__.py                   # python -m material_ocr
│   ├── cli.py                        # serve / analyze / replay / materials
│   ├── workflow.py                   # 通用工作流、运行状态和代码/数据指纹
│   ├── worker.py                     # 钢筋检验表和附件 OCR 独立阶段
│   ├── processes.py                  # 任务进程及进程组停止
│   ├── paths.py                      # 定位包内配置和审核模板
│   ├── web/
│   │   ├── app.py                    # FastAPI：上传、结果、审核备份、台账 API
│   │   ├── tasks.py                  # 持久任务、串行队列、结果缓存
│   │   └── static/
│   │       ├── index.html            # 上传与任务工作台
│   │       ├── app.js                # 文件/文件夹输入、任务轮询、打开审核页
│   │       └── style.css             # 工作台样式
│   ├── materials/
│   │   ├── base.py                   # MaterialAdapter 与通用数据类型
│   │   ├── registry.py               # 材料注册及插件发现
│   │   ├── examples/
│   │   │   ├── steel_beam.json       # 钢梁待接入的规则示例
│   │   │   └── concrete.json         # 混凝土待接入的规则示例
│   │   └── rebar/
│   │       ├── adapter.py            # 钢筋 OCR、匹配、统计、台账的组织入口
│   │       ├── routing.py            # 页头路由：检验页 / 其他 / 待复核
│   │       ├── parsing.py            # 钢筋检验记录字段解析
│   │       ├── validation.py         # 钢筋字段及记录校验
│   │       ├── review.py             # 全页分类修正、质编号检索、生成审核输入
│   │       ├── matching.py           # 当前网页使用的钢筋四表匹配规则
│   │       ├── filling.py            # 钢筋台账列定义及字段提取、溯源
│   │       ├── ledger_sources.py     # 铭牌/送货规格组合、检验数量优先及差异提示
│   │       └── config/
│   │           ├── material.json     # 材料信息、模板、匹配阈值、统计单位
│   │           ├── attachment_rules.json # 附件关键词、区域、OCR 配置
│   │           ├── inspection_6_rows.json # 六行检验表几何模板
│   │           └── inspection_11_rows.json # 十一行检验表几何模板
│   ├── extraction/
│   │   ├── batch.py                  # 全 PDF 检验页扫描与明细提取
│   │   ├── table.py                  # 页面渲染、表格几何、单元格 OCR
│   │   ├── alignment.py              # 表体定位和有限列宽漂移适配
│   │   ├── blank_rows.py             # 空白行候选判断
│   │   └── row_retry.py              # 行号 OCR 重试与证据保留
│   ├── ocr/
│   │   ├── attachments.py            # 全页附件 OCR、字段区域、坐标、检查点
│   │   ├── layout.py                 # 混合页实体拆分、送货物理行、重点区域
│   │   ├── orientation.py            # 方向模型与页面旋转
│   │   ├── cell.py                   # 单元格 OCR 裁剪与方向处理
│   │   └── crop_fusion.py            # 保存区域的 GPU 重识别与证据融合工具
│   ├── matching/
│   │   └── catalog.py                # 字段目录复用工具及历史通用匹配研发
│   ├── review/
│   │   ├── associations.py           # 内容分组、初始四表自动捆绑和库存
│   │   ├── render.py                 # 审核 HTML、JSON、初始 CSV 和图片组织
│   │   ├── images.py                 # 审核原图的本地可访问性处理
│   │   ├── review_state.js           # 人工选择、确认、解除、库存和状态导出
│   │   ├── review_ui.js              # 候选清单、原图、JSON/捆绑 CSV 交互
│   │   ├── filling_ui.js             # 台账预览、字段补正与确认、Excel 下载
│   │   └── templates/same_page.html  # 四表审核及台账页面模板
│   └── filling/
│       ├── base.py                   # ApprovedFormWriter 接口
│       ├── ledger.py                 # 可信关联重建、字段确认及版本校验
│       └── excel.py                  # 钢筋 Excel：材料台账与字段溯源
└── docs/                             # 当前使用、维护和交付说明
    ├── WORKFLOW.md                   # 上传到审核、台账与导出的完整流程
    ├── WEB_USAGE.md                  # 网页启动、操作与常见问题
    ├── CODE_MAP.md                   # 本文：代码结构和修改入口
    ├── ARCHITECTURE.md               # 通用流程和模块边界
    ├── MATERIALS.md                  # 新材料接口和注册方法
    ├── HANDOFF.md                    # 交付范围、现有能力和验收要点
    ├── ACCEPTANCE.md                 # 接收方环境准备、实际运行和逐项核验
    └── GITHUB_SUBMISSION.md          # 提交清单、检查与交付方法
```

`steel_beam.json` 和 `concrete.json` 用于展示材料规则组织方式；当前注册表将这两种材料标为待接入。仅添加配置不会获得完整 OCR、匹配或填表能力。

`materials/rebar/` 是运行钢筋识别、匹配和台账功能所需的算法与规则，随代码交付。钢筋 PDF、页面图像、OCR 文本、人工审核记录和导出台账属于本地输入及产物，不随仓库交付。

`pyproject.toml` 将材料 JSON、网页静态资源、审核模板和审核 JS 纳入包资源。运行包不依赖顶层 `experiments/`、`tools/`、`tests/`、模型清单或历史文档；接收方安装后可从自己的 PDF 开始运行。

## 主入口怎样调用

| 入口 | 调用关系 | 主要职责 |
| --- | --- | --- |
| `material-ocr serve` | `cli.main()` → `web.app.create_app()` → `TaskService` | 启动工作台，管理本地上传和后台任务 |
| 网页开始识别 | `POST /api/jobs` → `TaskService.create()` → `process_job()` → `run_document()` | 保存上传文件、排队、启动 `analyze` 子进程或复用缓存 |
| `material-ocr analyze` | `cli.main()` → `workflow.run_pipeline()` → `MaterialRegistry.get()` → 材料适配器 | 从原 PDF 执行 OCR、匹配和统计，登记产物及失败状态 |
| 钢筋 OCR | `RebarAdapter.extract()` → `worker` → `extraction.batch.run()` / `ocr.attachments.build_attachment_index()` | 先检验记录阶段，再全页附件阶段，串行释放 GPU 显存 |
| 钢筋匹配 | `RebarAdapter.match()` → `rebar.review.generate_review()` → `review.render.build()` → `rebar.matching.rematch()` | 修正分类、建立字段目录、匹配四表并生成审核页 |
| 初始捆绑 | `rebar.matching.rematch()` → `review.associations.prepare_associations()` | 唯一且无待核验项的关联自动完成，其他进入人工队列 |
| 人工审核 | `review_ui.js` → `review_state.js` | 在浏览器保存选择和确认，更新候选可用性，导出审核 JSON/捆绑 CSV |
| 台账预览 | `filling_ui.js` → `POST .../fill/preview` → `RebarLedgerWriter.preview()` → `ledger.preview_ledger()` | 从可信候选重建关联，生成可核对字段，校验确认是否仍有效 |
| 台账 Excel | `POST .../fill` → `RebarLedgerWriter.write()` | 只写字段已确认的有效行，并保存导出审计 JSON |
| `material-ocr replay` | `workflow.run_pipeline(replay_documents=...)` → 材料 `match()` | 复用原 PDF 的保存 OCR 与检验记录，重新匹配；不执行新 OCR |

`workflow.py` 管理通用生命周期；钢筋字段、业务关系和统计规则由 `materials/rebar/` 决定。`worker.py` 和现有 `extraction/` 的部分实现仍使用钢筋模板；新增材料可以提供自己的提取过程。

## `matching/catalog.py` 与当前匹配规则的区别

当前网页的四表关联判定入口是 **`materials/rebar/matching.py:rematch()`**，初始自动捆绑入口是 **`review/associations.py:prepare_associations()`**。

`matching/catalog.py` 保留历史通用关系、五表和日期匹配研发代码，也提供当前流程仍复用的 `build_keyword_catalog()` 字段目录构建工具。`materials/rebar/review.py` 会调用该工具，因此该文件仍属于运行代码并随包交付；其中历史匹配分支不能当作网页正在使用的规则。

## 修改功能时从哪里开始

| 要改的功能 | 优先查看的文件 | 修改边界 |
| --- | --- | --- |
| 新材料接入 | `materials/base.py`、`materials/registry.py`、`materials/rebar/adapter.py` | 实现 `extract()`、`match()`、`statistics()`，需要填表时提供 `form_writer()`；直接注册或用 `material_ocr.materials` 插件入口 |
| 新材料规则与表格 | 新建 `materials/<材料>/`，参考 `rebar/config/` 和 `materials/examples/` | 材料自行定义字段、版式、匹配关系和统计单位；规则变化应更新材料指纹以影响缓存 |
| 检验页没找到 | `materials/rebar/routing.py`、`extraction/batch.py` | 区分页头分类、方向、模板几何和明细 OCR 问题，使用已有逐页诊断定位 |
| 检验表版式变化 | `rebar/config/inspection_*.json`、`extraction/table.py`、`alignment.py` | 改表体和单元格几何；新增支持版式还需同步适配器、CLI 和工作台选项 |
| 附件分类、同页拆分 | `ocr/attachments.py`、`ocr/layout.py`、`materials/rebar/review.py` | 区分原始全页分类、独立实体/物理行及匹配前分类修正 |
| 附件重点字段 OCR | `rebar/config/attachment_rules.json`、`ocr/attachments.py`、`ocr/layout.py` | 改关键词、区域和重试，保留原文、页码、实体、物理行及坐标 |
| 质证编号及 `No.` 召回 | `materials/rebar/review.py:certificate_identifiers()`、`materials/rebar/filling.py` | 匹配编号召回和台账字段候选分别处理；多个原文值保留待核验 |
| 同炉批、多路径、重量/规格约束 | `materials/rebar/matching.py` | 修改 `rematch()`、`constrain_shared_heat()` 与同行字段冲突判断；保持证据和被排除候选 |
| 缺失单候选不全 | `materials/rebar/matching.py` | 查看 `manual_inventory()`、`rank_manual_candidates()`；分类成功但字段缺失的页仍应可供人工选择 |
| 自动捆绑或重复库存占用 | `review/associations.py`、`review/review_state.js`、`filling/ledger.py` | 同步后端初始捆绑、浏览器状态与服务端可信校验，铭牌/送货行按独立物料管理 |
| 台账列与字段来源 | `materials/rebar/filling.py` | 查看 `COLUMNS`、`build_filling_profile()` 及材料字段提取方法 |
| 台账核验和导出限制 | `filling/ledger.py`、`filling/excel.py`、`web/app.py` | 来源重建、必填/日期/数量、版本签名、导出行筛选与溯源工作表 |
| 上传/任务工作台 | `web/static/`、`web/app.py`、`web/tasks.py` | 上传交互、轮询、API、串行队列和缓存规则 |
| 匹配/台账审核页面 | `review/templates/same_page.html`、`review/*.js` | 这套页面独立于上传工作台；模板及 JS 在生成结果时复制到输出目录 |
| GPU 参数、失败重试 | `materials/rebar/adapter.py`、`worker.py`、`ocr/attachments.py` | 查看阶段隔离、附件分页批量、逐页检查点和 OOM 降批量重试 |
| 包发布缺静态资源 | `pyproject.toml`、`paths.py` | 配置 JSON、HTML、JS、CSS 都属于包资源；新增资源同步 package-data |

审核页是在生成匹配结果时输出的静态文件。只修改 `src/material_ocr/review/` 不会自动改写已生成的 `runs/.../review/`；要应用新审核模板/匹配规则，可基于同 PDF 保存证据使用 `replay` 生成新目录。代码或规则改变后应重启网页服务，使服务使用新的代码指纹和缓存键。

`crop_fusion.py` 用于已有区域的重识别/融合研发路径；日常新 PDF 上传所调用的附件 OCR 主路径是 `attachments.py`，它们不能混写成同一个执行入口。

## 交付代码与本地保留内容

| 内容 | 位置 | 用途与 Git 边界 |
| --- | --- | --- |
| 业务实现 | `src/material_ocr/` | 完整提交，包括钢筋规则、材料接口及网页资源 |
| 安装与当前说明 | 根目录四个入口文件及上述 `docs/` 文档 | 提交，供接收方安装、运行和核验 |
| 回归与诊断工具 | `tests/`、`tools/` | 本地保留，不在本次运行交付范围 |
| 研究设计、摘要和运行登记 | `experiments/` 全目录 | 本地保留，不提交，包括方案、分析、结果摘要、脚本和运行档案 |
| 历史交接和迁移说明 | `docs/history/`、`docs/MIGRATION.md` | 本地保留，不提交 |
| 历史模型清单和权重 | `models/` | 本地保留，不提交；接收方首次运行下载到指定缓存目录 |
| 本地输入和结果 | `runs/`、`data/`、业务 PDF、格式参考 Word | 本地保留，不提交，包括扫描件、OCR 文本/图像、审核备份、导出台账和审计 |

接收方启动后自动创建任务与结果目录；模型缓存按 `--model-cache` 指定路径使用，没有缓存时需要下载模型。源代码中的 `workflow.py` 仍会在每次结果目录下生成 `experiment/` 运行元数据及代码快照，用于排查该次任务。这些新产物留在接收方本地，不要求存在仓库顶层的 `experiments/`。

`runs/web/job-*/documents/file-*/` 内主要有 `work/`、`review-inputs/`、`review/`、`experiment/`、`summary.json` 和 `statistics.json`；原上传与日志位于同任务的 `inputs/`、`logs/`、`executions/`。命令行 `analyze --out` 和 `replay --out` 的目录由使用者指定。

浏览器人工状态也属于本地数据：它以 PDF 校验值保存于浏览器缓存，可下载 JSON 备份；服务器快照位于对应 `review/review_states/`，Excel 与审计位于 `review/exports/`。这些文件不属于源码。`.gitignore` 不会取消已经跟踪文件的提交；准备 GitHub 提交时应按 [提交说明](GITHUB_SUBMISSION.md) 核对暂存清单，确保本地目录没有进入交付范围。
