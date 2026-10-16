# 报审表 OCR 台账提取

当前使用 `前端/` 中的 Vue + Spring Boot 工作台，Python 提供本地 OCR 与自动匹配服务。目标流程：**上传 PDF → 自动提取和四表匹配 → 集中核验最终台账字段 → 导出 Excel**。匹配过程中不要求人工选择、捆绑或确认候选。

详细规则与接口见 [自动台账说明](docs/AUTOMATIC_LEDGER.md)。当前界面位于 `前端/vue`，旧 Python 静态网页退出主流程；CLI 保留诊断和回放能力。

## 环境准备

需要 Python 3.10+、JDK 17+、Maven 和 Node.js 20.19+（推荐 24 LTS，见 `前端/vue/.nvmrc`）。JDK 和 Maven 须加入 PATH；WSL/Linux 使用 Linux JDK。

已有 `ocr` conda 环境可直接激活；新机器先建立合适的 Python 环境，再在仓库根目录安装项目：

```bash
python -m pip install -e .
```

Paddle 计算后端需按硬件另行安装，参见 [Paddle 安装说明](https://www.paddlepaddle.org.cn/install/quick)。CPU 使用 `paddlepaddle`，GPU 使用与 CUDA 兼容的 `paddlepaddle-gpu`。首次识别会按需下载模型；模型权重和缓存清单不随仓库分发。

## 启动

三个终端分别启动下列服务。已有 `ocr` 环境和 `models/paddlex_cache` 缓存可以直接复用。

```bash
# 仓库根目录，Python OCR 服务，默认使用 gpu:0
# 使用已有 conda 环境时，先执行 conda activate ocr
python -m material_ocr serve --port 8000 --data-dir runs/web \
  --model-cache models/paddlex_cache
```

```bash
# 仓库根目录，Java 业务服务，监听 8080
export OCR_BASE_URL=http://127.0.0.1:8000
bash 前端/bin/start-local.sh
```

本地运行使用上述脚本，无需启动 MySQL。脚本使用 `application-local.yml`，数据库保存在 `前端/runtime/h2/`，文件和构建产物固定使用 `前端/image/`、`前端/dist/`，日志为 `前端/java/business/logs/run.log`。脚本优先使用 `JAVA_HOME`，也可自动复用已存在于 `tools/local-java/jdk17/` 的 Linux JDK；Windows 的 `java.exe` 不能直接作为 Linux Maven 的 Java。其他机器需要 JDK 17+ 和 Maven。首次启动需要联网下载 Maven 依赖，已缓存后可在命令末尾添加 `-o` 离线启动。停止服务按 `Ctrl+C`。

```bash
# Vue 开发服务，浏览器访问终端显示的地址（默认 http://localhost:5173）
cd 前端/vue
npm ci
npm run dev
```

可选的 MySQL 部署方式：先按实际环境配置 `application.yml` 的数据库连接并初始化表结构，再使用以下命令替代本地 Java 启动脚本。表结构见 [初始化 SQL](前端/sql/init.sql)，连接配置见 [application.yml](前端/java/business/src/main/resources/application.yml)；`ddl-auto=validate` 要求数据库表已存在。本地 H2 数据保存在独立文件中，不会自动迁移到 MySQL。

```bash
# 仓库根目录，使用已有 MySQL 启动 Java 业务服务
cd 前端/java/business
OCR_BASE_URL=http://127.0.0.1:8000 mvn spring-boot:run
```

Java 项目实际使用 Spring Boot **2.7.18**，编译目标 Java 8；建议使用兼容的 JDK 17 或 21，并配置 Maven。默认部署配置依赖 MySQL，仓库中的示例账号需要按实际情况配置；本地 `local` 配置使用 H2，无需外部数据库。Vue 开发代理转发 `/api` 到 Java 的 8080；Python 默认以此处命令指定的 8000 提供 OCR。CPU 启动增加 `--device cpu --profile complete`。

生产构建使用 `cd 前端/vue && npm run build` 和 `cd 前端/java/business && mvn package`；Java 的 `file.frontend` / `file.root` 相对其启动目录解析，需要按部署路径设置。不要直接运行未重新构建的旧 JAR，否则不会包含本次接口与核验约束。

## 使用

1. 在当前前端上传 PDF，点击整卷识别。使用本地 PaddleOCR，按规则自动匹配。
2. 查看最终台账；缺失、识别不清晰、信息冲突、重复和多候选均保留原因。点击单元格或诊断的页码，查看对应 PDF 渲染图及定位框；双击单元格补正。
3. 集中核对关键字段后点击「核验关键字段」，再导出 Excel。缺失必填项不能确认；修改字段或重新识别后须重新核验。匹配候选只用于此阶段查看证据。
4. Excel 包含「台账」和「字段溯源」，后者保留页码、原始坐标证据和诊断。核验保留原 OCR 观察，不会把人工补正伪装成 OCR 命中。

当前台账为前端约定的 12 列。「供应商是否报审」「送货单编号」没有可靠来源时留空并提示，不自动猜测。数量单位为吨；不累加重复进场记录，不擅自修改质证编号或炉批号。

## 功能边界与交付

扫描模糊、手写送货单、缺失铭牌及未见版式仍可能产生未完整匹配的行，全部进入最终字段核验。其他材料保留适配接口，实际业务能力需另行接入和验证。

交付包含运行代码、配置、依赖锁文件和使用说明。业务 PDF、OCR 原文与图像、审核和导出结果、实验记录、模型缓存、本地依赖和构建产物均保留在运行者本地。

[运行交接](docs/HANDOFF.md) · [接收方核验](docs/ACCEPTANCE.md) · [网页操作](docs/WEB_USAGE.md) · [完整流程](docs/WORKFLOW.md) · [提交范围](docs/GITHUB_SUBMISSION.md)
