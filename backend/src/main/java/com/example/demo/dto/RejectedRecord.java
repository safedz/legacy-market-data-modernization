
    package com.example.demo.dto;

public record RejectedRecord(
        long id,
        String orderId,
        String reason,
        String sourceFile,
        int lineNumber) {
}
