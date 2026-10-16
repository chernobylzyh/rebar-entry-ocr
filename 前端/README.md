# 前端工作台

Vue 3 + Vite 5 + Element Plus 提供界面，Spring Boot 2.7.18 提供业务接口，Python 提供本地 OCR 与自动匹配。完整流程和三服务启动方式见 [仓库 README](../README.md)，规则和接口见 [自动台账说明](../docs/AUTOMATIC_LEDGER.md)。

## 环境与目录

需要 Node.js 20.19+（推荐 `vue/.nvmrc` 指定的 24）、npm、JDK 17+ 与 Maven。Linux/WSL 使用 Linux JDK；Java 编译目标为 Java 8。

|路径|用途|
|---|---|
|`vue/`|Vue 源码、Vite 配置和依赖锁文件|
|`java/business/`|Java 源码、POM 和 Spring 配置|
|`bin/start-local.sh`|Linux/WSL 本地启动入口|
|`sql/init.sql`|可选 MySQL 部署的初始化表结构|
|`dist/`|前端构建产物，由构建生成|
|`runtime/h2/`|本地 H2 数据库，由运行生成|
|`image/library/`|上传文件、页面、OCR 和台账，由运行生成|

## 启动

先按仓库 README 启动 Python OCR 服务在 8000。从仓库根目录启动 Java：

```bash
OCR_BASE_URL=http://127.0.0.1:8000 bash 前端/bin/start-local.sh
```

脚本监听 8080，使用 `application-local.yml` 和文件型 H2，无需 MySQL；优先使用 `JAVA_HOME`，也可复用已存在的项目本地 JDK。首次需要联网下载 Maven 依赖，缓存齐全后可追加 `-o`。日志位于 `java/business/logs/run.log`。

另开终端启动界面：

```bash
cd 前端/vue
# 使用 nvm 时，可先执行 nvm install && nvm use
npm ci
npm run dev
```

若已在 `前端/`，先执行 `cd vue`。依赖安装在 `vue/`，以此处的 `package.json` 和 `package-lock.json` 为准。无需额外 `.env` 文件。

访问终端显示的地址，默认 http://localhost:5173。Vite 将 `/api` 和 `/image` 代理到 Java 的 8080。WSL 或远程开发需从其他设备访问时，可追加 `-- --host 0.0.0.0`，使用对应主机 IP 与实际端口；端口被占用时以终端输出为准。

## 构建与数据库

在 `vue/` 执行 `npm run build`，产物输出到 `../dist/`。本地 Java 配置可托管该目录，构建后重启 Java，即可从 http://localhost:8080 访问。Java 在 `java/business/` 执行 `mvn package` 构建。

MySQL 为可选部署方式：先配置 [application.yml](java/business/src/main/resources/application.yml)，执行 [初始化 SQL](sql/init.sql)，再在 `java/business/` 执行 `OCR_BASE_URL=http://127.0.0.1:8000 mvn spring-boot:run`。H2 与 MySQL 数据分别管理，不自动迁移。

上传的 PDF、页面图、OCR 缓存、核验记录、数据库、日志和构建产物均保留本地，不随 Git 交付。
