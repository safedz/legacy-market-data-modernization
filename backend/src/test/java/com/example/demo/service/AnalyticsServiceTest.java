package com.example.demo.service;

import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;

import com.example.demo.dto.AnalyticsSummary;

class AnalyticsServiceTest {

    @TempDir
    Path dir;

    private Path writeParquet() throws Exception {
        Path file = dir.resolve("validated_messages.parquet");
        String path = file.toAbsolutePath().toString().replace("\\", "/").replace("'", "''");
        try (Connection c = DriverManager.getConnection("jdbc:duckdb:");
             Statement s = c.createStatement()) {
            s.execute("COPY (SELECT * FROM (VALUES "
                    + "(100.0, 10, 'SUBMIT', false), "
                    + "(110.0, 100, 'SUBMIT', false), "
                    + "(120.0, 1000, 'DELETE', true), "
                    + "(130.0, 15000, 'EXECUTE_VISIBLE', false)) "
                    + "AS t(price_dollars, size, event_label, is_duplicate)) "
                    + "TO '" + path + "' (FORMAT PARQUET)");
        }
        return file;
    }

    @Test
    void headlineNumbersMatchTheData() throws Exception {
        AnalyticsSummary a = new AnalyticsService(writeParquet().toString()).getSummary();
        assertEquals(4, a.totalRecords());
        assertEquals(115.0, a.avgPrice(), 1e-9);
        assertEquals(100.0, a.minPrice(), 1e-9);
        assertEquals(130.0, a.maxPrice(), 1e-9);
        assertEquals(4027.5, a.avgOrderSize(), 1e-9);
        assertEquals(15000, a.largestOrder());
        assertEquals(1, a.duplicateRows());
    }

    @Test
    void eventCountsAreSortedByCountThenName() throws Exception {
        AnalyticsSummary a = new AnalyticsService(writeParquet().toString()).getSummary();
        assertEquals(3, a.eventCounts().size());
        assertEquals("SUBMIT", a.eventCounts().get(0).event());
        assertEquals(2, a.eventCounts().get(0).count());
        assertEquals("DELETE", a.eventCounts().get(1).event());
    }

    @Test
    void priceBucketsCoverEveryRecord() throws Exception {
        AnalyticsSummary a = new AnalyticsService(writeParquet().toString()).getSummary();
        assertEquals(10, a.priceBuckets().size());
        assertEquals(4, a.priceBuckets().stream().mapToLong(AnalyticsSummary.Bucket::count).sum());
        assertEquals(1, a.priceBuckets().get(0).count());
        assertEquals(1, a.priceBuckets().get(9).count()); // the maximum price lands in the last bucket
    }

    @Test
    void sizeBucketsUseFixedRanges() throws Exception {
        AnalyticsSummary a = new AnalyticsService(writeParquet().toString()).getSummary();
        long[] expected = {1, 0, 1, 0, 0, 2};
        assertEquals(expected.length, a.sizeBuckets().size());
        for (int i = 0; i < expected.length; i++) {
            assertEquals(expected[i], a.sizeBuckets().get(i).count(), "bucket " + i);
        }
    }

    @Test
    void missingLakeFileGivesServiceUnavailable() {
        AnalyticsService service = new AnalyticsService(dir.resolve("nope.parquet").toString());
        ResponseStatusException e = assertThrows(ResponseStatusException.class, service::getSummary);
        assertEquals(503, e.getStatusCode().value());
    }
}
