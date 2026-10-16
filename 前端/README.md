# 前端工作台

Vue 3 + Vite 5 + Element Plus 提供界面，Spring Boot 2.7.18 提供业务接口，Python 提供 OCR 与自动匹配。完整环境准备和三服务启动方式见 [仓库 README](../README.md)。

从仓库根目录启动 Java（需要 JDK 17+ 与 Maven）：

```bash
OCR_BASE_URL=http://127.0.0.1:8000 bash 前端/bin/start-local.sh
```

该脚本使用文件型 H2，无需 MySQL；数据库位于 `runtime/h2/`，上传文件位于 `image/library/`。Python 服务需另行启动在 8000。

另开终端启动界面（Node.js 20.19+，推荐 `vue/.nvmrc` 指定的 24）：

```bash
cd 前端/vue
npm ci
npm run dev
```

访问终端显示的地址，默认 http://localhost:5173。`/api` 与 `/image` 代理到 Java 的 8080；无需额外 `.env` 文件。需要其他设备访问时，在 `npm run dev` 后增加 `-- --host 0.0.0.0`。

在 `vue/` 执行 `npm run build`，产物输出到 `../dist/`。Java 的 `local` 配置可托管该目录，构建后重启 Java 即可访问 http://localhost:8080。
