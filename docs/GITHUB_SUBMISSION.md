# 最小运行版本的 GitHub 提交说明

本次只交付运行整个项目所需的代码、配置和当前说明。具体 PDF 上传、OCR、匹配及导出由接收方在自己的机器上核验，流程见 [接收方核验](ACCEPTANCE.md)。

## 提交范围

|路径|作用|
|---|---|
|`README.md`|项目能力、环境准备、安装和启动|
|`pyproject.toml`、`requirements.txt`|安装入口、依赖、CLI 和静态资源打包配置|
|`.gitignore`|本地输入、结果、研究资料和缓存的排除规则|
|`src/material_ocr/`|通用流程、OCR、网页、材料适配器、匹配、审核和台账导出|
|`docs/` 当前说明|流程、网页操作、架构、代码地图、材料扩展、交接、提交和核验|

整个 `src/material_ocr/` 保留，包括 `materials/rebar/` 钢筋算法、规则和模板。这些是实现当前钢筋 OCR、匹配和台账功能的必需代码。所谓“钢筋处理留在本地”指业务 PDF、OCR 数据、处理结果和审核/导出记录。

包内 HTML、JS、CSS 和 JSON 必须随代码提交，`pyproject.toml` 已声明它们的 package-data；不能只提交 Python 文件。

## 不提交且保留本地

`.gitignore` 排除下列目录和文件：

- `experiments/` 全部：方案、改动、分析、结果摘要、运行登记脚本和详细运行档案。
- `tools/`、`tests/`：本地研发诊断和回归代码，本次交付用接收方运行核验。
- `docs/history/`、`docs/MIGRATION.md`：历史说明和开发迁移记录。
- `models/`：本机模型清单及权重缓存。
- `runs/`、`data/`、业务 PDF、`钢筋报审文件/` 和本地格式参考 Word。
- OCR 原文/图像、四表关联、审核 JSON、浏览器记录备份、CSV、Excel 和日志等处理产物应统一置于 `runs/`。
- 虚拟环境、Python 缓存和构建产物。

本轮已将上述此前暂存的本地目录移出 Git 索引，文件仍完整保留在本机。`.gitignore` 本身不会取消已跟踪文件，已跟踪路径需要 `git rm --cached` 处理；本轮没有删除本地目录。

新克隆没有开发者业务样本和既有结果。接收方首次运行会创建模型缓存和本地任务目录，运行时在任务 `experiment/` 子目录保存配置和状态；它与不提交的顶层 `experiments/` 相互独立。

## 检查和提交

当前分支是 `phase2-form-matching`，已有远端 `origin`。本轮准备了提交范围及说明，未 commit 或 push。

在仓库根目录执行：

```bash
git branch --show-current
git status --short
git diff --check
git add --dry-run -A
```

确认忽略目录未出现在待加入清单，再更新暂存并检查：

```bash
git add -A
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

当前迁移会显示旧根脚本的删除及 `src/` 内新增，属于预期；不要为保留本地实验和测试而重新加入这些忽略目录。

完成代码范围检查后提交与推送：

```bash
git commit -m "Deliver runnable material OCR workbench and usage documentation"
git push -u origin phase2-form-matching
```

接收方按 [README](../README.md) 安装，按 [核验说明](ACCEPTANCE.md) 上传自己的样本。此次不分发开发者实验结论作为对方环境的核验结果，也不要求交接代码前重跑整份 PDF。

## 接收方获得什么

一个可安装的 Python 包和本地网页，包含已启用的钢筋业务实现、可扩展材料接口，以及使用/核验说明。GPU 或 CPU 的 Paddle 后端由接收方按硬件安装，首次使用需下载 OCR 权重，详见 README。

PDF、审核状态与导出台账不通过 GitHub 传递。若另有需求在另一台机器续用已有审核，可单独迁移同 PDF 的结果与下载的审核 JSON，不改变本次代码提交范围。
