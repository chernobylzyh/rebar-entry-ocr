# 自动匹配与最终台账核验（2026-10-15）

本说明描述当前自动匹配和最终字段核验流程。当前界面以 `前端/vue` 为准，Java 管理最终补正、确认和导出，Python 管理本地 OCR、自动关联与不可变的来源证据。

## 关联规则

|进场记录关键词|自动流程|失败处理|
|---|---|---|
|存在质量证明书编号|精确编号检索质证书 → 炉批号关联铭牌 → 规格和数量关联送货物理行|编号错误不悄悄改走规格路径，保留编号及链缺失原因|
|缺少质量证明书编号|同一独立铭牌内同时匹配牌号与直径 → 关联送货物理行 → 用该铭牌炉批号检索质证书|缺少任一关键词、多个铭牌、多个质证书或多个送货行时保留候选，不任意选择|

页码相邻或同页不足以证明对应关系。数量只能在满足规格条件的送货物理行中辅助消歧；清晰数量矛盾保留双方来源。不同铭牌即使炉批号相同也保留独立 ID。同一铭牌被多条进场记录命中时提示重复或资源冲突，不合计数量。

所有进场记录都生成最终可编辑行；匹配不足不会中断或要求人工捆绑。没有可靠证据的字段留空。存在多个不同 OCR 值时保留全部候选、原文和位置。

## 多铭牌登记

先利用牌号锚点、公司标题与列间空白确定独立区域，轮廓检测作为补充，再对每个区域单独运行 OCR。区域边界、裁剪图片、独立实体 ID 和原图多边形全部保存。全页 OCR 保留作证据，但已经拆出的铭牌不再使用全页字段池进行匹配；独立区域内缺少生产单位时也不借用旁边铭牌的公司名称。

规格和牌号必须从同一实体读取；炉批号或规格不唯一时保留异常。任意粘贴、遮挡或重叠版式可能使区域边界不明确；此时应在最终核验看到缺失或歧义，不能通过跨卡拼字段提高表面覆盖率。

## 诊断与位置

`automatic_ledger.records` 含 `fields`、`match_route`、`match_status`、`diagnostics`、`match_candidates` 和 `sources`。典型诊断有 `missing_keyword`、`unclear_ocr`、`conflicting_values`、`duplicate_resource`、`multiple_match_candidates`、`specification_mismatch_candidates`。

位置包含 `page_no`（从 1 开始）、`polygon_page`（原 PDF 渲染图左上角像素轴）、`source_pixel_size` 和必要的 `render_dpi`。首页固定模板使用 300 DPI，附件通常 180 DPI；接口按实际显示尺寸和用户旋转换算坐标。没有可靠文字框时退回来源页定位，不虚构关键词坐标。原始 PDF 和裁剪图均保存在运行目录。

页面 OCR 的台账框提供明确 `records[i].字段` 路径。同页同值不会通过文字模糊匹配定位到另一个铭牌。诊断和候选按钮按各自证据定位。

## 当前接口

Python（8000）返回原始 JSON，Java（8080）包装为 `{code,data,msg}`，Vue 请求 Java：

- `POST /api/pdf/to_images`：PDF 渲染；支持当前前端发送的 PNG/png。
- `POST /api/library/upload`、`GET /api/library`：库管理。
- `POST /api/library/{name}/recognize`、`GET /ledger`：整卷 OCR 和自动台账。
- `GET|POST /api/library/{name}/pages/{page}/ocr`、`GET .../image`：图像和带路径的证据框。
- `POST .../pages/{page}/rotate`：Python 使用逆时针角度，Java 将本地顺时针角度转换后传入。
- `POST /api/library/{name}/resplit`、`POST .../cache`：同步清理提取或台账缓存。仅清台账后复用已有提取并重新匹配；强制刷新重新运行 OCR。
- Java `PATCH /api/library/{name}/ledger/field`：最终补正，保留原值、证据和诊断，使原核验失效。
- Java `POST .../ledger/review`：校验版本和关键必填字段后确认最终核验；`GET .../export`：未确认禁止导出。总台账导出同样检查各卷确认状态。

Java 当前单次上传限制为 50 MB；Python 层上限为 256 MB。前端部署应使用 Java 入口。

## 使用与交付边界

当前自动台账用于钢筋流程。结果中的关联状态表示来源链的情况，不能代替字段准确性核验。缺失、冲突、重复和歧义均应对照原图处理；不通过猜测编号、跨铭牌拼接字段或合并重复数量来补齐台账。

接口和规则说明随源码交付。具体 PDF、页面图、OCR 索引、模型缓存、台账结果和实验记录均为本地数据，不随仓库分发。环境准备见 [README](../README.md)，接收方操作见 [核验说明](ACCEPTANCE.md)。
