package com.example.demo.service;

import com.example.demo.dto.LineageStep;
import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.RejectedRecord;
import com.example.demo.dto.SurveillanceAlert;
import com.example.demo.dto.Trade;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class MarketDataService {

    private final List<Trade> trades = List.of(
            new Trade("16113575", "34200.017459", "SUBMIT", 100, 585.33, "BUY"),
            new Trade("16120456", "34200.201532", "SUBMIT", 50, 585.40, "SELL"),
            new Trade("16113575", "34200.350011", "EXECUTE", 100, 585.33, "BUY"),
            new Trade("16135792", "34201.100874", "SUBMIT", 2000, 586.10, "SELL"),
            new Trade("16135792", "34201.101230", "CANCEL", 2000, 586.10, "SELL"),
            new Trade("16140001", "34202.554000", "SUBMIT", 300, 585.90, "BUY"));

    private final List<RejectedRecord> rejected = List.of(
            new RejectedRecord(1, "16150010", "Negative price", "AAPL_messages.csv", 1042),
            new RejectedRecord(2, "16150011", "Missing order ID", "AAPL_messages.csv", 1043),
            new RejectedRecord(3, "16150099", "Invalid event type: 9", "AAPL_messages.csv", 2210));

    private final List<SurveillanceAlert> alerts = List.of(
            new SurveillanceAlert(1, "SPOOFING", "16135792", "HIGH",
                    "Large order cancelled within 1 ms of submission", "2026-10-25T09:30:01"),
            new SurveillanceAlert(2, "RAPID_CANCEL", "16140001", "MEDIUM",
                    "Repeated submit/cancel pattern detected", "2026-10-25T09:30:05"));

    public PipelineSummary getSummary() {
        long source = 10_000;
        long rejectedCount = rejected.size();
        long loaded = source - rejectedCount;
        // reconciled: source = loaded + rejected
        boolean reconciled = source == loaded + rejectedCount;
        return new PipelineSummary(source, loaded, rejectedCount, reconciled, "2026-10-25T09:00:00");
    }

    public List<RejectedRecord> getRejectedRecords() {
        return rejected;
    }

    public List<SurveillanceAlert> getAlerts() {
        return alerts;
    }

    public List<Trade> searchTrades(String orderId) {
        if (orderId == null || orderId.isBlank()) {
            return trades;
        }
        return trades.stream().filter(t -> t.orderId().equals(orderId)).toList();
    }

    public List<LineageStep> getLineage(String orderId) {
        return List.of(
                new LineageStep(1, "RAW", "Read from AAPL_messages.csv (order " + orderId + ")", "OK", "2026-10-25T09:00:00"),
                new LineageStep(2, "CLEANSE", "Duplicates and nulls removed", "OK", "2026-10-25T09:00:05"),
                new LineageStep(3, "TRANSFORM", "Converted to common format", "OK", "2026-10-25T09:00:08"),
                new LineageStep(4, "VALIDATE", "Schema and range checks passed", "OK", "2026-10-25T09:00:10"),
                new LineageStep(5, "LOAD", "Loaded into trades table", "OK", "2026-10-25T09:00:12"));
    }
}