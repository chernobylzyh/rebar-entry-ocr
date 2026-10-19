# OCR 模型切换与结果对照

当前默认 **本地 GLM-OCR（`local-glm`）**，可切换到本地缓存 **Paddle PP-OCRv5（`local-paddle`）**。

## 在界面切换

刷新 Vue 工作台，在单卷结果页展开「识别配置」，通过「识别方式」选择模型，再点击「识别整卷 PDF」。页面打开时采用服务端默认 GLM；模型选择用于下一次识别，选择本身不会重算或修改已有台账。同卷正在识别时等待任务完成后再切换。

两种模型共用当前生产流程：表格几何与物理行列、关键词提取、附件窗口及裁剪、质保书—炉批号—铭牌—送货单匹配、来源证据及异常提示均保持原规则。切换只改变读字引擎及其运行环境。Paddle 不会调用历史的另一套完整业务流程；模型出错时会明确报错，不会静默换模型。

正常使用不用勾选「强制重跑 OCR」。各模型使用独立缓存，校验 PDF、权重、推理参数及规则版本；没有有效缓存时才识别缺失内容。强制重跑会重新推理并更新当前模型的稳定缓存，历史实验结果保留。

界面展示该卷最近完成的业务台账，切换识别完成后会更新它；历史运行目录仍保留。需要同时保留两种模型用于比较时，使用下面的独立对照入口。

## 独立比较结果（开发机功能）

本节的 `tools/compare_ocr_models.py`、实验登记器、比较模块和报告保留在开发机，不包含在本次最小运行交付中。生产模型切换不依赖这些文件。开发机示例路径：`experiments/runs/run-20261019T062507Z-saved-1208-model-comparison/comparison/index.html`。本例分析历史产物，没有新执行 OCR。10 条进场物理行全部对齐，40 个字段值不同。历史配置和规则指纹分别保存在 `comparison.json`，不能把这份报告当作当前代码重新运行两种模型的结果。

工具 `tools/compare_ocr_models.py` 支持两种方式，均不写业务台账。以下命令在仓库根目录执行，`python` 指已有 `ocr` 环境解释器：

```bash
# 比较已保存结果，不执行推理；输出目录必须为空或尚不存在。
PYTHONPATH=src:. python tools/compare_ocr_models.py \
  --left /路径/GLM运行目录 \
  --right /路径/Paddle运行目录 \
  --out experiments/analyses/某次独立对照
```

左右目录需包含 `automatic_ledger.json`，也可直接传入该 JSON 路径。实际运行比较命令时按项目约定用 `experiments/record_run.py` 登记，并关联对应改动记录；上面展示工具本身的参数。

同一 PDF 按当前代码依次运行两个模型，由登记器生成独立 `run_id`：

```bash
PYTHONPATH=src:. python experiments/record_run.py \
  --change-id chg-20261019T061943Z-ocr-model-switch \
  --label glm-paddle-current-comparison \
  --input '钢筋报审文件/2025.12.6日钢筋报审表.pdf' -- \
  python tools/compare_ocr_models.py \
    --pdf '钢筋报审文件/2025.12.6日钢筋报审表.pdf' \
    --models local-glm local-paddle
```

该入口默认复用各自有效缓存，缺失时执行真实推理；加 `--force-ocr-refresh` 可明确要求两种模型重新读字。GLM 自动使用隔离解释器，Paddle 使用服务环境或配置的解释器。输出在新运行目录的 `comparison/`：

- `local-glm/`、`local-paddle/`：当前代码各自的 OCR、资源、台账及元数据。
- `comparison.json`：字段值、状态、核验标记、诊断、证据与源运行引用。
- `differences.csv`、`index.html`：便于逐行查看的差异。

只对比相同 PDF SHA256，按进场页码及物理行号对齐，身份缺失或重复歧义的行单独报告。字段非空数和差异数不表示准确率，需结合原图及人工真值判断。OCR 可能已经读出某段文字，但其换行、空格或表格格式未满足现有提取规则；应联合检查原始文本、字段和失败环节。

## 维护入口

统一配置位于 `src/material_ocr/ocr/backends.py`。`DEFAULT_OCR_MODEL` 决定默认模型，`BACKENDS` 登记模型 ID、名称、权重、解释器、引擎及缓存命名空间。

Python 的 `GET /api/library/ocr-models` 返回目录，Java 原样转发至同路径，Vue 动态加载选项和默认值。新增选项不需要分别修改三个服务的模型列表；Python/Java 代码修改后需重新构建并重启相应服务。

| 模型 | 默认权重路径 | 默认推理解释器 | 缓存 |
| --- | --- | --- | --- |
| `local-glm` | `models/GLM-OCR/` | `.venv-glm/bin/python` | `runs/web/ocr-cache/glm/` |
| `local-paddle` | `models/paddlex_cache/official_models/` | 当前服务的 Python | `runs/web/ocr-cache/paddle/` |

Paddle 默认权重路径也接受服务启动参数 `--model-cache` 指定的目录，并取其中的 `official_models/`。以下环境变量在启动 Python 服务前设置，目录指向已有权重与环境，无须复制模型：

| 模型 | 权重覆盖变量 | 解释器覆盖变量 |
| --- | --- | --- |
| GLM | `MATERIAL_OCR_GLM_MODEL_DIR` | `MATERIAL_OCR_GLM_PYTHON`（兼容 `GLM_OCR_PYTHON`） |
| Paddle | `MATERIAL_OCR_PADDLE_MODEL_DIR` | `MATERIAL_OCR_PADDLE_PYTHON` |

新增模型时实现与已有引擎一致的构造参数、`recognize(PIL.Image)` 结果契约以及模块级 `model_fingerprint(directory)`；在注册表中使用唯一 ID 和缓存命名空间。全页、表格单元格、附件窗口三种调用均通过注册表派发。保留共同业务规则，并验证默认/指定模型、缓存身份、异步任务冲突和同 PDF 对照后再加入使用。
