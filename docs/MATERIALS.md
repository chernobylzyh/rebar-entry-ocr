# 新材料接入

基类在src/material_ocr/materials/base.py，三个接口分别负责提取、匹配和统计。其他材料不自动继承钢筋吨数/直径/炉号业务规则。

```python
from material_ocr.materials.base import MaterialAdapter, MaterialInfo

class SteelBeamAdapter(MaterialAdapter):
    info = MaterialInfo('steel_beam', '钢梁', True,
                        '截面、长度/重量与炉号匹配', ('auto',))

    def extract(self, pdf, output, options, progress):
        # 写原记录和坐标，返回ExtractedDocuments
        raise NotImplementedError

    def match(self, pdf, documents, output):
        # 写output/index.html和机器结果，返回entries及metrics
        raise NotImplementedError

    def statistics(self, result):
        # 按自己的单位、缺失/重复策略统计
        raise NotImplementedError
```

这是接口骨架，未实现方法不能启用。完整实现可参考 `src/material_ocr/materials/rebar/adapter.py`；`materials/examples/` 中的钢梁/混凝土 JSON 是禁用设计示例，配置本身不能替代真实提取和匹配实现。

项目内注册：在MaterialRegistry初始化中self.register(YourAdapter())。独立插件安装包可声明：

```toml
[project.entry-points."material_ocr.materials"]
steel_beam = "your_package.adapter:SteelBeamAdapter"
```

info.layouts动态成为网页版式选项，CLI的--layout也传给适配器。配置、模板和关键参数纳入fingerprint()，避免缓存规则串用。使用当前四表结果结构时可复用review.render；角色不同则提供自己生成的index.html。网页仅依赖审核入口、summary和statistics。

extract使用新输出目录，options包含device、profile、dpi、inspection_layout；progress(stage,current,total,message)只报告可观测进度。失败保留证据。match必须核对input/index/records的PDF校验；返回metrics建议包含record_count、complete_candidate_records、review_task_count。冲突和重复候选继续复核，原字段不覆盖。statistics说明单位、缺失、重复来源，不能把含重复来源的累计观察当实际进场总量。

form_writer()默认None。实现材料自己的ApprovedFormWriter.preview(result, review_state)与write(approved_records, template, output)即可接入网页预览和导出。钢筋已有RebarLedgerWriter：服务器从候选ID重建四表、字段确认签名绑定关联与提取版本、缺失/歧义通过字段补正、Excel附字段溯源；未接入材料仍返回None。钢筋的filling_profile和列定义位于materials/rebar/filling.py，其他材料需要独立设计来源范围、单位、必填项和目标模板。

钢筋config/material.json声明6/11行模板顺序、附件规则、0.90置信阈值和统计单位。字段别名/裁剪在attachment_rules.json，几何在inspection_6_rows/11_rows.json。自动模板选择只接受几何通过结果，失败尝试保留。接新材料前建立实验方案、基线和验收，添加规则边界/保存OCR对照/真实完整运行，没有实际验证就不声明支持。
