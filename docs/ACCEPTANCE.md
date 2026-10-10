# 接收方运行与核验

本文给接收方执行。仓库交付运行代码和说明；开发者的 PDF、实验记录、已处理数据与审核缓存不随代码提供。以下步骤是待执行的核验要求，不代表已在接收方机器通过。

## 1. 准备环境

建议建立独立 Python 3.10 环境：

```bash
conda create -n material-ocr python=3.10
conda activate material-ocr
```

已有合适环境可以直接使用。在仓库根目录安装项目：

```bash
python -m pip install -e .
```

还需安装 Paddle 计算后端。GPU 按本机 CUDA / GPU 兼容版本安装，开发环境的 CUDA 12.9 命令可参考 [README](../README.md)；仅 CPU 时：

```bash
python -m pip install paddlepaddle
```

一个环境选用对应的 GPU 或 CPU 后端。模型不随代码分发，首次识别需联网下载；下载后位于指定缓存目录。

检查安装和材料入口：

```bash
python -m material_ocr --help
python -m material_ocr materials
python -m pip check
```

预期 CLI 正常显示，钢筋已启用，钢梁 / 混凝土待接入。环境依赖冲突先处理，不将安装成功当作业务准确性通过。

## 2. 启动工作台

GPU：

```bash
python -m material_ocr serve --port 8080 --data-dir runs/web \
  --model-cache models/paddlex_cache --review-library runs
```

CPU：

```bash
python -m material_ocr serve --port 8080 --data-dir runs/web \
  --model-cache models/paddlex_cache --review-library runs \
  --device cpu --profile complete
```

保持终端运行，Chrome / Edge 打开 `http://localhost:8080`。新克隆首页无任务是正常状态。记录此次代码 commit、Python / Paddle / GPU 版本与所用 PDF 文件，方便重现问题。

## 3. 核验自己的 PDF

选择钢筋与自动版式，上传一份包含检验记录、质量证明书、铭牌、送货单和报审表的 PDF。当前已支持六行 / 十一行检验表，未知版式可出现明确失败提示。

|核验阶段|操作与检查|通过条件|
|---|---|---|
|输入与任务|检查文件名、任务进度、状态和日志|正确保存输入，完成或清楚报告失败原因|
|检验记录|打开「检验记录原图」逐页核对标题、目标页和明细|目标页正确，规格、进场量、证书号与原图一致或留出明确复核|
|附件分类|对照 `work/attachments/attachment_index.json` 与 `review-inputs/recognition_results.json`|质证书、铭牌、送货角色正确，混合页可同时具有多角色|
|编号与字段|检查原文、候选与坐标|不同证书编号原文保留，缺字母 / 点号差异可人工核验|
|四表关系|沿检验质编号 → 证书炉批 → 铭牌 → 同页送货行逐组检查|唯一正确关联自动捆绑，缺失 / 多解 / 矛盾进入复核|
|多路径约束|如样本存在相同炉批的多张附件，核对数量、同行规格和重量|不串行，不用合计或件重代替目标重量，矛盾不静默确认|
|人工候选|查看未匹配证书、铭牌和送货清单|分类成功但编号缺失的表单仍可选|
|库存更新|确认一组，查看后续候选，再解除本组|已用铭牌 / 送货行退出，解除后恢复；证书共用需核验|
|审核恢复|下载审核 JSON、刷新；需要时在同 PDF 页重新导入|最新捆绑及字段审核可恢复，不覆盖原 OCR|
|台账字段|选报审来源、核对独立铭牌和送货物理行，确认本行|必填完整，文件编号可空，数量单位为 t，一独立铭牌一行|
|字段确认有效性|如需核验，改变关联或解除再查看台账|旧字段确认失效，需要重新核对|
|CSV|点击「下载捆绑清单 CSV」|内容与当前捆绑相符，清楚是关联清单|
|XLSX|点击「导出已确认行 Excel」|已确认有效行正确，未确认行提示；含台账及字段溯源两表|

只对样本实际包含的情况给出观测结论。样本没有多路径、缺编号或混合页时，将对应核验项标为“未覆盖”，不要视为通过。严重遮挡无法确认的字段留待补正，禁止为完成导出而猜值。

## 4. 记录和交回核验意见

接收方自行保存输入和结果，不需要把业务资料提交 GitHub。程序产物在 `runs/web/job-*/documents/file-*/`，每次导出审计在 `review/exports/`。建议核验意见包含：

- 代码 commit、环境版本、GPU / CPU 模式、样本名称与页数、任务 ID。
- 已通过、失败和未覆盖的核验项。
- 错误页码、检验记录 ID、字段原文和预期关联。
- 相应的任务 / 阶段日志与必要原图证据。
- 本次导出行数、仍待匹配组数、未确认或遮挡字段。
- 下载的审核 JSON、CSV、Excel 和对应审计记录位置。

这些记录在接收方本地保存，需要沟通时另行交接。出现「未找到检验记录页」先查分类，出现「已找到但提取失败」查表格定位；编号缺失按分类、OCR 原文、字段提取逐层排查。完整排错与操作见 [网页说明](WEB_USAGE.md)。
