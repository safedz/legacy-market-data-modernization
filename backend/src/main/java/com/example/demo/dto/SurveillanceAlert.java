package com.example.demo.dto;

public record SurveillanceAlert(
        long id,
        String type,
        String orderId,
        String severity,
        String description,
        String detectedAt) {
}