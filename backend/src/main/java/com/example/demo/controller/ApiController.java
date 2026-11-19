package com.example.demo.controller;

import com.example.demo.dto.LineageStep;
import com.example.demo.dto.PipelineBatch;
import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.QualityReport;
import com.example.demo.dto.RejectedRecord;
import com.example.demo.dto.SurveillanceAlert;
import com.example.demo.dto.Trade;
import com.example.demo.service.MarketDataService;
import jakarta.validation.constraints.Pattern;
import java.util.List;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Validated
@RestController
@RequestMapping("/api")
public class ApiController {

    private final MarketDataService service;

    public ApiController(MarketDataService service) {
        this.service = service;
    }

    @GetMapping("/pipeline/summary")
    public PipelineSummary summary() {
        return service.getSummary();
    }

    @GetMapping("/pipeline/batches")
    public List<PipelineBatch> batches() {
        return service.getBatches();
    }

    @GetMapping("/quality")
    public QualityReport quality() {
        return service.getQuality();
    }

    @GetMapping("/rejected-records")
    public List<RejectedRecord> rejectedRecords() {
        return service.getRejectedRecords();
    }

    @GetMapping("/lineage/{orderId}")
    public List<LineageStep> lineage(
            @PathVariable @Pattern(regexp = "\\d{1,20}", message = "orderId must be numeric") String orderId) {
        return service.getLineage(orderId);
    }

    @GetMapping("/surveillance/alerts")
    public List<SurveillanceAlert> alerts() {
        return service.getAlerts();
    }

    @GetMapping("/trades")
    public List<Trade> trades(
            @RequestParam(required = false) @Pattern(regexp = "\\d{0,20}", message = "orderId must be numeric") String orderId,
            @RequestParam(required = false) @Pattern(regexp = "[A-Z_]{0,30}", message = "invalid eventType") String eventType,
            @RequestParam(required = false) @Pattern(regexp = "(\\d{4}-\\d{2}-\\d{2}([T ]\\d{2}:\\d{2}(:\\d{2})?)?)?", message = "from must look like 2012-06-21T09:30") String from,
            @RequestParam(required = false) @Pattern(regexp = "(\\d{4}-\\d{2}-\\d{2}([T ]\\d{2}:\\d{2}(:\\d{2})?)?)?", message = "to must look like 2012-06-21T10:00") String to) {
        return service.searchTrades(orderId, eventType, from, to);
    }
}