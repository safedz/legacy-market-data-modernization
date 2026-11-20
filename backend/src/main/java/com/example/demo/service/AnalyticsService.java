package com.example.demo.service;

import com.example.demo.dto.AnalyticsSummary;
import com.example.demo.dto.AnalyticsSummary.Bucket;
import com.example.demo.dto.AnalyticsSummary.EventCount;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;


@Service
public class AnalyticsService {

    private static final int PRICE_BUCKETS = 10;
    
    private static final long[] SIZE_EDGES = {50, 100, 200, 500, 1000};
    private static final String[] SIZE_LABELS = {"1-49", "50-99", "100-199", "200-499", "500-999", "1,000+"};
    private static final String[] SIZE_RANGES = {
        "1 to 49 shares", "50 to 99 shares", "100 to 199 shares",
        "200 to 499 shares", "500 to 999 shares", "1,000 shares or more"};

    private final Path curatedFile;

    public AnalyticsService(
            @Value("${lake.curated-file:../data/lake/curated/validated_messages.parquet}") String curatedFile) {
        this.curatedFile = Path.of(curatedFile);
    }

    public AnalyticsSummary getSummary() {
        if (!Files.exists(curatedFile)) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Data lake not available yet. Run the pipeline first.");
        }
        String parquet = sqlPath();
        try (Connection c = DriverManager.getConnection("jdbc:duckdb:");
             Statement s = c.createStatement()) {

            long total;
            double avgPrice;
            double minPrice;
            double maxPrice;
            double avgSize;
            long maxSize;
            long duplicates;
            try (ResultSet rs = s.executeQuery(
                    "SELECT count(*), avg(price_dollars), min(price_dollars), max(price_dollars), "
                            + "avg(size), max(size), count(*) FILTER (WHERE is_duplicate) "
                            + "FROM read_parquet('" + parquet + "')")) {
                rs.next();
                total = rs.getLong(1);
                avgPrice = rs.getDouble(2);
                minPrice = rs.getDouble(3);
                maxPrice = rs.getDouble(4);
                avgSize = rs.getDouble(5);
                maxSize = rs.getLong(6);
                duplicates = rs.getLong(7);
            }

            List<EventCount> events = new ArrayList<>();
            try (ResultSet rs = s.executeQuery(
                    "SELECT event_label, count(*) FROM read_parquet('" + parquet + "') "
                            + "GROUP BY 1 ORDER BY 2 DESC, 1")) {
                while (rs.next()) {
                    events.add(new EventCount(rs.getString(1), rs.getLong(2)));
                }
            }

            return new AnalyticsSummary(total, round4(avgPrice), minPrice, maxPrice, round4(avgSize),
                    maxSize, duplicates, events,
                    priceBuckets(s, parquet, total, minPrice, maxPrice),
                    sizeBuckets(s, parquet));
        } catch (SQLException e) {
            throw new IllegalStateException("DuckDB analytics query failed", e);
        }
    }

    private static List<Bucket> priceBuckets(Statement s, String parquet, long total,
                                             double min, double max) throws SQLException {
        List<Bucket> buckets = new ArrayList<>();
        if (total == 0) {
            return buckets;
        }
        double width = (max - min) / PRICE_BUCKETS;
        if (width <= 0) {
            buckets.add(new Bucket(fmt(min, 1), "$" + fmt(min, 2), total));
            return buckets;
        }
        long[] counts = new long[PRICE_BUCKETS];
        String sql = String.format(Locale.ROOT,
                "SELECT CAST(least(floor((price_dollars - %.6f) / %.6f), %d) AS INTEGER), count(*) "
                        + "FROM read_parquet('%s') GROUP BY 1 ORDER BY 1",
                min, width, PRICE_BUCKETS - 1, parquet);
        try (ResultSet rs = s.executeQuery(sql)) {
            while (rs.next()) {
                counts[rs.getInt(1)] = rs.getLong(2);
            }
        }
        for (int i = 0; i < PRICE_BUCKETS; i++) {
            double from = min + i * width;
            double to = (i == PRICE_BUCKETS - 1) ? max : from + width;
            buckets.add(new Bucket(fmt(from, 1), "$" + fmt(from, 2) + " to $" + fmt(to, 2), counts[i]));
        }
        return buckets;
    }

    private static List<Bucket> sizeBuckets(Statement s, String parquet) throws SQLException {
        StringBuilder cases = new StringBuilder("CASE");
        for (int i = 0; i < SIZE_EDGES.length; i++) {
            cases.append(" WHEN size < ").append(SIZE_EDGES[i]).append(" THEN ").append(i);
        }
        cases.append(" ELSE ").append(SIZE_EDGES.length).append(" END");
        long[] counts = new long[SIZE_LABELS.length];
        try (ResultSet rs = s.executeQuery("SELECT " + cases + ", count(*) FROM read_parquet('"
                + parquet + "') GROUP BY 1 ORDER BY 1")) {
            while (rs.next()) {
                counts[rs.getInt(1)] = rs.getLong(2);
            }
        }
        List<Bucket> buckets = new ArrayList<>();
        for (int i = 0; i < SIZE_LABELS.length; i++) {
            buckets.add(new Bucket(SIZE_LABELS[i], SIZE_RANGES[i], counts[i]));
        }
        return buckets;
    }

    private static String fmt(double value, int digits) {
        return String.format(Locale.ROOT, "%." + digits + "f", value);
    }

    private static double round4(double value) {
        return Math.round(value * 10000.0) / 10000.0;
    }

    private String sqlPath() {
        return curatedFile.toAbsolutePath().normalize().toString()
                .replace("\\", "/").replace("'", "''");
    }
}
