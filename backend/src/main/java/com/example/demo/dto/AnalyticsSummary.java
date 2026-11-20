package com.example.demo.dto;

import java.util.List;


public record AnalyticsSummary(
        long totalRecords,
        double avgPrice,
        double minPrice,
        double maxPrice,
        double avgOrderSize,
        long largestOrder,
        long duplicateRows,
        List<EventCount> eventCounts,
        List<Bucket> priceBuckets,
        List<Bucket> sizeBuckets) {

    public record EventCount(String event, long count) {}


    public record Bucket(String label, String range, long count) {}
}
