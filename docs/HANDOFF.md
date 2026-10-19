# 运行代码交接

交付内容为 Vue 前端、Java 业务服务、Python OCR 与钢筋自动匹配代码，以及安装、使用和接收方核验说明。业务扫描 PDF、模型权重与缓存清单、OCR 和台账结果、实验方案与运行记录不随代码交付。

## 当前流程与交付范围

主流程为：上传 PDF → 整卷 OCR 与自动四表匹配 → 查看 12 列台账及字段证据 → 集中补正和核验关键字段 → 导出 Excel。候选用于解释自动匹配结果，匹配过程无需逐组人工捆绑。

- Vue 工作台提供上传、历史记录、单卷结果、总台账、原图定位与字段编辑。
- Java 服务协调 Python 接口，保存文件和历史摘要，执行最终核验与导出约束。
- Python 服务提供 OCR、材料字段提取和钢筋匹配规则；缺失、冲突、识别不清或多候选保留诊断。
- Excel 包含「台账」和「字段溯源」两张工作表，保留字段页码、证据和诊断。
- 其他材料保留扩展入口，业务规则与真实材料接入需另行完成验证。

台账的 12 个业务字段为：供应商是否报审、文件编号、材料名称、规格品种、生产单位、供应单位、供货日期与工程材料报审签认日期、使用部位、送货单编号、炉批号、验收数量、质保书编号。数量单位为吨。缺少必填项或数量无效时不能完成最终核验；修改字段或重新识别后须重新核验。人工补正保留原始观察，不将补正值标为 OCR 识别结果。

当前 Vue 默认 `local-glm`，可选 `local-paddle`。全新环境还需准备 GLM 独立解释器及权重，按 [GLM 环境准备](GLM_OCR.md#模型与环境) 操作；`pip install -e .` 不包含这些推理依赖。

## 运行环境与启动

接收方需准备 Python 3.10 或以上与兼容的 Paddle 后端、JDK 17 和 Maven、Node.js 20.19 或以上与 npm。前端推荐 Node.js 24 LTS。模型不包含在仓库内，需准备可用模型缓存或允许首次使用时下载；GPU 模式需与设备和 CUDA 环境兼容，CPU 可使用完整处理配置。

在 Python 环境中先执行 `python -m pip install -e .`。之后从仓库根目录分别在三个终端启动：

```bash
# Python OCR：8000；CPU 增加 --device cpu --profile complete
python -m material_ocr serve --port 8000 --data-dir runs/web \
  --model-cache models/paddlex_cache
```

```bash
# Java 业务服务：8080；WSL/Linux 使用 Linux JDK
OCR_BASE_URL=http://127.0.0.1:8000 bash 前端/bin/start-local.sh
```

```bash
# Vue：5173，以终端实际地址为准
cd 前端/vue
npm ci
npm run dev
```

浏览器访问 `http://localhost:5173`。Vue 将业务请求转发到 Java 的 8080，Java 通过 `OCR_BASE_URL` 连接 Python 的 8000。首次运行需要安装依赖并准备模型；已安装环境的后续启动可跳过依赖安装。

`start-local.sh` 使用本地 H2 配置，无需安装 MySQL；它仍要求接收方安装 JDK 与 Maven，不依赖随代码分发的开发机工具。MySQL 部署与生产构建以[仓库 README](../README.md)为准，修改数据库配置时须准备对应表结构。

## 数据与维护入口

| 路径 | 用途 |
| --- | --- |
| `前端/vue/src/` | Vue 页面、接口封装与状态管理。 |
| `前端/java/business/src/` | Java 接口、业务约束、历史摘要与 Excel 导出。 |
| `前端/bin/start-local.sh` | WSL/Linux 本地 Java 启动入口。 |
| `src/material_ocr/web/` | Python 服务与前端适配接口。 |
| `src/material_ocr/materials/rebar/` | 钢筋字段提取、自动匹配及核验规则。 |
| `src/material_ocr/ocr/` | OCR 与附件信息处理。 |
| `runs/web/` | 启动命令指定的 Python 运行数据目录。 |
| `前端/image/` | Java 保存的输入文件、图片、OCR 缓存与台账。 |
| `前端/runtime/h2/` | 本地历史数据库。 |
| `前端/java/business/logs/run.log` | Java 日志。 |

模型缓存目录由 `--model-cache` 指定。以上运行数据和缓存由接收方管理，不能当作源码提交。迁移本地数据时一并保留 Python 数据、Java 文件数据和对应历史数据库；复制 H2 文件前先停止 Java。H2 与 MySQL 相互独立，不会自动迁移数据。

## 接收方核验与边界

按[接收方运行与核验](ACCEPTANCE.md)检查安装、服务链路、自己的业务材料、最终核验、Excel 内容和重启后的数据持久化。记录通过、失败和未覆盖项，反馈可复现的操作与必要日志。仓库可安装或服务可启动，不等于接收方业务材料的字段准确性已经通过。

模糊扫描、手写内容、缺失附件、冲突来源及未知版式仍需依据诊断补正。不得为完成核验猜测业务字段，也不能将单份材料的验证结论扩大到未覆盖的材料或版式。交接中不包含已有处理任务或人工核验结论；接收方使用自己的输入与数据目录完成核验。
