package com.example.demo.service;

import com.example.demo.dto.LineageStep;
import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.QualityReport;
import com.example.demo.dto.RejectedRecord;
import com.example.demo.dto.SurveillanceAlert;
import com.example.demo.dto.Trade;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class MarketDataService {

    private static final int MAX_ROWS = 1000;

    private final List<Trade> trades = List.of(
            new Trade("16113575", "34200.017459", "SUBMIT", 100, 585.33, "BUY"),
            new Trade("16120456", "34200.201532", "SUBMIT", 50, 585.40, "SELL"),
            new Trade("16113575", "34200.350011", "EXECUTE", 100, 585.33, "BUY"),
            new Trade("16135792", "34201.100874", "SUBMIT", 2000, 586.10, "SELL"),
            new Trade("16135792", "34201.101230", "CANCEL", 2000, 586.10, "SELL"),
            new Trade("16140001", "34202.554000", "SUBMIT", 300, 585.90, "BUY"));

    private final List<RejectedRecord> rejected = List.of(
            new RejectedRecord(1, "16150010", "Negative price", "AAPL_messages.csv", 1042),
            new RejectedRecord(2, "16150011", "Missing order ID", "AAPL_messages.csv", 1043),
            new RejectedRecord(3, "16150099", "Invalid event type: 9", "AAPL_messages.csv", 2210));

    private final Path processedDir;
    private final Path rejectedFile;
    private final ObjectMapper mapper = new ObjectMapper();
    private final DbMarketData db;

    private final List<SurveillanceAlert> alerts = List.of(
            new SurveillanceAlert(1, "SPOOFING", "16135792", "HIGH",
                    "Large order cancelled within 1 ms of submission", "2026-10-25T09:30:01"),
            new SurveillanceAlert(2, "RAPID_CANCEL", "16140001", "MEDIUM",
                    "Repeated submit/cancel pattern detected", "2026-10-25T09:30:05"));

    public MarketDataService(
            @Value("${pipeline.data-dir:../data}") String dataDir,
            Optional<DbMarketData> db) {

        Path base = Path.of(dataDir);
        this.processedDir = base.resolve("processed");
        this.rejectedFile = base.resolve("rejected").resolve("rejected_messages.csv");
        this.db = db.orElse(null);
    }

    public PipelineSummary getSummary() {

        if (db != null) {
            return db.getSummary();
        }

        Path file = processedDir.resolve("validation_report.json");

        if (!Files.exists(file)) {
            long source = 10_000;
            long rejectedCount = rejected.size();
            long loaded = source - rejectedCount;
            boolean reconciled = source == loaded + rejectedCount;

            return new PipelineSummary(
                    source,
                    loaded,
                    rejectedCount,
                    reconciled,
                    "2026-10-25T09:00:00");
        }

        try {
            JsonNode report = mapper.readTree(file.toFile());
            JsonNode stages = report.path("stages");

            long source = stages.path("ingested").path("records").asLong();
            long loaded = stages.path("valid").path("records").asLong();
            long rejectedCount = stages.path("rejected").path("records").asLong();

            boolean reconciled =
                    report.path("reconciliation_pass").asBoolean();

            return new PipelineSummary(
                    source,
                    loaded,
                    rejectedCount,
                    reconciled,
                    report.path("validated_at").asText());

        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public QualityReport getQuality() {

        Path file = processedDir.resolve("quality_report.json");

        if (!Files.exists(file)) {
            return new QualityReport(
                    "", "", "NOT_RUN", 0, 0, 0, 0, 0,
                    false, 0, Map.of(), false);
        }

        try {
            JsonNode report = mapper.readTree(file.toFile());
            JsonNode recon = report.path("orderbook_reconciliation");
            JsonNode lifecycle = report.path("order_lifecycle");

            Map<String, Long> violations = new LinkedHashMap<>();
            JsonNode counts = lifecycle.path("violations");

            counts.fieldNames().forEachRemaining(
                    name -> violations.put(
                            name,
                            counts.path(name).asLong()));

            return new QualityReport(
                    report.path("batch_id").asText(),
                    report.path("generated_at").asText(),
                    recon.path("status").asText("UNKNOWN"),
                    recon.path("checked").asLong(),
                    recon.path("matched").asLong(),
                    recon.path("mismatched").asLong(),
                    recon.path("match_rate").asDouble(),
                    recon.path("coverage").asDouble(),
                    lifecycle.path("pass").asBoolean(),
                    lifecycle.path("orphan_events").asLong(),
                    violations,
                    report.path("overall_pass").asBoolean());

        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public List<RejectedRecord> getRejectedRecords() {

        if (db != null) {
            return db.getRejectedRecords();
        }

        if (!Files.exists(rejectedFile)) {
            return rejected;
        }

        List<RejectedRecord> result = new ArrayList<>();
        int id = 1;

        for (Map<String, String> row :
                readCsv(rejectedFile, null, null, MAX_ROWS)) {

            result.add(new RejectedRecord(
                    id++,
                    wholeNumber(row.get("order_id")),
                    value(row, "reject_reason"),
                    value(row, "source_file"),
                    toInt(row.get("source_record_number"))));
        }

        return result;
    }

    public List<SurveillanceAlert> getAlerts() {
        return db != null ? db.getAlerts() : alerts;
    }

    public List<Trade> searchTrades(String orderId) {

        if (db != null) {
            return db.searchTrades(orderId);
        }

        Path file = validatedFile();

        
        if (Files.exists(file)) {

            boolean all = orderId == null || orderId.isBlank();

            List<Map<String, String>> rows = all
                    ? readCsv(file, null, null, MAX_ROWS)
                    : readCsv(
                            file,
                            "order_id",
                            orderId.trim(),
                            10 * MAX_ROWS);

            List<Trade> result = new ArrayList<>();

            for (Map<String, String> row : rows) {
                result.add(toTrade(row));
            }

            return result;
        }

        if (orderId == null || orderId.isBlank()) {
            return trades;
        }

        return trades.stream()
                .filter(t -> t.orderId().equals(orderId))
                .toList();
    }

    public List<LineageStep> getLineage(String orderId) {

        Map<String, String> row;

        if (db != null) {
            row = db.lineageRow(orderId);
        } else {
            row = firstRow(validatedFile(), orderId);

            if (row == null) {
                row = firstRow(rejectedFile, orderId);
            }
        }

      
        if (row != null) {
            return buildLineage(row);
        }

       
        if (db == null &&
                (orderId == null || orderId.isBlank()
                        || trades.stream()
                        .anyMatch(t -> t.orderId().equals(orderId)))) {

            return List.of(
                    new LineageStep(
                            1,
                            "RAW",
                            "Read from AAPL_messages.csv (order " + orderId + ")",
                            "OK",
                            "2026-10-25T09:00:00"),

                    new LineageStep(
                            2,
                            "CLEANSE",
                            "Duplicates and nulls removed",
                            "OK",
                            "2026-10-25T09:00:05"),

                    new LineageStep(
                            3,
                            "TRANSFORM",
                            "Converted to common format",
                            "OK",
                            "2026-10-25T09:00:08"),

                    new LineageStep(
                            4,
                            "VALIDATE",
                            "Schema and range checks passed",
                            "OK",
                            "2026-10-25T09:00:10"),

                    new LineageStep(
                            5,
                            "LOAD",
                            "Loaded into trades table",
                            "OK",
                            "2026-10-25T09:00:12"));
        }

        return List.of();
    }

    private List<LineageStep> buildLineage(
            Map<String, String> row) {

        boolean valid =
                "VALID".equals(row.get("validation_status"));

        String status =
                valid ? "OK" : "REJECTED";

        String hash =
                value(row, "file_sha256");

        String shortHash =
                hash.length() > 12
                        ? hash.substring(0, 12)
                        : hash;

        return List.of(
                new LineageStep(
                        1,
                        "INGEST",
                        "Read " + value(row, "source_file")
                                + " row "
                                + value(row, "source_record_number")
                                + " (batch "
                                + value(row, "batch_id")
                                + ", SHA-256 "
                                + shortHash
                                + ")",
                        "OK",
                        value(row, "ingestion_timestamp")),

                new LineageStep(
                        2,
                        "TRANSFORM",
                        "Applied "
                                + value(row, "transformations_applied")
                                + " (pipeline v"
                                + value(row, "pipeline_version")
                                + ")",
                        "OK",
                        value(row, "transformed_at")),

                new LineageStep(
                        3,
                        "VALIDATE",
                        valid
                                ? "Passed all validation rules"
                                : "Rejected: "
                                + value(row, "reject_reason"),
                        status,
                        value(row, "validated_at")),

                new LineageStep(
                        4,
                        "LOAD",
                        "Written to "
                                + value(row, "final_destination")
                                + " zone",
                        status,
                        value(row, "validated_at")));
    }

    private Path validatedFile() {
        return processedDir.resolve("validated_messages.csv");
    }

    private Map<String, String> firstRow(
            Path file,
            String orderId) {

        if (orderId == null || orderId.isBlank()) {
            return null;
        }

        List<Map<String, String>> rows =
                readCsv(
                        file,
                        "order_id",
                        orderId.trim(),
                        1);

        return rows.isEmpty()
                ? null
                : rows.get(0);
    }

    private Trade toTrade(
            Map<String, String> row) {

        String side =
                "1".equals(
                        wholeNumber(row.get("direction")))
                        ? "BUY"
                        : "SELL";

        return new Trade(
                wholeNumber(row.get("order_id")),
                value(row, "time"),
                value(row, "event_label"),
                toInt(row.get("size")),
                Double.parseDouble(
                        value(row, "price_dollars")),
                side);
    }

    private List<Map<String, String>> readCsv(
            Path file,
            String filterColumn,
            String filterValue,
            int limit) {

        List<Map<String, String>> rows =
                new ArrayList<>();

        if (!Files.exists(file)) {
            return rows;
        }

        try (BufferedReader reader =
                     Files.newBufferedReader(
                             file,
                             StandardCharsets.UTF_8)) {

            String headerLine =
                    reader.readLine();

            if (headerLine == null) {
                return rows;
            }

            String[] header =
                    headerLine.split(",", -1);

            int filterIndex = -1;

            if (filterColumn != null) {

                for (int i = 0;
                     i < header.length;
                     i++) {

                    if (header[i].equals(filterColumn)) {
                        filterIndex = i;
                        break;
                    }
                }

                if (filterIndex < 0) {
                    return rows;
                }
            }

            String line;

            while (rows.size() < limit
                    && (line = reader.readLine()) != null) {

                if (line.isBlank()) {
                    continue;
                }

                String[] cells =
                        line.split(",", -1);

                if (cells.length != header.length) {
                    throw new IllegalStateException(
                            "Malformed CSV row in " + file);
                }

                if (filterIndex >= 0
                        && !wholeNumber(
                                cells[filterIndex])
                        .equals(filterValue)) {

                    continue;
                }

                Map<String, String> row =
                        new HashMap<>();

                for (int i = 0;
                     i < header.length;
                     i++) {

                    row.put(
                            header[i],
                            cells[i]);
                }

                rows.add(row);
            }

        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }

        return rows;
    }

    private static String value(
            Map<String, String> row,
            String key) {

        String v = row.get(key);

        return v == null ? "" : v;
    }

    private static String wholeNumber(
            String text) {

        String s =
                text == null
                        ? ""
                        : text.trim();

        return s.endsWith(".0")
                ? s.substring(
                        0,
                        s.length() - 2)
                : s;
    }

    private static int toInt(
            String text) {

        String s =
                wholeNumber(text);

        return s.isEmpty()
                ? 0
                : Integer.parseInt(s);
    }
}