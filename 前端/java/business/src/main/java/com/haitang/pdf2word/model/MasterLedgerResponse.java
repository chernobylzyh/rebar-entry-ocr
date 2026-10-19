package com.haitang.pdf2word.model;

import lombok.Data;
import java.util.List;

/**
 * 总台账响应：所有已识别 PDF 的台账字段聚合视图。
 * 行 = 一个 PDF，列 = 固定的 11 个监理字段。
 */
@Data
public class MasterLedgerResponse {
    private List<String> columns;
    private List<MasterLedgerRow> rows;
    private boolean empty;
    private String revision;
    private Object diagnostics;
}
