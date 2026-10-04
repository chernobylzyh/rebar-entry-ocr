# 钢筋进场表 OCR（V6 基线）

第一阶段：从整份钢筋报审 PDF 筛选固定版式进场表，自动对齐网格，逐格 OCR，输出带来源证据的结构化草稿。第二阶段的附件检索关联尚未实现，接口见 [交接说明](HANDOFF.md)。

## 已实现

- 全PDF页头OCR分类、整页方向判断，不提前停止扫描。
- 固定11行8列模板的图像自动对齐及几何检查；异常停止，不强行套坐标。
- 单元格文字OCR、重量单位解析、厂家/证书号拆分、空白候选与证据保留。
- V6仅在固定表单元格OCR中禁止细长文字自动旋转；页头OCR及整页转正不受影响。
- 异常序号局部重试；必要时绕过检测器直接识别数字区域，保留原文及所有证据。
- 序号与核心字段状态分离；同PDF内按规格、重量、厂家、证书号列出重复候选，不自动删记录或求和。

## 环境

已使用的实验环境：Linux / AutoDL RTX 4090，Python 3.10，PaddleOCR 3.3.2，PaddleX 3.3.13，paddlepaddle-gpu 3.2.0，OpenCV 4.10.0.84，NumPy 1.26.4。具体依赖见requirements.txt。

GPU版Paddle须按机器CUDA兼容条件安装；requirements.txt不包含GPU Paddle。现有rebar-ocr环境可以直接复用。PaddleX是PaddleOCR依赖，复现实验时核对实际版本；私有裁剪接口变化会触发兼容性检查。

```bash
conda activate rebar-ocr
pip install -r requirements.txt
python -m unittest discover -p 'test_*.py'
```

不要将数据、模型缓存、凭据、环境目录提交到仓库。测试集使用合成图片及虚构/样例文本，不依赖业务PDF。

## 运行

将自己的输入PDF放在本地data目录（已忽略）。输出目录必须尚不存在。

```bash
# 仅筛页并生成几何预览
python batch.py --pdf data/input.pdf --out runs/preview_001 --device gpu:0

# 全流程OCR草稿
python batch.py --pdf data/input.pdf --out runs/draft_001 --device gpu:0 --extract-draft
```

打开输出目录的index.html。复核文字需查看各页ocr_draft/review.html；下载查看时需保留整个输出目录结构。

## 输出

| 文件 | 用途 |
|---|---|
| page_index.json | 所有页分类、方向尝试、错误和提取状态 |
| records_all_pages.json | 记录、重复候选、来源路径；不内嵌全部cell |
| pages/page_XXX/geometry.json | 原图到表格的变换矩阵与网格 |
| pages/page_XXX/ocr_draft/result.json | 字段、原始OCR、重试、单元格坐标、空白候选 |
| pages/page_XXX/ocr_draft/cells/ | 原始格图、OCR JSON及裁剪审计 |

注意：schema_version为v6，template_id沿用v4，因为模板几何定义未变。所有ready_for_search仍为false，规则通过不等于人工确认。

## 验证状态与限制

- 66项CPU回归测试通过；包含解析、几何、空白候选、方向坐标、重试、去重候选、禁旋转与异常恢复测试。
- 一个29页业务样例经用户AutoDL全量测试：目标4页，24条记录，12组重复候选，字段issues均为空；核心字段与V5一致。业务文件和结果不包含在仓库中。
- 上述结果不是任意厂家/版式的准确率证明。只支持当前固定表格版式，外框断裂、严重遮挡、弯曲等可能失败。
- 已知页头分类问题尚在：部分证明书别名未覆盖、方向重试选择可能受备注关键词影响；未知页必须保留复核。不能把other当作第二阶段无需处理的页面。
- 单元格适配器使用进程内临时方法替换，当前仅保证顺序调用；不要在同一进程并发执行其他OCR任务。
- 未实现自动审核放行、人工修正界面、正式记录合并及产品附件关联。

详细调试步骤：[README_V6.md](README_V6.md)。协作开发入口：[HANDOFF.md](HANDOFF.md)。
