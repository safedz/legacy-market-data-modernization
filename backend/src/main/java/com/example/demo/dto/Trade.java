package com.example.demo.dto;

public record Trade(
        String orderId,
        String time,
        String eventType,
        int size,
        double price,
        String direction) {
}