# 代码与文档提交范围

交付包含运行代码、配置、依赖锁文件和通用说明。业务输入、模型缓存、OCR 解析结果和实验记录保留本地。运行方式见 [README](../README.md)，交付检查见 [接收方核验](ACCEPTANCE.md)。

## 随仓库保存

|路径|作用|
|---|---|
|`README.md`、`docs/` 当前说明|环境、流程、匹配规则、接口、交接和核验步骤|
|`pyproject.toml`、`requirements.txt`|Python 安装入口与依赖|
|`.gitignore`、`前端/.gitignore`|本地数据、模型、依赖和产物排除规则|
|`src/material_ocr/`|OCR、材料配置、匹配、台账和 Python 接口|
|`前端/vue/`|Vue 源码、Vite 配置、Node 版本和依赖锁文件|
|`前端/java/business/pom.xml`、`前端/java/business/src/main/`|Java 源码、依赖与运行配置，含本地 H2 配置|
|`前端/bin/start-local.sh`|Linux/WSL 本地启动入口|
|`前端/sql/init.sql`|MySQL 可选部署的初始化表结构|
|`前端/README.md`|前端环境、开发与构建说明|

Python 包内的规则 JSON、模板、HTML、JS 和 CSS 属于运行资源，随源码交付。钢筋业务实现也属于运行代码，不因业务 PDF 留在本地而删减。

## 保留本地

- 模型权重、缓存和清单：`models/`、`.paddlex/` 等。
- PDF、页面图、OCR 原文和索引、自动匹配、审核、台账及导出文件：`runs/`、`data/`、`钢筋报审文件/`、`前端/image/library/`、`前端/image/documents/` 等。
- 实验方案、运行登记、结果摘要和历史研发资料：`experiments/`、`docs/history/`、`docs/MIGRATION.md`。
- 开发工具、调试测试和本地环境：根目录 `tools/`、`tests/`、虚拟环境、`node_modules/`、Maven 缓存和本地 JDK。
- 本地 H2 数据库、日志、JAR、Java `target/`、Vue `dist/` 和其他构建产物。
- 调试解包目录、临时 Excel 和其他处理产物。

README、接口、交付说明可以提交；含具体样本 OCR 结果、实验结论或开发机模型缓存明细的文档不在交付范围。忽略规则不会自动移除已被跟踪的文件，提交前仍需检查清单。不要使用强制加入来绕过这些规则。

## 本地检查和提交

在仓库根目录检查分支和差异：

```bash
git branch --show-current
git status --short
git diff --stat
```

按实际改动显式暂存路径。例如仅保存本轮文档：

```bash
git add -- README.md 前端/README.md docs/AUTOMATIC_LEDGER.md \
  docs/HANDOFF.md docs/ACCEPTANCE.md docs/WEB_USAGE.md \
  docs/WORKFLOW.md docs/GITHUB_SUBMISSION.md
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
git commit -m "Document frontend setup and delivery workflow"
```

已有前端文件使用 Windows 换行时，可用 `git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check` 检查空白。

本地 commit 不会自动推送到远端或合并到 main。准备同步 main 前，检查当前分支提交及工作区中未提交、未跟踪的内容；远端推送和分支合并另行执行。

新克隆不包含开发者的任务和核验数据。接收方准备 Python/Paddle、JDK/Maven 和 Node 环境后，按三服务流程上传自己的 PDF 核验。数据迁移应单独处理，不通过源码提交传递。
