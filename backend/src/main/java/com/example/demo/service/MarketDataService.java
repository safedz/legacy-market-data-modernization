package com.example.demo.service;

import com.example.demo.dto.LineageStep;
import com.example.demo.dto.PipelineBatch;
import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.QualityReport;
import com.example.demo.dto.RejectedRecord;
import com.example.demo.dto.SurveillanceAlert;
import com.example.demo.dto.Trade;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
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

    private final Path processedDir;
    private final Path rejectedFile;
    private final JsonMapper mapper = JsonMapper.builder().build();
    private final DbMarketData db;


    public MarketDataService(@Value("${pipeline.data-dir:../data}") String dataDir,
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
            return new PipelineSummary(0, 0, 0, false, "pipeline not run yet");
        }
        try {
            JsonNode report = mapper.readTree(file.toFile());
            JsonNode stages = report.path("stages");
            long source = stages.path("ingested").path("records").asLong();
            long loaded = stages.path("valid").path("records").asLong();
            long rejectedCount = stages.path("rejected").path("records").asLong();
            boolean reconciled = report.path("reconciliation_pass").asBoolean();
            return new PipelineSummary(source, loaded, rejectedCount, reconciled,
                    report.path("validated_at").asString());
        } catch (JacksonException e) {
            throw new IllegalStateException("Cannot read " + file, e);
        }
    }

    public QualityReport getQuality() {
        Path file = processedDir.resolve("quality_report.json");
        if (!Files.exists(file)) {
            return new QualityReport("", "", "NOT_RUN", 0, 0, 0, 0, 0, false, 0, Map.of(), false);
        }
        try {
            JsonNode report = mapper.readTree(file.toFile());
            JsonNode recon = report.path("orderbook_reconciliation");
            JsonNode lifecycle = report.path("order_lifecycle");
            Map<String, Long> violations = new LinkedHashMap<>();
            JsonNode counts = lifecycle.path("violations");
            counts.propertyNames().forEach(name -> violations.put(name, counts.path(name).asLong()));
            return new QualityReport(
                    report.path("batch_id").asString(),
                    report.path("generated_at").asString(),
                    recon.path("status").asString("UNKNOWN"),
                    recon.path("checked").asLong(),
                    recon.path("matched").asLong(),
                    recon.path("mismatched").asLong(),
                    recon.path("match_rate").asDouble(),
                    recon.path("coverage").asDouble(),
                    lifecycle.path("pass").asBoolean(),
                    lifecycle.path("orphan_events").asLong(),
                    violations,
                    report.path("overall_pass").asBoolean());
        } catch (JacksonException e) {
            throw new IllegalStateException("Cannot read " + file, e);
        }
    }

    public List<RejectedRecord> getRejectedRecords() {
        if (db != null) {
            return db.getRejectedRecords();
        }
        List<RejectedRecord> result = new ArrayList<>();
        int id = 1;
        for (Map<String, String> row : readCsv(rejectedFile, null, null, MAX_ROWS)) {
            result.add(new RejectedRecord(id++,
                    wholeNumber(row.get("order_id")),
                    value(row, "reject_reason"),
                    value(row, "source_file"),
                    toInt(row.get("source_record_number"))));
        }
        return result;
    }

    public List<PipelineBatch> getBatches() {
        if (db != null) {
            return db.getBatches();
        }
        Path file = processedDir.resolve("manifest.json");
        if (!Files.exists(file)) {
            return List.of();
        }
        try {
            JsonNode manifest = mapper.readTree(file.toFile());
            Path runFile = processedDir.resolve("run_manifest.json");
            String version = Files.exists(runFile)
                    ? mapper.readTree(runFile.toFile()).path("pipeline_version").asString("")
                    : "";
            PipelineSummary summary = getSummary();
            return List.of(new PipelineBatch(
                    manifest.path("batch_id").asString(""),
                    manifest.path("source_file").asString(""),
                    manifest.path("trading_date").asString(""),
                    manifest.path("file_sha256").asString(""),
                    version,
                    manifest.path("ingested_at").asString(""),
                    manifest.path("records_ingested").asInt(),
                    (int) summary.loadedRecords(),
                    (int) summary.rejectedRecords()));
        } catch (JacksonException e) {
            throw new IllegalStateException("Cannot read " + file, e);
        }
    }

    public List<SurveillanceAlert> getAlerts() {
        return db != null ? db.getAlerts() : sampleAlerts();
    }

    private static List<SurveillanceAlert> sampleAlerts() {
        return List.of(
                new SurveillanceAlert(1, "SPOOFING", "100001", "HIGH",
                        "Large order submitted and cancelled within 2 seconds", "2012-06-21 09:30:02"),
                new SurveillanceAlert(2, "LAYERING", "100002", "HIGH",
                        "Multiple orders placed at successive price levels then removed", "2012-06-21 09:41:15"),
                new SurveillanceAlert(3, "QUOTE_STUFFING", "100003", "MEDIUM",
                        "Unusually high message rate from a single order", "2012-06-21 10:05:44"),
                new SurveillanceAlert(4, "PRICE_SPIKE", "100004", "LOW",
                        "Price moved more than 1% from the previous trade", "2012-06-21 11:12:30"));
    }

    public List<Trade> searchTrades(String orderId) {
        return searchTrades(orderId, null, null, null);
    }

    public List<Trade> searchTrades(String orderId, String eventType, String from, String to) {
        if (db != null) {
            return db.searchTrades(orderId, eventType, from, to);
        }
        String type = (eventType == null || eventType.isBlank()) ? null : eventType.trim();
        String fromText = normalizeTime(from);
        String toText = normalizeTime(to);
        boolean filtered = type != null || fromText != null || toText != null;

        boolean all = orderId == null || orderId.isBlank();
        int limit = (all && !filtered) ? MAX_ROWS : 10 * MAX_ROWS;
        List<Map<String, String>> rows = all
                ? readCsv(validatedFile(), null, null, limit)
                : readCsv(validatedFile(), "order_id", orderId.trim(), limit);

        List<Trade> result = new ArrayList<>();
        for (Map<String, String> row : rows) {
            if (type != null && !type.equals(value(row, "event_label"))) {
                continue;
            }
            String ts = value(row, "event_timestamp");
            if (fromText != null && ts.compareTo(fromText) < 0) {
                continue;
            }
            if (toText != null && ts.compareTo(toText) > 0) {
                continue;
            }
            result.add(toTrade(row));
            if (result.size() >= MAX_ROWS) {
                break;
            }
        }
        return result;
    }

    private static String normalizeTime(String text) {
        return (text == null || text.isBlank()) ? null : text.trim().replace('T', ' ');
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
        if (row == null) {
            return List.of();
        }
        return buildLineage(row);
    }

    private List<LineageStep> buildLineage(Map<String, String> row) {
        boolean valid = "VALID".equals(row.get("validation_status"));
        String status = valid ? "OK" : "REJECTED";
        String hash = value(row, "file_sha256");
        String shortHash = hash.length() > 12 ? hash.substring(0, 12) : hash;

        return List.of(
                new LineageStep(1, "INGEST",
                        "Read " + value(row, "source_file") + " row " + value(row, "source_record_number")
                                + " (batch " + value(row, "batch_id") + ", SHA-256 " + shortHash + ")",
                        "OK", value(row, "ingestion_timestamp")),
                new LineageStep(2, "TRANSFORM",
                        "Applied " + value(row, "transformations_applied")
                                + " (pipeline v" + value(row, "pipeline_version") + ")",
                        "OK", value(row, "transformed_at")),
                new LineageStep(3, "VALIDATE",
                        valid ? "Passed all validation rules" : "Rejected: " + value(row, "reject_reason"),
                        status, value(row, "validated_at")),
                new LineageStep(4, "LOAD",
                        "Written to " + value(row, "final_destination") + " zone",
                        status, value(row, "validated_at")));
    }

    private Path validatedFile() {
        return processedDir.resolve("validated_messages.csv");
    }

    private Map<String, String> firstRow(Path file, String orderId) {
        if (orderId == null || orderId.isBlank()) {
            return null;
        }
        List<Map<String, String>> rows = readCsv(file, "order_id", orderId.trim(), 1);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Trade toTrade(Map<String, String> row) {
        String side = "1".equals(wholeNumber(row.get("direction"))) ? "BUY" : "SELL";
        return new Trade(
                wholeNumber(row.get("order_id")),
                value(row, "time"),
                value(row, "event_label"),
                toInt(row.get("size")),
                Double.parseDouble(value(row, "price_dollars")),
                side);
    }

    private List<Map<String, String>> readCsv(Path file, String filterColumn, String filterValue, int limit) {
        List<Map<String, String>> rows = new ArrayList<>();
        if (!Files.exists(file)) {
            return rows;
        }
        try (BufferedReader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                return rows;
            }
            String[] header = headerLine.split(",", -1);

            int filterIndex = -1;
            if (filterColumn != null) {
                for (int i = 0; i < header.length; i++) {
                    if (header[i].equals(filterColumn)) {
                        filterIndex = i;
                    }
                }
                if (filterIndex < 0) {
                    return rows;
                }
            }

            String line;
            while (rows.size() < limit && (line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                String[] cells = line.split(",", -1);
                if (cells.length != header.length) {
                    throw new IllegalStateException("Malformed CSV row in " + file);
                }
                if (filterIndex >= 0 && !wholeNumber(cells[filterIndex]).equals(filterValue)) {
                    continue;
                }
                Map<String, String> row = new HashMap<>();
                for (int i = 0; i < header.length; i++) {
                    row.put(header[i], cells[i]);
                }
                rows.add(row);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return rows;
    }

    private static String value(Map<String, String> row, String key) {
        String v = row.get(key);
        return v == null ? "" : v;
    }

    private static String wholeNumber(String text) {
        String s = text == null ? "" : text.trim();
        return s.endsWith(".0") ? s.substring(0, s.length() - 2) : s;
    }

    private static int toInt(String text) {
        String s = wholeNumber(text);
        return s.isEmpty() ? 0 : Integer.parseInt(s);
    }
}