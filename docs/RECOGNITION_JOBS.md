# OCR任务与进度接口

当前Vue通过Java服务调用任务接口；Python OCR服务也提供同名路径，但Python响应为原始JSON，Java响应使用`{code:200,data:...}`。

- `POST /api/library/{name}/recognition`：表单提交整卷任务，Python返回202。支持`force_ocr_refresh=true`；同卷仍在排队或运行时，无论重复点击或重发提交，均返回同一`task_id`。不同卷在本地OCR队列排队，单个服务进程内串行执行。
- `GET /api/library/{name}/recognition`：查询`task_id`、`status`、`stage`、`current`、`total`、`message`、`updated_at`、`queue_position`与失败`error`。Java在完成时将台账与页面OCR同步至当前应用，再返回`local_ready:true`。
- `status`取值：`idle`、`queued`、`running`、`completed`、`failed`、`interrupted`。进程重启后的遗留任务标为`interrupted`，可重新提交，不假定旧进程已安全完成。
- `stage`实际来自管线：`starting`、`classify`、`extract`、`attachments`、`matching`、`saving`、`completed`。`current/total`是该阶段实际完成页数，分类、主表提取和附件OCR的分母不同，不将请求返回数量当作OCR完成数量。模型加载与自动匹配没有可测页数时显示不定进度。

任务期间允许上传/提交另一卷和查看当前卷状态；修改当前卷的源文件、缓存或页面仍会返回409，前端相应按钮禁用。`POST .../recognize`旧阻塞接口、首次单页OCR入口均复用相同任务，避免并发单页请求重复启动整卷。

浏览器通过Pinia保留跨路由状态，重新打开卷时GET恢复任务。POST响应丢失后只查询状态，不盲目重发耗时操作。Java按`recognition_task_id`只导入一次完成结果，反复轮询不会覆盖此后的人工修订与核验确认。上传内部标识采用时间戳加UUID，防止同秒并发上传映射到同一卷。

本地自适应进场表还需要 `paddlex[ocr]==3.3.13`（项目依赖已包含）。仅安装基础 `paddleocr` 能运行文字识别，但无法创建表格识别管线。表格使用 PP-DocLayout-L、PP-LCNet_x1_0_table_cls、SLANeXt_wired/wireless、RT-DETR-L_wired/wireless_table_cell_det 六个模型，首次使用会下载到同一个本地缓存，后续复用。提取失败会保留实际错误和原页入口，即使台账没有记录也可查看。

验证记录见`experiments/changes/chg-20261016T082121Z-recognition-queue-progress.md`。接口系统测试和前端状态测试使用合成管线/模拟网络，不能替代真实浏览器多卷GPU识别验证，也不代表OCR准确率。
