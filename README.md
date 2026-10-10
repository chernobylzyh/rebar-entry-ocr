# 材料表单 OCR 工作台

在本地网页上传 PDF 或文件夹，完成表单分类、OCR、四表匹配、原图人工审核和材料台账导出。当前钢筋流程已跑通；钢梁、混凝土提供材料接口与配置示例，接入真实样本并验证后启用。

**主流程：上传 PDF → 检验记录与附件 OCR → 分类/字段目录 → 四表匹配与捆绑审核 → 捆绑 CSV / 审核 JSON；已捆绑物料 → 台账字段核验 → 台账 XLSX。**

[完整流程](docs/WORKFLOW.md) · [网页操作](docs/WEB_USAGE.md) · [代码地图](docs/CODE_MAP.md) · [GitHub 提交说明](docs/GITHUB_SUBMISSION.md)

## 安装和启动

在仓库根目录，使用现有 `ocr` conda 环境：

```bash
conda activate ocr
python -m pip install -e .
python -m material_ocr serve --port 8080 --data-dir runs/web \
  --model-cache models/paddlex_cache --review-library runs
```

安装命令在首次使用或依赖变化时执行。看到 `Uvicorn running on http://127.0.0.1:8080` 后，保持终端运行，浏览器打开 **[http://localhost:8080](http://localhost:8080)**；按 `Ctrl+C` 停止。Chrome / Edge 支持目录及子目录 PDF 选择。

开发环境参考：Python 3.10、PaddleOCR 3.3.2、PaddleX 3.3.13、GPU Paddle 3.4.0 / CUDA 12.9、RTX 5070 Ti；项目依赖见 [pyproject.toml](pyproject.toml)。项目安装不替换已有 Paddle 计算后端。

全新机器需另装适配硬件的 Paddle 后端。当前 Linux / RTX 5070 Ti 环境已使用以下 GPU 安装命令；其他 CUDA 环境按 Paddle 官方兼容版本安装：

```bash
python -m pip install paddlepaddle-gpu==3.4.0 \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cu129/ \
  --extra-index-url https://pypi.org/simple
```

CPU 环境安装 `paddlepaddle`，启动时加 `--device cpu --profile complete`。首次使用没有本地缓存的模型时需要下载，权重不随仓库分发。

## 网页使用

1. 选择「钢筋」与「自动选择支持的版式」，选择 PDF / 文件夹，点击「开始识别与匹配」。
2. 等待任务完成，点击「查看匹配与审核」；分类、逐格提取失败时查看「检验记录原图」和「运行日志」。
3. 唯一且无待核验项的四表自动捆绑。其余在「待补全 / 待复核」中核对质证书、铭牌、送货单候选和原图，点击「人工确认并捆绑四表」。
4. 下载审核 JSON 备份或四表捆绑 CSV；已用铭牌、送货行退出剩余候选，允许解除捆绑重新选择。
5. 在「自动填表 · 材料报审台账」选择报审信息来源，核对 / 补正字段，点击「确认本行字段」，再「导出已确认行 Excel」。

匹配确认与台账字段确认分别保存。改选表单或提取版本变化后，旧字段确认失效。钢筋台账以一个独立铭牌为一行：报审表提供材料名称、使用部位、供货日期和可空文件编号；铭牌提供规格、炉批号和生产单位；送货单提供供应单位与对应物理行重量；质证书提供质保书编号。

|导出|用途|
|---|---|
|审核 JSON|保存当前关联、人工记录、字段审核与剩余候选，可导入恢复|
|四表捆绑 CSV|当前已捆绑关联的页码、编号观察、送货行与原进场量|
|材料台账 XLSX|仅导出字段已确认行，含「材料台账」「字段溯源」|
|磁盘 `match_results.csv`|生成时的自动候选快照，人工确认不会回写|

完整十列台账当前导出为 XLSX；需要台账 CSV 时可将「材料台账」工作表另存为 UTF-8 CSV。当前没有独立台账 CSV 按钮。

## 已实现能力与边界

|能力|当前状态|
|---|---|
|PDF 多选、目录、拖放、任务进度与结果查看|已实现；每批最多 100 份、单份 256 MB、整批 1 GB；每 PDF 独立匹配，GPU 任务串行|
|钢筋检验表|六行 / 十一行自动几何选择，有限列宽漂移适配，失败诊断保留|
|附件 OCR 与分类|全页方向校验、同页铭牌 / 送货实体拆分、字段原文 / 坐标证据|
|四表关系|优先质证编号 → 质证书炉批号 → 铭牌；铭牌 / 送货单双向同页补全|
|多路径与字段冲突|进场数量对送货行重量消歧；重量不清晰时同行规格辅助；清晰矛盾继续复核|
|缺失单候选和人工审核|包含未提取编号 / 炉号的分类页，逐组捆绑更新库存；编号差异保留复核|
|审核后台账|钢筋十列字段、必填校验、补正确认、Excel 与字段溯源|
|其他材料|材料提取 / 匹配 / 统计 / 填表接口已建，钢梁 / 混凝土真实能力待接入|

默认 `gpu:0` 与 `batched_gpu`；附件识别 batch 32，每五页独立进程、逐页检查点，OOM 时 batch 6 重试未完成页。服务重启保留成功结果并将未完成任务记为中断，当前不支持跨服务自动续跑。严重遮挡、任意新版式与自定义 Excel 模板仍需扩展和人工验证。

材料统计注明单位与重复来源，原始记录累计不能直接视为去重进场总量。候选齐全不等于识别准确率。

## 工程结构

```text
src/material_ocr/
  cli.py / workflow.py    公开入口、通用流程与运行记录
  worker.py / processes.py 独立识别阶段、进程清理
  web/                    上传工作台、FastAPI、任务队列与缓存
  materials/              材料接口、注册、钢筋业务规则与配置
  extraction/             检验表定位、单元格与逐页提取
  ocr/                    附件 OCR、方向、实体 / 物理行与证据
  matching/               字段目录复用与历史关系研发工具
  review/                 四表捆绑、候选清单、原图审核与浏览器状态
  filling/                台账校验、Excel 和溯源导出
docs/                     使用、流程、架构、代码地图与接收方核验说明
```

本仓库只交付运行代码、包内规则/模板/网页资源、安装配置和当前说明。实验方案与结果、研发工具、测试、历史文档、模型清单、业务扫描件和已有 OCR / 审核 / 导出结果留在开发者本地，不提交。接收方首次运行会创建自己的模型缓存和任务目录。钢筋算法与配置位于 `materials/rebar/`，随运行代码交付。

逐文件职责与修改位置见 [代码地图](docs/CODE_MAP.md)。新增材料实现 `MaterialAdapter.extract()/match()/statistics()`，需要台账时提供 `form_writer()`；注册后网页读取材料及版式选项，业务规则在材料目录独立定义，见 [材料接入](docs/MATERIALS.md)。

## 命令行与接收方核验

```bash
# 完整 OCR；输出目录必须尚不存在
python -m material_ocr analyze --pdf data/input.pdf --out runs/new_analysis --material rebar

# 复用同 PDF 的已保存记录和完整 OCR 索引，只重新匹配
python -m material_ocr replay --pdf data/input.pdf \
  --records runs/source/work/inspection/records_all_pages.json \
  --index runs/source/work/attachments/attachment_index.json \
  --out runs/new_replay --material rebar

python -m material_ocr materials
python -m material_ocr --help
```

网页产物位于 `runs/web/job-*/documents/file-*/`；审核页位于 `review/index.html`。保存分类、原记录、OCR 索引、候选库存、日志、配置与源码快照。`--review-library runs` 可发现已有审核结果，并将任务入口链接到同 PDF 的最新回放；修改规则或审核模板后，使用 `replay` 生成新结果并重启服务。

接收方按 [运行与核验说明](docs/ACCEPTANCE.md) 在自己的环境安装后端、上传自己的 PDF，检查分类、四表关联、候选库存、台账字段与导出。既有样本结果不随代码交付，具体运行和核验结论由接收方保存。

## 文档与交接

|文档|用途|
|---|---|
|[完整流程](docs/WORKFLOW.md)|各阶段输入 / 输出、匹配规则、两步审核和导出|
|[网页使用](docs/WEB_USAGE.md)|启动、打开结果、操作与常见问题|
|[代码地图](docs/CODE_MAP.md)、[架构](docs/ARCHITECTURE.md)|目录、函数入口与维护职责|
|[材料扩展](docs/MATERIALS.md)|钢梁、混凝土及其他材料接入接口|
|[GitHub 提交](docs/GITHUB_SUBMISSION.md)|提交范围、忽略本地数据、暂存 / commit / push 命令|
|[当前交接](docs/HANDOFF.md)、[接收方核验](docs/ACCEPTANCE.md)|交付内容、运行前提与核验步骤|

浏览器审核缓存按协议、域名和端口隔离；下载审核 JSON 后可在同 PDF 页面导入恢复。运行时会自动在本地任务目录保存输入哈希、配置、日志与运行状态，不依赖开发者的实验目录。
