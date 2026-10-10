# 运行代码交接

本次交付运行所需代码和说明。开发者的实验方案、结果摘要、运行登记、业务 PDF、钢筋 OCR / 匹配 / 审核 / 台账结果均保留本地，具体执行和结果核验由接收方完成。

## 能力与入口

- 本地网页支持 PDF、多文件与目录上传，显示任务进度与日志。
- 钢筋支持六行 / 十一行检验表、附件分类与 OCR、四表匹配、完整缺失候选和逐组人工捆绑。
- 台账以独立铭牌为一行，人工核对字段后导出材料台账与字段溯源 XLSX。
- 四表捆绑 CSV 和审核 JSON 可下载，JSON 可导入恢复。
- 钢梁、混凝土提供接口与禁用配置示例，实际业务接入待完成。

先读 [README](../README.md) 和 [接收方核验](ACCEPTANCE.md)。阶段输入/输出见 [完整流程](WORKFLOW.md)，操作见 [网页说明](WEB_USAGE.md)，维护入口见 [代码地图](CODE_MAP.md)，材料规则扩展见 [接入指南](MATERIALS.md)。

## 最小运行安装

已有配置好的环境中，在仓库根运行：

```bash
python -m pip install -e .
python -m material_ocr serve --port 8080 --data-dir runs/web \
  --model-cache models/paddlex_cache --review-library runs
```

浏览器打开 `http://localhost:8080`。新机器先准备 Python 3.10 或以上和对应的 Paddle 后端；GPU 参考安装命令在 README，CPU 启动增加 `--device cpu --profile complete`。首次运行需下载模型。

新运行者使用自己的 PDF 和数据目录。浏览器确认绑定同一浏览器、协议、主机和端口；迁移前下载审核 JSON，服务端备份不会自动恢复前端。没有随代码分发的已有任务或人工确认。

## 维护约定

上传工作台与审核页面分别在 `web/static/` 和 `review/`。规则在 `materials/rebar/`；网页匹配入口为 `matching.py:rematch()`，字段目录构建仍复用 `matching/catalog.py`。不要删除运行代码中的钢筋实现。

审核模板与 JS 在生成结果时复制到产物；更新代码后重启服务，旧结果基于保存证据 `replay` 到新目录。运行目录包含输入哈希、配置、日志、源码快照和状态，记录由程序自动写入，不依赖开发者的顶层实验目录。

GPU 附件默认 batch 32，每五页独立进程、逐页检查点，OOM 时 batch 6 重试未完成页。跨服务重启续跑尚未实现。是否新 OCR 以任务 `summary.json` / `experiment/metadata.json` 顶层 `new_ocr_executed` 为准。

四表确认与台账字段确认分别保存，改关联或字段版本使旧确认失效。CSV 导出四表清单，完整台账为双工作表 XLSX；自定义模板、写回 PDF / Word、任意新版式和其他材料实际填表尚待扩展。

## 交付与核验边界

当前分支 `phase2-form-matching`，具体暂存范围见 [提交说明](GITHUB_SUBMISSION.md)。本轮没有 commit / push，也没有重跑业务 PDF。研发工具、测试、模型清单和历史资料同样留在开发者本地。

接收方应核验自己的页面分类、字段与关联、候选库存变化、审核恢复、台账单位和导出内容，并保存失败日志和核验意见。原始统计包含重复来源，候选齐全不代表已完成字段确认或已测得总体准确率。
