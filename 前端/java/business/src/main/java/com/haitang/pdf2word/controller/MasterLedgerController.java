package com.haitang.pdf2word.controller;

import com.haitang.pdf2word.model.MasterLedgerResponse;
import com.haitang.pdf2word.other.ApiResponse;
import com.haitang.pdf2word.service.LibraryService;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 总台账 REST 端点：聚合所有已识别 PDF 的 ledger 字段。
 */
@RestController
@RequestMapping("/api/master-ledger")
@RequiredArgsConstructor
public class MasterLedgerController {

    private final LibraryService libraryService;

    @GetMapping
    public Map<String, Object> master() {
        MasterLedgerResponse data = libraryService.getMasterLedger();
        return ApiResponse.ok(data);
    }

    /**
     * 清空所有 PDF 的台账（保留 OCR 缓存与图片）。
     */
    @DeleteMapping("/cache")
    public Map<String, Object> clearAll() {
        return ApiResponse.ok(libraryService.clearAllLedgers());
    }

    /**
     * 导出总台账。format=xlsx|csv，缺省 xlsx。
     * /api/master-ledger/export?format=xlsx
     */
    @GetMapping("/export")
    public ResponseEntity<Resource> export(@RequestParam(value = "format", defaultValue = "xlsx") String format) {
        String fmt = format == null || format.isEmpty() ? "xlsx" : format.toLowerCase();
        byte[] body = libraryService.exportMasterLedger(fmt);
        String filename = "master-ledger-" + System.currentTimeMillis() + "." + fmt;
        MediaType mt;
        if ("csv".equals(fmt)) {
            mt = MediaType.parseMediaType("text/csv");
        } else if ("xlsx".equals(fmt)) {
            mt = MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        } else {
            mt = MediaType.APPLICATION_OCTET_STREAM;
        }
        ByteArrayResource resource = new ByteArrayResource(body);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .header(HttpHeaders.CONTENT_TYPE, mt.toString())
                .contentLength(body.length)
                .body(resource);
    }
}
