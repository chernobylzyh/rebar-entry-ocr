# 报审表 OCR 工作台

Vue + Spring Boot 提供上传、原图查看、台账补正与导出，Python 提供本地 OCR 和四表自动匹配。当前支持钢筋流程：上传 PDF → 自动提取与匹配 → 核验最终字段 → 导出 Excel。

## 环境准备

需要 Python 3.10+、JDK 17+、Maven、Node.js 20.19+（推荐 24 LTS）和 npm。JDK 与 Maven 须加入 PATH；Linux/WSL 需要 Linux JDK。

在仓库根目录安装 Python 项目；已有 `ocr` conda 环境时先执行 `conda activate ocr`：

```bash
python -m pip install -e .
```

Paddle 计算后端需按硬件另行安装，参见 [Paddle 安装说明](https://www.paddlepaddle.org.cn/install/quick)。CPU 环境可安装 `paddlepaddle`，GPU 环境安装对应 CUDA 版本的 `paddlepaddle-gpu`。模型在首次识别时下载到本地缓存，已有缓存可复用。

## 启动

三个终端分别执行，前两组命令在仓库根目录运行。

```bash
# Python OCR，监听 8000；有 conda 环境时先 conda activate ocr
python -m material_ocr serve --port 8000 --data-dir runs/web \
  --model-cache models/paddlex_cache
```

默认使用 GPU。CPU 环境在上述命令末尾增加 `--device cpu --profile complete`。

```bash
# Java 业务服务，监听 8080
OCR_BASE_URL=http://127.0.0.1:8000 bash 前端/bin/start-local.sh
```

脚本使用 `local` 配置和文件型 H2，无需 MySQL。数据库保存在 `前端/runtime/h2/`，上传文件保存在 `前端/image/library/`。优先使用 `JAVA_HOME`；本地已有 `tools/local-java/jdk17/` 时可自动复用。首次运行需要联网下载 Maven 依赖，缓存齐全后可追加 `-o` 离线启动。

```bash
# Vue 开发服务
cd 前端/vue
npm ci
npm run dev
```

浏览器打开终端显示的地址，默认为 http://localhost:5173。Vite 将 `/api` 和 `/image` 代理到 Java 的 8080。各服务按 `Ctrl+C` 停止。

## 使用与匹配

上传 PDF 后执行整卷识别。存在质证编号时按编号关联质证书、炉批号和独立铭牌；缺少编号时按同一铭牌的牌号与直径匹配，再关联送货行和质证书。数量用于满足规格条件后的消歧，重复记录不累加。

缺失、歧义或冲突均保留诊断和来源，进入最终台账核验。点击字段查看来源页和定位框，双击补正；核验关键字段后才能导出。修改字段或重新识别后须重新核验。导出包含台账与字段溯源。

## 构建与可选数据库

`cd 前端/vue && npm run build` 输出到 `前端/dist/`；重启本地 Java 服务后可从 http://localhost:8080 访问构建页面。Java 在 `前端/java/business/` 执行 `mvn package` 构建。

如使用 MySQL，按实际环境配置 [application.yml](前端/java/business/src/main/resources/application.yml)，执行 [初始化 SQL](前端/sql/init.sql)，并在 `前端/java/business/` 执行 `OCR_BASE_URL=http://127.0.0.1:8000 mvn spring-boot:run`。默认 MySQL 配置要求表已存在；H2 数据不会自动迁移。

仓库仅包含代码、运行配置、依赖锁文件和启动说明。业务 PDF、解析和审核结果、实验记录、模型权重、本地依赖、日志及构建产物保留本地。
