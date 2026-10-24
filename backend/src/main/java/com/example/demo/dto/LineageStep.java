package com.example.demo.dto;

public record LineageStep(
        int step,
        String stage,
        String description,
        String status,
        String timestamp) {
}