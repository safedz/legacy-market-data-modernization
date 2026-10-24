package com.example.demo.dto;

public record PipelineSummary(
        long sourceRecords,
        long loadedRecords,
        long rejectedRecords,
        boolean reconciled,
        String lastRun) {
}