package com.example.demo.dto;

public record PipelineBatch(
        String batchId,
        String sourceFile,
        String tradingDate,
        String fileSha256,
        String pipelineVersion,
        String ingestionTimestamp,
        Integer sourceRecords,
        Integer loadedRecords,
        Integer rejectedRecords) {
}
