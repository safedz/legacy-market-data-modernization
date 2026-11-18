package com.example.demo.dto;

import java.util.Map;


public record QualityReport(
        String batchId,
        String generatedAt,
        String orderBookStatus,
        long checked,
        long matched,
        long mismatched,
        double matchRate,
        double coverage,
        boolean lifecyclePass,
        long orphanEvents,
        Map<String, Long> lifecycleViolations,
        boolean overallPass) {
}
